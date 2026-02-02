# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Multi-Agent Team

This repository uses multiple AI agents with specialized focuses:
- **CLAUDE.md** (this file): Technical architecture, implementation patterns, and deep-dive into critical flows
- **AGENTS.md** (Codex): Process guidelines, commit standards, testing workflows, and coding conventions
- **GEMINI.md** (Gemini): Current state tracking, quick command reference, and contextual memory
- **KIMI** (New): Fast code review and analysis tasks
- **AMP** (Trial): Substitute Architect during evaluation period. See `AMP_INSTRUCTIONS.md`

When making changes, ensure consistency across all memory files. Each agent brings unique value:
- Use **AGENTS.md** for procedural questions (how to test, commit format, style guide)
- Use **GEMINI.md** for current state (what's implemented, what's pending, quick commands)
- Use **CLAUDE.md** for technical questions (how auth works, why signature_type matters, bot architecture)
- Use **KIMI** for quick code reviews and analysis tasks

## Inter-Agent Communication (Pair Programming)

The AI agents can communicate programmatically via their CLI tools in non-interactive mode:

| Agent | Model | CLI Command | Non-Interactive Mode |
|-------|-------|-------------|---------------------|
| **Claude** | Opus 4.5 | `claude` | Already in session (this agent) |
| **Codex** | GPT-5.2 | `codex` | `codex exec "prompt" --full-auto` |
| **Gemini** | Gemini | `gemini` | `gemini -p "prompt" -o text` |
| **Kimi** | Moonshot | `kimi` | `kimi -p "prompt" --quiet -y` |
| **AMP** | - | `amp` | `amp -x "prompt"` (requires credits) |

### How to Communicate with Other Agents

**To Codex** (code review, refactoring, process questions):
```bash
codex exec "Your message here" --full-auto
# With output to file:
codex exec "Review market_scanner.py" --full-auto -o /tmp/codex_response.txt
```

**To Gemini** (state queries, context, quick tasks):
```bash
gemini -p "Your message here" -o text
# With auto-approval for actions:
gemini -p "Check project status" -o text -y
```

**To Kimi** (quick code analysis, reviews):
```bash
kimi -p "Your message here" --quiet -y
# Alternative with full output:
kimi -p "Review this function" --print -y
```

### Coordination Patterns
1. **Task Delegation**: Send specific, actionable prompts to other agents
2. **Code Review**: Ask Codex to review changes before committing
3. **State Sync**: Query Gemini for current project status
4. **Parallel Work**: Assign independent tasks to different agents
5. **Memory Updates**: Each agent updates its own memory file after significant work

### Best Practices
- Keep prompts clear and specific
- Include context when needed (file paths, task requirements)
- Update all three memory files when making cross-cutting changes
- Use `--full-auto` (Codex) or `-y` (Gemini) for automated workflows
- Document collaboration outcomes in CHANGELOG.md

## Project Overview

Polymarket trading client and autonomous bot written in Python. The project enables trading on Polymarket via API using the `py-clob-client` library, supporting both Magic Link (email/Gmail) and MetaMask authentication methods.

## Recent Implementation Notes (2026-02-02)
- **Position metadata**: `Position` now stores `question` and persists it to `data/positions.json` (see `bot/position_manager.py`).
- **Logging context**: `main_bot.py` uses `_format_label()` to include market names in open/close/TP/SL logs.
- **Telegram bot**:
  - `/positions` shows market names, entry price, current best bid, and PnL.
  - Market names are resolved via orderbook `condition_id` → Gamma `/markets?condition_id=...` → CLOB `get_market` fallback; cached in `data/market_cache.json`.
  - `/balance` shows raw + normalized USDC with unit heuristic.
- **Ops scripts**:
  - `scripts/start_telegram_bot.sh` uses venv Python if present and installs `requirements.txt` when deps are missing.
  - `scripts/restart_bot.sh` stops any running Telegram bots before restart to avoid duplicates.

## Core Architecture

### Authentication Flow

The client uses a two-tier authentication system:

1. **Wallet Authentication**: Private key + optional funder address (for Magic Link users)
2. **API Credentials**: Generated via `generate_user_api_keys.py` using `create_or_derive_api_creds()`

**Critical: Signature Types**
- `signature_type=1`: Magic Link (Gmail/email login) - most common
- `signature_type=0`: EOA wallets (MetaMask, hardware wallets)
- `signature_type=2`: Browser wallet proxy (rarely used)

The signature type is auto-detected in `poly_client.py:74` based on presence of `POLY_FUNDER_ADDRESS`.

### Key Components

1. **poly_client.py**: Main CLI client for market exploration, balance checks, and orderbook monitoring
   - Supports filtering markets (`--filter`), orderbook viewing (`--book`), and real-time monitoring (`--monitor`)
   - Uses `ClobClient` with automatic signature type detection

2. **place_order.py**: Manual order placement script
   - Configure `TOKEN_ID`, `PRICE`, and `SIZE` directly in the file
   - Currently uses `signature_type=2` hardcoded (line 42) - should match your auth method

3. **auto_sell.py**: Automated sell bot with safety protections
   - Implements take-profit/stop-loss monitoring
   - Requires manual confirmation by default (`REQUIRE_CONFIRMATION = True`)
   - Enforces minimum acceptable price (`MIN_ACCEPTABLE`) to prevent panic sells

4. **scripts/generate_user_api_keys.py**: Generates or retrieves API credentials
   - Must be run whenever credentials expire or are invalid
   - Derives wallet address for EOA users automatically

### Planned Architecture (Autonomous Bot)

Located in `docs/bot_plan.md` (526 lines, production-ready design), the autonomous bot implements:

**Market Selection** (all filters must pass):
- Odds: 0.30-0.70 (uncertain markets)
- Spread: <5% (critical for small trades)
- Volume: >$100 both sides
- Resolution timeframe: <30 days (avoid capital lockup)
- Weighted scoring algorithm for ranking candidates

**Position Management**:
- Persistent storage via `positions.json`, `blacklist.json`, `stats.json`
- Dynamic TP/SL based on entry odds (8-25% targets)
- Temporal blacklist (3 days, max 2 attempts per market)
- Partial fill handling
- Real balance verification each loop

**Risk Management** (10 protections):
- Capital: $5 safety reserve, $0.25-$1.00 per trade (phased)
- Daily loss limit: $3
- Max 5 concurrent positions
- 5-minute cooldown between trades
- Rate limiting: 20 API calls/min
- Dry run mode for testing

**Stats Tracking**:
- Win rate, profit factor, Sharpe ratio
- P&L by odds range
- Daily dashboard with performance metrics
- Fee tracking (integrated into TP/SL calculations)

**Deployment Phases**:
1. Dry run (7+ days simulation)
2. Paper trading (1 week analysis)
3. Micro trading ($0.25, 20-30 trades)
4. Normal trading ($1.00, gradual scaling)
5. VPS deployment (after 2+ weeks stable)

**Main Loop** (120-300s interval):
1. Load positions + verify balance
2. Scan open positions → execute TP/SL
3. Check if can operate (balance, limits, cooldown)
4. Scan markets → rank by score → select best
5. Execute trade → save position → update stats
6. Repeat

See `docs/bot_plan.md` for complete implementation details including `config.json` structure, logging format, and error handling patterns.

## Environment Setup

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your credentials (see Configuration section)

# Generate API keys
python scripts/generate_user_api_keys.py
```

## Configuration

Required environment variables in `.env`:

```bash
# Generated by generate_user_api_keys.py
POLY_API_KEY=...
POLY_API_SECRET=...
POLY_API_PASSPHRASE=...

# Wallet credentials from Polymarket Settings -> Export Private Key
POLY_PRIVATE_KEY=0x...

# Only for Magic Link users (most common)
POLY_FUNDER_ADDRESS=0x...
```

**Note**: If using MetaMask/EOA wallet, omit `POLY_FUNDER_ADDRESS` entirely.

## Common Commands

```bash
# Check account status
python poly_client.py --balance

# List markets with filter
python poly_client.py --filter "Trump" --limit 10

# View orderbook for specific token
python poly_client.py --book <TOKEN_ID>

# Monitor orderbook in real-time
python poly_client.py --book <TOKEN_ID> --monitor --interval 5

# Place order (edit file first)
python place_order.py

# Run auto-sell bot (edit configuration first)
python auto_sell.py

# Regenerate API credentials
python scripts/generate_user_api_keys.py

# Verify configuration
python scripts/verify_wallet.py
python scripts/diagnose_config.py
```

## Docker Deployment

```bash
docker-compose up --build -d
docker-compose logs -f
```

## Critical Implementation Details

1. **Signature Type Consistency**: When modifying authentication code, ensure `signature_type` matches the wallet type throughout. The client auto-detects in `poly_client.py` but some scripts like `place_order.py` have it hardcoded.

2. **API Credential Lifecycle**: User API credentials are derived from the private key via the CLOB API. They may expire or become invalid, requiring regeneration with `generate_user_api_keys.py`.

3. **Funder vs Key Parameter**:
   - Magic Link: `funder=POLY_FUNDER_ADDRESS`, `key=POLY_PRIVATE_KEY`
   - MetaMask: `funder=derived_address`, `key=POLY_PRIVATE_KEY`
   - See `generate_user_api_keys.py:42-50` for the pattern

4. **Order Execution**: Uses `create_and_post_order()` with `OrderArgs` and `PartialCreateOrderOptions`. The tick size is typically `"0.01"` for Polymarket markets.

5. **Orderbook Parsing**: The SDK returns objects with `.bids` and `.asks` attributes. Some markets may return empty lists. Always check with `getattr(book, 'bids', [])` pattern (see `poly_client.py:133-158`).

## Troubleshooting Patterns

- **401 Unauthorized**: Run `python generate_user_api_keys.py`
- **Invalid Signature**: Verify signature_type matches your authentication method (Magic Link = 1, MetaMask = 0)
- **Insufficient Balance**: Check wallet on PolygonScan or Polymarket portfolio
- **Empty Orderbook**: Market may have no liquidity; try a different token_id

## Architectural Decisions Log

### 2026-01-30: Stop Loss Emergency Exit Fix

**Problem**: The `min_sell_ratio` safety check in `trader.py` blocked Stop Loss execution when price dropped >50% from entry, causing positions to become "toxic" and unreachable.

**Root Cause**: `execute_sell()` applied the same price floor to all sells, including emergency Stop Loss exits where the priority is to exit at any price.

**Solution**: Added `is_emergency_exit: bool = False` parameter to `execute_sell()`. When `True`, the `min_sell_ratio` check is bypassed.

**Implementation**:
- `bot/trader.py:61-76`: New parameter, conditional check
- `main_bot.py:166`: Pass `is_emergency_exit=action == "stop_loss"` for SL orders

**Design Rationale**:
- `min_sell_ratio` is kept for Take Profits and normal sells (prevents accidental dumps)
- Stop Loss is an emergency exit - price floor makes no sense when you're cutting losses
- Parameter name `is_emergency_exit` is semantic and self-documenting

### 2026-01-30: Arbitrage Research & Whale Tracking Tools

**Research Conducted**: Investigated three arbitrage strategies for Polymarket.

**1. Dutch Book Arbitrage (YES + NO < 1)**
- **Result**: NOT VIABLE
- **Finding**: All markets have YES + NO ≥ 1.001 (no margin)
- **Reason**: HFT bots capture opportunities in <50ms, market makers efficient
- **Tool Created**: `tools/dutch_book_scanner.py`

**2. NegRisk Multi-Outcome Arbitrage**
- **Result**: NOT VIABLE
- **Finding**: All multi-outcome events have Σ(NO) ≥ N-1
- **Example**: Fed Chair (4 candidates) → Σ(NO) = 3.002 > $3.00 payout
- **Tool Created**: `tools/negrisk_scanner.py`

**3. Whale Tracking / Copy Trading**
- **Result**: VIABLE - Implemented
- **API**: `https://data-api.polymarket.com/trades` (public, no auth)
- **Data Available**: proxyWallet, side, size, price, timestamp, transactionHash
- **Tool Created**: `tools/whale_tracker.py`

**Whale Tracker Features**:
```bash
python tools/whale_tracker.py                    # Recent whale trades
python tools/whale_tracker.py --leaderboard      # Top traders by volume
python tools/whale_tracker.py --signals          # Copy trading signals
python tools/whale_tracker.py --monitor          # Continuous monitoring
python tools/whale_tracker.py --track 0xABC...   # Track specific wallet
```

**Key Findings**:
- Polymarket markets are highly efficient (no simple arbitrage)
- Whale data is publicly accessible via data-api
- Copy trading is viable strategy for future integration

### 2026-01-30: Gamma API Integration for Volume/Liquidity

**Problem**: CLOB API (`get_sampling_markets`) returns `volume=0.0` for all markets. Without volume data, the bot cannot filter by liquidity or score markets by trading activity.

**Solution**: Integrated Gamma API (`https://gamma-api.polymarket.com`) for market discovery while keeping CLOB API for trading execution.

**Architecture (Hybrid)**:
```
┌─────────────────────────────────────────────────┐
│  1. Gamma API: Pre-fetch markets with volume    │
│     GET /markets?active=true&closed=false       │
│     Cache by condition_id and token_id          │
│                                                 │
│  2. CLOB API: Fetch orderbooks for verification │
│     get_order_book(token_id)                    │
│     Validate spread, liquidity                  │
│                                                 │
│  3. Trade execution: CLOB API only              │
└─────────────────────────────────────────────────┘
```

**Implementation**:
- `bot/gamma_client.py`: New client with `get_markets()`, `get_top_volume_markets()`
- `bot/market_scanner.py`: Added `_prefetch_gamma_data()`, `_get_gamma_data()`, `_extract_liquidity()`
- `config.json`: Added `gamma_api.enabled`, `market_filters.min_volume_24h`, `market_filters.min_liquidity`

**Data Available from Gamma**:
- `volume24hr`, `volumeNum` (total), `volume1wk`, `volume1mo`
- `liquidityNum`, `bestBid`, `bestAsk`, `spread`
- `clobTokenIds` (for mapping to CLOB API)

**Design Rationale**:
- Gamma is Polymarket's official market data API (more complete than CLOB)
- CLOB is required for trading (Gamma has no trading endpoints)
- Pre-fetching with cache minimizes API calls
- Fallback to CLOB-only if Gamma fails (resilience)

### 2026-01-31: WebSocket Real-Time Monitoring + Concurrent Orders (v0.13.0)

**Problem**: Polling-based monitoring had 10-second latency and high API call rate (1,800 calls/hour). Orders placed sequentially (BUY → TP → SL) took 10+ seconds.

**Solution**: Implemented WebSocket for real-time orderbook subscriptions and concurrent order placement for instant TP/SL setup.

**Architecture**:
```
┌──────────────────────────────────────────────────┐
│  main_bot.py (dual mode)                         │
│  ├─ Async loop: run_loop_async() (WebSocket)   │
│  └─ Sync loop: run_loop() (polling fallback)   │
└──────────────────────────────────────────────────┘
         │
         ├─ WebSocket Mode ──────────────────────┐
         │                                       │
         │  ┌─────────────────────────────────┐  │
         │  │  PolymarketWebSocket            │  │
         │  │  wss://ws-subscriptions-...     │  │
         │  │  ├─ subscribe(token_ids)        │  │
         │  │  ├─ @on_book_update callback    │  │
         │  │  └─ <100ms latency              │  │
         │  └─────────────────────────────────┘  │
         │           │                            │
         │           v                            │
         │  ┌─────────────────────────────────┐  │
         │  │  monitor_positions_websocket    │  │
         │  │  ├─ Real-time TP/SL checks      │  │
         │  │  └─ Limit order fill detection  │  │
         │  └─────────────────────────────────┘  │
         │                                       │
         └─ Polling Mode (fallback) ────────────┤
                                                │
           ┌─────────────────────────────────┐  │
           │  Traditional 10s polling        │  │
           │  1,800 API calls/hour           │  │
           └─────────────────────────────────┘  │
```

**Implementation**:
- `bot/websocket_client.py` (715 lines): Full WebSocket client with callbacks
- `bot/websocket_monitor.py` (260 lines): Async position monitoring
- `bot/trader.py`: Added `execute_buy_with_exits()` for concurrent orders
- `bot/position_manager.py`: New fields: `tp_order_id`, `sl_order_id`, `exit_mode`

**Message Handling**:
- Handles empty keepalive messages
- Supports array responses (Polymarket sends `[{...}, {...}]`)
- Message types: `book`, `price_change`, `subscribed`, `heartbeat`, `pong`

**Concurrent Orders Flow**:
```python
# Entry: Execute buy with TP/SL limits simultaneously
result = trader.execute_buy_with_exits(
    token_id, entry_price, size, tp_price, sl_price
)
# Returns: {buy_fill, tp_order_id, sl_order_id}

# Exit: Monitor limit order fills
if position.exit_mode == "limit_orders":
    check_order_status(tp_order_id)  # Via API
    check_order_status(sl_order_id)
    # When filled, cancel opposite order
```

**Performance**:
- Latency: 10,000ms → <100ms (-99%)
- API calls: 1,800/hr → ~12/hr (-99.3%)
- Slippage: 0.2% → 0% (limit orders)

**Testing**: 5+ hours stable, 0 errors, 0 reconnects, 10 positions opened

---

### 2026-01-31: Telegram Command Bot + Alerts (v0.13.0)

**Implementation**: Full Telegram integration for remote monitoring and control

**Features**:
1. **Command Bot** (`tools/telegram_bot.py`, 411 lines):
   - Interactive commands: `/status`, `/positions`, `/simulate`, `/balance`, `/help`
   - Long polling for reliable message reception
   - Remote control without SSH access

2. **Alerts** (`tools/telegram_alerts.py`, 262 lines):
   - Real-time TP/SL fill notifications
   - Daily summary reports
   - Continuous monitoring mode

3. **Simulation** (`tools/simulate_fills.py`, 216 lines):
   - Checks current prices vs TP/SL levels
   - Calculates simulated P&L for dry-run
   - Loop mode for continuous validation

**Setup**:
```bash
# 1. Create bot with @BotFather
# 2. Add to .env:
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_id

# 3. Start bot
bash scripts/restart_bot.sh  # Auto-starts Telegram bot
```

**Integration**: Bot de Telegram inicia automáticamente con `restart_bot.sh` si está configurado en `.env`

---

### 2026-01-31: Fix de Mercados Resueltos (v0.13.1)

**Problem**: Bot abriendo posiciones en mercados que se resolvían rápidamente, causando pérdidas masivas (75% de posiciones con -95% a -99% loss).

**Root Cause**: Sin filtro de días mínimos, el bot aceptaba mercados que se resolverían en <48 horas o ya estaban resueltos.

**Solution**: Nuevo filtro `min_days_to_resolve` en config.json

**Implementation**:
```python
# bot/market_scanner.py: _passes_metadata_filters()
min_days = self.filters.get("min_days_to_resolve", 2)

if days_to_resolve < min_days:
    self.logger.info(
        f"Rejected {token_id[:8]}: resolves too soon "
        f"(days={days_to_resolve} < {min_days})"
    )
    return False

# bot/market_scanner.py: _is_closed()
if days_to_resolve < 0:  # Past resolution date
    self.logger.info("Rejected: past resolution date")
    return True, "closed_status"
```

**Configuration**:
```json
{
  "market_filters": {
    "min_days_to_resolve": 2,  // NEW: Reject markets < 2 days
    "max_days_to_resolve": 30
  }
}
```

**Diagnostic Tool**: `tools/diagnose_market_filters.py` (400 lines)
- Analyzes 50 markets and shows rejection reasons
- Validates filter is working correctly
- Exports to CSV for analysis

**Expected Impact**:
- Resolved market positions: 75% → <5%
- Average SL loss: -69% → -12%

---

### 2026-01-31: Management Scripts (v0.13.2)

**Problem**: Managing two processes (main bot + Telegram bot) manually was error-prone.

**Solution**: Comprehensive management scripts with automatic Telegram integration

**Scripts**:
1. **restart_bot.sh**: Reinicia ambos bots automáticamente
   - Auto-detects Telegram config in `.env`
   - Starts Telegram in background if configured
   - Starts main bot in foreground
   - Shows status of both on startup

2. **stop_bot.sh**: Detiene ambos bots de forma segura
   - Graceful shutdown: SIGINT → SIGTERM → SIGKILL
   - Handles both processes sequentially

3. **status_bot.sh**: Dashboard completo
   - PID, CPU, memory, uptime for both bots
   - Current positions count
   - Recent log activity (last 5 lines)
   - Configuration summary

4. **start_telegram_bot.sh**: Solo bot de Telegram
   - Standalone script for Telegram only
   - Validates configuration before starting
   - Interactive prompts

**Usage**:
```bash
# Reiniciar todo
bash scripts/restart_bot.sh

# Ver estado
bash scripts/status_bot.sh

# Detener todo
bash scripts/stop_bot.sh
```

**Documentation**: `docs/SCRIPTS_DISPONIBLES.md` (complete guide to all scripts)

### 2026-02-01: Phase 3 Features & Script Modernization (v0.14.1)

**1. Walk the Book (VWAP)**
- **Problem**: Large orders suffered high slippage using simple `best_ask` pricing.
- **Solution**: Implemented `MarketScanner.walk_the_book()` to calculate real Volume-Weighted Average Price.
- **Impact**: Precision entry pricing; prevents trades where slippage > 2%.

**2. Pre-signed Batch Orders**
- **Problem**: Sequential signing of BUY+TP+SL added ~300ms latency.
- **Solution**: Use `client.create_order()` to pre-sign all 3 orders offline, then `client.post_order()` in rapid succession.
- **Impact**: Execution time reduced from ~600ms to ~350ms.

**3. Script Modernization**
- **Problem**: Management scripts had hardcoded paths (`/home/user/poly`) and old branch references.
- **Solution**: Updated `restart_bot.sh` and friends to use:
  - `git rev-parse HEAD` for dynamic branch detection.
  - Absolute paths (`/home/josejordan/poly`).
  - `venv/bin/python` for execution.
  - Argument passing (`$@`) for flags like `--verbose-filters`.

---

### 2026-02-01: Critical Filter Optimization (v0.15.1)

**Problem**: Dry run analysis (14h, 31 trades) revealed the 0.40-0.60 odds range had low win rate (<25%) and negative PnL, while 0.60-0.70 showed 66% win rate and positive PnL.

**Solution**: Tightened `market_filters` in `config.json` to focus on high-probability setups.
- **Old**: `min_odds: 0.30`, `max_odds: 0.70`
- **New**: `min_odds: 0.60`, `max_odds: 0.80`

**Validation**: Based on 14-hour dry run data (31 trades). This shifts the strategy from "uncertainty farming" to "high-confidence harvesting".

### 2026-02-01: Whale Copy Trading System (v0.15.0)

**Goal**: Automatically replicate trades from profitable "whales" to diversify strategy.

**Architecture**:
- **Profiler (`bot/whale_profiler.py`)**: Ranks traders by volume (proxy for profitability). Top 20 are whitelisted.
- **Monitor (`bot/whale_monitor.py`)**: Polls `data-api.polymarket.com/trades` every 30s. Detects signals.
- **Engine (`bot/whale_copy_engine.py`)**: Validates signals against 11-step risk checklist (daily limits, diversification, etc.) before execution.
- **Hybrid Mode**: Runs in parallel with the main `market_scanner.py` loop.

**Key Components**:
1. **Volume-Weighted Ranking**: We assume high-volume traders (> $1M) are profitable survivors.
2. **Consensus Detection**: Can require N whales to trade same side before copying (optional).
3. **Risk Management**:
   - `max_copy_allocation`: $5.00 total risk cap
   - `daily_loss_limit`: $2.00 stop loss
   - `copy_position_size`: Fixed $0.50 per copy

**Integration**:
- Loaded in `main_bot.py` via `_run_whale_cycle()`.
- Alerts via `tools/telegram_alerts.py`.
- Status via `/whales` command.

## Security Considerations

- Never commit `.env` file (already in `.gitignore`)
- Private keys grant full access to wallet funds
- Bot operates on Polygon mainnet with real money
- Always test with small amounts first
- WebSocket connection is secure (WSS)

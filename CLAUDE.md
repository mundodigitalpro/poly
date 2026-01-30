# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Multi-Agent Team

This repository uses multiple AI agents with specialized focuses:
- **CLAUDE.md** (this file): Technical architecture, implementation patterns, and deep-dive into critical flows
- **AGENTS.md** (Codex): Process guidelines, commit standards, testing workflows, and coding conventions
- **GEMINI.md** (Gemini): Current state tracking, quick command reference, and contextual memory
- **AMP** (Trial): Substitute Architect during evaluation period. See `AMP_INSTRUCTIONS.md`

When making changes, ensure consistency across all three memory files. Each agent brings unique value:
- Use **AGENTS.md** for procedural questions (how to test, commit format, style guide)
- Use **GEMINI.md** for current state (what's implemented, what's pending, quick commands)
- Use **CLAUDE.md** for technical questions (how auth works, why signature_type matters, bot architecture)

## Inter-Agent Communication (Pair Programming)

The three AI agents can communicate programmatically via their CLI tools in non-interactive mode:

| Agent | Model | CLI Command | Non-Interactive Mode |
|-------|-------|-------------|---------------------|
| **Claude** | Opus 4.5 | `claude` | Already in session (this agent) |
| **Codex** | GPT-5.2 | `codex` | `codex exec "prompt" --full-auto` |
| **Gemini** | Gemini | `gemini` | `gemini -p "prompt" -o text` |

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

4. **generate_user_api_keys.py**: Generates or retrieves API credentials
   - Must be run whenever credentials expire or are invalid
   - Derives wallet address for EOA users automatically

### Planned Architecture (Autonomous Bot)

Located in `bot_plan.md` (526 lines, production-ready design), the autonomous bot implements:

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

See `bot_plan.md` for complete implementation details including `config.json` structure, logging format, and error handling patterns.

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
python generate_user_api_keys.py
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
python generate_user_api_keys.py

# Verify configuration
python verify_wallet.py
python diagnose_config.py
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

## Security Considerations

- Never commit `.env` file (already in `.gitignore`)
- Private keys grant full access to wallet funds
- Bot operates on Polygon mainnet with real money
- Always test with small amounts first

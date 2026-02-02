# Changelog

All notable changes to this project will be documented in this file.

## [0.16.0] - 2026-02-03 (Night)
### Changed - Strategy Improvements Phase 1 🎯
Implementation of critical improvements from `docs/strategy_improvement_plan.md`:

- **IMP-001: Expanded Odds Range**: `0.60-0.80` → `0.35-0.80`
  - Now utilizes all configured TP/SL ranges
  - More trading opportunities available
  - Aligned `bot/strategy.py` ranges with `config.json`

- **IMP-002: Improved Risk/Reward Ratio**: `1.2:1` → `2:1`
  - New TP/SL configuration by odds range:
    - 0.35-0.45: TP=28%, SL=14% (Ratio 2:1)
    - 0.45-0.55: TP=22%, SL=11% (Ratio 2:1)
    - 0.55-0.65: TP=18%, SL=9% (Ratio 2:1)
    - 0.65-0.75: TP=14%, SL=7% (Ratio 2:1)
    - 0.75-0.80: TP=12%, SL=6% (Ratio 2:1)
  - Breakeven win rate reduced from 48% to 33%

- **IMP-003: Increased Position Size**: `$0.25` → `$1.00`
  - Capital utilization improved from 27% to 55%
  - Reduced max positions: 20 → 10 (better focus)
  - Scale-up target: $2.00 after 20 profitable trades

### Files Modified
- `config.json`: Updated all strategy parameters
- `bot/strategy.py`: Aligned odds range detection with new config
- `tests/test_strategy.py`: Updated tests for new TP/SL values

### Verified
- ✅ All strategy tests passing
- ✅ Dry run cycle completed successfully
- ✅ New candidates found in expanded range (odds=0.49 now accepted)
- ✅ New position opened with 2:1 ratio (TP=0.8960, SL=0.7520 @ entry 0.80)

## [0.15.4] - 2026-02-03 (Night)
### Fixed - Docker Deployment
- **Telegram Command Bot**: Made opt-in via `TELEGRAM_COMMAND_BOT=true` environment variable.
  - Prevents HTTP 409 conflicts between command bot and main_bot's notification system.
  - Only starts when explicitly enabled in `.env` file.
  - Main bot notifications continue to work independently with `TELEGRAM_BOT_TOKEN`.

### Documentation
- **Strategy Analysis 2026**: Comprehensive review of current trading strategy.
  - `docs/strategy_analysis_2026.md`: Identifies critical issues (odds range inconsistency, poor R:R ratio).
  - Documents strengths and weaknesses with actionable recommendations.
- **Strategy Improvement Plan**: Detailed 8-week implementation roadmap.
  - `docs/strategy_improvement_plan.md`: 7 prioritized tasks with acceptance criteria.
  - KPIs for tracking progress and measurable outcomes.

## [0.15.3] - 2026-02-02 (Evening)
### Added - Testing Infrastructure & Automation
- **scripts/run_readonly_tests.sh**: New automated wrapper for read-only diagnostics and reporting.
- **Reporting System**: Standardized test report format in `docs/reports/`.
- **docs/TOOLS_SCRIPTS_TEST_PLAN.md**: Updated with recommendations and automated run instructions.

### Fixed - Configuration & Stability
- **config.json**: Added missing `trading` section required for concurrent order unit tests.
- **Unit Tests**: Restored 100% pass rate for `tests/test_concurrent_orders.py`.

### Documentation
- Created `docs/reports/test_run_complete_2026-02-02.md` with comprehensive results.

### Added - Telegram UX & Position Context
- **Positions metadata**: Store market question in `positions.json` and reuse it in Telegram.
- **Market name resolution**: Telegram `/positions` resolves market names via Gamma/CLOB and caches them in `data/market_cache.json`.

### Changed - Bot Logging & Telegram Commands
- **main_bot logs**: Position open/close/TP/SL logs now include market name + token short ID.
- **/positions**: Shows entry price, current best bid, per-position PnL, and total PnL summary.
- **/balance**: Shows raw balance/allowance plus normalized USDC with unit heuristic.

### Fixed - Telegram Startup
- **restart_bot.sh**: Stops existing Telegram bot instances to prevent duplicates.
- **start_telegram_bot.sh**: Uses venv Python if available and installs `requirements.txt` when deps are missing.

## [0.15.1] - 2026-02-02 (Morning)
### Changed - Optimization Phase 🚀
- **Config**: Optimized odds range to `0.60 - 0.80` (was 0.30-0.70) based on dry run analysis.
  - Removes unprofitable mid-range (0.40-0.60).
  - Focuses on high-probability setups (66% win rate observed in dry run).

## [0.15.0] - 2026-02-01 (Evening)
### Added - Whale Copy Trading System 🐋
- **Core Infrastructure (Phase 1)**: Complete whale copy trading system with volume-weighted ranking and real-time signal detection.

- **🆕 Tracked Wallets Feature (Phase 1.1)**: Ability to manually track specific whale wallets
  - Configure specific wallets to always copy (bypass ranking system)
  - Priority mode for trusted traders
  - Optional score requirement bypass
  - `tools/find_whale_wallet.py`: New CLI tool to discover wallet addresses
    - Search traders by name (e.g., "Theo4", "Fredi9999")
    - Find whales by market activity (e.g., "Trump", "Bitcoin")
    - View top traders by recent volume
    - Copy-paste ready wallet addresses
  - Visual indicators in leaderboard (⭐ TRACKED marker)
  - Config section: `whale_copy_trading.tracked_wallets`
    - `enabled`: Enable/disable tracked wallets feature
    - `wallets`: List of wallet addresses to track
    - `priority_over_ranking`: Always copy these wallets (default: true)
    - `bypass_score_requirement`: Skip min score check (default: false)

  **New Modules:**
  - `bot/whale_profiler.py`: Volume-weighted ranking system for identifying top traders
    - Composite scoring: volume (40%), consistency (30%), diversity (20%), recency (10%)
    - Auto-whitelist management (top 20 whales with score >60)
    - Persistent profiles in `data/whale_profiles.json`
    - Visual leaderboard with rankings and stats

  - `bot/whale_monitor.py`: Real-time whale trade monitoring
    - Polls API every 30s for new trades
    - Filters by whitelist (only top-scored traders)
    - Detects whale consensus (3+ whales on same market)
    - Generates signals with confidence scores (0-100)
    - Age filtering (only trades <10 minutes old)

  - `bot/whale_copy_engine.py`: Decision logic and execution
    - 11 validation checks before copying any trade
    - Risk management: daily limits, allocation caps, diversification
    - Dry-run mode for safe testing
    - Position tracking with P&L analytics
    - Configurable exit strategies (follow whale, TP/SL, hybrid)

  - `tools/test_whale_copy.py`: Comprehensive testing framework
    - Standalone testing of all components
    - Live demo mode with interactive walkthrough
    - Statistics and performance reporting

  **Configuration:**
  - Added `whale_copy_trading` section to `config.json`
    - Enabled: false (requires manual activation)
    - Mode: hybrid (original + whale copy strategies)
    - Copy size: $0.50 per trade
    - Limits: max 10 copies/day, max $5 total allocation
    - Risk: $2 daily loss limit, min 3 markets diversification

  **Risk Management Features:**
  - Whale whitelist validation (score >70 required)
  - Trade age limit (max 10 minutes)
  - Side filtering (BUY only by default)
  - Size bounds ($500-$50k whale trades)
  - Capital availability checks
  - Daily copy limits (max 10/day)
  - Risk allocation caps (max $5 total)
  - Diversification requirements (min 3 markets)
  - Daily loss limits ($2 stop)
  - Market filters (optional, uses same as main strategy)
  - Blacklist support

  **Exit Strategies:**
  - Follow the whale (monitor for whale sell signal)
  - Own TP/SL (use dynamic targets like main strategy)
  - Hybrid (default: follow whale with TP/SL backstop)

### Added - Trading Strategies Research
- **Comprehensive 2026 Strategy Analysis**: Research of real-world strategies from X.com, Reddit, GitHub
  - `docs/ESTRATEGIAS_REALES_2026.md`: 458-line analysis of viable strategies
    - Market context (volume -84% post-election, high competition)
    - 7 strategies evaluated (3 viable, 4 clickbait)
    - Data-backed evidence from NPR, DataWallet, GitHub repos
    - Implementation recommendations for our bot

  **Viable Strategies Identified:**
  1. ✅ Whale Copy Trading (implemented in v0.13.0)
  2. ✅ High-Probability Harvesting (>95% odds, <7 days)
  3. ✅ News-Based Trading (30-60s delay advantage)
  4. ✅ Cross-Platform Arbitrage (Kalshi, Opinion, Polymarket)
  5. ✅ Domain Expertise Focus (politics, sports)

  **Strategies Debunked:**
  1. ❌ Flash crash on 15-min markets (fees killed the edge)
  2. ❌ Dutch book arbitrage (HFT only, <10ms required)
  3. ❌ Passive market making (no longer profitable in 2026)
  4. ❌ AI prediction bots (edge is in structure, not prediction)

### Documentation
- `docs/WHALE_COPY_TRADING_DESIGN.md`: Complete architecture design (606 lines)
  - System architecture and component interactions
  - Pragmatic approach (volume-weighted scoring, no win-rate data needed)
  - Data structures and API integration
  - Implementation phases and testing plan
  - Risk mitigation strategies
  - KPIs and success metrics

- `docs/ESTRATEGIAS_REALES_2026.md`: Research backing (458 lines)
  - Real-world strategy analysis with sources
  - Performance data from top traders ($22M+ lifetime)
  - Market efficiency analysis
  - Implementation roadmap

- Updated `.gitignore`: Added whale copy trading runtime files
  - `data/whale_profiles.json`
  - `data/whale_copy_stats.json`
  - `data/whale_copy_positions.json`

### Changed
- **Config Schema**: Expanded with whale_copy_trading section
  - Profiler settings (update intervals, scoring thresholds)
  - Monitor settings (poll frequency, consensus detection)
  - Copy rules (sides, sizes, limits)
  - Risk management (allocation, diversification, loss limits)
  - Alert settings (Telegram integration ready)

### Technical Details
- **Whale Selection Method**: Volume-weighted ranking (no win-rate needed)
  - Assumption: High-volume traders likely profitable (or would have quit)
  - Composite score balances multiple factors
  - Top 20 whitelisted automatically
  - Consensus detection as secondary signal

- **Copy Validation Pipeline**: 11-step validation before execution
  1. Whale whitelist check
  2. Blacklist check
  3. Trade age validation
  4. Side filter (BUY/SELL)
  5. Trade size bounds
  6. Market filters (optional)
  7. Capital availability
  8. Daily copy limits
  9. Risk allocation limits
  10. Diversification requirements
  11. Daily loss limits

- **Data Sources**:
  - Polymarket trades API: `https://data-api.polymarket.com/trades`
  - Public whale data (no auth required)
  - Real-time polling every 30 seconds

### Next Steps (Phase 2 - Pending)
- [x] Integration with `main_bot.py` (dual mode)
- [x] Telegram alerts for whale trades
- [x] Telegram command `/whales`
- [ ] Real-world testing (20+ trades dry-run)
- [ ] Performance monitoring and tuning
- [ ] Real-world testing (20+ trades dry-run)
- [ ] Performance monitoring and tuning

### Research Sources
- NPR: Top trader analysis (+$22M lifetime profits)
- DataWallet: Win rate statistics (16.8% profitable wallets)
- GitHub: discountry/polymarket-trading-bot, warproxxx/poly-maker
- Medium, CoinsBench: Strategy analyses
- X.com: @Param_eth, @thejayden, @itslirrato

## [0.14.1] - 2026-02-01 (Morning)
### Added
- **Infrastructure**: Full Docker VPS support with secrets protection (`.dockerignore`) and data persistence.
- **Scripts**: New `scripts/docker_entrypoint.sh` for managing dual-bot startup (Main + Telegram) in container.

### Fixed
- **Tooling**: Updated `tools/diagnose_market_filters.py` to match new `PositionManager` and `TradingStrategy` signatures.
- **Scripts**: Modernized `restart_bot.sh` and others to support dynamic branch detection and absolute paths.
- **Whale Service**: Fixed `ImportError` by restructuring `tools/` as a python package.
- **WebSocket**: Silenced 'Unknown message type' logs by handling `event_type` key in messages.
- **Data**: Corrected `positions.json` initialization structure (dict instead of list).
- **Cleanup**: Archived legacy `auto_sell.py` to `legacy/` directory.

### Changed
- **Config**: Relaxed default market filters to increase trading volume.
  - Expanded odds range: `0.30` - `0.70` (was 0.45-0.60).
  - Increased max markets: `500` (was 200).

## [0.14.0] - 2026-01-31 (Night)
### Added
- **Walk the Book (VWAP)**: Calculate real slippage before executing trades
  - `MarketScanner.walk_the_book()`: Calculates VWAP for a given order size
  - `MarketScanner.get_orderbook_depth()`: Full orderbook depth analysis
  - Returns (vwap, filled_size, slippage_percent) for buy/sell orders
  - Prevents trades where slippage exceeds `max_slippage_percent`

- **Pre-sign Batch Orders**: Minimized latency for multiple orders
  - `BotTrader.execute_batch_orders()`: Execute multiple orders with pre-signing
  - `BotTrader.execute_paired_buy_with_batch()`: BUY + TP + SL with pre-signing
  - Separates slow signing (~100-200ms each) from fast submission (~50ms each)
  - Reduces total time for BUY+TP+SL from ~600ms to ~350ms

### Configuration
- New options in `config.json`:
  - `trading.use_presign_batch`: Enable pre-signed batch orders (default: false)
  - `trading.use_slippage_check`: Enable slippage verification (default: true)
  - `trading.max_slippage_percent`: Maximum allowed slippage (default: 2.0%)

### Technical Details
- Inspired by `gabagool222/15min-btc-polymarket-trading-bot` analysis
- VWAP calculation walks orderbook levels to determine actual fill price
- Batch pre-signing uses `client.create_order()` + `client.post_order()` pattern
- Fallback to sequential execution if pre-sign not available in SDK

---

## [0.13.2] - 2026-01-31 (Evening)
### Added
- **Telegram Bot Integration**: Automated startup and management
  - `scripts/restart_bot.sh`: Auto-detects Telegram config and starts both bots
  - `scripts/stop_bot.sh`: Stops both main bot and Telegram bot gracefully
  - `scripts/start_telegram_bot.sh`: Standalone script for Telegram bot only
  - `scripts/status_bot.sh`: Complete dashboard showing status of both bots
  - Bot de Telegram inicia automáticamente en background si está configurado

### Documentation
- `docs/SCRIPTS_DISPONIBLES.md`: Complete guide to all management scripts
- `docs/REINICIAR_BOT.md`: Comprehensive restart guide

### Benefits
- Single command to restart everything: `bash scripts/restart_bot.sh`
- Automatic Telegram bot management (no manual process juggling)
- Easy status monitoring: `bash scripts/status_bot.sh`
- Unified shutdown: `bash scripts/stop_bot.sh`

---

## [0.13.1] - 2026-01-31 (Afternoon)
### Fixed
- **CRITICAL: Resolved Markets Filter**: Bot was opening positions in markets resolving <48 hours
  - **Problem**: 75% of positions in resolved markets (losses of 95-99%)
  - **Root Cause**: No minimum days-to-resolve filter, markets resolved shortly after entry
  - **Solution**: New `min_days_to_resolve: 2` filter in config.json

- **Enhanced Market Detection**:
  - Detects markets past resolution date (`days_to_resolve < 0`)
  - Expanded closed status detection (`finalized`, `settled`)
  - Improved logging shows `days` for all accepted/rejected markets

### Added
- **Diagnostic Tools**:
  - `tools/diagnose_market_filters.py`: Analyzes 50 markets, shows rejection reasons
  - `scripts/quick_validate_fix.sh`: Validates filter implementation
  - Export to CSV support for analysis

### Configuration
- New filter: `market_filters.min_days_to_resolve: 2` (default)
- Prevents markets resolving today/tomorrow from being traded

### Documentation
- `docs/FIX_RESOLVED_MARKETS.md`: Technical documentation (450 lines)
- `docs/RESUMEN_FIX.md`: Spanish summary (261 lines)

### Expected Impact
- Resolved market positions: 75% → <5%
- Average SL loss: -69% → -12%
- Markets with days < 2: Rejected

---

## [0.13.0] - 2026-01-31 (Morning)
### Added
- **WebSocket Real-Time Monitoring** ✅ STABLE (5+ hours, 0 errors)
  - `bot/websocket_client.py`: Full WebSocket client for orderbook subscriptions
  - `bot/websocket_monitor.py`: Async position monitoring via WebSocket
  - Message handling: Empty keepalives, list responses, multiple message types
  - Latency: <100ms (vs 10s polling) - 99% improvement

- **Concurrent Order Placement** ✅ IMPLEMENTED
  - `bot/trader.py`: New methods for placing BUY + TP + SL simultaneously
  - Exit modes: `limit_orders` (concurrent) vs `monitor` (traditional)
  - Reduces post-entry latency from 10s to <1s

- **Telegram Command Bot** ✅ FUNCTIONAL
  - `tools/telegram_bot.py`: Interactive command bot (411 lines)
  - Commands: `/status`, `/positions`, `/simulate`, `/summary`, `/balance`, `/help`
  - Long polling for reliable message reception
  - Remote control of bot via Telegram

- **TP/SL Simulation Tool**
  - `tools/simulate_fills.py`: Simulates fills for dry-run positions
  - Calculates P&L without real trading
  - Loop mode for continuous monitoring
  - Saves results to `data/simulation_results.json`

- **Telegram Alerts**
  - `tools/telegram_alerts.py`: Send alerts and daily summaries
  - Modes: `--test`, `--monitor`, `--summary`
  - Real-time fill notifications

### Changed
- **Configuration**: Enabled production features in `config.json`
  - `use_websocket: true`
  - `use_concurrent_orders: true`
  - Still in `dry_run: true` for safety

### Testing
- **5-Hour Dry Run**: Stable operation
  - 10 positions opened
  - 0 errors
  - 0 WebSocket reconnects
  - 8,625+ log lines

### Documentation
- `docs/day3_progress.md`: Day 3 progress report
- `docs/TESTING_GUIDE.md`: Step-by-step testing instructions
- `docs/PROGRESS_DAY2.md`: WebSocket fix documentation

### Architecture
```
Main Bot → WebSocket (real-time) + Gamma API (volume) + CLOB API (trading)
         → Telegram Alerts (every 5 min)
         → Telegram Command Bot (interactive)
```

### Performance Improvements
- **Latency**: 10,000ms → <100ms (-99%)
- **API Calls**: 1,800/hr → ~12/hr (-99.3%)
- **Slippage**: 0.2% → 0% (limit orders)

---

## [0.12.3] - 2026-01-30 (Evening)
### Changed
- **Project Reorganization**: Restructured project for better maintainability.
  - Created `scripts/` for utility scripts (`generate_user_api_keys.py`, `verify_wallet.py`, `diagnose_config.py`, `test_all_sig_types.py`)
  - Created `tools/` for research & analysis (`whale_tracker.py`, `dutch_book_scanner.py`, `negrisk_scanner.py`, `analyze_positions.py`)
  - Created `docs/` for documentation (`bot_plan.md`, `PLAN.md`, `PROMPT.md`, `HANDOFF.md`)
  - Created `docs/proposals/` for feature proposals (`PROPOSAL_*.md`)
  - Created `docs/team/` for team coordination docs (`AMP_*.md`, `TEAM_INSTRUCTIONS.md`)

### Documentation
- Updated `README.md` with new project structure
- Updated `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` with new file paths
- All commands now reference correct paths (e.g., `scripts/verify_wallet.py`)

---

## [0.12.2] - 2026-01-30 (Late Evening)
### Added
- **Whale Tracking Integration**: Sentiment-based scoring from whale activity.
  - `bot/whale_service.py`: WhaleService class with sentiment scoring (-1 to +1)
  - Integrates into MarketScanner to boost/penalize scores based on whale activity
  - Configurable via `whale_tracking` section in config.json (disabled by default)

- **Position Analysis Tool**: `analyze_positions.py` utility for risk analysis.
  - Calculates distance to TP/SL for all positions
  - Risk/Reward ratio analysis
  - Flags positions near triggers

### Documentation
- `PROPOSAL_WHALE_INTEGRATION.md`: Design document for whale integration
- Updated `GEMINI.md` with current state

### Team Collaboration
- KIMI: Created whale_service.py and analyze_positions.py
- AMP: Designed proposal, integrated into market_scanner.py, config updates
- CODEX: Available for code reviews

---

## [0.12.1] - 2026-01-30 (Evening)
### Added
- **Arbitrage Research Tools**: Three scanners for investigating arbitrage strategies.
  - `dutch_book_scanner.py`: Detects YES+NO<1 opportunities (Dutch Book)
  - `negrisk_scanner.py`: Analyzes multi-outcome markets for NegRisk arbitrage
  - `whale_tracker.py`: Tracks whale trades and generates copy trading signals

- **Whale Tracker Features**:
  - Real-time whale trade detection via `data-api.polymarket.com/trades`
  - Trader leaderboard by volume
  - Copy trading signal generation (whale consensus)
  - Wallet tracking for specific addresses
  - Continuous monitoring mode with alerts

### Research Findings
- **Dutch Book**: NOT VIABLE - Markets maintain YES+NO ≥ 1.001, HFT bots dominate
- **NegRisk**: NOT VIABLE - All events have Σ(NO) ≥ N-1, markets efficient
- **Whale Tracking**: VIABLE - Public API available, useful data for copy trading

### Documentation
- Updated CLAUDE.md with arbitrage research findings
- Updated GEMINI.md with current state and new tools
- Created team handoff plan in HANDOFF.md

## [0.12.0] - 2026-01-30
### Added
- **Gamma API Integration**: New client for fetching volume and liquidity data from Polymarket's Gamma API.
  - New file: `bot/gamma_client.py` with `GammaClient` class.
  - Fetches: `volume24hr`, `volumeNum`, `liquidityNum`, `clobTokenIds`.
  - Hybrid architecture: Gamma for market discovery, CLOB for trading.
  - Configurable via `gamma_api.enabled` in `config.json`.

- **Volume/Liquidity Filtering**: Scanner now filters markets by real volume data.
  - New config: `market_filters.min_volume_24h` (default: $500).
  - New config: `market_filters.min_liquidity` (default: $1000).
  - Candidates now include `liquidity` field in output.

- **Gamma Cache**: Pre-fetches Gamma data at start of each scan for performance.
  - Maps by `condition_id` and `token_id` for fast lookups.
  - Falls back to CLOB-only data if Gamma fails.

- **Tests**: New `tests/test_gamma_client.py` with 13 tests covering:
  - Normalization, filtering, edge cases, and integration.

### Changed
- **Market Scanner**: Modified `bot/market_scanner.py` to integrate Gamma data.
  - New methods: `_prefetch_gamma_data()`, `_get_gamma_data()`, `_extract_liquidity()`.
  - `_extract_volume_usd()` now prefers Gamma API data over CLOB.
  - `_passes_metadata_filters()` now checks liquidity threshold.

### Technical Details
- Gamma API: `https://gamma-api.polymarket.com/markets`
- Solves issue: CLOB API returns `volume=0.0` for all markets.
- Implementation coordinated by CLAUDE following PROPOSAL_TRENDING_VOLUME.md.

## [0.11.5] - 2026-01-30
### Added
- **Dual-Frequency Loop Architecture**: Separated position monitoring from market scanning.
  - Position check: Every 10 seconds (reactive to price changes).
  - Market scan: Every 60-120 seconds (efficient API usage).
  - New config parameter: `bot.position_check_interval_seconds`.
  - Bot now monitors TP/SL conditions 6-12x more frequently than before.

### Changed
- **Performance Optimizations** (coordinated by AMP):
  - Reduced `max_markets` from 200 to 50 (4x faster scans).
  - Disabled detail fetches (`max_market_detail_fetch: 0`) to reduce API calls.
  - Increased `max_calls_per_minute` to 300 for faster scanning.
  - Market scan now completes in ~10 seconds instead of ~2 minutes.

## [0.11.4] - 2026-01-30
### Fixed
- **Critical: Best Bid/Ask Extraction Bug in main_bot.py**: Fixed `_best_bid_ask()` using `orders[0]` which returned worst price (0.01) instead of best price.
  - Root cause: Polymarket API returns bids sorted ascending (worst→best), so `bids[0]` = worst bid.
  - Solution: Replaced `_extract_price()` with `_extract_best_bid()` using `max(prices)` and `_extract_best_ask()` using `min(prices)`.
  - Impact: All positions were triggering false Stop Loss immediately after opening.
  - Discovery: Dry-run showed 100% SL triggers at bid=0.01 despite entry at 0.30-0.70.

## [0.11.3] - 2026-01-30
### Fixed
- **Market Scanner Resilience**: Multiple robustness improvements coordinated between AMP (architect) and CODEX (developer).
  - `_fetch_markets`: Wrapped API calls in try/except; returns partial results on failure instead of aborting.
  - `_analyze_market`: Token candidates with existing positions or blacklisted now `continue` to next candidate instead of rejecting entire market.
  - `_extract_token_candidates`: Top-level token_id fallback now only used when token list is empty (matches comment intent).
  - `_extract_token_candidates`: Detail fetch failures logged at debug level and gracefully handled.
  - `_rate_limit`: Switched from `datetime.utcnow().timestamp()` to `time.monotonic()` for clock-jump resilience.
  - `scan_markets`: Reset `_detail_fetch_count` at start of each scan to avoid stale limits.
- **Tests**: All 7 tests passing after changes.

## [0.11.2] - 2026-01-30
### Changed
- **Phase 3 Duration**: Reduced validation dry-run from 7 days to 2-4 hours (~15-30 cycles) for faster iteration.

## [0.11.1] - 2026-01-30
### Fixed
- **Critical: Stop Loss Execution Bug**: Fixed issue where Stop Loss orders were blocked when price dropped >50% from entry.
  - Root cause: `min_sell_ratio` safety check applied to all sells, including emergency exits.
  - Solution: Added `is_emergency_exit` flag to `execute_sell()` to bypass price floor for Stop Loss.
  - Files: `bot/trader.py`, `main_bot.py`
- **Test Coverage**: Added `tests/test_stop_loss_emergency_exit.py` to verify 90% price drop handling.

### Technical Details
- Incident discovered during 7-hour test run (2026-01-29).
- Analysis documented in `PLAN.md`.
- Coordinated fix between Claude (architecture), Codex (implementation), and Gemini (verification).

## [0.11.0] - 2026-01-30
### Added
- **Inter-Agent Communication System**: Enabled programmatic pair programming between AI agents.
  - Claude (Opus 4.5), Codex (GPT-5.2), and Gemini can now communicate via CLI.
  - Non-interactive commands: `codex exec "msg" --full-auto` and `gemini -p "msg" -o text`.
  - Documented communication protocols in all three memory files.
- **Documentation**: Updated `AGENTS.md`, `GEMINI.md`, and `CLAUDE.md` with:
  - Inter-agent communication commands and examples.
  - Coordination guidelines and best practices.
  - Protocol for task delegation and status reporting.

### Technical Details
- Codex CLI v0.92.0: Uses `exec` subcommand with `--full-auto` for non-interactive mode.
- Gemini CLI v0.26.0: Uses `-p` (prompt) flag with `-o text` for non-interactive mode.
- Communication is synchronous via stdout capture.

## [0.10.0] - 2026-01-29
### Added
- **Autonomous Bot Beta**: Complete implementation of the autonomous trading bot (dry-run ready).
  - **Core Modules**: `market_scanner`, `strategy`, `position_manager`, `trader`, `config`, `logger`.
  - **Main Loop**: `main_bot.py` integrated with rate limiting and error handling.
  - **Testing**: Added `tests/` with unit tests for strategy and position management (pytest).
  - **Optimization**: Market scanner uses client-side rate limiting to respect API limits.
- **Commands**: Added `python main_bot.py --once` for single-loop execution (dry run).

### Changed
- **Phase Status**: Fase 2 (Integración y Testing) completada; dry run `main_bot.py --once` verificado.

## [0.9.1] - 2026-01-29
### Added
- **Contributor Guide**: Added `AGENTS.md` with repository guidelines for contributors.

### Changed
- **README**: Clarified `--balance` output, added signature type notes, expanded troubleshooting commands, and updated the project structure list.

## [0.9.0] - 2026-01-29
### Enhanced
- **Autonomous Bot Plan**: Major upgrade to `bot_plan.md` with production-ready architecture
  - Market selection: Tightened spread filter from 10% to 5% for small trades
  - Added market resolution timeframe filter (<30 days) to avoid long-term capital lockup
  - Implemented weighted scoring algorithm for market ranking
  - Position persistence via `positions.json`, `blacklist.json`, `stats.json`
  - Temporal blacklist system (3 days, max 2 attempts) replacing permanent blocks
  - Partial fill handling for incomplete order executions
  - Real balance verification via API each loop
  - Fee calculations integrated into TP/SL targets
  - Comprehensive stats tracking (win rate, profit factor, Sharpe ratio, etc.)
  - Daily dashboard for monitoring bot performance
  - Phased rollout: Dry run → Paper trading → Micro ($0.25) → Normal ($1.00)
  - 10 safety protections including rate limiting and error handling
  - Detailed `config.json` structure with all configurable parameters

### Added
- **CLAUDE.md**: Documentation for future Claude Code instances
  - Authentication flow and signature type patterns
  - Core architecture and component descriptions
  - Critical implementation details and troubleshooting patterns
- **GEMINI.md**: Persistent memory and context for Gemini CLI agent integration

## [0.8.0] - 2026-01-28
### Added
- **Autonomous Bot Architecture**: Designed a full plan for a 24/7 VPS trading bot.
- **Auto-Sell Bot v2**: Created `auto_sell.py` with safety protections (TP/SL, spread alerts, confirmation).
- **Trading Success**: Executed the first buy and sell orders on the live CLOB API.

### Fixed
- **Signature Optimization**: Confirmed `signature_type=1` as the correct type for Magic Link email wallets.
- **Safety**: Prevented accidental "market-price" sales in illiquid markets by adding spread verification.

## [0.7.0] - 2026-01-28
### Fixed
- **Authentication**: Resolved 401 Unauthorized errors for Magic Link users
- **API Credentials**: Now properly generated using `derive_api_key()` method
- **Balance Command**: Replaced broken `get_balance_allowance` with working `get_orders` endpoint

### Added
- **Diagnostic Toolkit**:
  - `generate_user_api_keys.py`: Generate User API Credentials from private key
  - `verify_wallet.py`: Verify private key matches wallet address
  - `diagnose_config.py`: Verify .env configuration
  - `test_all_sig_types.py`: Test all signature_type configurations (0, 1, 2)
- **Documentation**: Updated README.md with Magic Link setup instructions

### Changed
- `poly_client.py`: `--balance` now shows account status (orders, trades) instead of problematic balance endpoint

## [0.5.0] - 2026-01-27
### Added
- **Balance Check**: Implementation of `--balance` argument to check USDC collateral
- **Proxy Support**: Added `POLY_FUNDER_ADDRESS` env var to support Magic Link / Gnosis Safe wallets
- **Debug Tools**: Scripts for troubleshooting authentication

## [0.4.0] - 2026-01-27
### Added
- **Polling**: Continuous monitoring loop with `--monitor` flag
- **Interval**: Customizable update frequency with `--interval` (default 5s)

## [0.3.0] - 2026-01-27
### Added
- **Orderbook**: Fetch price depth (bids/asks) for specific Token IDs (`--book`)
- **CLI**: Argument parsing for `--book` and `--limit` handling

## [0.2.0] - 2026-01-27
### Added
- **Market Filtering**: Filter markets by text using `--filter` argument
- **Enhanced Data**: Switched to `get_sampling_markets` for full metadata

## [0.1.0] - 2026-01-27
### Added
- **Initial Release**: Basic Python client structure
- **Connection**: Authentication using `py_clob_client` with API Keys
- **Docker**: Containerization support (`Dockerfile`, `docker-compose.yml`)
- **Config**: Environment variable management via `.env`
- **Docs**: Comprehensive `README.md` in Spanish
- **Fixes**: Graceful handling of missing/invalid Private Key (Read-Only mode)

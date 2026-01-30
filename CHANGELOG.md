# Changelog

All notable changes to this project will be documented in this file.

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

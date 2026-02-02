# Tools and Scripts Test Plan (Test Mode)

Goal: run and document untested tools/scripts while staying in dry-run mode.
This is a plan for the team to follow and record results during the test phase.

## Preconditions
- venv active (or use venv/bin/python explicitly)
- .env configured with POLY_* credentials
- config.json: bot.dry_run = true (unless explicitly testing live paths)
- Network access to Polymarket + Gamma API

## Safety Rules
- Keep dry_run true for all bot runs.
- Do not run any script that sends real orders unless explicitly approved.
- Prefer small limits and --once where available.

## Execution Order (Suggested)
1) Environment & config validation
2) Read-only market/position tooling
3) Websocket and concurrent-orders test scripts (dry-run)
4) Whale tooling + social search
5) Ops scripts (restart/stop/status) in a controlled window

## Test Matrix

### scripts/

- diagnose_config.py
  - Command: python scripts/diagnose_config.py
  - Expected: confirms .env keys found
  - Notes: read-only

- verify_wallet.py
  - Command: python scripts/verify_wallet.py
  - Expected: derived address matches POLY_FUNDER_ADDRESS (if set)
  - Notes: read-only

- generate_user_api_keys.py
  - Command: python scripts/generate_user_api_keys.py
  - Expected: API creds printed/saved
  - Notes: rotates keys; run only if needed

- test_all_sig_types.py
  - Command: python scripts/test_all_sig_types.py
  - Expected: signature_type 0/1 tests pass
  - Notes: requires valid POLY_* credentials

- test_concurrent_orders.sh
  - Command: bash scripts/test_concurrent_orders.sh
  - Expected: unit tests + one dry-run cycle
  - Notes: uses timeout; does not place orders

- test_websocket.sh
  - Command: bash scripts/test_websocket.sh
  - Expected: websocket connects and subscribes; no reconnect loop
  - Notes: temporarily edits config.json and restores it

- test_websocket_standalone.py
  - Command: python scripts/test_websocket_standalone.py
  - Expected: receives snapshots/updates for a sample market
  - Notes: read-only

- quick_validate_fix.sh
  - Command: bash scripts/quick_validate_fix.sh
  - Expected: confirms min_days_to_resolve and dry_run status
  - Notes: read-only

- status_bot.sh
  - Command: bash scripts/status_bot.sh
  - Expected: main bot + telegram bot status
  - Notes: read-only

- start_telegram_bot.sh
  - Command: bash scripts/start_telegram_bot.sh
  - Expected: bot starts with logs
  - Notes: choose background mode for log file

- restart_bot.sh
  - Command: bash scripts/restart_bot.sh
  - Expected: main bot restarts; telegram duplicates stopped
  - Notes: use during a controlled window

- stop_bot.sh
  - Command: bash scripts/stop_bot.sh
  - Expected: stops running bots
  - Notes: use after tests to clean up

### tools/

- analyze_positions.py
  - Command: python tools/analyze_positions.py
  - Expected: shows PnL, distance to TP/SL, optional live price
  - Notes: requires data/positions.json

- simulate_fills.py
  - Command: python tools/simulate_fills.py
  - Expected: shows which positions would hit TP/SL now
  - Notes: read-only

- diagnose_market_filters.py
  - Command: python tools/diagnose_market_filters.py --show-all
  - Expected: explains market rejection reasons
  - Notes: use --csv if team wants exports

- dutch_book_scanner.py
  - Command: python tools/dutch_book_scanner.py --once
  - Expected: prints opportunities or none
  - Notes: can be slow; use --limit and --once

- negrisk_scanner.py
  - Command: python tools/negrisk_scanner.py --once
  - Expected: prints opportunities or none
  - Notes: can be slow; use --limit and --once

- whale_tracker.py
  - Command: python tools/whale_tracker.py --leaderboard
  - Expected: shows top traders and recent large trades
  - Notes: read-only

- test_whale_copy.py
  - Command: python tools/test_whale_copy.py --test-all
  - Expected: profiler/monitor/engine tests pass
  - Notes: use --live-demo only with valid creds

- find_whale_wallet.py
  - Command: python tools/find_whale_wallet.py --top 5
  - Expected: list of wallets
  - Notes: read-only

- find_trending_whales.py
  - Command: python tools/find_trending_whales.py --platform reddit
  - Expected: returns trader mentions + suggested wallets
  - Notes: depends on web scraping; may be rate-limited

- live_social_search.py
  - Command: python tools/live_social_search.py --days 7
  - Expected: returns recent mentions
  - Notes: depends on web access; may be blocked

- telegram_alerts.py
  - Command: python tools/telegram_alerts.py --test
  - Expected: sends a test message
  - Notes: requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

- telegram_bot.py
  - Command: python tools/telegram_bot.py
  - Expected: responds to /status, /positions, /balance
  - Notes: stop any webhook if you see 409 Conflict

## Record Results
Create a short report per run and save to docs/reports/ with:
- Date/time
- Command
- Outcome (pass/fail)
- Notes or errors

Suggested filename:
- docs/reports/test_run_YYYY-MM-DD.md

## Recommendations & Resolutions
- **Automated Testing**: Nightly test runs are highly recommended using the new wrapper script.
- **Wrapper Script**: `scripts/run_readonly_tests.sh` has been implemented to run the read-only suite.
- **Config Maintenance**: Ensure the `trading` section remains in `config.json` for future concurrent order features.

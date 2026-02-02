# Test Report: Market & Position Tooling
Date/Time: 2026-02-02 16:47

## Commands Run
1. `venv/bin/python tools/analyze_positions.py`
2. `venv/bin/python tools/simulate_fills.py`
3. `venv/bin/python tools/diagnose_market_filters.py --show-all`

## Outcome
- **PASS**: `analyze_positions.py` successfully fetched live prices for all 5 positions.
  - Unrealized P&L: $-0.0004
  - 1 Winning, 4 Losing.
- **PASS**: `simulate_fills.py` confirmed no TP/SL triggers at current prices.
- **PASS**: `diagnose_market_filters.py` processed 50 markets.
  - 7 markets accepted.
  - 43 markets rejected (mostly due to `odds_out_of_range`).

## Notes
- Market detail fetching is currently disabled in config (`max_market_detail_fetch: 0`), which speeds up diagnostics.
- All 5 positions are currently in "HOLDING" status.

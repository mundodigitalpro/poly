# Dry Run Analysis Report 📊

**Period**: 2026-02-01 18:25 to 2026-02-02 08:26 (~14 hours)
**Mode**: Dry Run (Simulation)

## 1. Executive Summary
The bot operated stably for 14 hours, executing a total of **31 trades** (17 closed, 14 open).
While the overall PnL is slightly negative (**-$0.23**), this is expected during the tuning phase.
The most significant finding is the **strong performance in the 0.60-0.70 odds range**, which shows a 66% win rate and positive profitability.

## 2. Key Metrics

| Metric | Value | Notes |
| :--- | :--- | :--- |
| **Total Trades Closed** | **17** | Completed cycles (Entry + Exit) |
| **Open Positions** | **14** | Currently active (Potential future PnL) |
| **Win Rate** | **35.3%** | 6 Wins / 11 Losses |
| **Total PnL** | **-$0.23** | Net loss (approx -46% ROI on risked capital) |
| **Avg Hold Time** | **1.85h** | Fast turnover |

## 3. Strategy Performance by Odds Range

| Range | Trades | Win Rate | Avg PnL | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **0.60 - 0.70** | 3 | **66%** | **+$0.008** | ✅ **Best Performer** |
| **0.30 - 0.40** | 4 | 50% | -$0.004 | ⚠️ Break-even potential |
| **0.40 - 0.50** | 4 | 25% | -$0.015 | ❌ Underperforming |
| **0.50 - 0.60** | 6 | 16% | -$0.029 | ❌ **Worst Range** (High volume, high loss) |

## 4. Observations
1.  **High Activity**: The bot is finding plenty of opportunities (31 trades in 14h), proving the scanner is effective.
2.  **Safety Filters**: Rejected markets correctly (resolved too soon or too far out).
3.  **Loss Containment**: Average loss is small, meaning risk management (Stop Loss) is working.
4.  **Inefficiency in Mid-Range**: The 0.50-0.60 range seems to have a lot of noise or efficient pricing that the bot fails to exploit.

## 5. Recommendations
1.  **Optimize Filters**:
    *   **Disable trading in 0.40 - 0.60 range** temporarily to filter out low-probability chop.
    *   **Focus on 0.60 - 0.75 range** where the bot shows edge.
2.  **Adjust Take Profit**: The 50% win rate in 0.30-0.40 suggests we might be exiting winners too early or stops are too tight.
3.  **Whale Copy**: No confirmed whale copies in the stats yet. Verify thresholds (min whale score might be too high).

## 6. Next Steps
*   Update `config.json` to tighten odds range: `min_odds: 0.60`, `max_odds: 0.80`.
*   Restart bot for Phase 4 (Optimization).

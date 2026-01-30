#!/bin/bash
# Bot Monitor Script - Run anytime to check status
# Usage: ./scripts/monitor.sh

cd /home/josejordan/poly

echo "╔══════════════════════════════════════════════════════╗"
echo "║         POLYMARKET BOT MONITOR - $(date '+%H:%M:%S')          ║"
echo "╠══════════════════════════════════════════════════════╣"

# Check if bot is running
if pgrep -f "python main_bot.py" > /dev/null; then
    RUNTIME=$(ps -o etime= -p $(pgrep -f "python main_bot.py") 2>/dev/null | xargs)
    echo "║ Bot Status: ✅ RUNNING ($RUNTIME)                    "
else
    echo "║ Bot Status: ❌ STOPPED                               "
fi

# Positions
POSITIONS=$(cat data/positions.json | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
echo "║ Positions: $POSITIONS/20                              "

# Stats
cat data/stats.json 2>/dev/null | python3 -c "
import sys,json
s = json.load(sys.stdin)['lifetime']
print(f'║ Trades: {s[\"total_trades\"]} | Win Rate: {s[\"win_rate\"]*100:.1f}%')
print(f'║ Wins: {s[\"wins\"]} | Losses: {s[\"losses\"]}')
print(f'║ Total PnL: \${s[\"total_pnl\"]:.4f}')
" 2>/dev/null

echo "╠══════════════════════════════════════════════════════╣"
echo "║ Last 5 Events:                                       "
echo "╟──────────────────────────────────────────────────────"
TODAY=$(date +%Y-%m-%d)
grep -E "(STOP_LOSS|TAKE_PROFIT|Position opened)" logs/bot_$TODAY.log 2>/dev/null | tail -5 | while read line; do
    TIME=$(echo "$line" | grep -oP '\d{2}:\d{2}:\d{2}')
    if echo "$line" | grep -q "TAKE_PROFIT"; then
        echo "║ $TIME 🟢 Take Profit"
    elif echo "$line" | grep -q "STOP_LOSS"; then
        echo "║ $TIME 🔴 Stop Loss"
    elif echo "$line" | grep -q "Position opened"; then
        echo "║ $TIME 📈 New Position"
    fi
done
echo "╚══════════════════════════════════════════════════════╝"

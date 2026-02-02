#!/bin/bash

# run_readonly_tests.sh
# Automates the execution of read-only diagnostic tools.

LOG_FILE="docs/reports/readonly_test_run_$(date +%Y-%m-%d_%H-%M-%S).md"
PYTHON_BIN="venv/bin/python"

echo "# Read-Only Diagnostic Test Report" > "$LOG_FILE"
echo "Date: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

run_command() {
    local cmd="$1"
    local description="$2"
    echo "## $description" >> "$LOG_FILE"
    echo "\`\`\`bash" >> "$LOG_FILE"
    echo "$cmd" >> "$LOG_FILE"
    echo "\`\`\`" >> "$LOG_FILE"
    echo "### Result:" >> "$LOG_FILE"
    echo "\`\`\`" >> "$LOG_FILE"
    eval "$cmd" >> "$LOG_FILE" 2>&1
    echo "\`\`\`" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
}

echo "Starting read-only diagnostic tests..."

run_command "$PYTHON_BIN scripts/diagnose_config.py" "Environment & Config Diagnosis"
run_command "$PYTHON_BIN scripts/verify_wallet.py" "Wallet Verification"
run_command "bash scripts/status_bot.sh" "Bot Status"
run_command "$PYTHON_BIN tools/analyze_positions.py" "Position Analysis"
run_command "$PYTHON_BIN tools/simulate_fills.py" "Simulate Fills"
run_command "$PYTHON_BIN tools/diagnose_market_filters.py --show-all --limit 10" "Market Filters Diagnosis (Limit 10)"
run_command "$PYTHON_BIN tools/whale_tracker.py --leaderboard" "Whale Tracker Leaderboard"

echo "Tests completed. Report saved to $LOG_FILE"

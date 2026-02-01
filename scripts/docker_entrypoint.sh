#!/bin/bash
set -e

echo "🚀 Starting PolyBot Container"

# Trap SIGTERM/SIGINT for graceful shutdown
cleanup() {
    echo "🛑 Stopping bots..."
    ./scripts/stop_bot.sh
    exit 0
}
trap cleanup SIGTERM SIGINT

# 1. Start Telegram Bot (if enabled)
# We check if TELEGRAM_BOT_TOKEN is present in .env loaded by python
if grep -q "TELEGRAM_BOT_TOKEN=" .env; then
    echo "📱 Starting Telegram Bot..."
    python tools/telegram_bot.py > logs/telegram_docker.log 2>&1 &
    TELEGRAM_PID=$!
    echo "   Telegram PID: $TELEGRAM_PID"
fi

# 2. Start Main Bot (Foreground)
echo "🤖 Starting Main Bot..."
# Passing "$@" allows overriding flags like --verbose-filters via docker command
exec python main_bot.py "$@"

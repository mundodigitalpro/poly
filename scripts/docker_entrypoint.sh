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

# 1. Start Telegram Command Bot (ONLY if explicitly enabled)
# This bot receives commands via Telegram. Disabled by default to avoid
# conflicts with main_bot's notification system (HTTP 409 error).
# To enable, add TELEGRAM_COMMAND_BOT=true to .env
if grep -q "TELEGRAM_COMMAND_BOT=true" .env 2>/dev/null; then
    if grep -q "TELEGRAM_BOT_TOKEN=" .env; then
        echo "📱 Starting Telegram Command Bot..."
        python tools/telegram_bot.py > logs/telegram_docker.log 2>&1 &
        TELEGRAM_PID=$!
        echo "   Telegram Command Bot PID: $TELEGRAM_PID"
    else
        echo "⚠️  TELEGRAM_COMMAND_BOT=true but TELEGRAM_BOT_TOKEN not found"
    fi
else
    echo "ℹ️  Telegram Command Bot disabled (add TELEGRAM_COMMAND_BOT=true to .env to enable)"
fi

# 2. Start Main Bot (Foreground)
# Main bot handles trading and can send notifications if TELEGRAM_BOT_TOKEN is set
echo "🤖 Starting Main Bot..."
# Passing "$@" allows overriding flags like --verbose-filters via docker command
exec python main_bot.py "$@"

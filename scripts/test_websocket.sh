#!/bin/bash
# WebSocket Testing Script
# Tests the WebSocket implementation with real Polymarket data

set -e

echo "=========================================="
echo "WebSocket Stability Test"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "main_bot.py" ]; then
    echo "Error: Please run this script from the /home/user/poly directory"
    exit 1
fi

# Check if config.json exists
if [ ! -f "config.json" ]; then
    echo "Error: config.json not found"
    exit 1
fi

# Backup config
echo "1. Backing up config.json..."
cp config.json config.json.backup
echo "   ✓ Backup created: config.json.backup"
echo ""

# Enable WebSocket in config
echo "2. Enabling WebSocket in config.json..."
python3 -c "
import json
with open('config.json', 'r') as f:
    config = json.load(f)
config['trading']['use_websocket'] = True
config['bot']['dry_run'] = True
config['bot']['log_level'] = 'INFO'
with open('config.json', 'w') as f:
    json.dump(config, f, indent=2)
"
echo "   ✓ WebSocket enabled"
echo "   ✓ Dry run mode enabled"
echo "   ✓ Log level set to INFO"
echo ""

# Check for positions
echo "3. Checking for existing positions..."
if [ -f "data/positions.json" ]; then
    POSITION_COUNT=$(python3 -c "import json; print(len(json.load(open('data/positions.json'))))" 2>/dev/null || echo "0")
    echo "   Found $POSITION_COUNT position(s)"

    if [ "$POSITION_COUNT" -gt "0" ]; then
        echo "   WebSocket will subscribe to these positions"
    else
        echo "   Note: No positions to monitor. WebSocket will only connect."
    fi
else
    echo "   No positions.json file found"
fi
echo ""

# Check dependencies
echo "4. Checking dependencies..."
if python3 -c "import websockets" 2>/dev/null; then
    echo "   ✓ websockets library installed"
else
    echo "   ✗ websockets library not installed"
    echo "   Installing websockets..."
    pip install -q websockets>=12.0
    echo "   ✓ websockets installed"
fi
echo ""

# Display test instructions
echo "=========================================="
echo "Ready to Test WebSocket"
echo "=========================================="
echo ""
echo "The bot will run with these settings:"
echo "  - WebSocket: ENABLED"
echo "  - Dry run: ENABLED (no real trades)"
echo "  - Log level: INFO"
echo ""
echo "What to monitor:"
echo "  ✓ 'WebSocket connected to Polymarket'"
echo "  ✓ 'Subscribed to <token_id>...'"
echo "  ✓ Message types logged"
echo "  ✗ NO 'WebSocket connection closed' loops"
echo "  ✗ NO JSON parse errors"
echo ""
echo "Press Ctrl+C to stop the test"
echo ""
echo "=========================================="
echo ""

# Ask for confirmation
read -p "Start WebSocket test? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Test cancelled. Restoring config..."
    mv config.json.backup config.json
    exit 0
fi

echo "Starting bot with WebSocket enabled..."
echo ""
echo "=========================================="
echo ""

# Run the bot
python3 main_bot.py

# Restore config on exit
echo ""
echo "=========================================="
echo "Test completed. Restoring config..."
mv config.json.backup config.json
echo "✓ Config restored"
echo "=========================================="

#!/usr/bin/env python3
"""
Telegram alerts for Polymarket bot.

Setup:
1. Create bot with @BotFather on Telegram
2. Get your chat_id by messaging @userinfobot
3. Add to .env:
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id

Usage:
    python tools/telegram_alerts.py --test  # Send test message
    python tools/telegram_alerts.py --monitor  # Run alert monitor
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.parse

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TelegramBot:
    """Simple Telegram bot for sending alerts."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message to the configured chat."""
        try:
            url = f"{self.base_url}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }).encode()

            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
                return result.get("ok", False)

        except Exception as e:
            print(f"Telegram error: {e}")
            return False

    def send_alert(self, title: str, message: str, emoji: str = "🔔") -> bool:
        """Send a formatted alert."""
        text = f"{emoji} <b>{title}</b>\n\n{message}"
        return self.send_message(text)


def load_env():
    """Load environment variables."""
    from dotenv import load_dotenv
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    return token, chat_id


def get_bot() -> Optional[TelegramBot]:
    """Get configured Telegram bot."""
    token, chat_id = load_env()

    if not token or not chat_id:
        print("⚠️  Telegram not configured. Add to .env:")
        print("   TELEGRAM_BOT_TOKEN=your_bot_token")
        print("   TELEGRAM_CHAT_ID=your_chat_id")
        return None

    return TelegramBot(token, chat_id)


def send_position_alert(bot: TelegramBot, action: str, position: dict):
    """Send alert for position events."""
    token_id = position.get("token_id", "unknown")[:12]
    entry = position.get("entry_price", 0)
    size = position.get("size", 0)

    if action == "opened":
        tp = position.get("tp", 0)
        sl = position.get("sl", 0)
        msg = (
            f"Token: <code>{token_id}...</code>\n"
            f"Entry: ${entry:.4f}\n"
            f"Size: {size:.4f}\n"
            f"TP: ${tp:.4f} | SL: ${sl:.4f}"
        )
        bot.send_alert("Position Opened", msg, "📈")

    elif action == "tp_hit":
        exit_price = position.get("exit_price", 0)
        pnl = position.get("pnl_usd", 0)
        msg = (
            f"Token: <code>{token_id}...</code>\n"
            f"Entry: ${entry:.4f} → Exit: ${exit_price:.4f}\n"
            f"P&L: <b>${pnl:+.4f}</b>"
        )
        bot.send_alert("Take Profit Hit!", msg, "✅")

    elif action == "sl_hit":
        exit_price = position.get("exit_price", 0)
        pnl = position.get("pnl_usd", 0)
        msg = (
            f"Token: <code>{token_id}...</code>\n"
            f"Entry: ${entry:.4f} → Exit: ${exit_price:.4f}\n"
            f"P&L: <b>${pnl:+.4f}</b>"
        )
        bot.send_alert("Stop Loss Hit", msg, "❌")


def send_daily_summary(bot: TelegramBot, positions: dict, results: list):
    """Send daily summary."""
    total_positions = len(positions)
    total_value = sum(p["size"] * p["entry_price"] for p in positions.values())

    tp_hits = [r for r in results if r.get("type") == "take_profit"]
    sl_hits = [r for r in results if r.get("type") == "stop_loss"]
    total_pnl = sum(r.get("pnl_usd", 0) for r in results)

    msg = (
        f"📊 <b>Daily Summary</b>\n\n"
        f"Open Positions: {total_positions}\n"
        f"Total Value: ${total_value:.2f}\n\n"
        f"Today's Results:\n"
        f"  ✅ Take Profits: {len(tp_hits)}\n"
        f"  ❌ Stop Losses: {len(sl_hits)}\n"
        f"  💰 P&L: ${total_pnl:+.4f}"
    )
    bot.send_message(msg)


def monitor_alerts(interval: int = 300):
    """
    Monitor for alerts and send to Telegram.

    Runs the fill simulation periodically and sends alerts for new fills.
    """
    bot = get_bot()
    if not bot:
        return

    from tools.simulate_fills import simulate_fills, load_positions

    print(f"Starting alert monitor (interval: {interval}s)")
    print("Press Ctrl+C to stop\n")

    # Track seen results to avoid duplicates
    seen_fills = set()

    # Load existing results
    results_file = Path(__file__).parent.parent / "data" / "simulation_results.json"
    if results_file.exists():
        with open(results_file) as f:
            existing = json.load(f)
            for r in existing:
                key = f"{r['token_id']}_{r['type']}_{r['timestamp'][:10]}"
                seen_fills.add(key)

    bot.send_alert("Bot Monitor Started", f"Checking every {interval}s", "🤖")

    try:
        while True:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking fills...")

            results = simulate_fills(verbose=False)

            for r in results:
                key = f"{r['token_id']}_{r['type']}_{r['timestamp'][:10]}"
                if key not in seen_fills:
                    seen_fills.add(key)

                    # Send alert
                    action = "tp_hit" if r["type"] == "take_profit" else "sl_hit"
                    send_position_alert(bot, action, {
                        "token_id": r["token_id"],
                        "entry_price": r["entry_price"],
                        "exit_price": r["exit_price"],
                        "pnl_usd": r["pnl_usd"],
                    })
                    print(f"  Alert sent: {action} for {r['token_id'][:12]}...")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopping monitor...")
        bot.send_alert("Bot Monitor Stopped", "Manual shutdown", "🛑")


def test_connection():
    """Test Telegram connection."""
    bot = get_bot()
    if not bot:
        return False

    print("Sending test message...")
    success = bot.send_alert(
        "Test Alert",
        f"Connection successful!\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "🧪"
    )

    if success:
        print("✅ Test message sent successfully!")
    else:
        print("❌ Failed to send test message")

    return success


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Telegram alerts for Polymarket bot")
    parser.add_argument("--test", "-t", action="store_true", help="Send test message")
    parser.add_argument("--monitor", "-m", action="store_true", help="Run alert monitor")
    parser.add_argument("--interval", "-i", type=int, default=300,
                        help="Monitor interval in seconds (default: 300)")
    parser.add_argument("--summary", "-s", action="store_true", help="Send daily summary")
    args = parser.parse_args()

    if args.test:
        test_connection()
    elif args.monitor:
        monitor_alerts(args.interval)
    elif args.summary:
        bot = get_bot()
        if bot:
            positions = {}
            pos_file = Path(__file__).parent.parent / "data" / "positions.json"
            if pos_file.exists():
                with open(pos_file) as f:
                    positions = json.load(f)

            results = []
            res_file = Path(__file__).parent.parent / "data" / "simulation_results.json"
            if res_file.exists():
                with open(res_file) as f:
                    results = json.load(f)

            send_daily_summary(bot, positions, results)
            print("Summary sent!")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

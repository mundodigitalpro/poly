#!/usr/bin/env python3
"""
Standalone WebSocket Test Script

Tests the WebSocket client without running the full bot.
Connects to Polymarket WebSocket and monitors a sample market.
"""

import asyncio
import json
import sys
import os
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.websocket_client import PolymarketWebSocket, OrderbookSnapshot


class ColorLogger:
    """Simple colored logger for terminal output."""

    COLORS = {
        'INFO': '\033[94m',     # Blue
        'SUCCESS': '\033[92m',  # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'DEBUG': '\033[90m',    # Gray
        'RESET': '\033[0m'
    }

    def info(self, msg):
        print(f"{self.COLORS['INFO']}[INFO]{self.COLORS['RESET']} {msg}")

    def success(self, msg):
        print(f"{self.COLORS['SUCCESS']}[SUCCESS]{self.COLORS['RESET']} {msg}")

    def warn(self, msg):
        print(f"{self.COLORS['WARNING']}[WARN]{self.COLORS['RESET']} {msg}")

    def error(self, msg):
        print(f"{self.COLORS['ERROR']}[ERROR]{self.COLORS['RESET']} {msg}")

    def debug(self, msg):
        print(f"{self.COLORS['DEBUG']}[DEBUG]{self.COLORS['RESET']} {msg}")


async def test_websocket_connection(duration_seconds=60):
    """
    Test WebSocket connection and message handling.

    Args:
        duration_seconds: How long to run the test (default: 60 seconds)
    """
    logger = ColorLogger()

    print("=" * 70)
    print("WebSocket Standalone Test")
    print("=" * 70)
    print()

    # Configuration
    config = {
        "websocket_reconnect_delay": 5,
        "websocket_ping_interval": 30,
        "websocket_max_reconnects": 3
    }

    # Sample token IDs (popular markets)
    # You can replace these with actual token IDs from your positions
    sample_tokens = []

    # Try to load positions if available
    positions_file = "data/positions.json"
    if os.path.exists(positions_file):
        try:
            with open(positions_file, 'r') as f:
                positions = json.load(f)
                if positions:
                    sample_tokens = [pos['token_id'] for pos in positions[:3]]
                    logger.info(f"Loaded {len(sample_tokens)} token(s) from positions.json")
        except Exception as e:
            logger.warn(f"Could not load positions.json: {e}")

    if not sample_tokens:
        logger.warn("No positions found. Test will just connect without subscriptions.")
        logger.info("To test with real data, add positions to data/positions.json")

    print()
    logger.info(f"Test duration: {duration_seconds} seconds")
    logger.info(f"Token IDs to monitor: {len(sample_tokens)}")
    print()

    # Create WebSocket client
    ws = PolymarketWebSocket(logger, config)

    # Stats tracking
    message_types = {}
    update_count = 0
    start_time = time.time()

    # Register callback
    @ws.on_book_update
    async def on_update(snapshot: OrderbookSnapshot):
        nonlocal update_count
        update_count += 1

        timestamp = datetime.now().strftime("%H:%M:%S")
        logger.success(
            f"[{timestamp}] Update #{update_count} - "
            f"Token: {snapshot.token_id[:8]}... | "
            f"Bid: {snapshot.best_bid:.4f} | "
            f"Ask: {snapshot.best_ask:.4f} | "
            f"Mid: {snapshot.mid_price:.4f} | "
            f"Spread: {snapshot.spread_percent:.2f}%"
        )

    # Connect
    logger.info("Connecting to Polymarket WebSocket...")
    if not await ws.connect():
        logger.error("Failed to connect")
        return False

    logger.success("Connected!")
    print()

    # Subscribe if we have tokens
    if sample_tokens:
        logger.info(f"Subscribing to {len(sample_tokens)} token(s)...")
        await ws.subscribe(sample_tokens)
        logger.success("Subscribed!")
        print()

    # Run WebSocket in background
    websocket_task = asyncio.create_task(ws.run(auto_reconnect=True))

    logger.info("Monitoring WebSocket... (Press Ctrl+C to stop)")
    print()
    print("-" * 70)
    print()

    # Monitor for specified duration
    try:
        await asyncio.sleep(duration_seconds)
    except asyncio.CancelledError:
        logger.info("Test interrupted by user")

    # Stop WebSocket
    logger.info("Stopping WebSocket...")
    await ws.close()

    try:
        websocket_task.cancel()
        await websocket_task
    except asyncio.CancelledError:
        pass

    # Print statistics
    print()
    print("=" * 70)
    print("Test Results")
    print("=" * 70)
    print()

    stats = ws.get_stats()
    elapsed = time.time() - start_time

    logger.info(f"Test duration: {elapsed:.1f} seconds")
    logger.info(f"Messages received: {stats['messages_received']}")
    logger.info(f"Orderbook updates: {update_count}")
    logger.info(f"Reconnects: {stats['reconnect_count']}")
    logger.info(f"Subscribed tokens: {stats['subscribed_tokens']}")
    logger.info(f"Cached orderbooks: {stats['cached_orderbooks']}")

    if stats['last_message_age'] is not None:
        logger.info(f"Last message: {stats['last_message_age']:.1f}s ago")

    print()

    # Success criteria
    success = True

    if stats['messages_received'] == 0:
        logger.warn("⚠️  No messages received")
        if sample_tokens:
            logger.warn("   This might indicate a subscription issue")
        else:
            logger.info("   This is expected with no token subscriptions")
    else:
        logger.success(f"✓ Received {stats['messages_received']} messages")

    if stats['reconnect_count'] > 0:
        logger.warn(f"⚠️  Had {stats['reconnect_count']} reconnection(s)")
        logger.warn("   Check for connection stability issues")
    else:
        logger.success("✓ No reconnections (stable connection)")

    if update_count > 0:
        logger.success(f"✓ Received {update_count} orderbook updates")
        logger.success(f"✓ Callbacks working correctly")
    elif sample_tokens:
        logger.warn("⚠️  No orderbook updates received")
        logger.warn("   Markets might be inactive or have low liquidity")

    print()

    if success and stats['messages_received'] > 0 and stats['reconnect_count'] == 0:
        logger.success("✓ WebSocket test PASSED")
        return True
    else:
        logger.warn("⚠️  WebSocket test completed with warnings")
        return False


async def main():
    """Main test entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Test Polymarket WebSocket connection')
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Test duration in seconds (default: 60)'
    )
    parser.add_argument(
        '--tokens',
        nargs='+',
        help='Token IDs to subscribe to (optional)'
    )

    args = parser.parse_args()

    # Override sample tokens if provided
    if args.tokens:
        # Inject custom tokens for testing
        # (This is a bit hacky but works for a test script)
        import bot.websocket_client
        original_positions_file = "data/positions.json"
        if os.path.exists(original_positions_file):
            os.rename(original_positions_file, original_positions_file + ".backup")

        try:
            # Create temporary positions file
            positions = [{'token_id': token} for token in args.tokens]
            with open("data/positions.json", 'w') as f:
                json.dump(positions, f)

            # Run test
            success = await test_websocket_connection(duration_seconds=args.duration)
        finally:
            # Restore original positions
            os.remove("data/positions.json")
            if os.path.exists(original_positions_file + ".backup"):
                os.rename(original_positions_file + ".backup", original_positions_file)
    else:
        success = await test_websocket_connection(duration_seconds=args.duration)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)

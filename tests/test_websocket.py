#!/usr/bin/env python3
"""
Unit tests for WebSocket client.

Tests the WebSocket logic without requiring actual WebSocket connection.
"""

import sys
import os
import json
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_orderbook_snapshot_properties():
    """Test OrderbookSnapshot calculations."""
    from bot.websocket_client import OrderbookSnapshot

    # Create snapshot with realistic data
    snapshot = OrderbookSnapshot(
        token_id="test_token_123",
        timestamp=time.time(),
        bids=[(0.48, 100), (0.47, 200), (0.46, 150)],
        asks=[(0.52, 100), (0.53, 150), (0.54, 200)],
    )

    # Test best bid (highest bid)
    assert snapshot.best_bid == 0.48, "Best bid should be highest bid price"

    # Test best ask (lowest ask)
    assert snapshot.best_ask == 0.52, "Best ask should be lowest ask price"

    # Test mid price
    expected_mid = (0.48 + 0.52) / 2
    assert snapshot.mid_price == expected_mid, f"Mid price should be {expected_mid}"

    # Test spread
    expected_spread = 0.52 - 0.48
    assert (
        abs(snapshot.spread - expected_spread) < 0.0001
    ), f"Spread should be {expected_spread}"

    # Test spread percent
    expected_spread_pct = (expected_spread / expected_mid) * 100
    assert (
        abs(snapshot.spread_percent - expected_spread_pct) < 0.01
    ), f"Spread % should be ~{expected_spread_pct}"

    print("✓ OrderbookSnapshot properties work correctly")
    return True


def test_orderbook_snapshot_empty():
    """Test OrderbookSnapshot with empty bids/asks."""
    from bot.websocket_client import OrderbookSnapshot

    # Empty orderbook
    snapshot = OrderbookSnapshot(
        token_id="test_token_empty", timestamp=time.time(), bids=[], asks=[]
    )

    assert snapshot.best_bid == 0.0, "Empty bids should return 0.0"
    assert snapshot.best_ask == 0.0, "Empty asks should return 0.0"
    assert snapshot.mid_price == 0.0, "Empty orderbook mid price should be 0.0"
    assert snapshot.spread == 0.0, "Empty orderbook spread should be 0.0"

    print("✓ OrderbookSnapshot handles empty orderbook correctly")
    return True


def test_websocket_initialization():
    """Test WebSocket client initialization."""
    from bot.websocket_client import PolymarketWebSocket

    class MockLogger:
        def info(self, msg):
            pass

        def warn(self, msg):
            pass

        def error(self, msg):
            pass

        def debug(self, msg):
            pass

    logger = MockLogger()

    # Test with default config
    ws = PolymarketWebSocket(logger)
    assert ws.reconnect_delay == 5, "Default reconnect delay should be 5"
    assert ws.ping_interval == 30, "Default ping interval should be 30"
    assert ws.max_reconnects == 10, "Default max reconnects should be 10"
    assert ws.running == False, "Should not be running initially"
    assert len(ws.subscribed_tokens) == 0, "Should have no subscriptions initially"

    # Test with custom config
    config = {
        "websocket_reconnect_delay": 10,
        "websocket_ping_interval": 60,
        "websocket_max_reconnects": 5,
    }
    ws2 = PolymarketWebSocket(logger, config)
    assert ws2.reconnect_delay == 10, "Custom reconnect delay should be respected"
    assert ws2.ping_interval == 60, "Custom ping interval should be respected"
    assert ws2.max_reconnects == 5, "Custom max reconnects should be respected"

    print("✓ WebSocket initialization works correctly")
    return True


def test_orderbook_parsing():
    """Test parsing WebSocket message to OrderbookSnapshot."""
    from bot.websocket_client import PolymarketWebSocket

    class MockLogger:
        def info(self, msg):
            pass

        def warn(self, msg):
            pass

        def error(self, msg):
            pass

        def debug(self, msg):
            pass

    logger = MockLogger()
    ws = PolymarketWebSocket(logger)

    # Mock WebSocket message
    message_data = {
        "type": "book",
        "market": "test_token_789",
        "timestamp": 1706635200,
        "bids": [
            {"price": "0.49", "size": "100.5"},
            {"price": "0.48", "size": "200.75"},
        ],
        "asks": [
            {"price": "0.51", "size": "150.25"},
            {"price": "0.52", "size": "300.0"},
        ],
    }

    # Parse orderbook
    snapshot = ws._parse_orderbook(message_data)

    assert snapshot.token_id == "test_token_789"
    assert snapshot.timestamp == 1706635200
    assert len(snapshot.bids) == 2
    assert len(snapshot.asks) == 2
    assert snapshot.bids[0] == (0.49, 100.5)
    assert snapshot.asks[0] == (0.51, 150.25)
    assert snapshot.best_bid == 0.49
    assert snapshot.best_ask == 0.51

    print("✓ Orderbook parsing works correctly")
    return True


def test_orderbook_parsing_invalid_data():
    """Test parsing with invalid/malformed data."""
    from bot.websocket_client import PolymarketWebSocket

    class MockLogger:
        def info(self, msg):
            pass

        def warn(self, msg):
            pass

        def error(self, msg):
            pass

        def debug(self, msg):
            pass

    logger = MockLogger()
    ws = PolymarketWebSocket(logger)

    # Message with invalid prices
    message_data = {
        "type": "book",
        "market": "test_token_invalid",
        "timestamp": 1706635200,
        "bids": [
            {"price": "invalid", "size": "100"},
            {"price": "0.48", "size": "not_a_number"},
            {"price": "0", "size": "100"},  # Zero price should be filtered
        ],
        "asks": [
            {"price": "0.51", "size": "150"},
        ],
    }

    snapshot = ws._parse_orderbook(message_data)

    # Should skip invalid entries
    assert len(snapshot.bids) == 0, "Invalid bids should be filtered"
    assert len(snapshot.asks) == 1, "Valid asks should be kept"

    print("✓ Orderbook parsing handles invalid data correctly")
    return True


def test_get_orderbook():
    """Test getting cached orderbook."""
    from bot.websocket_client import PolymarketWebSocket, OrderbookSnapshot

    class MockLogger:
        def info(self, msg):
            pass

        def warn(self, msg):
            pass

        def error(self, msg):
            pass

        def debug(self, msg):
            pass

    logger = MockLogger()
    ws = PolymarketWebSocket(logger)

    # Add snapshot to cache
    snapshot = OrderbookSnapshot(
        token_id="cached_token", timestamp=time.time(), bids=[(0.50, 100)], asks=[(0.52, 100)]
    )
    ws.orderbooks["cached_token"] = snapshot

    # Get cached snapshot
    retrieved = ws.get_orderbook("cached_token")
    assert retrieved is not None, "Should retrieve cached snapshot"
    assert retrieved.token_id == "cached_token"
    assert retrieved.best_bid == 0.50

    # Try non-existent token
    missing = ws.get_orderbook("non_existent")
    assert missing is None, "Should return None for non-existent token"

    print("✓ Orderbook caching works correctly")
    return True


def test_stats():
    """Test WebSocket statistics."""
    from bot.websocket_client import PolymarketWebSocket

    class MockLogger:
        def info(self, msg):
            pass

        def warn(self, msg):
            pass

        def error(self, msg):
            pass

        def debug(self, msg):
            pass

    logger = MockLogger()
    ws = PolymarketWebSocket(logger)

    # Initial stats
    stats = ws.get_stats()
    assert stats["connected"] == False, "Should not be connected initially"
    assert stats["subscribed_tokens"] == 0
    assert stats["cached_orderbooks"] == 0
    assert stats["messages_received"] == 0
    assert stats["reconnect_count"] == 0

    # Simulate some activity
    ws.subscribed_tokens = ["token1", "token2"]
    ws.messages_received = 150
    ws.reconnect_count = 2

    stats = ws.get_stats()
    assert stats["subscribed_tokens"] == 2
    assert stats["messages_received"] == 150
    assert stats["reconnect_count"] == 2

    print("✓ Statistics tracking works correctly")
    return True


def test_callback_registration():
    """Test registering callbacks."""
    from bot.websocket_client import PolymarketWebSocket

    class MockLogger:
        def info(self, msg):
            pass

        def warn(self, msg):
            pass

        def error(self, msg):
            pass

        def debug(self, msg):
            pass

    logger = MockLogger()
    ws = PolymarketWebSocket(logger)

    # No callbacks initially
    assert len(ws.callbacks) == 0

    # Register callback
    async def callback1(snapshot):
        pass

    ws.on_book_update(callback1)
    assert len(ws.callbacks) == 1

    # Register another
    async def callback2(snapshot):
        pass

    ws.on_book_update(callback2)
    assert len(ws.callbacks) == 2

    print("✓ Callback registration works correctly")
    return True


def run_all_tests():
    """Run all unit tests."""
    tests = [
        ("OrderbookSnapshot properties", test_orderbook_snapshot_properties),
        ("OrderbookSnapshot empty", test_orderbook_snapshot_empty),
        ("WebSocket initialization", test_websocket_initialization),
        ("Orderbook parsing", test_orderbook_parsing),
        ("Orderbook parsing invalid data", test_orderbook_parsing_invalid_data),
        ("Get cached orderbook", test_get_orderbook),
        ("Statistics tracking", test_stats),
        ("Callback registration", test_callback_registration),
    ]

    print("=" * 60)
    print("Running WebSocket Unit Tests")
    print("=" * 60)
    print()

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"Testing: {name}")
            test_func()
            passed += 1
            print()
        except Exception as e:
            print(f"✗ FAILED: {e}")
            print()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

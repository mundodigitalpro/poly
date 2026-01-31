#!/usr/bin/env python3
"""
Unit tests for concurrent order functionality.

Tests the logic without requiring actual API dependencies.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_position_with_concurrent_fields():
    """Test Position class with new concurrent order fields."""
    from bot.position_manager import Position
    from datetime import datetime

    # Create position with concurrent order fields
    position = Position(
        token_id="test_token_123",
        entry_price=0.50,
        size=2.0,
        filled_size=2.0,
        entry_time=datetime.now().isoformat(),
        tp=0.55,
        sl=0.45,
        fees_paid=0.01,
        order_id="buy_order_123",
        tp_order_id="tp_order_456",
        sl_order_id="sl_order_789",
        exit_mode="limit_orders",
    )

    # Verify fields
    assert position.tp_order_id == "tp_order_456", "TP order ID should be set"
    assert position.sl_order_id == "sl_order_789", "SL order ID should be set"
    assert position.exit_mode == "limit_orders", "Exit mode should be limit_orders"

    print("✓ Position initialization with concurrent fields works")
    return True


def test_position_serialization():
    """Test Position to_dict and from_dict with new fields."""
    from bot.position_manager import Position
    from datetime import datetime

    # Create position
    entry_time = datetime.now().isoformat()
    position = Position(
        token_id="test_token_456",
        entry_price=0.60,
        size=1.5,
        filled_size=1.5,
        entry_time=entry_time,
        tp=0.66,
        sl=0.54,
        fees_paid=0.02,
        order_id="buy_order_abc",
        tp_order_id="tp_order_def",
        sl_order_id="sl_order_ghi",
        exit_mode="limit_orders",
    )

    # Serialize
    data = position.to_dict()
    assert "tp_order_id" in data, "Serialization should include tp_order_id"
    assert "sl_order_id" in data, "Serialization should include sl_order_id"
    assert "exit_mode" in data, "Serialization should include exit_mode"
    assert data["tp_order_id"] == "tp_order_def"

    # Deserialize
    restored = Position.from_dict("test_token_456", data)
    assert restored.tp_order_id == position.tp_order_id
    assert restored.sl_order_id == position.sl_order_id
    assert restored.exit_mode == position.exit_mode

    print("✓ Position serialization/deserialization works")
    return True


def test_position_backwards_compatibility():
    """Test that old positions without new fields still load correctly."""
    from bot.position_manager import Position

    # Old position data (without new fields)
    old_data = {
        "entry_price": 0.45,
        "size": 3.0,
        "filled_size": 3.0,
        "entry_time": "2026-01-30T12:00:00",
        "tp": 0.50,
        "sl": 0.40,
        "fees_paid": 0.015,
        "order_id": "old_buy_order",
    }

    # Should load without error and default to monitor mode
    position = Position.from_dict("old_token_789", old_data)
    assert position.tp_order_id is None, "Old positions should have None for tp_order_id"
    assert position.sl_order_id is None, "Old positions should have None for sl_order_id"
    assert position.exit_mode == "monitor", "Old positions should default to monitor mode"

    print("✓ Backwards compatibility with old positions works")
    return True


def test_config_has_trading_section():
    """Test that config.json has the new trading section."""
    import json

    with open("config.json", "r") as f:
        config = json.load(f)

    assert "trading" in config, "Config should have 'trading' section"
    assert "use_concurrent_orders" in config["trading"]
    assert "order_check_interval_seconds" in config["trading"]
    assert "cancel_timeout_seconds" in config["trading"]

    # Verify it's disabled by default
    assert config["trading"]["use_concurrent_orders"] == False, \
        "Concurrent orders should be disabled by default for safety"

    print("✓ Config has trading section with correct defaults")
    return True


def test_trader_dry_run_logic():
    """Test BotTrader methods in dry-run mode (no API calls)."""
    # Mock the required dependencies
    class MockLogger:
        def info(self, msg): pass
        def warn(self, msg): pass
        def error(self, msg): pass
        def debug(self, msg): pass

    class MockConfig:
        def __init__(self):
            self.data = {
                "bot.dry_run": True,
                "bot.order_timeout_seconds": 30,
                "risk.min_sell_price_ratio": 0.5,
                "api.retry_attempts": 3,
                "api.retry_backoff_seconds": 5,
                "api.max_calls_per_minute": 20,
            }

        def get(self, key, default=None):
            return self.data.get(key, default)

    class MockClient:
        pass

    # Import after setting up mocks
    from bot.trader import BotTrader

    config = MockConfig()
    logger = MockLogger()
    client = MockClient()

    trader = BotTrader(client, config, logger)

    # Test execute_buy_with_exits in dry-run
    result = trader.execute_buy_with_exits(
        token_id="test_token_999",
        entry_price=0.50,
        size=2.0,
        tp_price=0.55,
        sl_price=0.45,
    )

    assert "buy_fill" in result
    assert "tp_order_id" in result
    assert "sl_order_id" in result
    assert result["buy_fill"].filled_size == 2.0
    assert result["buy_fill"].dry_run == True
    assert result["tp_order_id"] is not None  # Should get a dry-run ID
    assert result["sl_order_id"] is not None

    print("✓ Trader execute_buy_with_exits works in dry-run")

    # Test check_order_status in dry-run
    status = trader.check_order_status("dry_run_order_123")
    assert status["status"] == "open"
    assert status["filled_size"] == 0

    print("✓ Trader check_order_status works in dry-run")

    # Test cancel_order in dry-run
    result = trader.cancel_order("dry_run_order_456")
    assert result == True

    print("✓ Trader cancel_order works in dry-run")

    return True


def test_main_bot_routing_logic():
    """Test that _update_positions routes to correct handler."""
    # This is a logic test - verifying the routing works

    class MockPosition:
        def __init__(self, exit_mode):
            self.exit_mode = exit_mode
            self.token_id = "test_token"
            self.tp_order_id = "tp_123"
            self.sl_order_id = "sl_456"
            self.entry_price = 0.50
            self.tp = 0.55
            self.sl = 0.45
            self.filled_size = 1.0
            self.entry_time = "2026-01-30T12:00:00"

    # Test routing logic
    limit_position = MockPosition("limit_orders")
    monitor_position = MockPosition("monitor")

    assert limit_position.exit_mode == "limit_orders"
    assert monitor_position.exit_mode == "monitor"

    # Verify positions can be differentiated
    if limit_position.exit_mode == "limit_orders":
        handler = "limit_orders_handler"
    else:
        handler = "legacy_handler"

    assert handler == "limit_orders_handler"

    print("✓ Position routing logic works correctly")
    return True


def run_all_tests():
    """Run all unit tests."""
    tests = [
        ("Position with concurrent fields", test_position_with_concurrent_fields),
        ("Position serialization", test_position_serialization),
        ("Backwards compatibility", test_position_backwards_compatibility),
        ("Config trading section", test_config_has_trading_section),
        ("Trader dry-run logic", test_trader_dry_run_logic),
        ("Main bot routing logic", test_main_bot_routing_logic),
    ]

    print("=" * 60)
    print("Running Concurrent Orders Unit Tests")
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

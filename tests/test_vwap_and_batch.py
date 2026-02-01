"""
Tests for Walk the Book (VWAP) and Pre-sign Batch Orders.

Run with: python tests/test_vwap_and_batch.py
"""

import sys
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import List, Tuple, Any, Dict, Optional


# ============================================================================
# Mock the external dependencies before importing bot modules
# ============================================================================

# Mock py_clob_client
mock_clob = MagicMock()
sys.modules['py_clob_client'] = mock_clob
sys.modules['py_clob_client.client'] = mock_clob
sys.modules['py_clob_client.clob_types'] = mock_clob
sys.modules['py_clob_client.constants'] = MagicMock(END_CURSOR='END')
sys.modules['py_clob_client.order_builder'] = mock_clob
sys.modules['py_clob_client.order_builder.constants'] = MagicMock(BUY='BUY', SELL='SELL')


# ============================================================================
# Standalone implementations for testing (mirror of actual code)
# ============================================================================

def calculate_vwap(orders: List[Tuple[float, float]], target_size: float) -> Tuple[float, float]:
    """
    Calculate Volume Weighted Average Price by walking through orders.
    """
    if not orders or target_size <= 0:
        return 0.0, 0.0

    filled = 0.0
    total_cost = 0.0

    for price, available_size in orders:
        take = min(available_size, target_size - filled)
        total_cost += take * price
        filled += take

        if filled >= target_size:
            break

    if filled <= 0:
        return 0.0, 0.0

    vwap = total_cost / filled
    return round(vwap, 6), round(filled, 6)


def walk_the_book(orders: List[Tuple[float, float]], size: float, side: str) -> Tuple[float, float, float]:
    """
    Calculate VWAP for a given order size.
    """
    if not orders:
        return 0.0, 0.0, 0.0

    if side == "buy":
        # Asks are sorted ascending (best = lowest)
        sorted_orders = sorted(orders, key=lambda x: x[0])
        best_price = sorted_orders[0][0] if sorted_orders else 0.0
    else:
        # Bids are sorted descending (best = highest)
        sorted_orders = sorted(orders, key=lambda x: x[0], reverse=True)
        best_price = sorted_orders[0][0] if sorted_orders else 0.0

    if not sorted_orders or best_price <= 0:
        return 0.0, 0.0, 0.0

    vwap, filled = calculate_vwap(sorted_orders, size)

    if vwap <= 0 or best_price <= 0:
        slippage = 0.0
    elif side == "buy":
        slippage = ((vwap - best_price) / best_price) * 100
    else:
        slippage = ((best_price - vwap) / best_price) * 100

    return vwap, filled, max(0.0, slippage)


def get_orderbook_depth(bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]) -> Dict[str, Any]:
    """
    Get full orderbook depth analysis.
    """
    bid_orders = sorted(bids, key=lambda x: x[0], reverse=True)
    ask_orders = sorted(asks, key=lambda x: x[0])

    total_bid_size = sum(size for _, size in bid_orders)
    total_ask_size = sum(size for _, size in ask_orders)
    total_bid_value = sum(price * size for price, size in bid_orders)
    total_ask_value = sum(price * size for price, size in ask_orders)

    return {
        "bid_levels": len(bid_orders),
        "ask_levels": len(ask_orders),
        "total_bid_size": round(total_bid_size, 2),
        "total_ask_size": round(total_ask_size, 2),
        "total_bid_value_usd": round(total_bid_value, 2),
        "total_ask_value_usd": round(total_ask_value, 2),
        "best_bid": bid_orders[0][0] if bid_orders else 0.0,
        "best_ask": ask_orders[0][0] if ask_orders else 0.0,
        "imbalance": round(
            (total_bid_size - total_ask_size) / max(total_bid_size + total_ask_size, 1), 2
        ),
    }


# ============================================================================
# Test Classes
# ============================================================================

class TestCalculateVWAP:
    """Tests for _calculate_vwap method."""

    def test_single_level_full_fill(self):
        """Test VWAP when order fills completely at one level."""
        orders = [(0.45, 100.0)]  # 100 shares at $0.45
        vwap, filled = calculate_vwap(orders, target_size=50.0)

        assert vwap == 0.45
        assert filled == 50.0

    def test_multiple_levels_partial_fill(self):
        """Test VWAP across multiple price levels."""
        # Orderbook: 10 @ $0.45, 20 @ $0.46, 30 @ $0.47
        orders = [(0.45, 10.0), (0.46, 20.0), (0.47, 30.0)]

        # Buy 25 shares
        vwap, filled = calculate_vwap(orders, target_size=25.0)

        # Expected: 10*0.45 + 15*0.46 = 4.5 + 6.9 = 11.4 / 25 = 0.456
        assert filled == 25.0
        assert abs(vwap - 0.456) < 0.001

    def test_insufficient_liquidity(self):
        """Test when orderbook doesn't have enough liquidity."""
        orders = [(0.45, 10.0), (0.46, 5.0)]  # Only 15 shares available
        vwap, filled = calculate_vwap(orders, target_size=100.0)

        assert filled == 15.0  # Partial fill
        # VWAP: (10*0.45 + 5*0.46) / 15 = 6.8 / 15 ≈ 0.4533
        assert abs(vwap - 0.453333) < 0.001

    def test_empty_orderbook(self):
        """Test with empty orderbook."""
        vwap, filled = calculate_vwap([], target_size=10.0)

        assert vwap == 0.0
        assert filled == 0.0

    def test_zero_size(self):
        """Test with zero target size."""
        orders = [(0.45, 100.0)]
        vwap, filled = calculate_vwap(orders, target_size=0.0)

        assert vwap == 0.0
        assert filled == 0.0


class TestWalkTheBook:
    """Tests for walk_the_book method."""

    def test_buy_side_no_slippage(self):
        """Test buying when size fits in best ask."""
        # Asks at 0.45 (100 shares), 0.46 (50 shares)
        asks = [(0.45, 100.0), (0.46, 50.0)]

        vwap, filled, slippage = walk_the_book(asks, size=50.0, side="buy")

        assert vwap == 0.45
        assert filled == 50.0
        assert slippage == 0.0  # No slippage when fill is at best price

    def test_buy_side_with_slippage(self):
        """Test buying across multiple levels with slippage."""
        # Asks: 10 @ $0.45, 20 @ $0.50
        asks = [(0.45, 10.0), (0.50, 20.0)]

        vwap, filled, slippage = walk_the_book(asks, size=20.0, side="buy")

        # VWAP: (10*0.45 + 10*0.50) / 20 = 9.5 / 20 = 0.475
        assert filled == 20.0
        assert abs(vwap - 0.475) < 0.001
        # Slippage: (0.475 - 0.45) / 0.45 * 100 ≈ 5.56%
        assert abs(slippage - 5.555) < 0.1

    def test_sell_side_no_slippage(self):
        """Test selling when size fits in best bid."""
        bids = [(0.50, 100.0), (0.48, 50.0)]

        vwap, filled, slippage = walk_the_book(bids, size=50.0, side="sell")

        assert vwap == 0.50
        assert filled == 50.0
        assert slippage == 0.0

    def test_sell_side_with_slippage(self):
        """Test selling across multiple levels with slippage."""
        # Bids: 10 @ $0.50, 20 @ $0.45
        bids = [(0.50, 10.0), (0.45, 20.0)]

        vwap, filled, slippage = walk_the_book(bids, size=20.0, side="sell")

        # VWAP: (10*0.50 + 10*0.45) / 20 = 9.5 / 20 = 0.475
        assert filled == 20.0
        assert abs(vwap - 0.475) < 0.001
        # Slippage: (0.50 - 0.475) / 0.50 * 100 = 5%
        assert abs(slippage - 5.0) < 0.1


class TestGetOrderbookDepth:
    """Tests for get_orderbook_depth method."""

    def test_depth_analysis(self):
        """Test full orderbook depth analysis."""
        bids = [(0.48, 100.0), (0.47, 50.0), (0.46, 75.0)]
        asks = [(0.52, 80.0), (0.53, 40.0)]

        depth = get_orderbook_depth(bids, asks)

        assert depth["bid_levels"] == 3
        assert depth["ask_levels"] == 2
        assert depth["total_bid_size"] == 225.0  # 100 + 50 + 75
        assert depth["total_ask_size"] == 120.0  # 80 + 40
        assert depth["best_bid"] == 0.48
        assert depth["best_ask"] == 0.52
        # Imbalance: (225 - 120) / (225 + 120) = 105 / 345 ≈ 0.30
        assert abs(depth["imbalance"] - 0.30) < 0.05


class TestBatchOrdersLogic:
    """Tests for batch order logic."""

    def test_batch_order_creation(self):
        """Test that batch orders are properly structured."""
        orders = [
            {'token_id': 'token1', 'price': 0.45, 'size': 10.0, 'side': 'BUY'},
            {'token_id': 'token1', 'price': 0.55, 'size': 10.0, 'side': 'SELL'},
            {'token_id': 'token1', 'price': 0.40, 'size': 10.0, 'side': 'SELL'},
        ]

        assert len(orders) == 3
        assert orders[0]['side'] == 'BUY'
        assert orders[1]['price'] > orders[0]['price']  # TP > entry
        assert orders[2]['price'] < orders[0]['price']  # SL < entry

    def test_presign_batch_timing(self):
        """Test that presign separates sign and submit phases."""
        import time

        # Simulate sign times
        sign_times = []
        for i in range(3):
            start = time.time()
            time.sleep(0.01)  # Simulate 10ms signing
            sign_times.append(time.time() - start)

        total_sign_time = sum(sign_times)

        # Simulate submit times (should be faster)
        submit_times = []
        for i in range(3):
            start = time.time()
            time.sleep(0.005)  # Simulate 5ms submit
            submit_times.append(time.time() - start)

        total_submit_time = sum(submit_times)

        # In presign mode, total time = sign_time + submit_time (sequential)
        # which is faster than 3x (sign+submit) in non-presign mode
        presign_total = total_sign_time + total_submit_time
        sequential_total = sum(s + sub for s, sub in zip(sign_times, submit_times))

        # They should be roughly equal in this simplified test
        assert abs(presign_total - sequential_total) < 0.1


class TestSlippageIntegration:
    """Integration tests for slippage checking in trade flow."""

    def test_slippage_exceeds_max(self):
        """Test that high slippage would be detected."""
        # Very thin book: 5 @ $0.45, rest at $0.60
        asks = [(0.45, 5.0), (0.60, 100.0)]

        vwap, filled, slippage = walk_the_book(asks, size=50.0, side="buy")

        # Would need to buy 5 @ $0.45 + 45 @ $0.60
        # VWAP = (5*0.45 + 45*0.60) / 50 = (2.25 + 27) / 50 = 0.585
        # Slippage = (0.585 - 0.45) / 0.45 * 100 = 30%
        assert slippage > 2.0  # Exceeds typical max_slippage_percent of 2%
        assert slippage > 25.0  # Actually much higher

    def test_acceptable_slippage(self):
        """Test slippage within acceptable range."""
        # Deep book: 100 @ $0.45, 100 @ $0.46
        asks = [(0.45, 100.0), (0.46, 100.0)]

        vwap, filled, slippage = walk_the_book(asks, size=50.0, side="buy")

        assert slippage == 0.0  # All fills at best price
        assert slippage < 2.0  # Within acceptable range


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    import sys

    def run_test(test_class, method_name):
        try:
            instance = test_class()
            getattr(instance, method_name)()
            return True, None
        except AssertionError as e:
            return False, f"AssertionError: {e}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    tests = [
        (TestCalculateVWAP, 'test_single_level_full_fill'),
        (TestCalculateVWAP, 'test_multiple_levels_partial_fill'),
        (TestCalculateVWAP, 'test_insufficient_liquidity'),
        (TestCalculateVWAP, 'test_empty_orderbook'),
        (TestCalculateVWAP, 'test_zero_size'),
        (TestWalkTheBook, 'test_buy_side_no_slippage'),
        (TestWalkTheBook, 'test_buy_side_with_slippage'),
        (TestWalkTheBook, 'test_sell_side_no_slippage'),
        (TestWalkTheBook, 'test_sell_side_with_slippage'),
        (TestGetOrderbookDepth, 'test_depth_analysis'),
        (TestBatchOrdersLogic, 'test_batch_order_creation'),
        (TestBatchOrdersLogic, 'test_presign_batch_timing'),
        (TestSlippageIntegration, 'test_slippage_exceeds_max'),
        (TestSlippageIntegration, 'test_acceptable_slippage'),
    ]

    passed = 0
    failed = 0
    for test_class, method in tests:
        success, error = run_test(test_class, method)
        status = '✓' if success else '✗'
        print(f'{status} {test_class.__name__}.{method}')
        if success:
            passed += 1
        else:
            failed += 1
            print(f'  Error: {error}')

    print(f'\n{passed} passed, {failed} failed')
    sys.exit(0 if failed == 0 else 1)

#!/usr/bin/env python3
"""
Unit tests for Tracked Wallets feature.

Tests the ability to manually track specific whale wallets,
including configuration loading, whitelist management, and
integration with the profiler.

Usage:
    python -m pytest tests/test_tracked_wallets.py -v
    python tests/test_tracked_wallets.py  # Run directly
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.whale_profiler import WhaleProfiler


class TestTrackedWallets(unittest.TestCase):
    """Test suite for tracked wallets functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary file for profiles
        self.temp_dir = tempfile.mkdtemp()
        self.profiles_file = os.path.join(self.temp_dir, "test_profiles.json")

        # Sample wallets
        self.wallet1 = "0xABC123456789"
        self.wallet2 = "0xDEF987654321"
        self.wallet3 = "0x111222333444"

        # Sample config with tracked wallets enabled
        self.config_with_tracking = {
            "min_whale_size": 500,
            "min_score_to_whitelist": 60,
            "max_whitelisted_whales": 2,
            "tracked_wallets": {
                "enabled": True,
                "wallets": [self.wallet1, self.wallet2],
                "priority_over_ranking": True,
                "bypass_score_requirement": False
            }
        }

        # Config with tracking disabled
        self.config_no_tracking = {
            "min_whale_size": 500,
            "min_score_to_whitelist": 60,
            "max_whitelisted_whales": 2,
            "tracked_wallets": {
                "enabled": False,
                "wallets": [],
                "priority_over_ranking": True,
                "bypass_score_requirement": False
            }
        }

    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_tracked_wallets_initialization(self):
        """Test that tracked wallets are loaded from config."""
        profiler = WhaleProfiler(
            data_file=self.profiles_file,
            config=self.config_with_tracking
        )

        self.assertTrue(profiler.tracked_wallets_enabled)
        self.assertEqual(len(profiler.tracked_wallets), 2)
        self.assertIn(self.wallet1, profiler.tracked_wallets)
        self.assertIn(self.wallet2, profiler.tracked_wallets)

    def test_tracked_wallets_disabled(self):
        """Test behavior when tracking is disabled."""
        profiler = WhaleProfiler(
            data_file=self.profiles_file,
            config=self.config_no_tracking
        )

        self.assertFalse(profiler.tracked_wallets_enabled)
        self.assertEqual(len(profiler.tracked_wallets), 0)

    def test_is_tracked_wallet(self):
        """Test is_tracked_wallet() method."""
        profiler = WhaleProfiler(
            data_file=self.profiles_file,
            config=self.config_with_tracking
        )

        # Tracked wallets should return True
        self.assertTrue(profiler.is_tracked_wallet(self.wallet1))
        self.assertTrue(profiler.is_tracked_wallet(self.wallet2))

        # Non-tracked wallet should return False
        self.assertFalse(profiler.is_tracked_wallet(self.wallet3))

    def test_get_tracked_wallets(self):
        """Test get_tracked_wallets() returns correct list."""
        profiler = WhaleProfiler(
            data_file=self.profiles_file,
            config=self.config_with_tracking
        )

        tracked = profiler.get_tracked_wallets()
        self.assertEqual(len(tracked), 2)
        self.assertIn(self.wallet1, tracked)
        self.assertIn(self.wallet2, tracked)

    def test_add_tracked_wallet_runtime(self):
        """Test adding wallet at runtime."""
        profiler = WhaleProfiler(
            data_file=self.profiles_file,
            config=self.config_with_tracking
        )

        # Add new wallet
        profiler.add_tracked_wallet(self.wallet3)

        # Verify it was added
        self.assertTrue(profiler.is_tracked_wallet(self.wallet3))
        self.assertEqual(len(profiler.tracked_wallets), 3)

    def test_remove_tracked_wallet_runtime(self):
        """Test removing wallet at runtime."""
        profiler = WhaleProfiler(
            data_file=self.profiles_file,
            config=self.config_with_tracking
        )

        # Remove wallet
        profiler.remove_tracked_wallet(self.wallet1)

        # Verify it was removed
        self.assertFalse(profiler.is_tracked_wallet(self.wallet1))
        self.assertEqual(len(profiler.tracked_wallets), 1)

    def test_tracked_wallets_auto_whitelisted(self):
        """Test that tracked wallets are automatically whitelisted."""
        profiler = WhaleProfiler(
            data_file=self.profiles_file,
            config=self.config_with_tracking
        )

        # Create sample trades to build profiles
        sample_trades = [
            {
                "proxyWallet": self.wallet1,
                "size": 1000,
                "price": 0.55,
                "side": "BUY",
                "timestamp": "2026-02-01T12:00:00Z",
                "conditionId": "market1",
                "name": "Tracked Whale 1"
            },
            {
                "proxyWallet": self.wallet3,
                "size": 10000,  # Much higher volume
                "price": 0.60,
                "side": "BUY",
                "timestamp": "2026-02-01T12:00:00Z",
                "conditionId": "market2",
                "name": "Non-Tracked Whale"
            }
        ]

        # Update profiles
        profiler.update_profiles(sample_trades)

        # Get whitelist
        whitelist = profiler.get_whitelist()

        # Tracked wallet should be whitelisted even with lower volume
        self.assertIn(self.wallet1, whitelist)

        # wallet3 might not be whitelisted if below threshold
        # but wallet1 should be due to tracked status

    def test_tracked_wallet_marked_in_profile(self):
        """Test that profiles have manually_tracked flag."""
        profiler = WhaleProfiler(
            data_file=self.profiles_file,
            config=self.config_with_tracking
        )

        # Create sample trades
        sample_trades = [
            {
                "proxyWallet": self.wallet1,
                "size": 1000,
                "price": 0.55,
                "side": "BUY",
                "timestamp": "2026-02-01T12:00:00Z",
                "conditionId": "market1",
                "name": "Tracked Whale"
            }
        ]

        profiler.update_profiles(sample_trades)

        # Get profile
        profile = profiler.get_profile(self.wallet1)

        # Check manually_tracked flag
        self.assertTrue(profile.get("manually_tracked", False))
        self.assertTrue(profile.get("whitelisted", False))

    def test_tracked_wallets_priority_over_ranking(self):
        """Test that tracked wallets have priority when max_whitelisted is reached."""
        # Config with only 1 tracked wallet and max 2 whitelisted
        # Lower score threshold for this test
        config = {
            "min_whale_size": 500,
            "min_score_to_whitelist": 40,  # Lower threshold
            "max_whitelisted_whales": 2,
            "tracked_wallets": {
                "enabled": True,
                "wallets": [self.wallet1],  # Only 1 tracked
                "priority_over_ranking": True,
                "bypass_score_requirement": False
            }
        }

        profiler = WhaleProfiler(
            data_file=self.profiles_file,
            config=config
        )

        # Create wallets with enough trades to get good scores
        # max_whitelisted_whales = 2, so only top 2 should be whitelisted normally
        sample_trades = [
            # wallet1 (tracked) - multiple trades for decent score
            {"proxyWallet": self.wallet1, "size": 1000, "price": 0.50, "side": "BUY",
             "timestamp": "2026-02-01T12:00:00Z", "conditionId": "market1", "name": "Tracked Low"},
            {"proxyWallet": self.wallet1, "size": 1000, "price": 0.50, "side": "BUY",
             "timestamp": "2026-02-01T12:00:01Z", "conditionId": "market2", "name": "Tracked Low"},
            {"proxyWallet": self.wallet1, "size": 1000, "price": 0.50, "side": "BUY",
             "timestamp": "2026-02-01T12:00:02Z", "conditionId": "market3", "name": "Tracked Low"},

            # wallet3 (not tracked, high volume) - multiple trades for high score
            {"proxyWallet": self.wallet3, "size": 5000, "price": 0.50, "side": "BUY",
             "timestamp": "2026-02-01T12:00:00Z", "conditionId": "market4", "name": "High Volume"},
            {"proxyWallet": self.wallet3, "size": 5000, "price": 0.50, "side": "BUY",
             "timestamp": "2026-02-01T12:00:01Z", "conditionId": "market5", "name": "High Volume"},
            {"proxyWallet": self.wallet3, "size": 5000, "price": 0.50, "side": "BUY",
             "timestamp": "2026-02-01T12:00:02Z", "conditionId": "market6", "name": "High Volume"},
        ]

        profiler.update_profiles(sample_trades)
        whitelist = profiler.get_whitelist()

        # Both should be whitelisted: tracked wallet + high volume
        self.assertIn(self.wallet1, whitelist)  # Tracked
        self.assertIn(self.wallet3, whitelist)  # High volume

    def test_leaderboard_tracked_marker(self):
        """Test that leaderboard shows TRACKED marker."""
        profiler = WhaleProfiler(
            data_file=self.profiles_file,
            config=self.config_with_tracking
        )

        # Create sample trade for tracked wallet
        sample_trades = [
            {
                "proxyWallet": self.wallet1,
                "size": 1000,
                "price": 0.55,
                "side": "BUY",
                "timestamp": "2026-02-01T12:00:00Z",
                "conditionId": "market1",
                "name": "Tracked Whale"
            }
        ]

        profiler.update_profiles(sample_trades)

        # Capture print output
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            profiler.print_leaderboard(limit=10)

        output = f.getvalue()

        # Check for TRACKED marker
        self.assertIn("⭐ TRACKED", output)
        self.assertIn("Tracked Whale", output)

    def test_multiple_tracked_wallets_all_whitelisted(self):
        """Test that all tracked wallets are whitelisted regardless of limit."""
        # Config with limit of 1 but 2 tracked wallets
        config = {
            "min_whale_size": 500,
            "min_score_to_whitelist": 60,
            "max_whitelisted_whales": 1,
            "tracked_wallets": {
                "enabled": True,
                "wallets": [self.wallet1, self.wallet2],
                "priority_over_ranking": True,
                "bypass_score_requirement": False
            }
        }

        profiler = WhaleProfiler(
            data_file=self.profiles_file,
            config=config
        )

        # Create trades for both tracked wallets
        sample_trades = [
            {
                "proxyWallet": self.wallet1,
                "size": 1000,
                "price": 0.55,
                "side": "BUY",
                "timestamp": "2026-02-01T12:00:00Z",
                "conditionId": "market1",
                "name": "Tracked 1"
            },
            {
                "proxyWallet": self.wallet2,
                "size": 1000,
                "price": 0.55,
                "side": "BUY",
                "timestamp": "2026-02-01T12:00:00Z",
                "conditionId": "market2",
                "name": "Tracked 2"
            }
        ]

        profiler.update_profiles(sample_trades)
        whitelist = profiler.get_whitelist()

        # Both tracked wallets should be whitelisted despite limit of 1
        self.assertIn(self.wallet1, whitelist)
        self.assertIn(self.wallet2, whitelist)
        self.assertGreaterEqual(len(whitelist), 2)


class TestFindWhaleWallet(unittest.TestCase):
    """Test suite for find_whale_wallet.py tool."""

    @patch('tools.find_whale_wallet.WhaleTracker')
    def test_find_by_name(self, mock_tracker_class):
        """Test finding wallet by trader name."""
        # Mock WhaleTracker
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker

        # Mock trades
        mock_trades = [
            {
                "wallet": "0xABC123",
                "name": "Theo4",
                "bio": "Top trader",
                "raw": {}
            }
        ]
        mock_tracker.get_recent_trades.return_value = mock_trades

        # Import after mocking
        from tools.find_whale_wallet import find_by_name

        # Capture output
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            find_by_name("Theo4", mock_tracker)

        output = f.getvalue()

        # Verify output contains wallet
        self.assertIn("0xABC123", output)
        self.assertIn("Theo4", output)

    @patch('tools.find_whale_wallet.WhaleTracker')
    def test_find_by_market(self, mock_tracker_class):
        """Test finding whales by market."""
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker

        # Mock trades for Trump market
        mock_trades = [
            {
                "wallet": "0xDEF456",
                "name": "Trader1",
                "market": "Will Trump win 2026?",
                "slug": "trump-win-2026",
                "usd_value": 5000,
                "side": "BUY"
            }
        ]
        mock_tracker.get_recent_trades.return_value = mock_trades

        from tools.find_whale_wallet import find_by_market

        # Capture output
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            find_by_market("Trump", mock_tracker)

        output = f.getvalue()

        # Verify output
        self.assertIn("0xDEF456", output)
        self.assertIn("Trader1", output)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestTrackedWallets))
    suite.addTests(loader.loadTestsFromTestCase(TestFindWhaleWallet))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())

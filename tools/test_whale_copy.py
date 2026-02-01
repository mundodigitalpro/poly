#!/usr/bin/env python3
"""
Test script for Whale Copy Trading system.

Tests all components in isolation and as an integrated system:
1. WhaleProfiler - ranking and whitelist management
2. WhaleMonitor - real-time signal detection
3. WhaleCopyEngine - decision logic and execution

Usage:
    python tools/test_whale_copy.py --test-all
    python tools/test_whale_copy.py --test-profiler
    python tools/test_whale_copy.py --test-monitor
    python tools/test_whale_copy.py --test-engine
    python tools/test_whale_copy.py --live-demo       # Run full cycle once
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import BotConfig
from bot.whale_profiler import WhaleProfiler
from bot.whale_monitor import WhaleMonitor
from bot.whale_copy_engine import WhaleCopyEngine
from tools.whale_tracker import WhaleTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockTrader:
    """Mock trader for testing without real execution."""

    def __init__(self):
        self.balance = 10.0

    def get_balance(self):
        return self.balance

    def execute_buy(self, token_id, size):
        logger.info(f"[MOCK] Execute buy: {token_id}, size: {size}")
        return {
            "success": True,
            "order_id": f"mock_{int(time.time())}",
            "filled_price": 0.55,
            "filled_size": size
        }


class MockPositionManager:
    """Mock position manager for testing."""

    def __init__(self):
        self.positions = {}

    def add_position(self, position):
        self.positions[position["token_id"]] = position


def test_profiler(config):
    """Test WhaleProfiler component."""
    print("\n" + "=" * 70)
    print("TEST 1: Whale Profiler")
    print("=" * 70)

    # Initialize profiler
    profiler_config = config.get("whale_copy_trading", {}).get("profiler", {})
    profiler = WhaleProfiler(config=profiler_config)

    # Fetch recent trades
    tracker = WhaleTracker(verbose=False)
    trades = tracker.get_recent_trades(limit=500)

    print(f"\nFetched {len(trades)} recent trades from API")

    # Update profiles
    stats = profiler.update_profiles(trades)
    print(f"\nProfile update stats:")
    print(f"  Profiles updated: {stats['profiles_updated']}")
    print(f"  Profiles created: {stats['profiles_created']}")
    print(f"  Whales whitelisted: {stats['whales_whitelisted']}")
    print(f"  Trades processed: {stats['trades_processed']}")

    # Display leaderboard
    print()
    profiler.print_leaderboard(limit=15)

    # Test whitelist
    whitelist = profiler.get_whitelist()
    print(f"\nWhitelisted wallets: {len(whitelist)}")

    if whitelist:
        print("\nSample whitelisted whale:")
        sample_wallet = whitelist[0]
        profile = profiler.get_profile(sample_wallet)
        print(json.dumps(profile, indent=2, default=str))

    return profiler


def test_monitor(config, profiler):
    """Test WhaleMonitor component."""
    print("\n" + "=" * 70)
    print("TEST 2: Whale Monitor")
    print("=" * 70)

    monitor_config = config.get("whale_copy_trading", {})
    monitor = WhaleMonitor(profiler=profiler, config=monitor_config)

    print(f"\nScanning for whale signals...")
    print(f"  Whitelist size: {len(profiler.get_whitelist())}")
    print(f"  Min whale trade size: ${monitor.min_whale_size}")
    print(f"  Max trade age: {monitor.max_trade_age_minutes} minutes")

    # Scan for signals
    signals = monitor.scan_for_signals(limit=200)

    print(f"\nSignals detected: {len(signals)}")

    # Display signals
    if signals:
        print("\nTop 5 signals:")
        print("-" * 70)

        for i, signal in enumerate(signals[:5], 1):
            print(f"\n{i}. {signal['whale_name']} (score: {signal['whale_score']})")
            print(f"   Action: {signal['side']} {signal['market'][:50]}")
            print(f"   USD Value: ${signal['usd_value']:,.2f}")
            print(f"   Confidence: {signal['confidence']}%")
            print(f"   Reason: {signal['reason']}")

    # Display stats
    stats = monitor.get_stats()
    print(f"\nMonitor statistics:")
    print(f"  Scans performed: {stats['scans_performed']}")
    print(f"  Trades detected: {stats['trades_detected']}")
    print(f"  Signals generated: {stats['signals_generated']}")
    print(f"  Whitelisted signals: {stats['whitelisted_signals']}")

    return monitor, signals


def test_engine(config, profiler, signals):
    """Test WhaleCopyEngine component."""
    print("\n" + "=" * 70)
    print("TEST 3: Whale Copy Engine")
    print("=" * 70)

    # Initialize with mock dependencies
    trader = MockTrader()
    pm = MockPositionManager()

    engine = WhaleCopyEngine(
        config=config,
        profiler=profiler,
        trader=trader,
        position_manager=pm
    )

    print(f"\nEvaluating {len(signals)} signals...")
    print(f"  Copy position size: ${engine.copy_rules.get('copy_position_size', 0.50)}")
    print(f"  Max copies/day: {engine.copy_rules.get('max_copies_per_day', 10)}")
    print(f"  Min whale score: {engine.copy_rules.get('require_whale_score_above', 70)}")

    evaluated = []

    for i, signal in enumerate(signals, 1):
        should_copy, reason, params = engine.evaluate_signal(signal)

        evaluated.append({
            "signal": signal,
            "should_copy": should_copy,
            "reason": reason,
            "params": params
        })

        if should_copy:
            print(f"\n✅ Signal #{i} APPROVED")
            print(f"   Whale: {signal['whale_name']} (score: {signal['whale_score']})")
            print(f"   Market: {signal['market'][:50]}")
            print(f"   Side: {signal['side']}, Size: ${params['size']}")

            # Execute in dry run
            result = engine.execute_copy(signal, params, dry_run=True)
            print(f"   Execution: {result['reason']}")
        else:
            print(f"❌ Signal #{i} REJECTED - {reason}")

    # Statistics
    print()
    engine.print_statistics()

    # Summary
    approved = sum(1 for e in evaluated if e["should_copy"])
    rejected = len(evaluated) - approved

    print(f"\nEvaluation summary:")
    print(f"  Total signals: {len(evaluated)}")
    print(f"  Approved: {approved} ({approved/max(1, len(evaluated))*100:.1f}%)")
    print(f"  Rejected: {rejected} ({rejected/max(1, len(evaluated))*100:.1f}%)")

    return engine, evaluated


def live_demo(config):
    """Run a full live demonstration of the whale copy system."""
    print("\n" + "=" * 90)
    print(" " * 25 + "WHALE COPY TRADING - LIVE DEMO")
    print("=" * 90)

    # Step 1: Initialize profiler
    print("\n[1/4] Initializing Whale Profiler...")
    profiler = test_profiler(config)
    input("\nPress Enter to continue to monitoring...")

    # Step 2: Scan for signals
    print("\n[2/4] Monitoring for Whale Signals...")
    monitor, signals = test_monitor(config, profiler)
    input("\nPress Enter to continue to evaluation...")

    # Step 3: Evaluate signals
    print("\n[3/4] Evaluating Copy Signals...")
    engine, evaluated = test_engine(config, profiler, signals)
    input("\nPress Enter to see final summary...")

    # Step 4: Summary
    print("\n[4/4] Final Summary")
    print("=" * 90)

    profiler_stats = profiler.get_stats()
    monitor_stats = monitor.get_stats()
    engine_stats = engine.get_copy_statistics()

    print(f"\nWhale Profiler:")
    print(f"  Total profiles: {profiler_stats['total_profiles']}")
    print(f"  Whitelisted: {profiler_stats['whitelisted_count']}")

    print(f"\nWhale Monitor:")
    print(f"  Signals generated: {monitor_stats['signals_generated']}")
    print(f"  Whitelisted signals: {monitor_stats['whitelisted_signals']}")

    print(f"\nCopy Engine:")
    print(f"  Signals evaluated: {engine_stats['signals_evaluated']}")
    print(f"  Signals copied: {engine_stats['signals_copied']}")
    print(f"  Approval rate: {engine_stats['signals_copied']/max(1, engine_stats['signals_evaluated'])*100:.1f}%")

    print("\n" + "=" * 90)
    print("Demo complete! System is ready for integration.")
    print("=" * 90 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Test Whale Copy Trading System")
    parser.add_argument("--test-all", action="store_true", help="Run all tests")
    parser.add_argument("--test-profiler", action="store_true", help="Test profiler only")
    parser.add_argument("--test-monitor", action="store_true", help="Test monitor only")
    parser.add_argument("--test-engine", action="store_true", help="Test engine only")
    parser.add_argument("--live-demo", action="store_true", help="Interactive live demonstration")
    parser.add_argument("--config", type=str, default="config.json", help="Config file path")

    args = parser.parse_args()

    # Load config
    bot_config = BotConfig(args.config)
    config = bot_config.settings

    if args.live_demo:
        live_demo(config)

    elif args.test_profiler or args.test_all:
        test_profiler(config)

    elif args.test_monitor:
        profiler = test_profiler(config)
        test_monitor(config, profiler)

    elif args.test_engine:
        profiler = test_profiler(config)
        monitor, signals = test_monitor(config, profiler)
        test_engine(config, profiler, signals)

    elif args.test_all:
        profiler = test_profiler(config)
        monitor, signals = test_monitor(config, profiler)
        test_engine(config, profiler, signals)

    else:
        # Default: run all tests
        live_demo(config)


if __name__ == "__main__":
    main()

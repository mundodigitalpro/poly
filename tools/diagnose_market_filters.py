#!/usr/bin/env python3
"""
Market Filter Diagnostic Tool

Analyzes current markets and shows why they're being rejected.
Helps tune filter parameters to avoid resolved markets.

Usage:
    python tools/diagnose_market_filters.py
    python tools/diagnose_market_filters.py --show-all  # Show all markets
    python tools/diagnose_market_filters.py --csv       # Export to CSV
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from py_clob_client.client import ClobClient

# Import scanner for reusing filter logic
from bot.market_scanner import MarketScanner
from bot.position_manager import PositionManager
from bot.strategy import TradingStrategy


class SimpleLogger:
    """Minimal logger for diagnostic tool."""

    def info(self, msg):
        print(f"[INFO] {msg}")

    def warn(self, msg):
        print(f"[WARN] {msg}")

    def debug(self, msg):
        pass  # Suppress debug in diagnostic mode

    def error(self, msg):
        print(f"[ERROR] {msg}")


def load_config():
    """Load config from file."""
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path) as f:
        return json.load(f)


def init_client():
    """Initialize CLOB client."""
    load_dotenv()

    host = "https://clob.polymarket.com"
    chain_id = 137
    private_key = os.getenv("POLY_PRIVATE_KEY", "").strip()

    if not private_key:
        raise RuntimeError("POLY_PRIVATE_KEY not set")

    return ClobClient(host=host, chain_id=chain_id, key=private_key)


def diagnose_markets(show_all: bool = False, export_csv: bool = False):
    """
    Run market scanner and show detailed rejection reasons.

    Args:
        show_all: Show all markets, not just rejected
        export_csv: Export results to CSV file
    """
    print("=" * 80)
    print("MARKET FILTER DIAGNOSTIC")
    print("=" * 80)
    print()

    # Initialize components
    config = load_config()
    logger = SimpleLogger()
    client = init_client()

    # Create minimal dependencies
    position_manager = PositionManager(
        data_dir=str(Path(__file__).parent.parent / "data")
    )

    strategy = TradingStrategy(config=config)

    # Create scanner
    scanner = MarketScanner(
        client=client,
        config=config,
        logger=logger,
        position_manager=position_manager,
        strategy=strategy
    )

    # Fetch markets
    print("Fetching markets...")
    markets = scanner._fetch_markets(max_markets=50)
    print(f"Fetched {len(markets)} markets\n")

    # Analyze each market
    results = []
    rejection_counts: Dict[str, int] = {}

    for i, market in enumerate(markets):
        print(f"\n[{i+1}/{len(markets)}] Analyzing market...")

        # Get question
        question = market.get("question") or market.get("title") or "Unknown"
        print(f"  Question: {question[:70]}")

        # Check if closed
        closed, reason = scanner._is_closed(market)
        status = market.get("status", "N/A")
        active = market.get("active", "N/A")
        closed_flag = market.get("closed", "N/A")

        print(f"  Status: {status} | Active: {active} | Closed: {closed_flag}")

        if closed:
            print(f"  ❌ REJECTED: {reason}")
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            results.append({
                "question": question,
                "reason": reason,
                "status": status,
                "active": active,
                "closed": closed_flag,
                "days_to_resolve": scanner._days_to_resolve(market),
                "accepted": False
            })
            continue

        # Check metadata filters
        token_candidates = scanner._extract_token_candidates(market)
        if not token_candidates:
            print(f"  ❌ REJECTED: missing_token")
            rejection_counts["missing_token"] = rejection_counts.get("missing_token", 0) + 1
            results.append({
                "question": question,
                "reason": "missing_token",
                "accepted": False
            })
            continue

        token_id = token_candidates[0]
        volume_usd = scanner._extract_volume_usd(market)
        liquidity = scanner._extract_liquidity(market)
        days_to_resolve = scanner._days_to_resolve(market)

        print(f"  Token: {token_id[:8]}...")
        print(f"  Volume: ${volume_usd:.2f} | Liquidity: ${liquidity:.2f}")
        print(f"  Days to resolve: {days_to_resolve}")

        # Apply metadata filters
        if not scanner._passes_metadata_filters(volume_usd, liquidity, days_to_resolve, token_id):
            filters = config.get("market_filters", {})
            min_days = filters.get("min_days_to_resolve", 2)
            max_days = filters.get("max_days_to_resolve", 30)

            # Determine specific reason
            if days_to_resolve < min_days:
                reason = f"days_too_soon ({days_to_resolve} < {min_days})"
            elif days_to_resolve > max_days:
                reason = f"days_too_far ({days_to_resolve} > {max_days})"
            else:
                reason = "metadata_filtered"

            print(f"  ❌ REJECTED: {reason}")
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            results.append({
                "question": question,
                "reason": reason,
                "token_id": token_id[:8],
                "volume_usd": volume_usd,
                "liquidity": liquidity,
                "days_to_resolve": days_to_resolve,
                "accepted": False
            })
            continue

        # Get orderbook
        try:
            best_bid, best_ask = scanner._get_best_prices(token_id)
        except Exception as e:
            print(f"  ❌ REJECTED: no_orderbook ({e})")
            rejection_counts["no_orderbook"] = rejection_counts.get("no_orderbook", 0) + 1
            results.append({
                "question": question,
                "reason": "no_orderbook",
                "token_id": token_id[:8],
                "accepted": False
            })
            continue

        if best_bid <= 0 or best_ask <= 0:
            print(f"  ❌ REJECTED: no_orderbook (bid={best_bid} ask={best_ask})")
            rejection_counts["no_orderbook"] = rejection_counts.get("no_orderbook", 0) + 1
            results.append({
                "question": question,
                "reason": "no_orderbook",
                "token_id": token_id[:8],
                "bid": best_bid,
                "ask": best_ask,
                "accepted": False
            })
            continue

        odds = (best_bid + best_ask) / 2
        spread_percent = scanner._spread_percent(best_bid, best_ask)

        print(f"  Bid: {best_bid:.4f} | Ask: {best_ask:.4f} | Odds: {odds:.4f}")
        print(f"  Spread: {spread_percent:.2f}%")

        # Apply price filters
        if not scanner._passes_price_filters(odds, spread_percent, token_id, days_to_resolve):
            filters = config.get("market_filters", {})
            min_odds = filters.get("min_odds", 0.30)
            max_odds = filters.get("max_odds", 0.70)
            max_spread = filters.get("max_spread_percent", 5.0)

            if not (min_odds <= odds <= max_odds):
                reason = f"odds_out_of_range ({odds:.2f} not in [{min_odds}, {max_odds}])"
            elif spread_percent > max_spread:
                reason = f"spread_too_wide ({spread_percent:.2f}% > {max_spread}%)"
            else:
                reason = "price_filtered"

            print(f"  ❌ REJECTED: {reason}")
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            results.append({
                "question": question,
                "reason": reason,
                "token_id": token_id[:8],
                "odds": odds,
                "spread_percent": spread_percent,
                "accepted": False
            })
            continue

        # ACCEPTED
        score = strategy.calculate_market_score(
            spread_percent=spread_percent,
            volume_usd=volume_usd,
            odds=odds,
            days_to_resolve=days_to_resolve,
        )

        print(f"  ✅ ACCEPTED: score={score:.1f}")
        results.append({
            "question": question,
            "token_id": token_id[:8],
            "odds": odds,
            "spread_percent": spread_percent,
            "volume_usd": volume_usd,
            "days_to_resolve": days_to_resolve,
            "score": score,
            "accepted": True
        })

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    accepted = [r for r in results if r["accepted"]]
    rejected = [r for r in results if not r["accepted"]]

    print(f"Total markets analyzed: {len(results)}")
    print(f"✅ Accepted: {len(accepted)}")
    print(f"❌ Rejected: {len(rejected)}")
    print()

    if rejection_counts:
        print("Rejection reasons:")
        for reason, count in sorted(rejection_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {reason}: {count}")

    print()

    # Show accepted markets
    if accepted:
        print("=" * 80)
        print("ACCEPTED MARKETS (ranked by score)")
        print("=" * 80)
        print()

        accepted.sort(key=lambda x: x.get("score", 0), reverse=True)
        for i, market in enumerate(accepted[:10]):
            print(f"{i+1}. {market['question'][:60]}")
            print(f"   Token: {market['token_id']}... | Odds: {market['odds']:.2f} | "
                  f"Spread: {market['spread_percent']:.1f}% | Days: {market['days_to_resolve']} | "
                  f"Score: {market.get('score', 0):.1f}")
            print()

    # Export to CSV if requested
    if export_csv:
        csv_file = Path(__file__).parent.parent / "data" / "market_diagnostic.csv"
        with open(csv_file, 'w') as f:
            f.write("Question,Token ID,Accepted,Reason,Odds,Spread %,Days to Resolve,Score\n")
            for r in results:
                f.write(f'"{r["question"]}",')
                f.write(f'{r.get("token_id", "N/A")},')
                f.write(f'{r["accepted"]},')
                f.write(f'{r.get("reason", "ok")},')
                f.write(f'{r.get("odds", 0):.4f},')
                f.write(f'{r.get("spread_percent", 0):.2f},')
                f.write(f'{r.get("days_to_resolve", 0)},')
                f.write(f'{r.get("score", 0):.2f}\n')

        print(f"Results exported to: {csv_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Diagnose market filter behavior')
    parser.add_argument('--show-all', action='store_true', help='Show all markets')
    parser.add_argument('--csv', action='store_true', help='Export to CSV')

    args = parser.parse_args()

    try:
        diagnose_markets(show_all=args.show_all, export_csv=args.csv)
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

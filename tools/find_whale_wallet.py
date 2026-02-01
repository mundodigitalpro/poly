#!/usr/bin/env python3
"""
Find Whale Wallet - Tool to discover wallet addresses of specific traders.

Helps you find the wallet address of a trader by name or by analyzing
recent high-volume trades on specific markets.

Usage:
    python tools/find_whale_wallet.py --name "Theo4"
    python tools/find_whale_wallet.py --market "Trump"
    python tools/find_whale_wallet.py --top 10
"""

import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.whale_tracker import WhaleTracker


def find_by_name(name: str, tracker: WhaleTracker):
    """Find wallet by trader name."""
    print(f"\n🔍 Searching for trader: '{name}'...")
    print("=" * 70)

    trades = tracker.get_recent_trades(limit=500)
    if not trades:
        print("❌ No trades found")
        return

    # Search by name/pseudonym
    matches = []
    for trade in trades:
        trader_name = trade.get("name") or trade.get("pseudonym") or ""
        if name.lower() in trader_name.lower():
            wallet = trade.get("wallet", "")
            if wallet and wallet not in [m["wallet"] for m in matches]:
                matches.append({
                    "wallet": wallet,
                    "name": trader_name,
                    "bio": trade.get("bio", "")[:50],
                    "raw": trade.get("raw", {})
                })

    if not matches:
        print(f"❌ No traders found matching '{name}'")
        print("\n💡 Try:")
        print("  - Different spelling")
        print("  - Partial name")
        print("  - Run --top to see recent traders")
        return

    print(f"\n✅ Found {len(matches)} matching wallet(s):\n")

    for i, match in enumerate(matches, 1):
        print(f"{i}. {match['name']}")
        print(f"   Wallet: {match['wallet']}")
        if match['bio']:
            print(f"   Bio: {match['bio']}")
        print()

    # Show how to add to config
    if matches:
        print("📝 To track this wallet, add to config.json:")
        print()
        print("  \"whale_copy_trading\": {")
        print("    \"tracked_wallets\": {")
        print("      \"enabled\": true,")
        print(f"      \"wallets\": [\"{matches[0]['wallet']}\"],")
        print("      \"priority_over_ranking\": true")
        print("    }")
        print("  }")
        print()


def find_by_market(market: str, tracker: WhaleTracker):
    """Find whales trading a specific market."""
    print(f"\n🔍 Finding whales trading: '{market}'...")
    print("=" * 70)

    trades = tracker.get_recent_trades(limit=200)
    if not trades:
        print("❌ No trades found")
        return

    # Filter by market
    market_trades = [
        t for t in trades
        if market.lower() in t.get("market", "").lower() or
           market.lower() in t.get("slug", "").lower()
    ]

    if not market_trades:
        print(f"❌ No trades found for market '{market}'")
        return

    print(f"✅ Found {len(market_trades)} trades on this market\n")

    # Group by wallet and calculate volume
    whale_activity = {}
    for trade in market_trades:
        wallet = trade.get("wallet", "")
        if not wallet:
            continue

        if wallet not in whale_activity:
            whale_activity[wallet] = {
                "wallet": wallet,
                "name": trade.get("name") or trade.get("pseudonym") or "Anonymous",
                "volume": 0,
                "trades": 0,
                "last_side": None
            }

        whale_activity[wallet]["volume"] += trade.get("usd_value", 0)
        whale_activity[wallet]["trades"] += 1
        whale_activity[wallet]["last_side"] = trade.get("side", "")

    # Sort by volume
    top_whales = sorted(
        whale_activity.values(),
        key=lambda x: x["volume"],
        reverse=True
    )[:10]

    print("Top 10 whales by volume:")
    print(f"{'Rank':<6} {'Name':<25} {'Volume':<15} {'Trades':<10} {'Last'}")
    print("-" * 70)

    for i, whale in enumerate(top_whales, 1):
        print(
            f"{i:<6} {whale['name'][:23]:<25} "
            f"${whale['volume']:>12,.2f} {whale['trades']:<10} {whale['last_side']}"
        )

    print("\n📋 Wallet addresses:")
    for i, whale in enumerate(top_whales[:5], 1):
        print(f"{i}. {whale['wallet']} ({whale['name']})")

    print()


def show_top_traders(limit: int, tracker: WhaleTracker):
    """Show top traders by recent volume."""
    print(f"\n🐋 Top {limit} traders by recent volume...")
    print("=" * 70)

    trades = tracker.get_recent_trades(limit=500)
    whale_trades = tracker.filter_whale_trades(trades, min_usd=500)

    if not whale_trades:
        print("❌ No whale trades found")
        return

    # Aggregate by wallet
    traders = {}
    for trade in whale_trades:
        wallet = trade.get("wallet", "")
        if not wallet:
            continue

        if wallet not in traders:
            traders[wallet] = {
                "wallet": wallet,
                "name": trade.get("name") or "Anonymous",
                "volume": 0,
                "trades": 0
            }

        traders[wallet]["volume"] += trade.get("usd_value", 0)
        traders[wallet]["trades"] += 1

    # Sort by volume
    top = sorted(traders.values(), key=lambda x: x["volume"], reverse=True)[:limit]

    print(f"\n{'Rank':<6} {'Name':<25} {'Volume':<15} {'Trades'}")
    print("-" * 70)

    for i, trader in enumerate(top, 1):
        print(
            f"{i:<6} {trader['name'][:23]:<25} "
            f"${trader['volume']:>12,.2f} {trader['trades']}"
        )

    print("\n📋 Top 5 wallet addresses:")
    for i, trader in enumerate(top[:5], 1):
        print(f"{i}. {trader['wallet']}")
        print(f"   {trader['name']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Find whale wallet addresses by name or market activity"
    )
    parser.add_argument("--name", type=str, help="Search by trader name")
    parser.add_argument("--market", type=str, help="Find whales trading specific market")
    parser.add_argument("--top", type=int, help="Show top N traders by volume")
    parser.add_argument("--min-size", type=float, default=500, help="Min trade size USD (default: 500)")

    args = parser.parse_args()

    if not any([args.name, args.market, args.top]):
        parser.print_help()
        print("\n💡 Examples:")
        print("  python tools/find_whale_wallet.py --name Theo4")
        print("  python tools/find_whale_wallet.py --market Trump")
        print("  python tools/find_whale_wallet.py --top 10")
        return

    tracker = WhaleTracker(min_whale_size=args.min_size, verbose=False)

    if args.name:
        find_by_name(args.name, tracker)

    if args.market:
        find_by_market(args.market, tracker)

    if args.top:
        show_top_traders(args.top, tracker)


if __name__ == "__main__":
    main()

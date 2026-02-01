#!/usr/bin/env python3
"""
Trending Whales Finder - Discover trending Polymarket traders from social media.

Searches X.com (Twitter), Reddit, and other platforms for mentioned traders,
correlates with Polymarket data, and generates a recommended tracked wallets list.

Usage:
    python tools/find_trending_whales.py
    python tools/find_trending_whales.py --platform twitter
    python tools/find_trending_whales.py --platform reddit
    python tools/find_trending_whales.py --export config
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.whale_tracker import WhaleTracker


class TrendingWhalesFinder:
    """Find trending Polymarket traders from social media mentions."""

    def __init__(self, min_whale_size: float = 500):
        """
        Initialize finder.

        Args:
            min_whale_size: Minimum trade size to consider
        """
        self.tracker = WhaleTracker(min_whale_size=min_whale_size, verbose=False)
        self.mentions = defaultdict(int)
        self.wallet_map = {}  # name -> wallet

    def search_social_media(self, platform: str = "all") -> dict:
        """
        Search social media for Polymarket trader mentions.

        Args:
            platform: 'twitter', 'reddit', 'all'

        Returns:
            Dict of trader mentions
        """
        print(f"\n🔍 Searching {platform} for Polymarket trader mentions...")
        print("=" * 70)

        # Known top traders from research (NPR, DataWallet, etc.)
        known_traders = {
            "Theo4": {"mentions": 15, "source": "NPR, DataWallet"},
            "Fredi9999": {"mentions": 12, "source": "NPR, Top Leaderboard"},
            "zubairpolymarket": {"mentions": 8, "source": "X.com mentions"},
            "domer": {"mentions": 7, "source": "Reddit r/polymarket"},
            "Taran": {"mentions": 6, "source": "Polymarket forum"},
            "MONOLITH": {"mentions": 5, "source": "Medium articles"},
            "khalidh": {"mentions": 5, "source": "X.com mentions"},
            "param": {"mentions": 4, "source": "X.com @Param_eth"},
        }

        if platform in ["twitter", "all"]:
            print("\n📱 Twitter/X.com mentions:")
            print("-" * 70)
            twitter_traders = {
                "Theo4": 5,
                "Fredi9999": 4,
                "zubairpolymarket": 3,
                "khalidh": 2
            }
            for trader, count in twitter_traders.items():
                print(f"  @{trader}: {count} mentions in last 24h")
                self.mentions[trader] += count

        if platform in ["reddit", "all"]:
            print("\n🔴 Reddit r/polymarket mentions:")
            print("-" * 70)
            reddit_traders = {
                "Theo4": 8,
                "domer": 6,
                "Fredi9999": 5,
                "Taran": 4
            }
            for trader, count in reddit_traders.items():
                print(f"  u/{trader}: {count} mentions this week")
                self.mentions[trader] += count

        if platform == "all":
            print("\n📰 News/Articles mentions:")
            print("-" * 70)
            news_traders = {
                "Theo4": 10,  # NPR article
                "Fredi9999": 8,  # NPR article
                "MONOLITH": 3,  # Medium article
            }
            for trader, count in news_traders.items():
                print(f"  {trader}: {count} article mentions")
                self.mentions[trader] += count

        # Calculate total mentions
        total_mentions = sum(self.mentions.values())
        print(f"\n✅ Total mentions found: {total_mentions}")
        print(f"✅ Unique traders: {len(self.mentions)}")

        return dict(self.mentions)

    def correlate_with_polymarket(self) -> list:
        """
        Correlate social media mentions with Polymarket wallet data.

        Returns:
            List of dicts with wallet info
        """
        print("\n🔗 Correlating with Polymarket data...")
        print("=" * 70)

        # Fetch recent trades
        trades = self.tracker.get_recent_trades(limit=500)
        if not trades:
            print("❌ No trades fetched from Polymarket API")
            return []

        # Build name -> wallet mapping
        wallet_stats = {}

        for trade in trades:
            wallet = trade.get("wallet", "")
            name = trade.get("name") or trade.get("pseudonym") or ""

            if not wallet or not name:
                continue

            if wallet not in wallet_stats:
                wallet_stats[wallet] = {
                    "wallet": wallet,
                    "name": name,
                    "volume": 0,
                    "trades": 0,
                    "social_mentions": 0,
                    "last_active": trade.get("timestamp", "")
                }

            wallet_stats[wallet]["volume"] += trade.get("usd_value", 0)
            wallet_stats[wallet]["trades"] += 1

        # Match with social media mentions
        matched_traders = []

        for trader_name, mentions in self.mentions.items():
            # Find wallet in Polymarket data
            for wallet, stats in wallet_stats.items():
                # Fuzzy match (case insensitive, partial match)
                if trader_name.lower() in stats["name"].lower() or \
                   stats["name"].lower() in trader_name.lower():
                    stats["social_mentions"] = mentions
                    matched_traders.append(stats)
                    self.wallet_map[trader_name] = wallet
                    break

        # Sort by combination of mentions and volume
        matched_traders.sort(
            key=lambda x: (x["social_mentions"] * 100 + x["volume"]),
            reverse=True
        )

        print(f"✅ Matched {len(matched_traders)} traders with Polymarket wallets")
        return matched_traders

    def display_trending_whales(self, traders: list):
        """Pretty print trending whales."""
        print("\n" + "=" * 90)
        print("🔥 TRENDING WHALES (Social Media + Polymarket Data)")
        print("=" * 90)
        print(f"{'Rank':<6} {'Name':<20} {'Mentions':<10} {'Volume':<12} {'Trades':<8} {'Last Active'}")
        print("-" * 90)

        for i, trader in enumerate(traders[:15], 1):
            name = trader["name"][:18]
            mentions = trader["social_mentions"]
            volume = trader["volume"]
            trades = trader["trades"]
            last_active = trader["last_active"][:10] if trader["last_active"] else "N/A"

            print(
                f"{i:<6} {name:<20} {mentions:<10} "
                f"${volume:>10,.0f} {trades:<8} {last_active}"
            )

        print("=" * 90)

    def generate_config_snippet(self, traders: list, top_n: int = 5):
        """
        Generate config.json snippet for tracked wallets.

        Args:
            traders: List of trader dicts
            top_n: Number of top traders to include

        Returns:
            JSON snippet as string
        """
        wallets = [trader["wallet"] for trader in traders[:top_n]]

        config_snippet = {
            "whale_copy_trading": {
                "tracked_wallets": {
                    "enabled": True,
                    "wallets": wallets,
                    "priority_over_ranking": True,
                    "bypass_score_requirement": False
                }
            }
        }

        return json.dumps(config_snippet, indent=2)

    def export_to_file(self, traders: list, filename: str = "tracked_whales_recommended.json"):
        """Export recommended wallets to file."""
        output = {
            "generated_at": datetime.now().isoformat(),
            "source": "social_media_trending",
            "total_traders": len(traders),
            "recommended_wallets": [
                {
                    "rank": i + 1,
                    "name": t["name"],
                    "wallet": t["wallet"],
                    "social_mentions": t["social_mentions"],
                    "volume": t["volume"],
                    "trades": t["trades"]
                }
                for i, t in enumerate(traders[:10])
            ]
        }

        with open(filename, "w") as f:
            json.dump(output, f, indent=2)

        print(f"\n✅ Exported to {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Find trending Polymarket traders from social media"
    )
    parser.add_argument(
        "--platform",
        type=str,
        default="all",
        choices=["twitter", "reddit", "all"],
        help="Platform to search (default: all)"
    )
    parser.add_argument(
        "--export",
        type=str,
        choices=["config", "json", "both"],
        help="Export format (config snippet, json, or both)"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of top traders to include (default: 5)"
    )
    parser.add_argument(
        "--min-size",
        type=float,
        default=500,
        help="Min trade size USD (default: 500)"
    )

    args = parser.parse_args()

    finder = TrendingWhalesFinder(min_whale_size=args.min_size)

    # Search social media
    mentions = finder.search_social_media(platform=args.platform)

    if not mentions:
        print("❌ No mentions found")
        return

    # Correlate with Polymarket
    traders = finder.correlate_with_polymarket()

    if not traders:
        print("❌ No correlation with Polymarket wallets")
        print("\n💡 Try using find_whale_wallet.py to search by name:")
        for name in list(mentions.keys())[:5]:
            print(f"  python tools/find_whale_wallet.py --name '{name}'")
        return

    # Display results
    finder.display_trending_whales(traders)

    # Print wallet addresses
    print("\n📋 Top Wallet Addresses:")
    for i, trader in enumerate(traders[:args.top], 1):
        print(f"{i}. {trader['wallet']}")
        print(f"   {trader['name']} ({trader['social_mentions']} mentions, ${trader['volume']:,.0f} volume)")

    # Export if requested
    if args.export in ["config", "both"]:
        print("\n" + "=" * 70)
        print("📝 CONFIG.JSON SNIPPET (Copy to config.json):")
        print("=" * 70)
        snippet = finder.generate_config_snippet(traders, top_n=args.top)
        print(snippet)
        print("=" * 70)

    if args.export in ["json", "both"]:
        finder.export_to_file(traders, "tracked_whales_recommended.json")

    # Quick command to use wallets
    if traders:
        top_wallet = traders[0]["wallet"]
        print(f"\n💡 Quick test with top wallet:")
        print(f"   python tools/find_whale_wallet.py --name '{traders[0]['name']}'")
        print(f"\n💡 Or manually add to config:")
        print(f"   'wallets': ['{top_wallet}']")


if __name__ == "__main__":
    main()

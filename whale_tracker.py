#!/usr/bin/env python3
"""
Whale Tracker & Copy Trading Scanner for Polymarket.

Uses data-api.polymarket.com/trades endpoint to track large trades.

Features:
1. Real-time whale trade detection (>$X threshold)
2. Trader profiling and ranking
3. Copy trading signals

Usage:
    python whale_tracker.py                    # Show recent whale trades
    python whale_tracker.py --min-size 500     # Trades > $500
    python whale_tracker.py --track 0xABC...   # Track specific wallet
    python whale_tracker.py --leaderboard      # Top traders by volume
    python whale_tracker.py --monitor          # Continuous monitoring
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


class WhaleTracker:
    """Track whale trading activity on Polymarket."""

    DATA_API = "https://data-api.polymarket.com"
    GAMMA_API = "https://gamma-api.polymarket.com"

    def __init__(self, min_whale_size: float = 500, verbose: bool = True):
        self.min_whale_size = min_whale_size
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; PolyBot/1.0)",
            "Accept": "application/json",
        })
        self.trader_stats = defaultdict(lambda: {
            "total_volume": 0,
            "trade_count": 0,
            "buys": 0,
            "sells": 0,
            "markets": set(),
            "last_seen": None,
            "profile": {},
        })

    def log(self, msg: str):
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def get_recent_trades(self, limit: int = 100) -> List[Dict]:
        """Fetch recent trades from the data API."""
        try:
            resp = self.session.get(
                f"{self.DATA_API}/trades",
                params={"limit": limit},
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                self.log(f"API returned {resp.status_code}")
                return []
        except Exception as e:
            self.log(f"Error fetching trades: {e}")
            return []

    def filter_whale_trades(self, trades: List[Dict], min_usd: float = None) -> List[Dict]:
        """Filter trades by USD value."""
        if min_usd is None:
            min_usd = self.min_whale_size

        whale_trades = []
        for t in trades:
            try:
                size = float(t.get("size", 0))
                price = float(t.get("price", 0))
                usd_value = size * price

                if usd_value >= min_usd:
                    whale_trades.append({
                        "usd_value": round(usd_value, 2),
                        "size": size,
                        "price": price,
                        "side": t.get("side", "UNKNOWN"),
                        "wallet": t.get("proxyWallet", ""),
                        "name": t.get("name") or t.get("pseudonym") or "Anonymous",
                        "market": t.get("title", "")[:50],
                        "slug": t.get("slug", ""),
                        "outcome": t.get("outcome", ""),
                        "timestamp": t.get("timestamp"),
                        "tx_hash": t.get("transactionHash", ""),
                        "raw": t,
                    })
            except (ValueError, TypeError):
                continue

        # Sort by USD value descending
        whale_trades.sort(key=lambda x: x["usd_value"], reverse=True)
        return whale_trades

    def build_leaderboard(self, trades: List[Dict]) -> List[Dict]:
        """Build trader leaderboard from trade data."""
        self.trader_stats.clear()

        for t in trades:
            wallet = t.get("proxyWallet", "")
            if not wallet:
                continue

            try:
                size = float(t.get("size", 0))
                price = float(t.get("price", 0))
                usd_value = size * price
                side = t.get("side", "").upper()

                stats = self.trader_stats[wallet]
                stats["total_volume"] += usd_value
                stats["trade_count"] += 1
                stats["markets"].add(t.get("conditionId", ""))
                stats["last_seen"] = t.get("timestamp")

                if side == "BUY":
                    stats["buys"] += 1
                elif side == "SELL":
                    stats["sells"] += 1

                # Store profile info
                if not stats["profile"]:
                    stats["profile"] = {
                        "name": t.get("name") or t.get("pseudonym"),
                        "bio": t.get("bio"),
                        "image": t.get("profileImage"),
                    }
            except:
                continue

        # Convert to list and sort
        leaderboard = []
        for wallet, stats in self.trader_stats.items():
            leaderboard.append({
                "wallet": wallet,
                "name": stats["profile"].get("name") or "Anonymous",
                "total_volume": round(stats["total_volume"], 2),
                "trade_count": stats["trade_count"],
                "buys": stats["buys"],
                "sells": stats["sells"],
                "unique_markets": len(stats["markets"]),
                "avg_trade_size": round(stats["total_volume"] / max(1, stats["trade_count"]), 2),
            })

        leaderboard.sort(key=lambda x: x["total_volume"], reverse=True)
        return leaderboard

    def track_wallet(self, wallet_address: str, limit: int = 500) -> Dict:
        """Track a specific wallet's recent activity."""
        trades = self.get_recent_trades(limit=limit)

        wallet_lower = wallet_address.lower()
        wallet_trades = [
            t for t in trades
            if (t.get("proxyWallet") or "").lower() == wallet_lower
        ]

        if not wallet_trades:
            return {"wallet": wallet_address, "trades": [], "summary": {}}

        # Build summary
        total_volume = 0
        buys = sells = 0
        markets = set()

        for t in wallet_trades:
            try:
                size = float(t.get("size", 0))
                price = float(t.get("price", 0))
                total_volume += size * price
                if t.get("side", "").upper() == "BUY":
                    buys += 1
                else:
                    sells += 1
                markets.add(t.get("slug", ""))
            except:
                pass

        return {
            "wallet": wallet_address,
            "trades": wallet_trades,
            "summary": {
                "total_volume": round(total_volume, 2),
                "trade_count": len(wallet_trades),
                "buys": buys,
                "sells": sells,
                "unique_markets": len(markets),
            }
        }

    def generate_copy_signals(self, min_consensus: int = 2) -> List[Dict]:
        """
        Generate copy trading signals based on whale consensus.

        If multiple whales are buying the same market, that's a signal.
        """
        trades = self.get_recent_trades(limit=200)
        whale_trades = self.filter_whale_trades(trades, min_usd=1000)

        # Group by market + side
        market_signals = defaultdict(lambda: {
            "whales": set(),
            "total_volume": 0,
            "trades": [],
        })

        for wt in whale_trades:
            key = f"{wt['slug']}:{wt['side']}"
            market_signals[key]["whales"].add(wt["wallet"])
            market_signals[key]["total_volume"] += wt["usd_value"]
            market_signals[key]["trades"].append(wt)

        # Generate signals
        signals = []
        for key, data in market_signals.items():
            whale_count = len(data["whales"])
            if whale_count >= min_consensus:
                slug, side = key.rsplit(":", 1)
                signals.append({
                    "market": data["trades"][0]["market"] if data["trades"] else slug,
                    "slug": slug,
                    "action": side,
                    "whale_count": whale_count,
                    "total_volume": round(data["total_volume"], 2),
                    "confidence": min(100, whale_count * 25 + data["total_volume"] // 1000),
                    "whales": list(data["whales"])[:5],
                })

        signals.sort(key=lambda x: x["confidence"], reverse=True)
        return signals

    def monitor(self, interval: int = 30):
        """Continuous monitoring mode."""
        self.log(f"Starting whale monitor (interval: {interval}s, threshold: ${self.min_whale_size})")
        seen_hashes = set()
        scan_count = 0

        while True:
            scan_count += 1
            trades = self.get_recent_trades(limit=50)
            whale_trades = self.filter_whale_trades(trades)

            # Find new whale trades
            new_whales = []
            for wt in whale_trades:
                tx = wt.get("tx_hash")
                if tx and tx not in seen_hashes:
                    seen_hashes.add(tx)
                    new_whales.append(wt)

            if new_whales:
                print(f"\n{'='*60}")
                print(f"NEW WHALE TRADES DETECTED (Scan #{scan_count})")
                print(f"{'='*60}")
                for wt in new_whales[:5]:
                    self._print_whale_trade(wt)

            # Keep seen_hashes manageable
            if len(seen_hashes) > 1000:
                seen_hashes = set(list(seen_hashes)[-500:])

            time.sleep(interval)

    def _print_whale_trade(self, wt: Dict):
        """Pretty print a whale trade."""
        print(f"\n  ${wt['usd_value']:,.2f} {wt['side']}")
        print(f"  Market: {wt['market']}")
        print(f"  Trader: {wt['name']} ({wt['wallet'][:12]}...)")
        print(f"  Size: {wt['size']} @ ${wt['price']}")
        if wt.get("tx_hash"):
            print(f"  TX: https://polygonscan.com/tx/{wt['tx_hash']}")


def main():
    parser = argparse.ArgumentParser(description="Polymarket Whale Tracker")
    parser.add_argument("--min-size", type=float, default=500, help="Min trade size in USD")
    parser.add_argument("--limit", type=int, default=100, help="Number of trades to fetch")
    parser.add_argument("--track", type=str, help="Track specific wallet address")
    parser.add_argument("--leaderboard", action="store_true", help="Show trader leaderboard")
    parser.add_argument("--signals", action="store_true", help="Generate copy signals")
    parser.add_argument("--monitor", action="store_true", help="Continuous monitoring")
    parser.add_argument("--interval", type=int, default=30, help="Monitor interval in seconds")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")

    args = parser.parse_args()

    tracker = WhaleTracker(min_whale_size=args.min_size, verbose=not args.quiet)

    print("=" * 70)
    print("POLYMARKET WHALE TRACKER")
    print("=" * 70)
    print(f"Min whale size: ${args.min_size}")
    print()

    if args.monitor:
        tracker.monitor(interval=args.interval)

    elif args.track:
        result = tracker.track_wallet(args.track, limit=args.limit)
        print(f"\nWallet: {args.track}")
        print("-" * 50)
        print(f"Total volume: ${result['summary'].get('total_volume', 0):,.2f}")
        print(f"Trades: {result['summary'].get('trade_count', 0)}")
        print(f"Buys/Sells: {result['summary'].get('buys', 0)}/{result['summary'].get('sells', 0)}")
        print(f"Unique markets: {result['summary'].get('unique_markets', 0)}")

        if result["trades"]:
            print("\nRecent trades:")
            for t in result["trades"][:5]:
                side = t.get("side", "?")
                size = t.get("size", 0)
                price = t.get("price", 0)
                market = t.get("title", "")[:40]
                print(f"  {side} {size} @ {price} - {market}...")

    elif args.leaderboard:
        trades = tracker.get_recent_trades(limit=args.limit)
        leaderboard = tracker.build_leaderboard(trades)

        print(f"\nTOP TRADERS (from {len(trades)} trades):")
        print("-" * 70)
        print(f"{'#':<3} {'Name':<20} {'Volume':>12} {'Trades':>8} {'Avg':>10} {'B/S':>8}")
        print("-" * 70)

        for i, t in enumerate(leaderboard[:20], 1):
            name = (t["name"] or "Anonymous")[:18]
            print(
                f"{i:<3} {name:<20} "
                f"${t['total_volume']:>10,.0f} "
                f"{t['trade_count']:>8} "
                f"${t['avg_trade_size']:>9,.0f} "
                f"{t['buys']}/{t['sells']:>5}"
            )

    elif args.signals:
        signals = tracker.generate_copy_signals()

        print("\nCOPY TRADING SIGNALS:")
        print("-" * 70)

        if signals:
            for i, s in enumerate(signals[:10], 1):
                print(f"\n{i}. {s['action']} - {s['market']}")
                print(f"   Whales: {s['whale_count']} | Volume: ${s['total_volume']:,.0f}")
                print(f"   Confidence: {s['confidence']}%")
        else:
            print("No strong signals detected (need 2+ whales on same market)")

    else:
        # Default: show recent whale trades
        trades = tracker.get_recent_trades(limit=args.limit)
        whale_trades = tracker.filter_whale_trades(trades)

        print(f"\nRecent whale trades (>${args.min_size}):")
        print("-" * 70)

        if whale_trades:
            for wt in whale_trades[:15]:
                tracker._print_whale_trade(wt)
        else:
            print(f"No trades found above ${args.min_size}")
            print(f"Try lowering threshold: --min-size 100")


if __name__ == "__main__":
    main()

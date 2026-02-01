"""
Whale Profiler - Volume-weighted ranking system for identifying top traders.

This module maintains profiles of whale traders based on trading activity,
calculates composite scores, and manages whitelist for copy trading.
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class WhaleProfiler:
    """Build and maintain whale trader profiles with volume-weighted scoring."""

    def __init__(self, data_file: str = "data/whale_profiles.json", config: Dict = None):
        """
        Initialize the whale profiler.

        Args:
            data_file: Path to JSON file for persisting profiles
            config: Configuration dict from config.json
        """
        self.data_file = Path(data_file)
        self.config = config or {}
        self.profiles: Dict[str, Dict] = {}
        self.last_update = None

        # Config defaults
        self.min_whale_size = self.config.get("min_whale_size", 500)
        self.min_score_to_whitelist = self.config.get("min_score_to_whitelist", 60)
        self.max_whitelisted = self.config.get("max_whitelisted_whales", 20)

        # Ensure data directory exists
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing profiles
        self.load()

    def load(self):
        """Load profiles from disk."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    self.profiles = data.get("profiles", {})
                    self.last_update = data.get("last_update")
                logger.info(f"Loaded {len(self.profiles)} whale profiles from disk")
            except Exception as e:
                logger.error(f"Error loading whale profiles: {e}")
                self.profiles = {}
        else:
            logger.info("No existing whale profiles found, starting fresh")
            self.profiles = {}

    def save(self):
        """Persist profiles to disk."""
        try:
            data = {
                "profiles": self.profiles,
                "last_update": datetime.now().isoformat(),
                "version": "1.0"
            }
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Saved {len(self.profiles)} whale profiles to disk")
        except Exception as e:
            logger.error(f"Error saving whale profiles: {e}")

    def update_profiles(self, trades: List[Dict]) -> Dict[str, int]:
        """
        Update whale profiles from a batch of trades.

        Args:
            trades: List of trade dicts from Polymarket API

        Returns:
            Dict with update stats: {profiles_updated, profiles_created, whales_whitelisted}
        """
        stats = {
            "profiles_updated": 0,
            "profiles_created": 0,
            "whales_whitelisted": 0,
            "trades_processed": len(trades)
        }

        # Build temporary aggregation
        aggregated = defaultdict(lambda: {
            "total_volume": 0,
            "trade_count": 0,
            "buys": 0,
            "sells": 0,
            "markets": set(),
            "last_seen": None,
            "first_seen": None,
            "profile_data": {}
        })

        for trade in trades:
            wallet = trade.get("proxyWallet", "")
            if not wallet:
                continue

            try:
                size = float(trade.get("size", 0))
                price = float(trade.get("price", 0))
                usd_value = size * price

                # Filter small trades
                if usd_value < self.min_whale_size:
                    continue

                side = trade.get("side", "").upper()
                timestamp = trade.get("timestamp")

                # Aggregate
                agg = aggregated[wallet]
                agg["total_volume"] += usd_value
                agg["trade_count"] += 1
                agg["markets"].add(trade.get("conditionId", ""))
                agg["last_seen"] = max(agg["last_seen"] or timestamp, timestamp or "")
                agg["first_seen"] = min(agg["first_seen"] or timestamp, timestamp or "")

                if side == "BUY":
                    agg["buys"] += 1
                elif side == "SELL":
                    agg["sells"] += 1

                # Store profile metadata (name, image, etc.)
                if not agg["profile_data"]:
                    agg["profile_data"] = {
                        "name": trade.get("name") or trade.get("pseudonym"),
                        "bio": trade.get("bio"),
                        "image": trade.get("profileImage")
                    }

            except (ValueError, TypeError) as e:
                logger.debug(f"Skipping trade due to parse error: {e}")
                continue

        # Merge aggregated data into existing profiles
        for wallet, agg_data in aggregated.items():
            if wallet in self.profiles:
                # Update existing profile
                profile = self.profiles[wallet]
                profile["stats"]["total_volume"] += agg_data["total_volume"]
                profile["stats"]["trade_count"] += agg_data["trade_count"]
                profile["stats"]["buys"] += agg_data["buys"]
                profile["stats"]["sells"] += agg_data["sells"]
                profile["stats"]["markets"].update(agg_data["markets"])
                profile["stats"]["last_seen"] = agg_data["last_seen"]
                stats["profiles_updated"] += 1
            else:
                # Create new profile
                self.profiles[wallet] = {
                    "wallet": wallet,
                    "name": agg_data["profile_data"].get("name") or "Anonymous",
                    "stats": {
                        "total_volume": agg_data["total_volume"],
                        "trade_count": agg_data["trade_count"],
                        "buys": agg_data["buys"],
                        "sells": agg_data["sells"],
                        "markets": agg_data["markets"],
                        "last_seen": agg_data["last_seen"],
                        "first_seen": agg_data["first_seen"]
                    },
                    "profile_data": agg_data["profile_data"],
                    "score": 0,
                    "rank": None,
                    "whitelisted": False,
                    "tags": [],
                    "created_at": datetime.now().isoformat()
                }
                stats["profiles_created"] += 1

        # Calculate scores and update rankings
        self._calculate_scores()
        self._update_rankings()
        self._update_whitelist()

        # Count whitelisted
        stats["whales_whitelisted"] = sum(1 for p in self.profiles.values() if p["whitelisted"])

        # Save to disk
        self.save()
        self.last_update = datetime.now().isoformat()

        logger.info(f"Profile update complete: {stats}")
        return stats

    def _calculate_scores(self):
        """
        Calculate composite score for each whale.

        Score = weighted combination of:
        - Volume (40%)
        - Consistency (30%)
        - Diversity (20%)
        - Recency (10%)
        """
        for wallet, profile in self.profiles.items():
            stats = profile["stats"]

            # Convert set to list for JSON serialization
            if isinstance(stats.get("markets"), set):
                stats["markets"] = list(stats["markets"])

            unique_markets = len(stats.get("markets", []))
            total_volume = stats.get("total_volume", 0)
            trade_count = stats.get("trade_count", 0)
            last_seen = stats.get("last_seen")

            # Volume score (max at $10,000)
            volume_score = min(100, (total_volume / 10000) * 100)

            # Consistency score (max at 50 trades)
            consistency_score = min(100, (trade_count / 50) * 100)

            # Diversity score (max at 20 markets)
            diversity_score = min(100, (unique_markets / 20) * 100)

            # Recency score (100 if seen in last 24h, 50 if last week, 0 if >30 days)
            recency_score = self._calculate_recency_score(last_seen)

            # Weighted composite score
            composite = (
                volume_score * 0.40 +
                consistency_score * 0.30 +
                diversity_score * 0.20 +
                recency_score * 0.10
            )

            profile["score"] = round(composite, 2)

            # Update stats (derived)
            stats["unique_markets"] = unique_markets
            stats["avg_trade_size"] = round(total_volume / max(1, trade_count), 2)

            # Tag classification
            tags = []
            if total_volume > 50000:
                tags.append("ultra_whale")
            elif total_volume > 10000:
                tags.append("high_volume")
            if trade_count > 100:
                tags.append("consistent")
            if unique_markets > 30:
                tags.append("diverse")
            if recency_score == 100:
                tags.append("active")

            profile["tags"] = tags

    def _calculate_recency_score(self, last_seen: Optional[str]) -> float:
        """Calculate recency score based on last trade timestamp."""
        if not last_seen:
            return 0.0

        try:
            # Parse ISO timestamp
            last_trade = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            now = datetime.now(last_trade.tzinfo)
            hours_ago = (now - last_trade).total_seconds() / 3600

            if hours_ago < 24:
                return 100.0
            elif hours_ago < 168:  # 7 days
                return 50.0
            elif hours_ago < 720:  # 30 days
                return 25.0
            else:
                return 0.0
        except Exception:
            return 0.0

    def _update_rankings(self):
        """Update rank field based on scores."""
        # Sort by score descending
        sorted_profiles = sorted(
            self.profiles.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )

        for rank, (wallet, profile) in enumerate(sorted_profiles, start=1):
            profile["rank"] = rank

    def _update_whitelist(self):
        """Update whitelisted status based on score threshold and max count."""
        # Get top N whales above threshold
        eligible = [
            (wallet, profile)
            for wallet, profile in self.profiles.items()
            if profile["score"] >= self.min_score_to_whitelist
        ]

        # Sort by score
        eligible.sort(key=lambda x: x[1]["score"], reverse=True)

        # Whitelist top N
        whitelisted_wallets = set(wallet for wallet, _ in eligible[:self.max_whitelisted])

        # Update whitelisted flag
        for wallet, profile in self.profiles.items():
            profile["whitelisted"] = wallet in whitelisted_wallets

    def get_top_whales(self, limit: int = 10, whitelisted_only: bool = False) -> List[Dict]:
        """
        Get top N whale profiles.

        Args:
            limit: Maximum number of whales to return
            whitelisted_only: If True, only return whitelisted whales

        Returns:
            List of whale profile dicts
        """
        profiles = list(self.profiles.values())

        if whitelisted_only:
            profiles = [p for p in profiles if p.get("whitelisted", False)]

        # Sort by score
        profiles.sort(key=lambda x: x.get("score", 0), reverse=True)

        return profiles[:limit]

    def get_profile(self, wallet: str) -> Optional[Dict]:
        """Get full profile for a specific wallet."""
        return self.profiles.get(wallet)

    def is_whitelisted(self, wallet: str, min_score: Optional[float] = None) -> bool:
        """
        Check if a wallet is whitelisted for copy trading.

        Args:
            wallet: Wallet address
            min_score: Optional additional score threshold

        Returns:
            True if whitelisted and (optionally) above min_score
        """
        profile = self.get_profile(wallet)
        if not profile:
            return False

        whitelisted = profile.get("whitelisted", False)
        if not whitelisted:
            return False

        if min_score is not None:
            return profile.get("score", 0) >= min_score

        return True

    def get_whitelist(self) -> List[str]:
        """Get list of whitelisted wallet addresses."""
        return [
            wallet
            for wallet, profile in self.profiles.items()
            if profile.get("whitelisted", False)
        ]

    def get_stats(self) -> Dict:
        """Get summary statistics about the profiler."""
        return {
            "total_profiles": len(self.profiles),
            "whitelisted_count": sum(1 for p in self.profiles.values() if p.get("whitelisted")),
            "last_update": self.last_update,
            "avg_score": round(
                sum(p.get("score", 0) for p in self.profiles.values()) / max(1, len(self.profiles)),
                2
            ),
            "top_whale": self.get_top_whales(limit=1)[0] if self.profiles else None
        }

    def print_leaderboard(self, limit: int = 20):
        """Pretty print whale leaderboard."""
        print("=" * 90)
        print("WHALE TRADER LEADERBOARD")
        print("=" * 90)
        print(f"{'Rank':<6} {'Name':<20} {'Score':<8} {'Volume':<12} {'Trades':<8} {'Markets':<8} {'Status'}")
        print("-" * 90)

        top_whales = self.get_top_whales(limit=limit)

        for whale in top_whales:
            rank = whale.get("rank", "-")
            name = (whale.get("name") or "Anonymous")[:18]
            score = whale.get("score", 0)
            volume = whale["stats"].get("total_volume", 0)
            trades = whale["stats"].get("trade_count", 0)
            markets = whale["stats"].get("unique_markets", 0)
            status = "✓ WHITELISTED" if whale.get("whitelisted") else ""

            print(
                f"{rank:<6} {name:<20} {score:<8.1f} "
                f"${volume:>10,.0f} {trades:<8} {markets:<8} {status}"
            )

        print("=" * 90)
        stats = self.get_stats()
        print(f"Total profiles: {stats['total_profiles']} | Whitelisted: {stats['whitelisted_count']}")
        print(f"Last update: {stats['last_update']}")
        print("=" * 90)

"""
Whale Monitor - Real-time detection of whale trades for copy trading signals.

This module monitors the Polymarket trades API for new whale activity,
filters by whitelist, and generates copy trading signals.
"""

import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add parent to path for tools import
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.whale_tracker import WhaleTracker
from bot.whale_profiler import WhaleProfiler

logger = logging.getLogger(__name__)


class WhaleMonitor:
    """Monitor whale trades in real-time and generate copy signals."""

    def __init__(
        self,
        profiler: WhaleProfiler,
        config: Dict = None,
        min_whale_size: float = 500
    ):
        """
        Initialize whale monitor.

        Args:
            profiler: WhaleProfiler instance for whitelist management
            config: Configuration dict from config.json
            min_whale_size: Minimum trade size in USD to consider
        """
        self.profiler = profiler
        self.config = config or {}
        self.min_whale_size = min_whale_size

        # Initialize WhaleTracker
        self.tracker = WhaleTracker(min_whale_size=min_whale_size, verbose=False)

        # Config from whale_copy_trading.monitor section
        monitor_config = self.config.get("monitor", {})
        self.poll_interval = monitor_config.get("poll_interval_seconds", 30)
        self.max_trade_age_minutes = monitor_config.get("max_trade_age_minutes", 10)
        self.require_consensus = monitor_config.get("require_consensus", False)
        self.min_consensus_whales = monitor_config.get("min_consensus_whales", 3)

        # Track seen trades to avoid duplicates
        self.seen_trades: Set[str] = set()
        self.last_scan_time = None

        # Statistics
        self.stats = {
            "scans_performed": 0,
            "trades_detected": 0,
            "signals_generated": 0,
            "whitelisted_signals": 0,
            "consensus_signals": 0
        }

    def scan_for_signals(self, limit: int = 100) -> List[Dict]:
        """
        Poll API for new whale trades and generate copy signals.

        Args:
            limit: Number of recent trades to fetch

        Returns:
            List of signal dicts: {
                signal_id, wallet, whale_name, side, market, slug,
                token_id, usd_value, price, size, confidence,
                timestamp, reason, whale_score
            }
        """
        self.stats["scans_performed"] += 1
        scan_start = time.time()

        # Fetch recent trades
        trades = self.tracker.get_recent_trades(limit=limit)
        if not trades:
            logger.debug("No trades fetched from API")
            return []

        # Filter whale trades
        whale_trades = self.tracker.filter_whale_trades(trades, min_usd=self.min_whale_size)
        self.stats["trades_detected"] += len(whale_trades)

        # Filter by whitelist
        whitelisted_trades = self._filter_whitelisted_trades(whale_trades)
        logger.debug(
            f"Filtered {len(whale_trades)} whale trades → "
            f"{len(whitelisted_trades)} whitelisted"
        )

        # Filter new trades only (not seen before)
        new_trades = self._filter_new_trades(whitelisted_trades)
        logger.debug(f"New whitelisted trades: {len(new_trades)}")

        # Filter by age
        fresh_trades = self._filter_by_age(new_trades)

        # Generate signals
        signals = []

        # Mode 1: Individual whale signals
        if not self.require_consensus:
            for trade in fresh_trades:
                signal = self._create_signal_from_trade(trade, reason="whale_whitelisted")
                signals.append(signal)

        # Mode 2: Consensus signals (multiple whales on same market)
        if self.require_consensus or len(signals) == 0:
            consensus_signals = self._detect_consensus(fresh_trades)
            signals.extend(consensus_signals)
            self.stats["consensus_signals"] += len(consensus_signals)

        self.stats["signals_generated"] += len(signals)
        self.stats["whitelisted_signals"] += len([s for s in signals if s["reason"] == "whale_whitelisted"])

        scan_duration = time.time() - scan_start
        logger.info(
            f"Whale scan complete: {len(signals)} signals generated "
            f"({len(whitelisted_trades)} whitelisted, {len(fresh_trades)} fresh) "
            f"in {scan_duration:.2f}s"
        )

        self.last_scan_time = datetime.now()

        return signals

    def _filter_whitelisted_trades(self, trades: List[Dict]) -> List[Dict]:
        """Keep only trades from whitelisted whales."""
        whitelisted = []

        for trade in trades:
            wallet = trade.get("wallet", "")
            if self.profiler.is_whitelisted(wallet):
                # Enrich with whale profile data
                profile = self.profiler.get_profile(wallet)
                trade["whale_score"] = profile.get("score", 0)
                trade["whale_rank"] = profile.get("rank")
                trade["whale_name"] = profile.get("name", "Anonymous")
                whitelisted.append(trade)

        return whitelisted

    def _filter_new_trades(self, trades: List[Dict]) -> List[Dict]:
        """Filter out trades we've already seen."""
        new_trades = []

        for trade in trades:
            # Use tx_hash as unique identifier
            tx_hash = trade.get("tx_hash", "")
            if not tx_hash:
                # Fallback: use combination of wallet + timestamp + market
                tx_hash = f"{trade.get('wallet')}:{trade.get('timestamp')}:{trade.get('slug')}"

            if tx_hash not in self.seen_trades:
                self.seen_trades.add(tx_hash)
                new_trades.append(trade)

        # Cleanup seen_trades if it gets too large
        if len(self.seen_trades) > 5000:
            logger.info("Trimming seen_trades cache")
            self.seen_trades = set(list(self.seen_trades)[-2500:])

        return new_trades

    def _filter_by_age(self, trades: List[Dict]) -> List[Dict]:
        """Filter trades by maximum age."""
        now = datetime.now()
        max_age = timedelta(minutes=self.max_trade_age_minutes)

        fresh_trades = []

        for trade in trades:
            timestamp_str = trade.get("timestamp", "")
            if not timestamp_str:
                continue

            try:
                # Parse ISO timestamp
                trade_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                # Make now timezone-aware if trade_time is
                now_aware = now.replace(tzinfo=trade_time.tzinfo) if trade_time.tzinfo else now
                age = now_aware - trade_time

                if age <= max_age:
                    fresh_trades.append(trade)
                else:
                    logger.debug(
                        f"Trade too old: {age.total_seconds()/60:.1f} min "
                        f"(max {self.max_trade_age_minutes})"
                    )
            except Exception as e:
                logger.debug(f"Error parsing timestamp {timestamp_str}: {e}")
                continue

        return fresh_trades

    def _create_signal_from_trade(self, trade: Dict, reason: str = "whale_whitelisted") -> Dict:
        """Create a copy trading signal from a whale trade."""
        # Generate unique signal ID
        signal_id = f"signal_{trade.get('wallet', '')[:8]}_{int(time.time())}"

        return {
            "signal_id": signal_id,
            "wallet": trade.get("wallet", ""),
            "whale_name": trade.get("whale_name", "Anonymous"),
            "whale_score": trade.get("whale_score", 0),
            "whale_rank": trade.get("whale_rank"),
            "side": trade.get("side", "BUY"),
            "market": trade.get("market", ""),
            "slug": trade.get("slug", ""),
            "outcome": trade.get("outcome", ""),
            "token_id": self._extract_token_id(trade),
            "usd_value": trade.get("usd_value", 0),
            "price": trade.get("price", 0),
            "size": trade.get("size", 0),
            "timestamp": trade.get("timestamp"),
            "tx_hash": trade.get("tx_hash", ""),
            "confidence": self._calculate_confidence(trade, whale_count=1),
            "reason": reason,
            "raw_trade": trade.get("raw", {})
        }

    def _extract_token_id(self, trade: Dict) -> str:
        """Extract token_id from trade data."""
        # Try multiple fields
        raw = trade.get("raw", {})
        return (
            raw.get("token_id") or
            raw.get("tokenID") or
            raw.get("asset_id") or
            trade.get("token_id") or
            ""
        )

    def _calculate_confidence(self, trade: Dict, whale_count: int = 1) -> int:
        """
        Calculate confidence score for a signal.

        Based on:
        - Whale score (0-100)
        - Whale count (for consensus)
        - Trade size

        Returns:
            Confidence score 0-100
        """
        whale_score = trade.get("whale_score", 50)
        usd_value = trade.get("usd_value", 0)

        # Base confidence from whale score (50% weight)
        base_confidence = whale_score * 0.5

        # Whale consensus bonus (30% weight)
        consensus_bonus = min(30, whale_count * 10)

        # Trade size bonus (20% weight, max at $5000)
        size_bonus = min(20, (usd_value / 5000) * 20)

        total = base_confidence + consensus_bonus + size_bonus

        return int(min(100, total))

    def _detect_consensus(self, trades: List[Dict]) -> List[Dict]:
        """
        Detect markets where multiple whales are trading.

        Returns signals only when >= min_consensus_whales operate on same market/side.
        """
        # Group by market + side
        market_activity = defaultdict(lambda: {
            "whales": set(),
            "trades": [],
            "total_volume": 0
        })

        for trade in trades:
            key = f"{trade.get('slug', '')}:{trade.get('side', 'BUY')}"
            market_activity[key]["whales"].add(trade.get("wallet", ""))
            market_activity[key]["trades"].append(trade)
            market_activity[key]["total_volume"] += trade.get("usd_value", 0)

        # Generate consensus signals
        signals = []

        for key, data in market_activity.items():
            whale_count = len(data["whales"])

            if whale_count >= self.min_consensus_whales:
                # Use the most recent trade as template
                latest_trade = max(data["trades"], key=lambda t: t.get("timestamp", ""))

                signal = self._create_signal_from_trade(
                    latest_trade,
                    reason=f"whale_consensus_{whale_count}"
                )

                # Update confidence based on consensus
                signal["confidence"] = self._calculate_confidence(
                    latest_trade,
                    whale_count=whale_count
                )

                signal["whale_count"] = whale_count
                signal["consensus_volume"] = round(data["total_volume"], 2)
                signal["consensus_whales"] = list(data["whales"])[:5]  # Top 5

                signals.append(signal)

                logger.info(
                    f"CONSENSUS DETECTED: {whale_count} whales on {latest_trade.get('market', '')} "
                    f"({latest_trade.get('side', '')})"
                )

        return signals

    def get_stats(self) -> Dict:
        """Get monitor statistics."""
        return {
            **self.stats,
            "seen_trades_cache_size": len(self.seen_trades),
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "whitelist_size": len(self.profiler.get_whitelist())
        }

    def reset_stats(self):
        """Reset statistics counters."""
        self.stats = {
            "scans_performed": 0,
            "trades_detected": 0,
            "signals_generated": 0,
            "whitelisted_signals": 0,
            "consensus_signals": 0
        }
        logger.info("Monitor stats reset")

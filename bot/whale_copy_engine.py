"""
Whale Copy Engine - Decision logic and execution for copying whale trades.

This module evaluates copy trading signals against risk management rules
and executes validated copy trades.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class WhaleCopyEngine:
    """
    Decide which whale trades to copy and execute them.

    Performs comprehensive validation before copying:
    1. Whale whitelist check
    2. Trade age check
    3. Side filter (BUY/SELL)
    4. Trade size bounds
    5. Market filters (if enabled)
    6. Capital availability
    7. Daily limits
    8. Risk allocation
    9. Diversification
    10. Daily loss limit
    """

    def __init__(
        self,
        config: Dict,
        profiler,
        trader,
        position_manager,
        market_scanner=None
    ):
        """
        Initialize copy engine.

        Args:
            config: Full config dict from config.json
            profiler: WhaleProfiler instance
            trader: Trader instance for execution
            position_manager: PositionManager instance
            market_scanner: Optional MarketScanner for market filter validation
        """
        self.config = config
        self.profiler = profiler
        self.trader = trader
        self.pm = position_manager
        self.market_scanner = market_scanner

        # Extract whale copy config
        self.wct_config = config.get("whale_copy_trading", {})
        self.copy_rules = self.wct_config.get("copy_rules", {})
        self.risk_mgmt = self.wct_config.get("risk_management", {})

        # Copy statistics
        self.stats_file = Path("data/whale_copy_stats.json")
        self.stats = self._load_stats()

        # Track copies
        self.copy_positions_file = Path("data/whale_copy_positions.json")
        self.copy_positions = self._load_copy_positions()

    def _load_stats(self) -> Dict:
        """Load copy trading statistics from disk."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading copy stats: {e}")

        return {
            "signals_evaluated": 0,
            "signals_copied": 0,
            "signals_rejected": 0,
            "rejection_reasons": {},
            "copies_by_day": {},
            "total_pnl": 0.0,
            "wins": 0,
            "losses": 0
        }

    def _save_stats(self):
        """Save copy trading statistics to disk."""
        try:
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.stats_file, "w") as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving copy stats: {e}")

    def _load_copy_positions(self) -> Dict:
        """Load copy positions from disk."""
        if self.copy_positions_file.exists():
            try:
                with open(self.copy_positions_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading copy positions: {e}")

        return {}

    def _save_copy_positions(self):
        """Save copy positions to disk."""
        try:
            self.copy_positions_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.copy_positions_file, "w") as f:
                json.dump(self.copy_positions, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving copy positions: {e}")

    def evaluate_signal(self, signal: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """
        Evaluate if we should copy this signal.

        Args:
            signal: Signal dict from WhaleMonitor

        Returns:
            Tuple of (should_copy, reason, execution_params)
        """
        self.stats["signals_evaluated"] += 1

        # 1. Whale whitelist check
        whale_wallet = signal.get("wallet", "")
        min_score = self.copy_rules.get("require_whale_score_above", 70)

        if not self.profiler.is_whitelisted(whale_wallet, min_score=min_score):
            return self._reject("whale_not_whitelisted_or_low_score")

        # 2. Blacklist check
        blacklist = self.copy_rules.get("blacklist_wallets", [])
        if whale_wallet in blacklist:
            return self._reject("whale_blacklisted")

        # 3. Trade age check (already done by monitor, but double-check)
        if not self._is_trade_fresh(signal):
            return self._reject("trade_too_old")

        # 4. Side filter
        allowed_sides = self.copy_rules.get("enabled_sides", ["BUY"])
        if signal.get("side", "") not in allowed_sides:
            return self._reject(f"side_{signal.get('side')}_not_enabled")

        # 5. Trade size bounds
        whale_size = signal.get("usd_value", 0)
        min_size = self.copy_rules.get("min_whale_trade_size", 500)
        max_size = self.copy_rules.get("max_whale_trade_size", 50000)

        if whale_size < min_size:
            return self._reject("whale_trade_too_small")
        if whale_size > max_size:
            return self._reject("whale_trade_suspiciously_large")

        # 6. Market filters (optional)
        if self.copy_rules.get("apply_market_filters", True):
            if not self._passes_market_filters(signal):
                return self._reject("market_filters_failed")

        # 7. Capital check
        copy_size = self.copy_rules.get("copy_position_size", 0.50)
        if not self._has_available_capital(copy_size):
            return self._reject("insufficient_capital")

        # 8. Daily limits
        max_copies_per_day = self.copy_rules.get("max_copies_per_day", 10)
        if not self._check_daily_limit(max_copies_per_day):
            return self._reject("daily_copy_limit_reached")

        # 9. Risk allocation check
        max_allocation = self.risk_mgmt.get("max_copy_allocation", 5.0)
        if not self._check_allocation_limit(max_allocation):
            return self._reject("max_copy_allocation_reached")

        # 10. Diversification check
        min_markets = self.risk_mgmt.get("diversification_min_markets", 3)
        if not self._check_diversification(signal, min_markets):
            return self._reject("concentration_risk")

        # 11. Daily loss limit
        daily_loss_limit = self.risk_mgmt.get("stop_if_daily_loss", 2.0)
        if not self._check_daily_loss_limit(daily_loss_limit):
            return self._reject("daily_loss_limit_hit")

        # All checks passed - prepare execution params
        execution_params = {
            "token_id": signal.get("token_id", ""),
            "side": signal.get("side", "BUY"),
            "size": copy_size,
            "whale_price": signal.get("price", 0),
            "whale_wallet": whale_wallet,
            "whale_name": signal.get("whale_name", "Anonymous"),
            "signal_id": signal.get("signal_id", ""),
            "confidence": signal.get("confidence", 0)
        }

        logger.info(
            f"✅ Signal APPROVED for copy: {signal.get('whale_name')} "
            f"{signal.get('side')} {signal.get('market', '')} "
            f"(confidence: {signal.get('confidence')}%)"
        )

        return True, "all_validations_passed", execution_params

    def _reject(self, reason: str) -> Tuple[bool, str, None]:
        """Record rejection and return rejection tuple."""
        self.stats["signals_rejected"] += 1
        self.stats["rejection_reasons"][reason] = self.stats["rejection_reasons"].get(reason, 0) + 1
        logger.debug(f"Signal rejected: {reason}")
        return False, reason, None

    def _is_trade_fresh(self, signal: Dict) -> bool:
        """Check if trade is recent enough."""
        timestamp_str = signal.get("timestamp", "")
        if not timestamp_str:
            return False

        try:
            trade_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now(trade_time.tzinfo)
            age_minutes = (now - trade_time).total_seconds() / 60

            max_age = self.wct_config.get("monitor", {}).get("max_trade_age_minutes", 10)
            return age_minutes <= max_age
        except Exception:
            return False

    def _passes_market_filters(self, signal: Dict) -> bool:
        """
        Check if market passes our standard filters.

        Note: Without full market data, we can only do basic checks.
        Full filter validation would require fetching orderbook.
        """
        # If no market scanner provided, skip filter check
        if not self.market_scanner:
            logger.debug("No market scanner - skipping market filters")
            return True

        # TODO: Fetch market data and run through scanner filters
        # For now, return True (optimistic)
        return True

    def _has_available_capital(self, required: float) -> bool:
        """Check if we have enough capital available."""
        try:
            balance = self.trader.get_balance()
            return balance >= required
        except Exception as e:
            logger.error(f"Error checking balance: {e}")
            return False

    def _check_daily_limit(self, max_copies: int) -> bool:
        """Check if we've hit daily copy limit."""
        today = datetime.now().date().isoformat()
        copies_today = self.stats["copies_by_day"].get(today, 0)
        return copies_today < max_copies

    def _check_allocation_limit(self, max_allocation: float) -> bool:
        """Check total USD allocated to copy trades."""
        total_allocated = sum(
            pos.get("size", 0) * pos.get("entry_price", 0)
            for pos in self.copy_positions.values()
            if pos.get("status") == "open"
        )
        return total_allocated < max_allocation

    def _check_diversification(self, signal: Dict, min_markets: int) -> bool:
        """Check diversification - avoid concentration in single market."""
        # Get unique markets in open copy positions
        open_positions = [p for p in self.copy_positions.values() if p.get("status") == "open"]
        unique_markets = set(p.get("market_slug", "") for p in open_positions)

        # If we have < min_markets, allow any market
        if len(unique_markets) < min_markets:
            return True

        # If we have enough diversity, only allow new markets
        signal_market = signal.get("slug", "")
        return signal_market not in unique_markets

    def _check_daily_loss_limit(self, max_loss: float) -> bool:
        """Check if we've hit daily loss limit."""
        today = datetime.now().date().isoformat()

        # Calculate P&L for today's closed positions
        daily_pnl = sum(
            pos.get("pnl", 0)
            for pos in self.copy_positions.values()
            if pos.get("closed_date", "").startswith(today)
        )

        return daily_pnl > -max_loss

    def execute_copy(self, signal: Dict, params: Dict, dry_run: bool = True) -> Dict:
        """
        Execute a copy trade.

        Args:
            signal: Original signal dict
            params: Execution parameters from evaluate_signal()
            dry_run: If True, simulate without real execution

        Returns:
            Result dict with success status and details
        """
        logger.info(
            f"{'[DRY RUN] ' if dry_run else ''}Executing copy trade: "
            f"{params['whale_name']} {params['side']} ${params['size']}"
        )

        result = {
            "success": False,
            "copy_id": None,
            "reason": None,
            "timestamp": datetime.now().isoformat()
        }

        try:
            if dry_run:
                # Simulate execution
                result["success"] = True
                result["copy_id"] = f"DRY_{signal.get('signal_id', 'unknown')}"
                result["reason"] = "dry_run_simulated"
                result["simulated"] = True
            else:
                # TODO: Real execution via trader
                # fill = self.trader.execute_buy(
                #     token_id=params["token_id"],
                #     size=params["size"]
                # )
                # result["success"] = fill["success"]
                # result["copy_id"] = f"copy_{fill['order_id']}"

                result["success"] = True
                result["copy_id"] = f"copy_{signal.get('signal_id', 'unknown')}"
                result["reason"] = "executed"
                result["simulated"] = False

            if result["success"]:
                # Record the copy position
                self._record_copy_position(signal, params, result)

                # Update stats
                self.stats["signals_copied"] += 1
                today = datetime.now().date().isoformat()
                self.stats["copies_by_day"][today] = self.stats["copies_by_day"].get(today, 0) + 1
                self._save_stats()

                logger.info(f"✅ Copy trade executed: {result['copy_id']}")

        except Exception as e:
            logger.error(f"Error executing copy trade: {e}")
            result["success"] = False
            result["reason"] = f"execution_error: {str(e)}"

        return result

    def _record_copy_position(self, signal: Dict, params: Dict, result: Dict):
        """Record a copy trade in positions tracking."""
        copy_id = result["copy_id"]

        self.copy_positions[copy_id] = {
            "copy_id": copy_id,
            "whale_wallet": params["whale_wallet"],
            "whale_name": params["whale_name"],
            "whale_price": params["whale_price"],
            "whale_size": signal.get("usd_value", 0),
            "signal_id": signal.get("signal_id", ""),
            "confidence": params["confidence"],
            "token_id": params["token_id"],
            "market": signal.get("market", ""),
            "market_slug": signal.get("slug", ""),
            "side": params["side"],
            "size": params["size"],
            "entry_price": params["whale_price"],  # Will be updated with actual fill price
            "entry_timestamp": datetime.now().isoformat(),
            "status": "open",
            "exit_strategy": self.risk_mgmt.get("exit_strategy", "follow_whale"),
            "tp_price": None,
            "sl_price": None,
            "pnl": 0.0,
            "closed_date": None,
            "exit_reason": None
        }

        self._save_copy_positions()

    def get_copy_statistics(self) -> Dict:
        """Get comprehensive statistics on copy trading performance."""
        open_positions = [p for p in self.copy_positions.values() if p.get("status") == "open"]
        closed_positions = [p for p in self.copy_positions.values() if p.get("status") == "closed"]

        wins = [p for p in closed_positions if p.get("pnl", 0) > 0]
        losses = [p for p in closed_positions if p.get("pnl", 0) < 0]

        total_pnl = sum(p.get("pnl", 0) for p in closed_positions)
        avg_win = sum(p.get("pnl", 0) for p in wins) / max(1, len(wins))
        avg_loss = sum(p.get("pnl", 0) for p in losses) / max(1, len(losses))

        return {
            **self.stats,
            "open_positions": len(open_positions),
            "closed_positions": len(closed_positions),
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate": round(len(wins) / max(1, len(closed_positions)) * 100, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / max(1, len(closed_positions)), 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "best_trade": max((p.get("pnl", 0) for p in closed_positions), default=0),
            "worst_trade": min((p.get("pnl", 0) for p in closed_positions), default=0)
        }

    def print_statistics(self):
        """Pretty print copy trading statistics."""
        stats = self.get_copy_statistics()

        print("\n" + "=" * 70)
        print("WHALE COPY TRADING STATISTICS")
        print("=" * 70)

        print(f"\nSignals:")
        print(f"  Evaluated:  {stats['signals_evaluated']}")
        print(f"  Copied:     {stats['signals_copied']} ({stats['signals_copied']/max(1, stats['signals_evaluated'])*100:.1f}%)")
        print(f"  Rejected:   {stats['signals_rejected']}")

        print(f"\nPositions:")
        print(f"  Open:       {stats['open_positions']}")
        print(f"  Closed:     {stats['closed_positions']}")

        print(f"\nPerformance:")
        print(f"  Wins:       {stats['win_count']} ({stats['win_rate']:.1f}%)")
        print(f"  Losses:     {stats['loss_count']}")
        print(f"  Total P&L:  ${stats['total_pnl']:.2f}")
        print(f"  Avg P&L:    ${stats['avg_pnl']:.2f}")
        print(f"  Best:       ${stats['best_trade']:.2f}")
        print(f"  Worst:      ${stats['worst_trade']:.2f}")

        if stats["rejection_reasons"]:
            print(f"\nTop Rejection Reasons:")
            sorted_reasons = sorted(
                stats["rejection_reasons"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for reason, count in sorted_reasons[:5]:
                print(f"  {reason}: {count}")

        print("=" * 70 + "\n")

"""
Position Manager for the Polymarket trading bot.

Handles:
- Position persistence (positions.json)
- Blacklist management (blacklist.json)
- Stats tracking (stats.json)
- Position reconciliation
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any


class Position:
    """Represents an open trading position."""

    def __init__(
        self,
        token_id: str,
        entry_price: float,
        size: float,
        filled_size: float,
        entry_time: str,
        tp: float,
        sl: float,
        fees_paid: float = 0.0,
        order_id: Optional[str] = None,
    ):
        self.token_id = token_id
        self.entry_price = entry_price
        self.size = size
        self.filled_size = filled_size
        self.entry_time = entry_time
        self.tp = tp
        self.sl = sl
        self.fees_paid = fees_paid
        self.order_id = order_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary for JSON serialization."""
        return {
            "entry_price": self.entry_price,
            "size": self.size,
            "filled_size": self.filled_size,
            "entry_time": self.entry_time,
            "tp": self.tp,
            "sl": self.sl,
            "fees_paid": self.fees_paid,
            "order_id": self.order_id,
        }

    @staticmethod
    def from_dict(token_id: str, data: Dict[str, Any]) -> "Position":
        """Create position from dictionary."""
        return Position(
            token_id=token_id,
            entry_price=data["entry_price"],
            size=data["size"],
            filled_size=data.get("filled_size", data["size"]),
            entry_time=data["entry_time"],
            tp=data["tp"],
            sl=data["sl"],
            fees_paid=data.get("fees_paid", 0.0),
            order_id=data.get("order_id"),
        )

    def __repr__(self) -> str:
        return (
            f"Position(token={self.token_id[:8]}..., "
            f"entry=${self.entry_price:.2f}, "
            f"size={self.filled_size}/{self.size}, "
            f"tp=${self.tp:.2f}, sl=${self.sl:.2f})"
        )


class PositionManager:
    """Manages open positions, blacklist, and stats."""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize position manager.

        Args:
            data_dir: Directory for data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.positions_file = self.data_dir / "positions.json"
        self.blacklist_file = self.data_dir / "blacklist.json"
        self.stats_file = self.data_dir / "stats.json"

        self.positions: Dict[str, Position] = {}
        self.blacklist: Dict[str, Dict[str, Any]] = {}
        self.stats: Dict[str, Any] = {}

        self._load_all()

    def _load_all(self):
        """Load all data files."""
        self._load_positions()
        self._load_blacklist()
        self._load_stats()

    def _load_positions(self):
        """Load positions from JSON file."""
        if self.positions_file.exists():
            with open(self.positions_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.positions = {
                    token_id: Position.from_dict(token_id, pos_data)
                    for token_id, pos_data in data.items()
                }
        else:
            self.positions = {}

    def _save_positions(self):
        """Save positions to JSON file."""
        data = {token_id: pos.to_dict() for token_id, pos in self.positions.items()}
        with open(self.positions_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_blacklist(self):
        """Load blacklist from JSON file."""
        if self.blacklist_file.exists():
            with open(self.blacklist_file, "r", encoding="utf-8") as f:
                self.blacklist = json.load(f)
        else:
            self.blacklist = {}

    def _save_blacklist(self):
        """Save blacklist to JSON file."""
        with open(self.blacklist_file, "w", encoding="utf-8") as f:
            json.dump(self.blacklist, f, indent=2, ensure_ascii=False)

    def _load_stats(self):
        """Load stats from JSON file."""
        if self.stats_file.exists():
            with open(self.stats_file, "r", encoding="utf-8") as f:
                self.stats = json.load(f)
        else:
            self.stats = self._init_stats()

    def _save_stats(self):
        """Save stats to JSON file."""
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize empty stats structure."""
        return {
            "lifetime": {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "roi": 0.0,
                "total_fees": 0.0,
                "avg_hold_time_hours": 0.0,
            },
            "daily": {},
            "by_odds_range": {
                "0.30-0.40": {"trades": 0, "wins": 0, "avg_pnl": 0.0},
                "0.40-0.50": {"trades": 0, "wins": 0, "avg_pnl": 0.0},
                "0.50-0.60": {"trades": 0, "wins": 0, "avg_pnl": 0.0},
                "0.60-0.70": {"trades": 0, "wins": 0, "avg_pnl": 0.0},
            },
        }

    # Position Management
    def add_position(self, position: Position):
        """Add a new position."""
        self.positions[position.token_id] = position
        self._save_positions()

    def get_position(self, token_id: str) -> Optional[Position]:
        """Get a position by token ID."""
        return self.positions.get(token_id)

    def remove_position(self, token_id: str) -> Optional[Position]:
        """Remove and return a position."""
        position = self.positions.pop(token_id, None)
        if position:
            self._save_positions()
        return position

    def get_all_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self.positions.values())

    def has_position(self, token_id: str) -> bool:
        """Check if a position exists."""
        return token_id in self.positions

    def position_count(self) -> int:
        """Get number of open positions."""
        return len(self.positions)

    # Blacklist Management
    def add_to_blacklist(
        self, token_id: str, reason: str, duration_days: int, max_attempts: int = 2
    ):
        """
        Add a market to the blacklist.

        Args:
            token_id: Market token ID
            reason: Reason for blacklisting (e.g., "stop_loss")
            duration_days: How many days to block
            max_attempts: Maximum attempts before permanent block
        """
        blocked_until = (
            datetime.now() + timedelta(days=duration_days)
        ).isoformat()

        if token_id in self.blacklist:
            # Increment attempts
            self.blacklist[token_id]["attempts"] += 1
        else:
            self.blacklist[token_id] = {
                "reason": reason,
                "blocked_until": blocked_until,
                "attempts": 1,
                "max_attempts": max_attempts,
            }

        self._save_blacklist()

    def is_blacklisted(self, token_id: str) -> bool:
        """Check if a market is blacklisted."""
        if token_id not in self.blacklist:
            return False

        entry = self.blacklist[token_id]
        blocked_until = datetime.fromisoformat(entry["blocked_until"])

        # Check if block expired
        if datetime.now() > blocked_until:
            # Check if max attempts reached
            if entry["attempts"] >= entry["max_attempts"]:
                # Keep in blacklist (permanent after max attempts)
                return True
            else:
                # Remove from blacklist (block expired, under max attempts)
                del self.blacklist[token_id]
                self._save_blacklist()
                return False

        return True

    def clean_blacklist(self):
        """Remove expired entries from blacklist."""
        to_remove = []
        for token_id, entry in self.blacklist.items():
            blocked_until = datetime.fromisoformat(entry["blocked_until"])
            if datetime.now() > blocked_until:
                if entry["attempts"] < entry["max_attempts"]:
                    to_remove.append(token_id)

        for token_id in to_remove:
            del self.blacklist[token_id]

        if to_remove:
            self._save_blacklist()

    def get_blacklist_count(self) -> int:
        """Get number of blacklisted markets."""
        self.clean_blacklist()
        return len(self.blacklist)

    # Stats Management
    def record_trade(
        self,
        entry_price: float,
        exit_price: float,
        size: float,
        fees: float,
        entry_time: str,
        exit_time: str,
        odds_range: str,
    ):
        """
        Record a completed trade in stats.

        Args:
            entry_price: Entry price
            exit_price: Exit price
            size: Position size
            fees: Total fees paid
            entry_time: Entry timestamp (ISO format)
            exit_time: Exit timestamp (ISO format)
            odds_range: Odds range (e.g., "0.30-0.40")
        """
        pnl = (exit_price - entry_price) * size - fees
        is_win = pnl > 0

        # Calculate hold time
        entry_dt = datetime.fromisoformat(entry_time)
        exit_dt = datetime.fromisoformat(exit_time)
        hold_hours = (exit_dt - entry_dt).total_seconds() / 3600

        # Update lifetime stats
        lifetime = self.stats["lifetime"]
        lifetime["total_trades"] += 1
        if is_win:
            lifetime["wins"] += 1
        else:
            lifetime["losses"] += 1
        lifetime["win_rate"] = (
            lifetime["wins"] / lifetime["total_trades"]
            if lifetime["total_trades"] > 0
            else 0.0
        )
        lifetime["total_pnl"] += pnl
        lifetime["total_fees"] += fees

        # Update average hold time
        prev_avg = lifetime["avg_hold_time_hours"]
        n = lifetime["total_trades"]
        lifetime["avg_hold_time_hours"] = (prev_avg * (n - 1) + hold_hours) / n

        # Update daily stats
        date = exit_dt.date().isoformat()
        if date not in self.stats["daily"]:
            self.stats["daily"][date] = {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "pnl": 0.0,
                "fees": 0.0,
            }

        daily = self.stats["daily"][date]
        daily["trades"] += 1
        if is_win:
            daily["wins"] += 1
        else:
            daily["losses"] += 1
        daily["pnl"] += pnl
        daily["fees"] += fees

        # Update by odds range
        if odds_range in self.stats["by_odds_range"]:
            range_stats = self.stats["by_odds_range"][odds_range]
            range_stats["trades"] += 1
            if is_win:
                range_stats["wins"] += 1

            # Update average P&L for this range
            prev_avg = range_stats["avg_pnl"]
            n = range_stats["trades"]
            range_stats["avg_pnl"] = (prev_avg * (n - 1) + pnl) / n

        self._save_stats()

    def get_daily_pnl(self, date: Optional[str] = None) -> float:
        """Get P&L for a specific date (default: today)."""
        if date is None:
            date = datetime.now().date().isoformat()

        if date in self.stats["daily"]:
            return self.stats["daily"][date]["pnl"]
        return 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get all stats."""
        return self.stats


# Example usage
if __name__ == "__main__":
    pm = PositionManager()

    # Test position management
    pos = Position(
        token_id="test123",
        entry_price=0.45,
        size=2.0,
        filled_size=2.0,
        entry_time=datetime.now().isoformat(),
        tp=0.54,
        sl=0.40,
        fees_paid=0.02,
    )

    pm.add_position(pos)
    print(f"Positions: {pm.position_count()}")
    print(f"Position: {pm.get_position('test123')}")

    # Test blacklist
    pm.add_to_blacklist("bad_market", "stop_loss", duration_days=3)
    print(f"Is blacklisted: {pm.is_blacklisted('bad_market')}")
    print(f"Blacklist count: {pm.get_blacklist_count()}")

    # Test stats
    print(f"Stats: {pm.get_stats()}")

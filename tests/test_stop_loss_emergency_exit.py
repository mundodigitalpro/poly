from datetime import datetime, timezone

from bot.position_manager import Position, PositionManager
from bot.trader import BotTrader
from main_bot import _update_positions


class DummyConfig:
    def __init__(self, min_sell_ratio=0.5):
        self.min_sell_ratio = min_sell_ratio

    def get(self, key, default=None):
        settings = {
            "bot.dry_run": True,
            "bot.order_timeout_seconds": 0,
            "risk.min_sell_price_ratio": self.min_sell_ratio,
            "api": {},
        }
        return settings.get(key, default)


class DummyLogger:
    def info(self, *args, **kwargs):
        pass

    def warn(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class DummyOrder:
    def __init__(self, price):
        self.price = price


class DummyBook:
    def __init__(self, bid, ask):
        self.bids = [DummyOrder(bid)]
        self.asks = [DummyOrder(ask)]


class DummyClient:
    def __init__(self, bid, ask):
        self.book = DummyBook(bid, ask)

    def get_order_book(self, token_id):
        return self.book


class DummyStrategy:
    def get_odds_range(self, odds):
        return "0.50-0.60"


def test_stop_loss_emergency_exit_allows_deep_drop(tmp_path):
    pm = PositionManager(data_dir=str(tmp_path))
    position = Position(
        token_id="token_90_drop",
        entry_price=1.0,
        size=10.0,
        filled_size=10.0,
        entry_time=datetime.now(timezone.utc).isoformat(),
        tp=1.2,
        sl=0.2,
    )
    pm.add_position(position)

    client = DummyClient(bid=0.1, ask=0.11)
    trader = BotTrader(client, DummyConfig(), DummyLogger())
    strategy = DummyStrategy()

    _update_positions(
        client,
        DummyLogger(),
        pm,
        trader,
        strategy,
        {"duration_days": 1, "max_attempts": 1},
    )

    assert pm.position_count() == 0
    assert pm.get_stats()["lifetime"]["total_trades"] == 1

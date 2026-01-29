import pytest
from bot.strategy import TradingStrategy
from bot.config import BotConfig

class MockConfig:
    def get(self, key, default=None):
        settings = {
            "strategy.tp_sl_by_odds": {
                "0.30-0.40": {"tp_percent": 25, "sl_percent": 15},
                "0.40-0.50": {"tp_percent": 20, "sl_percent": 12},
                "0.50-0.60": {"tp_percent": 15, "sl_percent": 10},
                "0.60-0.70": {"tp_percent": 12, "sl_percent": 8}
            },
            "strategy.market_score_weights": {
                "spread": 40,
                "volume": 30,
                "odds_distance": 20,
                "time_to_resolve": 10
            }
        }
        return settings.get(key, default)

@pytest.fixture
def strategy():
    return TradingStrategy(MockConfig())

def test_calculate_tp_sl(strategy):
    # Test range 0.40-0.50 (+20% / -12%)
    tp, sl = strategy.calculate_tp_sl(0.45)
    assert tp == pytest.approx(0.45 * 1.20)
    assert sl == pytest.approx(0.45 * 0.88)

    # Test range 0.60-0.70 (+12% / -8%)
    tp, sl = strategy.calculate_tp_sl(0.65)
    assert tp == pytest.approx(0.65 * 1.12)
    assert sl == pytest.approx(0.65 * 0.92)

def test_calculate_market_score(strategy):
    # High quality market: low spread, high volume, far from 0.5, low time
    score = strategy.calculate_market_score(
        spread_percent=1.0, 
        volume_usd=1000.0, 
        odds=0.30, 
        days_to_resolve=1
    )
    assert score > 80

    # Low quality market: high spread, low volume, near 0.5, high time
    score = strategy.calculate_market_score(
        spread_percent=10.0, 
        volume_usd=10.0, 
        odds=0.50, 
        days_to_resolve=30
    )
    assert score < 30

def test_calculate_position_size(strategy):
    # Normal case
    size = strategy.calculate_position_size(18.0, 1.0, 0, 5)
    assert size == 1.0

    # Limited capital
    size = strategy.calculate_position_size(0.5, 1.0, 0, 5)
    assert size == 0.5

    # Near max positions (80% of 5 = 4)
    size = strategy.calculate_position_size(18.0, 1.0, 4, 5)
    assert size == 0.75 # 1.0 * 0.75

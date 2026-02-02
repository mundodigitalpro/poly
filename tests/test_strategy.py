import pytest
from bot.strategy import TradingStrategy
from bot.config import BotConfig

class MockConfig:
    def get(self, key, default=None):
        settings = {
            "strategy.tp_sl_by_odds": {
                "0.35-0.45": {"tp_percent": 28, "sl_percent": 14},
                "0.45-0.55": {"tp_percent": 22, "sl_percent": 11},
                "0.55-0.65": {"tp_percent": 18, "sl_percent": 9},
                "0.65-0.75": {"tp_percent": 14, "sl_percent": 7},
                "0.75-0.80": {"tp_percent": 12, "sl_percent": 6}
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
    # Test range 0.45-0.55 (+22% / -11%) - 2:1 ratio
    tp, sl = strategy.calculate_tp_sl(0.50)
    assert tp == pytest.approx(0.50 * 1.22)
    assert sl == pytest.approx(0.50 * 0.89)

    # Test range 0.65-0.75 (+14% / -7%) - 2:1 ratio
    tp, sl = strategy.calculate_tp_sl(0.70)
    assert tp == pytest.approx(0.70 * 1.14)
    assert sl == pytest.approx(0.70 * 0.93)

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

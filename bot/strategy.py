"""
Trading strategy module for the Polymarket bot.

Handles:
- Dynamic TP/SL calculation based on entry odds
- Market scoring and ranking
- Position sizing
"""

from typing import Dict, Tuple


class TradingStrategy:
    """Implements trading strategy logic."""

    def __init__(self, config):
        """
        Initialize strategy with configuration.

        Args:
            config: BotConfig instance
        """
        self.config = config
        self.tp_sl_config = config.get("strategy.tp_sl_by_odds", {})
        self.score_weights = config.get("strategy.market_score_weights", {})

    def calculate_tp_sl(self, entry_odds: float) -> Tuple[float, float]:
        """
        Calculate take-profit and stop-loss prices based on entry odds.

        Args:
            entry_odds: Entry odds/price (0.0-1.0)

        Returns:
            Tuple of (tp_price, sl_price)
        """
        # Determine odds range (aligned with config ranges)
        if 0.35 <= entry_odds < 0.45:
            range_key = "0.35-0.45"
        elif 0.45 <= entry_odds < 0.55:
            range_key = "0.45-0.55"
        elif 0.55 <= entry_odds < 0.65:
            range_key = "0.55-0.65"
        elif 0.65 <= entry_odds < 0.75:
            range_key = "0.65-0.75"
        elif 0.75 <= entry_odds <= 0.80:
            range_key = "0.75-0.80"
        else:
            # Default to middle range if outside expected range
            range_key = "0.55-0.65"

        # Get TP/SL percentages for this range
        tp_sl = self.tp_sl_config.get(range_key, {"tp_percent": 18, "sl_percent": 9})
        tp_percent = tp_sl["tp_percent"] / 100
        sl_percent = tp_sl["sl_percent"] / 100

        # Calculate actual prices
        tp_price = entry_odds * (1 + tp_percent)
        sl_price = entry_odds * (1 - sl_percent)

        # Ensure prices are within valid range [0, 1]
        tp_price = min(tp_price, 0.99)
        sl_price = max(sl_price, 0.01)

        return (tp_price, sl_price)

    def calculate_market_score(
        self,
        spread_percent: float,
        volume_usd: float,
        odds: float,
        days_to_resolve: int,
    ) -> float:
        """
        Calculate a score for a market based on multiple factors.

        Higher score = better market for trading.

        Args:
            spread_percent: Bid-ask spread as percentage (e.g., 5.0 for 5%)
            volume_usd: Total volume in USD (both sides)
            odds: Current odds (0.0-1.0)
            days_to_resolve: Days until market resolution

        Returns:
            Market score (0-100)
        """
        # Get weights from config
        spread_weight = self.score_weights.get("spread", 40)
        volume_weight = self.score_weights.get("volume", 30)
        odds_weight = self.score_weights.get("odds_distance", 20)
        time_weight = self.score_weights.get("time_to_resolve", 10)

        # Normalize spread (lower is better)
        # 0% spread = 100 points, 10% spread = 0 points
        spread_score = max(0, 100 - (spread_percent * 10))

        # Normalize volume (higher is better)
        # $1000+ = 100 points, $0 = 0 points
        volume_score = min(100, (volume_usd / 1000) * 100)

        # Normalize odds distance from 0.50 (further from 0.50 is better for mean reversion)
        # 0.50 = 0 points, 0.30 or 0.70 = 100 points
        odds_distance = abs(odds - 0.50)
        odds_score = min(100, (odds_distance / 0.20) * 100)

        # Normalize time to resolve (closer is better)
        # 1 day = 100 points, 30 days = 0 points
        time_score = max(0, 100 - ((days_to_resolve / 30) * 100))

        # Calculate weighted score
        total_weight = spread_weight + volume_weight + odds_weight + time_weight
        score = (
            (spread_score * spread_weight)
            + (volume_score * volume_weight)
            + (odds_score * odds_weight)
            + (time_score * time_weight)
        ) / total_weight

        return round(score, 2)

    def calculate_position_size(
        self,
        available_capital: float,
        max_trade_size: float,
        num_open_positions: int,
        max_positions: int,
    ) -> float:
        """
        Calculate position size based on available capital and risk management.

        Args:
            available_capital: Available capital for trading
            max_trade_size: Maximum size per trade from config
            num_open_positions: Current number of open positions
            max_positions: Maximum allowed positions

        Returns:
            Position size in USD
        """
        # Basic position sizing: use max_trade_size or available capital, whichever is smaller
        position_size = min(max_trade_size, available_capital)

        # Additional safety: if nearing max positions, reduce size
        if num_open_positions >= max_positions * 0.8:  # 80% of max
            position_size *= 0.75  # Reduce by 25%

        # Ensure minimum trade size (e.g., $0.10)
        position_size = max(0.10, position_size)

        return round(position_size, 2)

    def get_odds_range(self, odds: float) -> str:
        """
        Get the odds range string for a given odds value.

        Args:
            odds: Odds value (0.0-1.0)

        Returns:
            Odds range string (e.g., "0.35-0.45")
        """
        if 0.35 <= odds < 0.45:
            return "0.35-0.45"
        elif 0.45 <= odds < 0.55:
            return "0.45-0.55"
        elif 0.55 <= odds < 0.65:
            return "0.55-0.65"
        elif 0.65 <= odds < 0.75:
            return "0.65-0.75"
        elif 0.75 <= odds <= 0.80:
            return "0.75-0.80"
        else:
            return "0.55-0.65"  # Default


# Example usage
if __name__ == "__main__":
    from bot.config import load_bot_config

    config = load_bot_config()
    strategy = TradingStrategy(config)

    # Test TP/SL calculation
    print("=== TP/SL Calculation (new 2:1 ratio) ===")
    test_odds = [0.40, 0.50, 0.60, 0.70, 0.77]
    for odds in test_odds:
        tp, sl = strategy.calculate_tp_sl(odds)
        range_key = strategy.get_odds_range(odds)
        tp_pct = (tp - odds) / odds * 100
        sl_pct = (odds - sl) / odds * 100
        print(f"Odds: {odds:.2f} [{range_key}] → TP: {tp:.3f} (+{tp_pct:.1f}%), SL: {sl:.3f} (-{sl_pct:.1f}%), Ratio: {tp_pct/sl_pct:.2f}:1")

    print("\n=== Market Scoring ===")
    # Test market scoring
    markets = [
        {"spread": 3.0, "volume": 500, "odds": 0.35, "days": 7},
        {"spread": 8.0, "volume": 150, "odds": 0.50, "days": 25},
        {"spread": 2.0, "volume": 1200, "odds": 0.65, "days": 3},
    ]

    for i, market in enumerate(markets, 1):
        score = strategy.calculate_market_score(
            market["spread"],
            market["volume"],
            market["odds"],
            market["days"],
        )
        print(
            f"Market {i}: spread={market['spread']}%, "
            f"vol=${market['volume']}, odds={market['odds']}, "
            f"days={market['days']} → Score: {score}"
        )

    print("\n=== Position Sizing ===")
    # Test position sizing
    scenarios = [
        (18.0, 1.0, 0, 5),  # Full capital, no positions
        (5.0, 1.0, 4, 5),   # Limited capital, near max positions
        (10.0, 1.0, 2, 5),  # Mid scenario
    ]

    for capital, max_size, open_pos, max_pos in scenarios:
        size = strategy.calculate_position_size(capital, max_size, open_pos, max_pos)
        print(
            f"Capital: ${capital}, Open: {open_pos}/{max_pos} → Size: ${size}"
        )

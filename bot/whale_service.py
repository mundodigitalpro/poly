"""Whale sentiment service for market scoring."""

from typing import Dict, Optional
from datetime import datetime, timedelta
from tools.whale_tracker import WhaleTracker


class WhaleService:
    """Provide whale sentiment scores for tokens."""
    
    def __init__(self, min_whale_size: float = 500, cache_ttl: int = 300):
        self.tracker = WhaleTracker(min_whale_size=min_whale_size, verbose=False)
        self.cache_ttl = cache_ttl  # 5 minutes
        self._cache: Dict[str, tuple] = {}  # token_id -> (sentiment, timestamp)
    
    def get_sentiment(self, token_id: str) -> float:
        """
        Get whale sentiment for a token.
        
        Returns:
            float: -1.0 (bearish) to +1.0 (bullish), 0.0 if no data
        """
        # Check cache
        if token_id in self._cache:
            sentiment, ts = self._cache[token_id]
            if (datetime.now() - ts).seconds < self.cache_ttl:
                return sentiment
        
        # Fetch recent trades for this token
        trades = self.tracker.get_recent_trades(limit=100)
        whale_trades = self.tracker.filter_whale_trades(trades)
        
        # Filter to this token
        token_trades = [t for t in whale_trades if t.get("token_id") == token_id]
        
        if not token_trades:
            return 0.0
        
        # Calculate buy/sell ratio
        buys = sum(t["usd_value"] for t in token_trades if t["side"] == "BUY")
        sells = sum(t["usd_value"] for t in token_trades if t["side"] == "SELL")
        total = buys + sells
        
        if total == 0:
            return 0.0
        
        # Sentiment: +1 = all buys, -1 = all sells
        sentiment = (buys - sells) / total
        
        # Cache result
        self._cache[token_id] = (sentiment, datetime.now())
        
        return round(sentiment, 2)
    
    def check_position_alerts(self, positions: list) -> list:
        """
        Check if whales are trading tokens we hold.
        
        Returns:
            List of alert dicts: {token_id, action, volume, traders}
        """
        alerts = []
        trades = self.tracker.get_recent_trades(limit=100)
        whale_trades = self.tracker.filter_whale_trades(trades)
        
        held_tokens = {p.get("token_id") for p in positions}
        
        for token_id in held_tokens:
            token_trades = [t for t in whale_trades if t.get("token_id") == token_id]
            if not token_trades:
                continue
            
            sells = [t for t in token_trades if t["side"] == "SELL"]
            if sells:
                total_sell = sum(t["usd_value"] for t in sells)
                if total_sell >= 1000:  # Alert threshold
                    alerts.append({
                        "token_id": token_id,
                        "action": "WHALE_SELLING",
                        "volume": total_sell,
                        "count": len(sells),
                    })
        
        return alerts

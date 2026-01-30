# Proposal: Whale Tracking Integration

**Author**: AMP (Orchestrator)  
**Date**: 2026-01-30  
**Status**: Draft  
**Priority**: Medium  

---

## Objective

Integrate whale trading signals from `whale_tracker.py` into the market scanner to:
1. Boost scores for markets with bullish whale activity
2. Penalize/filter markets where whales are selling
3. Alert when whales trade tokens we hold

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  data-api.poly  │────▶│  WhaleTracker    │────▶│  MarketScanner  │
│  /trades        │     │  (whale_tracker) │     │  (bot/)         │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │                         │
                              ▼                         ▼
                        whale_sentiment          calculate_market_score()
                        (-1 to +1)               score *= (1 + sentiment*0.2)
```

---

## Implementation Plan

### Phase 1: Whale Sentiment Service (New File)

Create `bot/whale_service.py`:

```python
"""Whale sentiment service for market scoring."""

from typing import Dict, Optional
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '..')
from whale_tracker import WhaleTracker


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
```

### Phase 2: Integrate into MarketScanner

Modify `bot/market_scanner.py`:

```python
# In __init__, add:
whale_cfg = config.get("whale_tracking", {})
self.whale_enabled = whale_cfg.get("enabled", False)
self.whale_weight = whale_cfg.get("score_weight", 0.2)
self.whale_service = None
if self.whale_enabled:
    from bot.whale_service import WhaleService
    self.whale_service = WhaleService(
        min_whale_size=whale_cfg.get("min_size", 500)
    )

# In _process_market(), after calculating score (line 226-231):
if self.whale_enabled and self.whale_service:
    sentiment = self.whale_service.get_sentiment(token_id)
    score *= (1 + sentiment * self.whale_weight)
    # Log whale influence
    if abs(sentiment) > 0.3:
        self.logger.info(
            f"Whale sentiment for {token_id[:8]}: {sentiment:+.2f} "
            f"(score adjusted: {score:.2f})"
        )
```

### Phase 3: Config Schema Update

Add to `config.json`:

```json
{
  "whale_tracking": {
    "enabled": false,
    "min_size": 500,
    "score_weight": 0.2,
    "alert_on_sell": true
  }
}
```

---

## Risk Analysis

| Risk | Mitigation |
|------|------------|
| API rate limits | Cache results for 5 minutes |
| Stale data | TTL-based cache invalidation |
| False signals | Weight at 0.2 (20% max impact) |
| No whale data | Default sentiment = 0 (neutral) |

---

## Testing Plan

1. **Unit test**: Mock whale API, verify sentiment calculation
2. **Integration test**: Verify scanner includes sentiment in score
3. **Dry-run**: Enable in config, monitor logs for 24h

---

## Acceptance Criteria

- [ ] `WhaleService` class created and tested
- [ ] `MarketScanner` integrates sentiment into score
- [ ] Config flag `whale_tracking.enabled` controls feature
- [ ] No performance regression (< 1s added latency per scan)
- [ ] Alerts generated when whales sell held positions

---

## Implementation Order

1. **CODEX**: Create `bot/whale_service.py` based on spec above
2. **CODEX**: Modify `bot/market_scanner.py` to use service
3. **AMP**: Review and merge
4. **GEMINI**: Test in dry-run mode

---

## Estimated Effort

| Task | Time |
|------|------|
| whale_service.py | 30 min |
| market_scanner.py changes | 20 min |
| Config + tests | 20 min |
| Dry-run validation | 24h |

**Total dev time**: ~1.5 hours

---

*Proposal by AMP - Awaiting team review*

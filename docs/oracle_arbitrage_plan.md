# Oracle-Based Arbitrage Implementation Plan

## Overview
Implement oracle-based arbitrage strategy inspired by eurobeta2smyr/polymarket-trading-bot.

## Strategy Description
The bot compares a theoretical "fair value" (oracle price) against the current market price. When the difference exceeds a threshold (e.g., 1.5%), it signals a trade opportunity.

**Example**:
- Oracle calculates fair value: $0.65
- Market price: $0.70
- Difference: -7.1% → Market is OVERPRICED → Consider SELL
- Oracle calculates fair value: $0.65
- Market price: $0.60
- Difference: +8.3% → Market is UNDERPRICED → Consider BUY

## Oracle Implementation Options

### Option 1: Fair Value Calculator (RECOMMENDED)
**Approach**: Calculate theoretical price based on market fundamentals.

**Data Sources**:
- Historical win rates for similar market types
- Related market odds (e.g., if betting on Team A vs Team B, check individual player markets)
- Volume-weighted average price (VWAP) over time windows
- Implied probability from bid/ask spread

**Model**:
```python
def calculate_fair_value(market_data: dict) -> float:
    """
    Calculate fair value using statistical model.

    Factors:
    - Current spread midpoint (weight: 0.4)
    - 1-hour VWAP (weight: 0.3)
    - Related market odds (weight: 0.2)
    - Historical base rate (weight: 0.1)
    """
    mid_price = (market_data['best_bid'] + market_data['best_ask']) / 2
    vwap_1h = get_vwap(market_data['token_id'], hours=1)
    related_odds = get_related_market_odds(market_data)
    base_rate = get_historical_base_rate(market_data['category'])

    fair_value = (
        mid_price * 0.4 +
        vwap_1h * 0.3 +
        related_odds * 0.2 +
        base_rate * 0.1
    )

    return fair_value
```

**Pros**:
- Self-contained (no external dependencies)
- Adapts to Polymarket-specific dynamics
- Can incorporate whale tracking data

**Cons**:
- Requires historical data collection
- Model needs tuning/backtesting

---

### Option 2: External Betting Odds Feed
**Approach**: Compare Polymarket odds against traditional sportsbooks.

**APIs to Consider**:
- **The Odds API** (theoddsapi.com) - $0.0001/request, covers sports/politics
- **Odds-API** (odds-api.com) - Free tier available
- **BetFair Exchange API** - Real betting exchange data

**Implementation**:
```python
import requests

class ExternalOddsOracle:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"

    def get_fair_value(self, event_description: str) -> float:
        """
        Map Polymarket event to external odds.

        Example:
        - Polymarket: "Will Trump win 2024 election?"
        - External: "2024 US Presidential Election - Trump"
        """
        # 1. Parse event description to match external market
        external_market = self._map_event(event_description)

        # 2. Fetch odds from multiple bookmakers
        response = requests.get(
            f"{self.base_url}/sports/{external_market}/odds",
            params={"apiKey": self.api_key, "regions": "us,uk"}
        )

        # 3. Calculate consensus odds (average across bookmakers)
        odds_data = response.json()
        consensus_prob = self._calculate_consensus(odds_data)

        return consensus_prob

    def _calculate_consensus(self, odds_data: list) -> float:
        """Average implied probabilities from multiple bookmakers."""
        probabilities = []
        for bookmaker in odds_data:
            # Convert decimal odds to probability
            decimal_odds = bookmaker['price']
            prob = 1 / decimal_odds
            probabilities.append(prob)

        return sum(probabilities) / len(probabilities)
```

**Pros**:
- Objective external price reference
- Works well for sports/political events
- High-quality data from professional bookmakers

**Cons**:
- API costs (can add up)
- Limited to mainstream events
- Latency (external API calls)

---

### Option 3: Cross-Market Arbitrage
**Approach**: Find same event listed under different condition_ids within Polymarket.

**Implementation**:
```python
class CrossMarketOracle:
    def __init__(self, gamma_client):
        self.gamma_client = gamma_client

    def get_fair_value(self, token_id: str, question: str) -> float:
        """
        Search for duplicate/related markets and compare prices.

        Example:
        - Market A: "Will Bitcoin exceed $100k in 2026?" → 0.65
        - Market B: "Bitcoin price on Dec 31, 2026 > $100k?" → 0.70
        - Arbitrage: Buy A at 0.65, sell B at 0.70 → 5% edge
        """
        # 1. Search for related markets using question similarity
        related_markets = self._find_related_markets(question)

        # 2. Extract odds from related markets
        related_odds = []
        for market in related_markets:
            odds = (market['bestBid'] + market['bestAsk']) / 2
            related_odds.append(odds)

        # 3. Return median as fair value
        if related_odds:
            return sorted(related_odds)[len(related_odds) // 2]

        return None  # No related markets found

    def _find_related_markets(self, question: str) -> list:
        """Use fuzzy matching to find duplicate markets."""
        from difflib import SequenceMatcher

        all_markets = self.gamma_client.get_markets()
        matches = []

        for market in all_markets:
            similarity = SequenceMatcher(
                None,
                question.lower(),
                market['question'].lower()
            ).ratio()

            if similarity > 0.7:  # 70% similar
                matches.append(market)

        return matches
```

**Pros**:
- Pure arbitrage (risk-free if executed correctly)
- No external dependencies
- Exploits Polymarket inefficiencies

**Cons**:
- Rare opportunities (markets usually consistent)
- Requires fast execution
- Limited to markets with duplicates

---

## Recommended Hybrid Approach

**Combine all three methods** with weighted confidence:

```python
class HybridOracle:
    def __init__(self, gamma_client, external_api_key=None):
        self.fair_value_calc = FairValueCalculator()
        self.external_odds = ExternalOddsOracle(external_api_key) if external_api_key else None
        self.cross_market = CrossMarketOracle(gamma_client)

    def get_oracle_price(self, market_data: dict) -> dict:
        """
        Get consensus oracle price from multiple sources.

        Returns:
            {
                'oracle_price': 0.65,
                'confidence': 0.85,  # Higher = more sources agree
                'sources': ['fair_value', 'external_odds'],
                'variance': 0.02  # Spread between sources
            }
        """
        prices = []
        sources = []

        # Method 1: Internal fair value model
        fv = self.fair_value_calc.calculate_fair_value(market_data)
        if fv:
            prices.append(fv)
            sources.append('fair_value')

        # Method 2: External odds (if available)
        if self.external_odds:
            ext = self.external_odds.get_fair_value(market_data['question'])
            if ext:
                prices.append(ext)
                sources.append('external_odds')

        # Method 3: Cross-market comparison
        cross = self.cross_market.get_fair_value(
            market_data['token_id'],
            market_data['question']
        )
        if cross:
            prices.append(cross)
            sources.append('cross_market')

        # Calculate consensus
        if not prices:
            return None

        oracle_price = sum(prices) / len(prices)
        variance = max(prices) - min(prices)
        confidence = 1.0 - (variance / oracle_price) if oracle_price > 0 else 0

        return {
            'oracle_price': oracle_price,
            'confidence': min(confidence, 1.0),
            'sources': sources,
            'variance': variance,
            'num_sources': len(sources)
        }
```

---

## Integration into Bot

### Modified Market Scanner

```python
# bot/market_scanner.py - ENHANCED

def _analyze_market(self, market: dict) -> Tuple[Optional[dict], str]:
    """Analyze market with oracle-based arbitrage detection."""

    # ... existing filters ...

    # NEW: Oracle arbitrage check
    oracle_result = self.oracle_service.get_oracle_price(candidate)

    if oracle_result and oracle_result['confidence'] > 0.7:
        market_price = candidate['odds']
        oracle_price = oracle_result['oracle_price']
        difference_pct = ((market_price - oracle_price) / oracle_price) * 100

        # Only trade if significant mispricing
        if abs(difference_pct) > self.config.get("oracle.min_difference_pct", 1.5):
            candidate['oracle_data'] = oracle_result
            candidate['arbitrage_edge'] = difference_pct

            # Boost score for high-confidence arbitrage
            candidate['score'] *= (1 + oracle_result['confidence'])

            self.logger.info(
                f"Oracle arbitrage found: market={market_price:.4f} "
                f"oracle={oracle_price:.4f} edge={difference_pct:+.2f}% "
                f"confidence={oracle_result['confidence']:.2f}"
            )

    return candidate, "ok"
```

### Config Changes

```json
// config.json - NEW SECTION
{
  "oracle": {
    "enabled": true,
    "min_difference_pct": 1.5,
    "min_confidence": 0.7,
    "external_api_key": null,
    "methods": {
      "fair_value": true,
      "external_odds": false,
      "cross_market": true
    }
  }
}
```

---

## Testing Strategy

### Phase 1: Dry Run (7 days)
- Collect oracle vs market data
- Calculate hypothetical P&L
- Tune thresholds and weights

### Phase 2: Paper Trading (7 days)
- Simulate trades without execution
- Track which oracle method is most accurate
- Measure edge decay time

### Phase 3: Live Micro Trading ($0.25/trade, 20 trades)
- Validate oracle accuracy with real money
- Adjust confidence thresholds based on outcomes
- Monitor for false positives

### Phase 4: Scale Up
- Increase to $1.00/trade if win rate >55%
- Implement position sizing based on oracle confidence
- Add dynamic threshold adjustment

---

## Risk Considerations

1. **Oracle Latency**: External APIs may lag real-time market moves
2. **False Signals**: Oracle might be wrong (especially for unique Polymarket events)
3. **Market Impact**: Large arbitrage trades can move prices before execution
4. **Event-Specific**: Some markets don't have external odds (need fallback)

---

## Expected Performance

Based on their config (1.5% threshold, 1% TP, 0.5% SL):
- **Win Rate Target**: 60-70%
- **Average Win**: +1.0% (TP hit)
- **Average Loss**: -0.5% (SL hit)
- **Profit Factor**: ~2.0
- **Sharpe Ratio**: 1.5-2.0 (if edge is real)

**Critical**: Their disclaimer states "demo version is not working" and directs to paid version. This suggests:
- Implementation is complex
- May require proprietary data sources
- Likely needs continuous tuning

---

## Next Steps

1. ✅ **Start with Option 1** (Fair Value Calculator) - lowest risk, self-contained
2. Add **Option 3** (Cross-Market) - easy to implement, pure arbitrage
3. **Evaluate** after 2 weeks of data collection
4. Consider **Option 2** (External Odds) only if edge is proven and ROI justifies API costs

## Files to Create

- `bot/oracle_service.py` - Main oracle interface
- `bot/fair_value_calculator.py` - Internal valuation model
- `bot/cross_market_finder.py` - Duplicate market detector
- `tools/oracle_backtest.py` - Historical analysis tool
- `tests/test_oracle.py` - Unit tests

## Timeline

- **Week 1**: Implement FairValueCalculator + data collection
- **Week 2**: Add CrossMarketFinder + dry run testing
- **Week 3**: Integration into market scanner + paper trading
- **Week 4**: Micro trading validation ($0.25/trade)
- **Week 5+**: Scale up or pivot based on results

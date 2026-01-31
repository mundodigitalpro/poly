# Concurrent Order Placement Implementation Plan

## Overview
Replace sequential order monitoring with concurrent limit order placement (Buy + TP + SL simultaneously).

## Current vs Proposed Architecture

### Current (Sequential Monitoring)
```
1. Execute market BUY
2. Save position to positions.json
3. Loop every 10s:
   - Fetch orderbook
   - Check if best_bid >= TP → execute market SELL
   - Check if best_bid <= SL → execute market SELL
4. Remove position when sold
```

**Problems**:
- High API call frequency (orderbook fetches every 10s)
- Execution latency (up to 10s delay between price hit and execution)
- Market orders on exit (slippage risk)
- More complex position monitoring logic

### Proposed (Concurrent Limit Orders)
```
1. Execute market BUY
2. Place limit SELL @ TP price
3. Place limit SELL @ SL price
4. Monitor order fills (passive, low frequency)
5. When one order fills → cancel the other
```

**Benefits**:
- Reduced API calls (no constant orderbook monitoring)
- Instant execution when price hits (limit order already in book)
- No slippage on exits (limit price guaranteed)
- Simpler position management

---

## Implementation Details

### 1. New Trader Methods

```python
# bot/trader.py - ADD NEW METHODS

from py_clob_client.clob_types import OrderType

def execute_buy_with_exits(
    self,
    token_id: str,
    entry_price: float,
    size: float,
    tp_price: float,
    sl_price: float,
) -> dict:
    """
    Execute market buy and place TP/SL limit orders.

    Args:
        token_id: Token to buy
        entry_price: Market price for buy (best_ask)
        size: Amount to buy (in shares)
        tp_price: Take profit limit price
        sl_price: Stop loss limit price

    Returns:
        {
            'buy_fill': TradeFill,
            'tp_order_id': str,
            'sl_order_id': str,
            'tp_price': float,
            'sl_price': float
        }
    """
    # Step 1: Execute market buy
    buy_fill = self.execute_buy(token_id, entry_price, size)

    if buy_fill.filled_size == 0:
        raise RuntimeError("Buy order filled 0 shares")

    # Step 2: Place TP limit sell
    try:
        tp_order_id = self._place_limit_sell(
            token_id=token_id,
            price=tp_price,
            size=buy_fill.filled_size,
        )
    except Exception as exc:
        self.logger.error(f"Failed to place TP order: {exc}")
        # Still return buy fill so position can be managed manually
        return {
            'buy_fill': buy_fill,
            'tp_order_id': None,
            'sl_order_id': None,
            'tp_price': tp_price,
            'sl_price': sl_price,
        }

    # Step 3: Place SL limit sell
    try:
        sl_order_id = self._place_limit_sell(
            token_id=token_id,
            price=sl_price,
            size=buy_fill.filled_size,
        )
    except Exception as exc:
        self.logger.error(f"Failed to place SL order: {exc}")
        # Cancel TP order if SL fails
        try:
            self._cancel_order(tp_order_id)
        except:
            pass
        return {
            'buy_fill': buy_fill,
            'tp_order_id': None,
            'sl_order_id': None,
            'tp_price': tp_price,
            'sl_price': sl_price,
        }

    return {
        'buy_fill': buy_fill,
        'tp_order_id': tp_order_id,
        'sl_order_id': sl_order_id,
        'tp_price': tp_price,
        'sl_price': sl_price,
    }


def _place_limit_sell(self, token_id: str, price: float, size: float) -> str:
    """
    Place a limit SELL order (not market).

    Args:
        token_id: Token to sell
        price: Limit price
        size: Amount to sell

    Returns:
        order_id: ID of the placed limit order
    """
    if self.dry_run:
        self.logger.info(
            f"DRY RUN - LIMIT SELL {size} @ {price:.4f} (token {token_id[:8]}...)"
        )
        return f"dry_run_{token_id[:8]}_{price}"

    # IMPORTANT: Check py-clob-client for limit order syntax
    # This may need adjustment based on actual SDK implementation
    order_args = OrderArgs(
        token_id=token_id,
        price=price,
        size=size,
        side=SELL,
        # May need: order_type=OrderType.LIMIT or similar
    )

    options = PartialCreateOrderOptions(
        tick_size="0.01",
        neg_risk=False,
        # May need: time_in_force="GTC" (Good Till Canceled)
    )

    result = self._call_api_with_retries(
        self.client.create_and_post_order, order_args, options
    )

    order_id = self._extract_order_id(result)
    if not order_id:
        raise RuntimeError("Failed to extract order ID from limit order response")

    self.logger.info(f"Limit SELL placed: {order_id} @ {price:.4f}")
    return order_id


def _cancel_order(self, order_id: str) -> bool:
    """
    Cancel an open order.

    Args:
        order_id: Order to cancel

    Returns:
        True if canceled, False if failed
    """
    if self.dry_run:
        self.logger.info(f"DRY RUN - CANCEL order {order_id}")
        return True

    try:
        self._call_api_with_retries(self.client.cancel_order, order_id)
        self.logger.info(f"Order canceled: {order_id}")
        return True
    except Exception as exc:
        self.logger.warn(f"Failed to cancel order {order_id}: {exc}")
        return False


def check_order_status(self, order_id: str) -> dict:
    """
    Check if a limit order has filled.

    Args:
        order_id: Order to check

    Returns:
        {
            'status': 'open' | 'filled' | 'partial' | 'canceled',
            'filled_size': float,
            'avg_price': float,
            'fees': float
        }
    """
    try:
        order = self._call_api_with_retries(self.client.get_order, order_id)
        status = self._extract_order_status(order)
        filled_size, avg_price, fees = self._parse_order_fill(
            order, expected_size=0, expected_price=0
        )

        return {
            'status': status,
            'filled_size': filled_size,
            'avg_price': avg_price,
            'fees': fees,
        }
    except Exception as exc:
        self.logger.warn(f"Failed to fetch order {order_id}: {exc}")
        return {
            'status': 'unknown',
            'filled_size': 0,
            'avg_price': 0,
            'fees': 0,
        }
```

---

### 2. Update Position Dataclass

```python
# bot/position_manager.py - MODIFY Position

@dataclass
class Position:
    """Represents an open trading position."""

    token_id: str
    entry_price: float
    size: float
    filled_size: float
    entry_time: str
    tp: float
    sl: float
    fees_paid: float = 0.0
    order_id: Optional[str] = None

    # NEW FIELDS for concurrent orders
    tp_order_id: Optional[str] = None
    sl_order_id: Optional[str] = None
    exit_mode: str = "monitor"  # "monitor" or "limit_orders"
```

---

### 3. Update Main Bot Loop

```python
# main_bot.py - MODIFY _update_positions

def _update_positions(
    client,
    logger,
    position_manager: PositionManager,
    trader: BotTrader,
    strategy: TradingStrategy,
    blacklist_cfg: dict,
):
    """Check limit orders for fills."""
    positions = position_manager.get_all_positions()
    if not positions:
        return

    for position in positions:
        # Skip positions without limit orders (legacy or fallback)
        if position.exit_mode != "limit_orders":
            # Use old monitoring logic
            _monitor_position_legacy(position, client, logger, trader, ...)
            continue

        # NEW: Check limit order status
        tp_status = trader.check_order_status(position.tp_order_id)
        sl_status = trader.check_order_status(position.sl_order_id)

        # TP filled
        if tp_status['status'] in ('filled', 'partial'):
            logger.info(
                f"TAKE PROFIT filled for {position.token_id[:8]}... "
                f"@ {tp_status['avg_price']:.4f}"
            )
            # Cancel SL order
            trader._cancel_order(position.sl_order_id)

            # Record trade
            exit_time = datetime.now(timezone.utc).isoformat()
            odds_range = strategy.get_odds_range(position.entry_price)
            position_manager.record_trade(
                entry_price=position.entry_price,
                exit_price=tp_status['avg_price'],
                size=tp_status['filled_size'],
                fees=tp_status['fees'],
                entry_time=position.entry_time,
                exit_time=exit_time,
                odds_range=odds_range,
            )

            position_manager.remove_position(position.token_id)
            continue

        # SL filled
        if sl_status['status'] in ('filled', 'partial'):
            logger.info(
                f"STOP LOSS filled for {position.token_id[:8]}... "
                f"@ {sl_status['avg_price']:.4f}"
            )
            # Cancel TP order
            trader._cancel_order(position.tp_order_id)

            # Record trade
            exit_time = datetime.now(timezone.utc).isoformat()
            odds_range = strategy.get_odds_range(position.entry_price)
            position_manager.record_trade(
                entry_price=position.entry_price,
                exit_price=sl_status['avg_price'],
                size=sl_status['filled_size'],
                fees=sl_status['fees'],
                entry_time=position.entry_time,
                exit_time=exit_time,
                odds_range=odds_range,
            )

            # Blacklist after SL
            duration = blacklist_cfg.get("duration_days", 3)
            max_attempts = blacklist_cfg.get("max_attempts", 2)
            position_manager.add_to_blacklist(
                position.token_id, "stop_loss", duration, max_attempts
            )

            position_manager.remove_position(position.token_id)
            continue

        # Both orders still open
        logger.debug(
            f"Position {position.token_id[:8]}... "
            f"TP={tp_status['status']} SL={sl_status['status']}"
        )


def _monitor_position_legacy(position, client, logger, trader, ...):
    """Legacy monitoring for positions without limit orders."""
    # Current implementation from main_bot.py lines 149-213
    pass
```

---

### 4. Update Trade Placement

```python
# main_bot.py - MODIFY _place_new_trade

def _place_new_trade(
    client,
    logger,
    scanner: MarketScanner,
    trader: BotTrader,
    position_manager: PositionManager,
    strategy: TradingStrategy,
    config,
) -> Optional[TradeFill]:
    """Place new trade with concurrent TP/SL limit orders."""

    candidate = scanner.pick_best_candidate()
    if not candidate:
        logger.info("No suitable market candidate found.")
        return None

    # ... (size calculation logic same as before) ...

    tp, sl = strategy.calculate_tp_sl(price)

    logger.info(
        f"Placing BUY {size_shares} @ {price:.4f} "
        f"TP={tp:.4f} SL={sl:.4f} (concurrent limit orders)"
    )

    # NEW: Use concurrent order placement
    result = trader.execute_buy_with_exits(
        token_id=candidate["token_id"],
        entry_price=price,
        size=size_shares,
        tp_price=tp,
        sl_price=sl,
    )

    buy_fill = result['buy_fill']
    entry_time = datetime.now(timezone.utc).isoformat()

    # Save position with limit order IDs
    position = Position(
        token_id=candidate["token_id"],
        entry_price=buy_fill.avg_price,
        size=size_shares,
        filled_size=buy_fill.filled_size,
        entry_time=entry_time,
        tp=tp,
        sl=sl,
        fees_paid=buy_fill.fees_paid,
        order_id=buy_fill.order_id,
        # NEW FIELDS
        tp_order_id=result['tp_order_id'],
        sl_order_id=result['sl_order_id'],
        exit_mode="limit_orders" if result['tp_order_id'] else "monitor",
    )

    position_manager.add_position(position)

    if result['tp_order_id']:
        logger.info(
            f"Position opened with limit orders: "
            f"TP={result['tp_order_id'][:8]}... SL={result['sl_order_id'][:8]}..."
        )
    else:
        logger.warn("Limit orders failed, using legacy monitoring")

    return buy_fill
```

---

## Configuration Changes

```json
// config.json - ADD
{
  "trading": {
    "use_concurrent_orders": true,
    "cancel_timeout_seconds": 5,
    "order_check_interval_seconds": 30
  }
}
```

---

## Migration Strategy

### Phase 1: Parallel Implementation
- Keep existing monitoring logic (`exit_mode="monitor"`)
- Add new concurrent order logic (`exit_mode="limit_orders"`)
- Run both in parallel for 1 week
- Compare execution quality

### Phase 2: A/B Testing
- 50% positions use concurrent orders
- 50% positions use monitoring
- Measure:
  - API call reduction
  - Execution price quality
  - Fill rate differences

### Phase 3: Full Rollout
- Switch all new positions to concurrent orders
- Legacy positions continue with monitoring until closed
- Remove old monitoring code after all positions closed

---

## Error Handling

### Scenario 1: TP/SL Placement Fails
```python
if not result['tp_order_id']:
    # Fallback to legacy monitoring
    position.exit_mode = "monitor"
    logger.warn("Using fallback monitoring for this position")
```

### Scenario 2: One Order Fills, Cancel Fails
```python
# Check order status before assuming it's canceled
opposite_status = trader.check_order_status(opposite_order_id)
if opposite_status['status'] == 'filled':
    # Both filled! Need to reverse one side
    logger.error("Both TP and SL filled - manual intervention needed")
    # Send alert, pause bot, etc.
```

### Scenario 3: Partial Fills
```python
if tp_status['status'] == 'partial':
    # Calculate unfilled amount
    unfilled = position.size - tp_status['filled_size']

    # Option A: Wait for full fill
    # Option B: Cancel and market sell remainder
    if unfilled > 0.01:  # Threshold for caring
        logger.warn(f"Partial TP fill: {unfilled} shares remaining")
        # Implement logic based on preference
```

---

## API Call Reduction Analysis

### Current (Monitoring)
```
Per position per loop (10s):
- 1 orderbook fetch
- 0-1 sell orders (when triggered)

5 open positions, 1 hour:
- 5 pos × 6 loops/min × 60 min = 1,800 API calls
```

### Proposed (Concurrent)
```
Per position lifecycle:
- 1 market buy
- 2 limit sells (TP + SL)
- 1 cancel order (when one fills)
- 6-12 order status checks (every 30s)

5 positions closing in 1 hour:
- 5 × (1 + 2 + 1 + 12) = 80 API calls
```

**Reduction**: 1,800 → 80 = **95.6% fewer API calls**

---

## Risks and Mitigation

### Risk 1: Limit Orders Don't Fill
**Scenario**: Price spikes past TP but limit order doesn't execute (low liquidity).

**Mitigation**:
- Monitor order age
- If TP order open >1 hour, consider market sell
- Add "time-based exit" fallback

### Risk 2: Price Gaps
**Scenario**: Price jumps from 0.68 → 0.74 (skipping TP at 0.70).

**Mitigation**:
- Limit orders should fill if price crosses (not guaranteed on low liquidity)
- Add monitoring for "stuck" orders above TP price

### Risk 3: Order Book Removal
**Scenario**: Market resolves or gets delisted while limit orders are open.

**Mitigation**:
- Check for "market closed" errors
- Handle order cancellation failures gracefully
- Monitor market status separately

---

## Testing Checklist

- [ ] Verify `create_and_post_order` supports limit orders (check SDK docs)
- [ ] Test limit order placement in dry-run mode
- [ ] Confirm order cancellation works
- [ ] Test concurrent order placement with $0.25 real trade
- [ ] Measure actual API call reduction over 24h
- [ ] Verify both TP and SL scenarios execute correctly
- [ ] Test partial fill handling
- [ ] Test "one order fills, other cancels" flow
- [ ] Benchmark execution price (limit vs market)

---

## Next Steps

1. **Research py-clob-client limit order syntax** (check docs/examples)
2. **Implement `_place_limit_sell` method** in trader.py
3. **Add unit tests** for concurrent order logic
4. **Deploy to testnet/dry-run** for validation
5. **Run micro trades** ($0.25) to verify real execution
6. **Measure performance** vs current monitoring approach
7. **Full rollout** if metrics improve

---

## Expected Benefits

- ✅ **95%+ reduction in API calls**
- ✅ **Instant execution** at TP/SL prices (no 10s delay)
- ✅ **No slippage** on exits (limit price guaranteed)
- ✅ **Simpler bot logic** (passive order monitoring vs active price checking)
- ✅ **Lower infrastructure costs** (fewer API requests)

## Files to Modify

- `bot/trader.py` - Add concurrent order methods
- `bot/position_manager.py` - Update Position dataclass
- `main_bot.py` - Modify position monitoring and trade placement
- `config.json` - Add concurrent order settings
- `tests/test_trader.py` - Add test coverage

## Timeline

- **Day 1**: Research SDK limit order syntax
- **Day 2-3**: Implement concurrent order methods in trader.py
- **Day 4**: Update position management and main loop
- **Day 5-7**: Testing (dry-run + micro trades)
- **Week 2**: A/B testing vs legacy monitoring
- **Week 3**: Full rollout

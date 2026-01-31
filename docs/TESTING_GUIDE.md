# WebSocket & Concurrent Orders Testing Guide

This guide walks you through testing the new WebSocket and Concurrent Orders features.

---

## Quick Start

### Option 1: Standalone WebSocket Test (Recommended First)

Test WebSocket in isolation without running the full bot:

```bash
cd /home/user/poly
python scripts/test_websocket_standalone.py --duration 60
```

**What it does**:
- Connects to Polymarket WebSocket
- Subscribes to any positions in `data/positions.json`
- Monitors for 60 seconds
- Shows real-time orderbook updates
- Prints statistics and success criteria

**Success criteria**:
- ✓ WebSocket connects successfully
- ✓ Receives messages (keepalives, orderbook updates)
- ✓ No reconnection loops
- ✓ Callbacks trigger correctly

---

### Option 2: Full Bot with WebSocket

Test WebSocket integrated with the main bot:

```bash
cd /home/user/poly
bash scripts/test_websocket.sh
```

**What it does**:
- Backs up config.json
- Enables WebSocket in config
- Runs main_bot.py with WebSocket enabled
- Monitors positions if available
- Restores config on exit

---

## Detailed Testing Steps

### Phase 1: WebSocket Stability (No Trading)

**Goal**: Verify WebSocket connects and handles messages correctly

**Steps**:

1. **Clean setup**:
   ```bash
   # Ensure you're on the correct branch
   git checkout claude/investigate-article-implementation-CG7Bb
   git pull origin claude/investigate-article-implementation-CG7Bb

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Run standalone test**:
   ```bash
   python scripts/test_websocket_standalone.py --duration 60
   ```

3. **Monitor output**:
   - ✓ `[INFO] Connecting to Polymarket WebSocket...`
   - ✓ `[SUCCESS] Connected!`
   - ✓ `[SUCCESS] Subscribed!` (if you have positions)
   - ✓ `[SUCCESS] Update #1 - Token: ...` (if markets are active)
   - ✓ `[INFO] Messages received: X` (X > 0)
   - ✗ NO `[ERROR]` messages
   - ✗ NO `[WARN] WebSocket connection closed` loops

4. **Check statistics**:
   ```
   Test Results
   ============
   Messages received: 50+      ✓ Good
   Reconnects: 0               ✓ Good
   Orderbook updates: 5+       ✓ Good (if you have positions)
   ```

**Expected results**:
- Messages received: 10-100+ (depends on market activity)
- Reconnects: 0
- Orderbook updates: 0-20+ (depends on positions and market activity)

---

### Phase 2: WebSocket with Position Monitoring

**Goal**: Verify WebSocket monitors open positions correctly

**Prerequisites**:
- At least one position in `data/positions.json`
- If no positions, see "Creating Test Position" below

**Steps**:

1. **Check positions**:
   ```bash
   cat data/positions.json | python -m json.tool
   ```

   Expected format:
   ```json
   [
     {
       "token_id": "abc123...",
       "entry_price": 0.50,
       "tp": 0.60,
       "sl": 0.40,
       "filled_size": 1.0,
       ...
     }
   ]
   ```

2. **Enable WebSocket in config**:
   ```bash
   # Edit config.json
   # Set: "use_websocket": true
   # Keep: "dry_run": true
   ```

   Or use the test script which does this automatically:
   ```bash
   bash scripts/test_websocket.sh
   ```

3. **Run bot**:
   ```bash
   python main_bot.py
   ```

4. **Monitor logs**:
   ```
   [INFO] WebSocket connected to Polymarket
   [INFO] Subscribed to abc123...
   [INFO] Monitoring 1 positions via WebSocket
   [DEBUG] Position abc123... price=0.52 tp=0.60 sl=0.40
   ```

5. **Verify callbacks**:
   - Log should show price updates for each position
   - Updates should arrive in real-time (<1s apart for active markets)
   - No disconnect/reconnect loops

**Success criteria**:
- ✓ WebSocket subscribes to all position token_ids
- ✓ Receives orderbook updates for positions
- ✓ TP/SL checks trigger on each update
- ✓ No errors or disconnects

---

### Phase 3: Concurrent Orders (No WebSocket)

**Goal**: Test concurrent order placement without WebSocket

**Steps**:

1. **Configure**:
   ```bash
   # Edit config.json
   {
     "trading": {
       "use_concurrent_orders": true,
       "use_websocket": false  // Test in isolation first
     },
     "capital": {
       "max_trade_size": 0.25  // Start small
     },
     "bot": {
       "dry_run": false  // Must be false to place real orders
     }
   }
   ```

   **⚠️ WARNING**: This will place real orders with real money!

2. **Verify balance**:
   ```bash
   python poly_client.py --balance
   ```

   Ensure you have at least $1.00 available.

3. **Run bot** (supervised):
   ```bash
   python main_bot.py
   ```

4. **Monitor for trade**:
   ```
   [INFO] Scanning markets...
   [INFO] Selected market: Token abc123... (score=85.2)
   [INFO] Executing buy with concurrent TP/SL orders
   [INFO] Market buy filled: size=1.00 @ 0.50
   [INFO] Limit TP placed: order_id=tp_123
   [INFO] Limit SL placed: order_id=sl_456
   [INFO] Position saved with exit_mode=limit_orders
   ```

5. **Verify position**:
   ```bash
   cat data/positions.json | python -m json.tool
   ```

   Should show:
   ```json
   {
     "token_id": "abc123...",
     "entry_price": 0.50,
     "tp": 0.60,
     "sl": 0.40,
     "tp_order_id": "tp_123",
     "sl_order_id": "sl_456",
     "exit_mode": "limit_orders"
   }
   ```

6. **Monitor limit orders**:
   - Bot will check order status every 30 seconds
   - When TP or SL fills, opposite order is cancelled
   - Position is closed automatically

**Success criteria**:
- ✓ Market buy executes successfully
- ✓ TP limit order placed immediately after
- ✓ SL limit order placed immediately after
- ✓ Position saved with order IDs
- ✓ Bot monitors order fills (not orderbook prices)

---

### Phase 4: Combined (WebSocket + Concurrent)

**Goal**: Test both features together for maximum efficiency

**Configuration**:
```json
{
  "trading": {
    "use_concurrent_orders": true,
    "use_websocket": true
  },
  "capital": {
    "max_trade_size": 0.25
  },
  "bot": {
    "dry_run": false
  }
}
```

**Expected behavior**:
1. Bot scans markets (via Gamma API or CLOB)
2. Selects best market
3. Executes buy with concurrent TP/SL orders
4. WebSocket subscribes to the position token_id
5. WebSocket monitors order fills in real-time
6. When TP/SL fills, WebSocket callback detects it instantly (<100ms)
7. Opposite order cancelled immediately
8. Position closed and removed

**Advantages over baseline**:
- Entry: Concurrent orders eliminate post-entry API calls
- Exit: WebSocket detects fills instantly (vs 10s polling)
- Total latency: <100ms (vs 10s)
- Total API calls: ~12/hr (vs 1,800/hr)

---

## Creating Test Position

If you don't have positions to test with:

### Option A: Create Manual Position

```bash
# Edit data/positions.json
[
  {
    "token_id": "YOUR_TOKEN_ID_HERE",
    "entry_price": 0.50,
    "entry_time": "2026-01-31T12:00:00Z",
    "tp": 0.60,
    "sl": 0.40,
    "filled_size": 1.0,
    "entry_order_id": "test_order",
    "exit_mode": "monitor"
  }
]
```

Replace `YOUR_TOKEN_ID_HERE` with a real token ID from a liquid market.

To find token IDs:
```bash
python poly_client.py --filter "Trump" --limit 5
```

### Option B: Place Real Micro Trade

```bash
# 1. Enable trading
# config.json: "dry_run": false

# 2. Set small size
# config.json: "max_trade_size": 0.25

# 3. Run bot once
python main_bot.py

# 4. Stop after first trade (Ctrl+C)

# 5. Check position
cat data/positions.json
```

---

## Troubleshooting

### WebSocket connects but immediately disconnects

**Symptom**:
```
[INFO] WebSocket connected
[INFO] Subscribed to abc123...
[WARN] WebSocket connection closed
[INFO] Reconnecting...
```

**Causes**:
1. ✅ FIXED: Empty message handling (commit a2e6700)
2. ✅ FIXED: Incorrect subscription format (commit a16acea)
3. ✅ FIXED: Unknown message types

**Solution**: You should already have the fixes. If still happening:
```bash
git pull origin claude/investigate-article-implementation-CG7Bb
```

---

### No orderbook updates received

**Symptom**:
```
[INFO] Messages received: 50
[INFO] Orderbook updates: 0
```

**Causes**:
1. No positions to monitor
2. Markets are inactive (low liquidity)
3. Token IDs are invalid

**Solution**:
```bash
# Check positions
cat data/positions.json

# Test with known active market
python scripts/test_websocket_standalone.py \
  --tokens 21742633143463906290569050155826241533067272736897614950488156847949938836455 \
  --duration 60

# (Use a real token ID from a liquid market)
```

---

### Concurrent orders not placing

**Symptom**:
```
[INFO] Executing buy...
[INFO] Buy filled
[INFO] Position saved with exit_mode=monitor
```

No mention of TP/SL orders.

**Cause**: `use_concurrent_orders` is `false` in config

**Solution**:
```bash
# Edit config.json
{
  "trading": {
    "use_concurrent_orders": true
  }
}
```

---

### Orders not detected as filled

**Symptom**:
```
[INFO] Checking order status: tp_order_123
[INFO] Order status: open
```

TP hits but bot doesn't detect fill.

**Cause**: Order might still be partially filled or not yet confirmed

**Solution**:
- Wait 30-60 seconds (order confirmation delay)
- Check order on Polymarket website
- Verify order ID in position data

---

## Performance Metrics

After testing, measure improvements:

### Latency Test

**Baseline (polling)**:
```bash
# Set use_websocket=false
# Time from market price hitting TP to sell execution
# Expected: 5-15 seconds (avg 10s)
```

**WebSocket**:
```bash
# Set use_websocket=true
# Time from market price hitting TP to sell execution
# Expected: <100ms
```

### API Call Test

**Baseline (monitor mode)**:
- Position checks: 360/hr (every 10s)
- Market scans: 30/hr (every 120s)
- Total: ~400 calls/hr

**WebSocket + Concurrent**:
- Order status checks: 2/hr (every 30min for long positions)
- Market scans: 30/hr
- Total: ~35 calls/hr

**Improvement**: -91% API calls

---

## Success Checklist

### WebSocket
- [ ] Standalone test passes (60+ messages, 0 reconnects)
- [ ] Integrates with main bot without errors
- [ ] Subscribes to all positions
- [ ] Receives orderbook updates in real-time
- [ ] TP/SL checks trigger on updates
- [ ] No disconnect/reconnect loops

### Concurrent Orders
- [ ] Market buy executes
- [ ] TP limit order places immediately
- [ ] SL limit order places immediately
- [ ] Position saves with order IDs and exit_mode=limit_orders
- [ ] Bot monitors order fills (not prices)
- [ ] Opposite order cancels when one fills

### Combined
- [ ] Both features work together without conflicts
- [ ] Entry latency: <1s (concurrent orders)
- [ ] Exit latency: <100ms (WebSocket)
- [ ] API calls: <50/hr total
- [ ] No errors in logs

---

## Next Steps After Testing

1. **Document results**: Update PROGRESS_DAY2.md with actual metrics
2. **Adjust config**: Fine-tune intervals, reconnect delays
3. **Gradual scale**: If successful, increase trade size gradually
4. **Implement gasless**: Add Builder Program integration
5. **Production deploy**: Move to VPS after 2+ weeks stable

---

## Getting Help

If you encounter issues:

1. **Check logs**: Look for ERROR or WARN messages
2. **Verify config**: Ensure flags are set correctly
3. **Test in isolation**: Use standalone scripts first
4. **Review commits**: Ensure you have latest fixes
5. **Report issues**: Create detailed bug report with logs

---

**Branch**: `claude/investigate-article-implementation-CG7Bb`
**Status**: Ready for testing
**Last updated**: 2026-01-31

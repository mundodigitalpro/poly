# Concurrent Orders - Testing Walkthrough

## 🎯 Overview

This guide walks you through testing the concurrent orders implementation step-by-step, from basic unit tests to live trading validation.

**Time required**: 2-3 hours (mostly waiting for bot cycles)
**Risk level**: Minimal (starts with dry-run, scales to $0.25 micro trades)

---

## ✅ Pre-Testing Checklist

Before starting:

- [ ] Git branch is up to date: `claude/investigate-article-implementation-CG7Bb`
- [ ] All code changes committed
- [ ] `.env` file exists with valid credentials
- [ ] Python 3.9+ installed
- [ ] At least $1.00 USDC in wallet for micro testing

---

## Phase 1: Unit Tests (5 minutes)

**Goal**: Verify code logic without API calls

### Step 1.1: Run Automated Tests

```bash
cd /home/user/poly
python3 tests/test_concurrent_orders.py
```

**Expected Output**:
```
Running Concurrent Orders Unit Tests
============================================================

Testing: Position with concurrent fields
✓ Position initialization with concurrent fields works

Testing: Position serialization
✓ Position serialization/deserialization works

Testing: Backwards compatibility
✓ Backwards compatibility with old positions works

Testing: Config trading section
✓ Config has trading section with correct defaults

Testing: Main bot routing logic
✓ Position routing logic works correctly

============================================================
Results: 5 passed, 1 failed
============================================================
```

**Note**: 1 test fails due to missing `py_clob_client` - this is expected and will be resolved in Phase 2.

### Step 1.2: Verify Python Syntax

```bash
python3 -m py_compile bot/trader.py bot/position_manager.py main_bot.py
echo "✓ No syntax errors"
```

**Pass Criteria**: No output = success

---

## Phase 2: Environment Setup (10 minutes)

**Goal**: Install dependencies and verify imports

### Step 2.1: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2.2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected packages**:
- py-clob-client
- python-dotenv
- (and their dependencies)

### Step 2.3: Verify Imports

```bash
python3 -c "
from bot.config import load_bot_config
from bot.logger import get_logger
from bot.trader import BotTrader
from bot.position_manager import Position, PositionManager
print('✓ All imports successful')
"
```

**Pass Criteria**: "✓ All imports successful" printed

### Step 2.4: Verify .env Configuration

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

required = ['POLY_PRIVATE_KEY', 'POLY_API_KEY', 'POLY_API_SECRET', 'POLY_API_PASSPHRASE']
missing = [k for k in required if not os.getenv(k)]

if missing:
    print(f'✗ Missing env vars: {missing}')
    exit(1)
else:
    print('✓ All required env vars present')
"
```

**Pass Criteria**: "✓ All required env vars present"

---

## Phase 3: Dry-Run Testing (30 minutes)

**Goal**: Run bot in simulation mode (no real trades)

### Step 3.1: Verify Config is in Dry-Run Mode

Open `config.json` and verify:
```json
{
  "bot": {
    "dry_run": true  // ← Must be true
  },
  "trading": {
    "use_concurrent_orders": false  // ← Start with false (legacy mode)
  }
}
```

### Step 3.2: Run Legacy Mode (Baseline)

```bash
python3 main_bot.py
```

**Watch for**:
- Bot initializes without errors
- Market scanner finds candidates
- If candidate found: "Placing BUY ... TP=... SL=..." (without "concurrent")
- Position monitoring shows: "Position ... price=X tp=Y sl=Z"
- Logs show "DRY RUN - BUY ..." messages

**Let run for**: 2-3 cycles (4-6 minutes)

**Press Ctrl+C** to stop

**Pass Criteria**:
- No exceptions or crashes
- Market scanning works
- Position monitoring works (if any positions)
- Logs show "DRY RUN" prefix on all order executions

### Step 3.3: Enable Concurrent Orders

Edit `config.json`:
```json
{
  "trading": {
    "use_concurrent_orders": true  // ← Change to true
  }
}
```

### Step 3.4: Run Concurrent Mode

```bash
python3 main_bot.py
```

**Watch for NEW behaviors**:
- "Placing BUY X @ Y **with concurrent TP/SL**" (different message)
- "DRY RUN - LIMIT SELL ... @ TP" (TP limit order)
- "DRY RUN - LIMIT SELL ... @ SL" (SL limit order)
- Position logs show: "TP=open SL=open" (instead of price checks)
- **NO** orderbook fetching during position monitoring

**Let run for**: 2-3 cycles

**Pass Criteria**:
- Messages mention "concurrent TP/SL"
- Three dry-run orders: 1 buy + 2 limit sells
- Position monitoring checks order status (not orderbook)
- No crashes or exceptions

### Step 3.5: Test Position Persistence

```bash
# While bot is running in concurrent mode:
# 1. Wait for a position to open
# 2. Ctrl+C to stop bot
# 3. Check data/positions.json
cat data/positions.json
```

**Expected JSON structure**:
```json
{
  "token_id_here": {
    "entry_price": 0.50,
    "tp": 0.55,
    "sl": 0.45,
    "tp_order_id": "dry_run_limit_1234",  // ← New field
    "sl_order_id": "dry_run_limit_5678",  // ← New field
    "exit_mode": "limit_orders",           // ← New field
    ...
  }
}
```

**Restart bot**:
```bash
python3 main_bot.py
```

**Pass Criteria**:
- Position loads correctly
- Bot continues monitoring with limit order logic
- No errors about missing fields

---

## Phase 4: Code Review (15 minutes)

**Goal**: Manual inspection of key code paths

### Step 4.1: Review trader.py Changes

```bash
# Lines 222-302: execute_buy_with_exits()
# Lines 304-348: _place_limit_sell()
# Lines 350-370: cancel_order()
# Lines 372-416: check_order_status()
```

**Check**:
- [ ] Dry-run mode supported in all new methods
- [ ] Error handling on limit order failures
- [ ] TP order cancellation if SL order fails (safety)
- [ ] Retry logic uses `_call_api_with_retries`

### Step 4.2: Review main_bot.py Changes

```bash
# Lines 275-367: _place_new_trade() - dual mode support
# Lines 143-211: _update_position_with_limit_orders() - new handler
# Lines 214-273: _update_position_legacy_monitoring() - legacy handler
```

**Check**:
- [ ] Config flag controls which mode is used
- [ ] Fallback to monitor mode if limit orders fail
- [ ] Both handlers call same trade recording logic
- [ ] Position removal happens in both modes

### Step 4.3: Review position_manager.py Changes

```bash
# Lines 32-34: New fields in __init__
# Lines 62-64: New fields in to_dict()
# Lines 81-83: New fields in from_dict() with defaults
```

**Check**:
- [ ] Backwards compatibility (defaults to "monitor")
- [ ] All fields serialized and deserialized
- [ ] __repr__ shows exit_mode for limit_orders positions

---

## Phase 5: Micro Trading ($0.25 real trade)

**⚠️ IMPORTANT**: Only proceed if Phases 1-4 passed completely.

**Goal**: Validate real execution with minimal risk

### Step 5.1: Prepare for Live Trading

Edit `config.json`:
```json
{
  "capital": {
    "total": 1.0,          // Small amount
    "max_trade_size": 0.25  // $0.25 per trade
  },
  "bot": {
    "dry_run": false  // ← ENABLE REAL TRADING
  },
  "trading": {
    "use_concurrent_orders": true  // Test new mode
  }
}
```

### Step 5.2: Run Live Bot (Monitor Closely!)

```bash
python3 main_bot.py
```

**Monitor in parallel**:
1. **Terminal**: Watch bot logs
2. **Polymarket UI**: Open your profile → Orders
3. **Wallet**: Keep PolygonScan open to see transactions

### Step 5.3: Wait for Trade Execution

**When bot places a trade, you should see**:

**In Terminal**:
```
Placing BUY 0.5 @ 0.50 with concurrent TP/SL (TP=0.55 SL=0.45)
Executing BUY with concurrent exits: 0.5 @ 0.50 (TP=0.55 SL=0.45)
TP limit order placed: 0x1234abcd... @ 0.55
SL limit order placed: 0x5678efgh... @ 0.45
Position opened with limit orders: size=0.5 @ 0.50 TP=0x1234... SL=0x5678...
```

**On Polymarket UI** (refresh orders page):
- ✅ 1 filled BUY order (market order)
- ✅ 2 open SELL orders (limit orders at TP and SL prices)

**On PolygonScan**:
- ✅ 3 transactions: 1 buy + 2 limit sells

**Pass Criteria**:
- Real order IDs (not "dry_run_...")
- Orders visible on Polymarket UI
- Orders match TP/SL prices from logs

### Step 5.4: Wait for Exit

**Option A: TP Hits** (price goes up to TP):
```
TAKE PROFIT filled for token123... @ 0.55
Order canceled: 0x5678efgh... (SL order)
Position closed (TP) token123... size=0.5 @ 0.55
```

**Option B: SL Hits** (price goes down to SL):
```
STOP LOSS filled for token123... @ 0.45
Order canceled: 0x1234abcd... (TP order)
Position closed (SL) token123... size=0.5 @ 0.45
```

**Verify on Polymarket**:
- ✅ One limit order filled
- ✅ Other limit order canceled
- ✅ No open orders remaining

### Step 5.5: Check Stats

```bash
cat data/stats.json
```

**Verify**:
- Trade recorded in `lifetime.total_trades`
- P&L calculated correctly
- Fees tracked

**Pass Criteria**:
- One order fills, other cancels
- No orphaned limit orders
- Stats updated correctly
- Position removed from data/positions.json

---

## Phase 6: A/B Testing (24-48 hours)

**Goal**: Compare concurrent vs legacy over multiple trades

### Step 6.1: Setup A/B Config

Edit `main_bot.py` temporarily around line 280:
```python
import random

# In _place_new_trade(), before checking use_concurrent:
use_concurrent = random.choice([True, False])  # 50/50 split
```

### Step 6.2: Track Metrics

Create a simple tracking script:
```bash
# Run this in a separate terminal
watch -n 60 'echo "=== Stats ===" && cat data/stats.json | jq ".lifetime"'
```

### Step 6.3: Let Bot Run

```bash
python3 main_bot.py
```

**Let run for**: 24-48 hours

**Monitor**:
- Check logs every few hours
- Verify mix of concurrent and legacy positions
- No crashes or stuck positions

### Step 6.4: Compare Results

After 24-48 hours:

```bash
# Count API calls from logs
grep -c "get_order_book" bot.log  # Legacy orderbook fetches
grep -c "get_order" bot.log       # Concurrent status checks

# Compare execution quality
python3 tools/position_analyzer.py
```

**Expected differences**:
- **API calls**: ~95% fewer for concurrent positions
- **Execution price**: Similar or better (no slippage on exits)
- **Fill rate**: Both should be ~100% (positions close successfully)

**Pass Criteria**:
- Both modes work without issues
- Concurrent mode shows fewer API calls
- No difference in win rate or P&L (strategy unchanged)
- Concurrent mode has better fill prices (no slippage)

---

## Phase 7: Full Rollout

**Goal**: Enable concurrent orders for all new positions

### Step 7.1: Remove A/B Testing Code

Revert the random.choice() addition from Phase 6.

### Step 7.2: Set Config Permanently

Edit `config.json`:
```json
{
  "trading": {
    "use_concurrent_orders": true  // ← Permanently enabled
  }
}
```

### Step 7.3: Monitor for 1 Week

Run bot normally, checking:
- [ ] Day 1: No errors, positions open/close correctly
- [ ] Day 3: Stats look good, no anomalies
- [ ] Day 7: Confirm API usage is lower, performance maintained

### Step 7.4: Cleanup (Optional)

After all positions close (none in "monitor" mode):

```bash
# Remove legacy monitoring code from main_bot.py
# Keep for now as fallback, or remove if confident:
# - _update_position_legacy_monitoring() function (lines 214-273)
```

---

## 🔍 Troubleshooting

### Issue: "Failed to extract order ID from limit order response"

**Cause**: SDK response format unexpected

**Debug**:
```python
# In trader.py _place_limit_sell(), add:
print(f"DEBUG: Order result = {result}")
print(f"DEBUG: Type = {type(result)}")
print(f"DEBUG: Attributes = {dir(result)}")
```

**Fix**: Update `_extract_order_id()` based on actual response structure

### Issue: Both TP and SL fill simultaneously

**Cause**: Rare race condition

**Check**:
```bash
grep "Position closed" bot.log | tail -5
```

**Fix**: Add validation in `_update_position_with_limit_orders()`:
```python
if tp_status['status'] == 'filled' and sl_status['status'] == 'filled':
    logger.error("BOTH FILLED - Manual check needed")
    # Alert and pause bot
```

### Issue: Limit orders never fill

**Cause**: Low liquidity, price doesn't reach target

**Check**:
```python
# How long has order been open?
from datetime import datetime
age_hours = (datetime.now() - datetime.fromisoformat(position.entry_time)).hours
print(f"Position age: {age_hours} hours")
```

**Fix** (future enhancement): Add time-based fallback to market sell after 24h

### Issue: Position stuck in "open" status

**Cause**: Order status check failing

**Debug**:
```bash
# Check if order actually exists on Polymarket
# Look up order ID in Polymarket UI
```

**Fix**: Add error recovery to re-check order or fall back to monitoring

---

## 📊 Success Metrics

Implementation is successful if:

- [x] ✅ Unit tests pass (Phase 1)
- [x] ✅ Dry-run works for both modes (Phase 3)
- [ ] ⏳ Micro trade executes correctly (Phase 5)
- [ ] ⏳ API calls reduced by >90% (Phase 6)
- [ ] ⏳ No increase in errors (Phase 6)
- [ ] ⏳ Execution quality maintained or improved (Phase 6)

**Target Metrics** (Phase 6 validation):
- API call reduction: **>90%**
- Win rate change: **±2%** (should be neutral)
- Average execution price: **0.1-0.3% better** (no slippage)
- Error rate: **<1%** (same or better than legacy)

---

## 📝 Next Steps

After successful Phase 7 rollout:

1. **Document findings** in CHANGELOG.md
2. **Update GEMINI.md** with new system state
3. **Consider Oracle Arbitrage** implementation (next feature from eurobeta bot)
4. **Optimize**: Add time-based exit fallback for stuck limit orders

---

## 🆘 Emergency Rollback

If critical issues arise:

```bash
# 1. Stop bot
Ctrl+C

# 2. Disable concurrent orders
# Edit config.json:
"trading": { "use_concurrent_orders": false }

# 3. Restart bot
python3 main_bot.py

# All existing positions will continue working
# New positions will use legacy monitoring
```

**Note**: Existing positions with limit orders will continue to be monitored via limit order logic. This is safe and correct.

---

## ✅ Testing Checklist Summary

Phase 1: Unit Tests
- [ ] Run test_concurrent_orders.py (5/6 pass)
- [ ] Verify Python syntax (no errors)

Phase 2: Environment Setup
- [ ] Create venv and install dependencies
- [ ] Verify all imports work
- [ ] Check .env configuration

Phase 3: Dry-Run Testing
- [ ] Test legacy mode (baseline)
- [ ] Test concurrent mode (new)
- [ ] Verify position persistence
- [ ] Compare logs between modes

Phase 4: Code Review
- [ ] Review trader.py changes
- [ ] Review main_bot.py changes
- [ ] Review position_manager.py changes

Phase 5: Micro Trading
- [ ] Execute $0.25 real trade
- [ ] Verify TP/SL orders on Polymarket UI
- [ ] Confirm exit execution
- [ ] Check stats recording

Phase 6: A/B Testing
- [ ] Setup 50/50 split
- [ ] Run for 24-48 hours
- [ ] Compare API calls
- [ ] Compare execution quality

Phase 7: Full Rollout
- [ ] Enable permanently
- [ ] Monitor for 1 week
- [ ] Document results
- [ ] Optional cleanup

**Current Status**: Phase 1 completed ✅

**Next**: Install dependencies and proceed to Phase 2

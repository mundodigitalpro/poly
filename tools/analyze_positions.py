#!/usr/bin/env python3
"""
Position Analysis Tool (Enhanced with Live Prices)
Analyzes positions.json with real-time price data from Polymarket API.

Features:
- Live bid prices from orderbook
- Real distance to TP/SL based on current market
- P&L calculation per position
- Flags positions near triggers
"""

import argparse
import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

POLYMARKET_HOST = "https://clob.polymarket.com"
CHAIN_ID = 137


def create_client():
    """Create CLOB client for fetching live prices."""
    private_key = os.getenv("POLY_PRIVATE_KEY")
    if not private_key:
        return None
    
    try:
        creds = ClobClient(POLYMARKET_HOST, key=private_key, chain_id=CHAIN_ID)
        api_creds = creds.derive_api_key()
        return ClobClient(
            POLYMARKET_HOST,
            key=private_key,
            chain_id=CHAIN_ID,
            creds=ApiCreds(
                api_key=api_creds.api_key,
                api_secret=api_creds.api_secret,
                api_passphrase=api_creds.api_passphrase,
            ),
            signature_type=1,
            funder=os.getenv("POLY_FUNDER_ADDRESS"),
        )
    except Exception as e:
        print(f"Warning: Could not create client: {e}")
        return None


def get_live_price(client, token_id):
    """Get current best bid price for a token."""
    if not client:
        return None
    
    try:
        book = client.get_order_book(token_id)
        if book and book.bids:
            prices = [float(b.price) for b in book.bids]
            return max(prices) if prices else None
    except Exception:
        pass
    return None


def calculate_metrics(entry_price, tp, sl, current_price=None):
    """Calculate position metrics with optional live price."""
    if current_price is None:
        current_price = entry_price
        is_live = False
    else:
        is_live = True
    
    # Calculate distances from current price
    distance_to_tp = tp - current_price
    distance_to_sl = current_price - sl
    
    # Percentage distances
    pct_to_tp = (distance_to_tp / current_price) * 100 if current_price != 0 else 0
    pct_to_sl = (distance_to_sl / current_price) * 100 if current_price != 0 else 0
    
    # P&L calculation
    pnl = current_price - entry_price
    pnl_pct = (pnl / entry_price) * 100 if entry_price != 0 else 0
    
    # Risk/Reward from entry
    risk = abs(entry_price - sl)
    reward = abs(tp - entry_price)
    risk_reward_ratio = risk / reward if reward != 0 else float('inf')
    
    return {
        'current_price': current_price,
        'is_live': is_live,
        'distance_to_tp': distance_to_tp,
        'distance_to_sl': distance_to_sl,
        'pct_to_tp': pct_to_tp,
        'pct_to_sl': pct_to_sl,
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'risk_reward_ratio': risk_reward_ratio,
    }


def analyze_positions(filepath='data/positions.json', use_live=True):
    """Load and analyze all positions with optional live prices."""
    with open(filepath, 'r') as f:
        positions = json.load(f)
    
    client = create_client() if use_live else None
    if use_live and client:
        print("📡 Fetching live prices from Polymarket...")
    elif use_live:
        print("⚠️  Could not connect to API, using entry prices")
    
    analyzed = []
    
    for token_id, pos in positions.items():
        entry = pos['entry_price']
        tp = pos['tp']
        sl = pos['sl']
        size = pos.get('filled_size', pos['size'])
        entry_time = pos['entry_time']
        
        # Get live price if available
        live_price = get_live_price(client, token_id) if client else None
        metrics = calculate_metrics(entry, tp, sl, live_price)
        
        analyzed.append({
            'token_id': token_id[:16] + '...',
            'full_token_id': token_id,
            'entry_price': entry,
            'size': size,
            'tp': tp,
            'sl': sl,
            'entry_time': entry_time,
            **metrics
        })
    
    return analyzed


def format_output(positions, show_live=True):
    """Format and display position analysis."""
    print()
    print("=" * 110)
    print("📊 POSITION ANALYSIS REPORT" + (" (LIVE PRICES)" if show_live else ""))
    print(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 110)
    
    if not positions:
        print("No positions found.")
        return
    
    # Count live vs static
    live_count = sum(1 for p in positions if p.get('is_live', False))
    print(f"   Positions: {len(positions)} | Live prices: {live_count}/{len(positions)}")
    print()
    
    # Summary: Total P&L
    total_pnl = sum(p['pnl'] * p['size'] for p in positions)
    winning = [p for p in positions if p['pnl'] > 0]
    losing = [p for p in positions if p['pnl'] < 0]
    
    print(f"   💰 Unrealized P&L: ${total_pnl:.4f}")
    print(f"   📈 Winning: {len(winning)} | 📉 Losing: {len(losing)}")
    print()
    
    # Find extremes
    if positions:
        closest_to_tp = min(positions, key=lambda x: abs(x['pct_to_tp']))
        closest_to_sl = min(positions, key=lambda x: abs(x['pct_to_sl']))
        print(f"   🎯 Closest to TP: {closest_to_tp['token_id']} ({closest_to_tp['pct_to_tp']:+.1f}%)")
        print(f"   ⚠️  Closest to SL: {closest_to_sl['token_id']} ({closest_to_sl['pct_to_sl']:+.1f}%)")
    
    print()
    print("-" * 110)
    header = f"{'Token':<19} {'Entry':>6} {'Now':>6} {'TP':>6} {'SL':>6} {'P&L':>8} {'→TP':>7} {'→SL':>7} {'Status'}"
    print(header)
    print("-" * 110)
    
    # Sort by P&L descending
    for p in sorted(positions, key=lambda x: x['pnl_pct'], reverse=True):
        # Status flags
        status = ""
        if p['pct_to_tp'] <= 3:
            status = "🔥 NEAR TP!"
        elif p['pct_to_sl'] <= 3:
            status = "⚠️ NEAR SL!"
        elif p['pnl_pct'] > 5:
            status = "📈 Profit"
        elif p['pnl_pct'] < -5:
            status = "📉 Loss"
        
        # Format P&L with color indicator
        pnl_str = f"{p['pnl_pct']:+.1f}%"
        
        # Live indicator
        live_ind = "●" if p.get('is_live') else "○"
        
        print(f"{live_ind} {p['token_id']:<17} "
              f"{p['entry_price']:>6.3f} "
              f"{p['current_price']:>6.3f} "
              f"{p['tp']:>6.3f} "
              f"{p['sl']:>6.3f} "
              f"{pnl_str:>8} "
              f"{p['pct_to_tp']:>+6.1f}% "
              f"{p['pct_to_sl']:>+6.1f}% "
              f"{status}")
    
    print("-" * 110)
    print()
    print("Legend: ● = Live price | ○ = Entry price (API unavailable)")
    print("=" * 110)


def main():
    parser = argparse.ArgumentParser(description="Analyze open positions with live prices")
    parser.add_argument("--no-live", action="store_true", help="Don't fetch live prices")
    parser.add_argument("--file", default="data/positions.json", help="Positions file path")
    args = parser.parse_args()
    
    try:
        positions = analyze_positions(args.file, use_live=not args.no_live)
        format_output(positions, show_live=not args.no_live)
    except FileNotFoundError:
        print(f"Error: File not found: {args.file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {args.file}")
        sys.exit(1)


if __name__ == "__main__":
    main()

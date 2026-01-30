#!/usr/bin/env python3
"""
Position Analysis Tool
Analyzes positions.json to calculate:
- Distance to TP (%)
- Distance to SL (%)
- Risk/Reward ratio
- Flags positions closest to triggers
"""

import json
from datetime import datetime

def calculate_metrics(entry_price, tp, sl, current_price=None):
    """Calculate position metrics.
    
    If current_price is None, assumes current_price = entry_price (neutral position)
    """
    if current_price is None:
        current_price = entry_price
    
    # Calculate absolute distances
    distance_to_tp = tp - current_price
    distance_to_sl = current_price - sl
    
    # Calculate percentage distances
    pct_to_tp = (distance_to_tp / current_price) * 100 if current_price != 0 else 0
    pct_to_sl = (distance_to_sl / current_price) * 100 if current_price != 0 else 0
    
    # Risk/Reward ratio (risk amount / reward amount)
    # Risk = entry - SL (how much we lose if stopped out)
    # Reward = TP - entry (how much we gain if target hit)
    risk = abs(entry_price - sl)
    reward = abs(tp - entry_price)
    risk_reward_ratio = risk / reward if reward != 0 else float('inf')
    
    # Alternative: Distance ratio (current distance to SL / current distance to TP)
    # This shows current risk/reward from current position
    current_risk = abs(current_price - sl)
    current_reward = abs(tp - current_price)
    current_rr_ratio = current_risk / current_reward if current_reward != 0 else float('inf')
    
    return {
        'distance_to_tp': distance_to_tp,
        'distance_to_sl': distance_to_sl,
        'pct_to_tp': pct_to_tp,
        'pct_to_sl': pct_to_sl,
        'risk_reward_ratio': risk_reward_ratio,
        'current_rr_ratio': current_rr_ratio,
        'current_price': current_price
    }

def analyze_positions(filepath='data/positions.json'):
    """Load and analyze all positions."""
    with open(filepath, 'r') as f:
        positions = json.load(f)
    
    analyzed = []
    
    for token_id, pos in positions.items():
        entry = pos['entry_price']
        tp = pos['tp']
        sl = pos['sl']
        size = pos['size']
        entry_time = pos['entry_time']
        
        metrics = calculate_metrics(entry, tp, sl)
        
        analyzed.append({
            'token_id': token_id[:20] + '...' if len(token_id) > 20 else token_id,
            'full_token_id': token_id,
            'entry_price': entry,
            'size': size,
            'tp': tp,
            'sl': sl,
            'entry_time': entry_time,
            **metrics
        })
    
    return analyzed

def format_output(positions):
    """Format and display position analysis."""
    print("=" * 100)
    print("POSITION ANALYSIS REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    print()
    
    # Summary statistics
    print("📊 SUMMARY STATISTICS")
    print("-" * 100)
    print(f"Total Positions: {len(positions)}")
    
    # Calculate min distances to triggers
    closest_to_tp = min(positions, key=lambda x: abs(x['pct_to_tp']))
    closest_to_sl = min(positions, key=lambda x: abs(x['pct_to_sl']))
    
    print(f"Closest to Take Profit: {closest_to_tp['token_id']} ({closest_to_tp['pct_to_tp']:+.2f}%)")
    print(f"Closest to Stop Loss: {closest_to_sl['token_id']} ({closest_to_sl['pct_to_sl']:+.2f}%)")
    print()
    
    # Detailed position table
    print("📋 POSITION DETAILS")
    print("-" * 100)
    print(f"{'Token ID':<23} {'Entry':>8} {'TP':>8} {'SL':>8} {'Dist→TP':>9} {'Dist→SL':>9} {'R/R':>6} {'Status'}")
    print("-" * 100)
    
    for p in positions:
        # Determine status flag
        status = ""
        if abs(p['pct_to_tp']) < 5:
            status = "🔥 NEAR TP"
        elif abs(p['pct_to_sl']) < 5:
            status = "⚠️  NEAR SL"
        elif p['risk_reward_ratio'] > 2.0:
            status = "📉 Poor R/R"
        elif p['risk_reward_ratio'] < 0.5:
            status = "📈 Good R/R"
        
        print(f"{p['token_id']:<23} "
              f"{p['entry_price']:>8.3f} "
              f"{p['tp']:>8.3f} "
              f"{p['sl']:>8.3f} "
              f"{p['pct_to_tp']:>+8.1f}% "
              f"{p['pct_to_sl']:>+8.1f}% "
              f"{p['risk_reward_ratio']:>6.2f} "
              f"{status}")
    
    print("-" * 100)
    print()
    
    # Risk/Reward Analysis
    print("⚖️  RISK/REWARD ANALYSIS (At Entry)")
    print("-" * 100)
    print("R/R Ratio Interpretation:")
    print("  • R/R < 0.5: Excellent ( risking $1 to make $2+ )")
    print("  • R/R 0.5-1.0: Good ( risking $1 to make $1-2 )")
    print("  • R/R 1.0-2.0: Fair ( risking $1 to make $0.5-1 )")
    print("  • R/R > 2.0: Poor ( risking $1 to make <$0.5 )")
    print()
    
    sorted_by_rr = sorted(positions, key=lambda x: x['risk_reward_ratio'])
    
    print("Best R/R Ratios:")
    for i, p in enumerate(sorted_by_rr[:3], 1):
        print(f"  {i}. {p['token_id']}: {p['risk_reward_ratio']:.2f} "
              f"(Risk ${p['entry_price']-p['sl']:.3f} → Reward ${p['tp']-p['entry_price']:.3f})")
    
    print()
    print("Worst R/R Ratios:")
    for i, p in enumerate(sorted_by_rr[-3:], 1):
        print(f"  {i}. {p['token_id']}: {p['risk_reward_ratio']:.2f} "
              f"(Risk ${p['entry_price']-p['sl']:.3f} → Reward ${p['tp']-p['entry_price']:.3f})")
    
    print()
    
    # Flagged positions
    print("🚩 POSITIONS FLAGGED FOR ATTENTION")
    print("-" * 100)
    
    flagged = []
    
    for p in positions:
        reasons = []
        if p['risk_reward_ratio'] > 2.0:
            reasons.append("Poor R/R ratio")
        if p['entry_price'] - p['sl'] < 0.03:
            reasons.append("Tight stop loss")
        if p['tp'] - p['entry_price'] < 0.03:
            reasons.append("Tight take profit")
        
        if reasons:
            flagged.append({
                'token_id': p['token_id'],
                'entry': p['entry_price'],
                'tp': p['tp'],
                'sl': p['sl'],
                'rr': p['risk_reward_ratio'],
                'reasons': reasons
            })
    
    if flagged:
        for f in flagged:
            print(f"⚠️  {f['token_id']}")
            print(f"    Entry: {f['entry']:.3f} | TP: {f['tp']:.3f} | SL: {f['sl']:.3f} | R/R: {f['rr']:.2f}")
            print(f"    Issues: {', '.join(f['reasons'])}")
            print()
    else:
        print("✅ No major issues detected")
    
    print("=" * 100)

if __name__ == "__main__":
    positions = analyze_positions()
    format_output(positions)

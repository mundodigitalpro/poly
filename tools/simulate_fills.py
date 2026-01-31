#!/usr/bin/env python3
"""
Simulate TP/SL fills for dry run positions.

Checks current market prices against position TP/SL levels
and reports which positions would have been filled.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from py_clob_client.client import ClobClient


def load_positions():
    """Load positions from JSON file."""
    positions_file = Path(__file__).parent.parent / "data" / "positions.json"
    if not positions_file.exists():
        return {}
    with open(positions_file) as f:
        return json.load(f)


def save_simulation_results(results: list):
    """Save simulation results to file."""
    results_file = Path(__file__).parent.parent / "data" / "simulation_results.json"

    # Load existing results
    existing = []
    if results_file.exists():
        with open(results_file) as f:
            existing = json.load(f)

    # Append new results
    existing.extend(results)

    with open(results_file, "w") as f:
        json.dump(existing, f, indent=2)


def get_best_bid(client, token_id: str) -> float:
    """Get best bid price for a token."""
    try:
        book = client.get_order_book(token_id)
        bids = getattr(book, "bids", [])
        if not bids:
            return 0.0

        prices = []
        for bid in bids:
            if hasattr(bid, "price"):
                prices.append(float(bid.price))
            elif isinstance(bid, dict) and "price" in bid:
                prices.append(float(bid["price"]))

        return max(prices) if prices else 0.0
    except Exception as e:
        print(f"  Error getting orderbook: {e}")
        return 0.0


def init_client():
    """Initialize CLOB client."""
    load_dotenv()

    host = "https://clob.polymarket.com"
    chain_id = 137
    private_key = os.getenv("POLY_PRIVATE_KEY", "").strip()

    if not private_key:
        raise RuntimeError("POLY_PRIVATE_KEY not set")

    return ClobClient(host=host, chain_id=chain_id, key=private_key)


def simulate_fills(verbose: bool = True):
    """
    Check all positions against current prices.

    Returns list of simulated fills.
    """
    positions = load_positions()

    if not positions:
        print("No positions found.")
        return []

    print(f"\n{'='*60}")
    print(f"  SIMULATING TP/SL FILLS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"Positions: {len(positions)}\n")

    client = init_client()
    results = []

    for token_id, pos in positions.items():
        short_id = token_id[:12] + "..."
        entry = pos["entry_price"]
        tp = pos["tp"]
        sl = pos["sl"]
        size = pos["filled_size"]

        if verbose:
            print(f"Position: {short_id}")
            print(f"  Entry: ${entry:.4f} | TP: ${tp:.4f} | SL: ${sl:.4f}")

        # Get current price
        best_bid = get_best_bid(client, token_id)

        if best_bid <= 0:
            if verbose:
                print(f"  Current: N/A (no bids)")
            continue

        # Calculate P&L
        pnl_pct = ((best_bid - entry) / entry) * 100
        pnl_usd = (best_bid - entry) * size

        # Check TP/SL
        status = "HOLDING"
        if best_bid >= tp:
            status = "TP HIT ✅"
            results.append({
                "token_id": token_id,
                "type": "take_profit",
                "entry_price": entry,
                "exit_price": best_bid,
                "tp": tp,
                "sl": sl,
                "size": size,
                "pnl_usd": pnl_usd,
                "pnl_pct": pnl_pct,
                "timestamp": datetime.now().isoformat(),
            })
        elif best_bid <= sl:
            status = "SL HIT ❌"
            results.append({
                "token_id": token_id,
                "type": "stop_loss",
                "entry_price": entry,
                "exit_price": best_bid,
                "tp": tp,
                "sl": sl,
                "size": size,
                "pnl_usd": pnl_usd,
                "pnl_pct": pnl_pct,
                "timestamp": datetime.now().isoformat(),
            })

        if verbose:
            color = "🟢" if pnl_pct > 0 else "🔴" if pnl_pct < 0 else "⚪"
            print(f"  Current: ${best_bid:.4f} | P&L: {pnl_pct:+.2f}% (${pnl_usd:+.4f}) {color}")
            print(f"  Status: {status}")

            # Distance to TP/SL
            to_tp = ((tp - best_bid) / best_bid) * 100
            to_sl = ((best_bid - sl) / best_bid) * 100
            print(f"  Distance: TP {to_tp:+.2f}% | SL {to_sl:+.2f}%")
            print()

    # Summary
    print(f"{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    tp_hits = [r for r in results if r["type"] == "take_profit"]
    sl_hits = [r for r in results if r["type"] == "stop_loss"]

    print(f"Take Profits: {len(tp_hits)}")
    print(f"Stop Losses: {len(sl_hits)}")

    if results:
        total_pnl = sum(r["pnl_usd"] for r in results)
        print(f"Simulated P&L: ${total_pnl:+.4f}")

        # Save results
        save_simulation_results(results)
        print(f"\nResults saved to data/simulation_results.json")
    else:
        print("No fills triggered yet.")

    print()
    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Simulate TP/SL fills")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    parser.add_argument("--loop", "-l", type=int, default=0,
                        help="Loop every N seconds (0=once)")
    args = parser.parse_args()

    if args.loop > 0:
        import time
        print(f"Running every {args.loop} seconds. Ctrl+C to stop.\n")
        try:
            while True:
                simulate_fills(verbose=not args.quiet)
                time.sleep(args.loop)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        simulate_fills(verbose=not args.quiet)


if __name__ == "__main__":
    main()

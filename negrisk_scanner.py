#!/usr/bin/env python3
"""
NegRisk Multi-Outcome Arbitrage Scanner for Polymarket.

Detects risk-free arbitrage in markets with >2 mutually exclusive outcomes.

Strategy: In a market with N outcomes where exactly ONE wins:
- Buy NO on ALL outcomes
- Guaranteed payout = $(N-1) (all but the winner pay $1)
- If total NO cost < $(N-1), profit is guaranteed
"""

import argparse
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

from bot.gamma_client import GammaClient

TAKER_FEE = 0.01


class NegRiskScanner:
    def __init__(self, client: ClobClient, gamma: GammaClient, min_profit_pct: float = 0.5, verbose: bool = True):
        self.client = client
        self.gamma = gamma
        self.min_profit_pct = min_profit_pct
        self.verbose = verbose
        self.opportunities = []
        self.all_events = []
        self._api_calls = 0

    def log(self, msg: str):
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def scan(self, limit: int = 300) -> List[Dict]:
        self.log(f"Fetching {limit} markets...")
        markets = self.gamma.get_markets(active=True, closed=False, limit=limit, order="volume24hr", ascending=False)
        self.log(f"Found {len(markets)} markets")

        # Find NegRisk markets
        negrisk = []
        for m in markets:
            raw = m.get("_raw", {})
            if raw.get("negRisk") is True:
                m["_group_title"] = raw.get("groupItemTitle", "")
                negrisk.append(m)

        self.log(f"Found {len(negrisk)} NegRisk markets")

        # Group by question pattern
        groups = self._group_by_pattern(negrisk)
        self.log(f"Identified {len(groups)} multi-outcome events (3+ outcomes)")

        opportunities = []

        for pattern, event_markets in groups.items():
            if len(event_markets) < 3:
                continue

            result = self._analyze_event(pattern, event_markets)
            if result:
                self.all_events.append(result)
                if result["net_profit_pct"] >= self.min_profit_pct:
                    opportunities.append(result)
                    self.log(f"  *** OPPORTUNITY: {result['event'][:50]}... ({result['net_profit_pct']:.2f}%)")

            time.sleep(0.1)

        self.opportunities = opportunities
        self._show_results()
        return opportunities

    def _group_by_pattern(self, markets: List[Dict]) -> Dict[str, List[Dict]]:
        """Group markets by question pattern, replacing specific option with placeholder."""
        groups = defaultdict(list)

        for m in markets:
            question = m.get("question", "")
            group_title = m.get("_group_title", "")

            if group_title and group_title in question:
                pattern = question.replace(group_title, "___")
            else:
                pattern = question

            groups[pattern].append(m)

        return {k: v for k, v in groups.items() if len(v) >= 3}

    def _analyze_event(self, pattern: str, markets: List[Dict]) -> Optional[Dict]:
        """Analyze multi-outcome event for arbitrage."""
        outcomes = []
        total_no_cost = 0.0
        total_yes_sum = 0.0

        for m in markets:
            clob_ids = m.get("clob_token_ids", [])
            if len(clob_ids) < 2:
                continue

            yes_token = str(clob_ids[0])
            no_token = str(clob_ids[1])

            # Get prices
            yes_bid = self._get_best_bid(yes_token)
            no_ask = self._get_best_ask(no_token)

            # Estimate NO price from YES if needed
            if no_ask <= 0 and yes_bid > 0:
                no_ask = 1.0 - yes_bid + 0.01

            if no_ask <= 0:
                continue

            outcomes.append({
                "title": m.get("_group_title", "")[:30] or m.get("question", "")[:30],
                "yes_bid": round(yes_bid, 4),
                "no_ask": round(no_ask, 4),
                "volume_24h": m.get("volume_24h", 0),
            })
            total_no_cost += no_ask
            total_yes_sum += yes_bid

        if len(outcomes) < 3:
            return None

        n = len(outcomes)
        guaranteed_payout = n - 1
        gross_profit = guaranteed_payout - total_no_cost
        fee_cost = total_no_cost * TAKER_FEE  # Simplified: fee on total
        net_profit = gross_profit - fee_cost
        net_profit_pct = (net_profit / total_no_cost) * 100 if total_no_cost > 0 else 0

        outcomes.sort(key=lambda x: x["no_ask"])

        return {
            "event": pattern.replace("___", "[X]"),
            "n_outcomes": n,
            "outcomes": outcomes,
            "total_no_cost": round(total_no_cost, 4),
            "total_yes_sum": round(total_yes_sum, 4),
            "guaranteed_payout": guaranteed_payout,
            "gross_profit": round(gross_profit, 4),
            "fee_cost": round(fee_cost, 4),
            "net_profit": round(net_profit, 4),
            "net_profit_pct": round(net_profit_pct, 2),
            "is_profitable": net_profit > 0,
        }

    def _get_best_ask(self, token_id: str) -> float:
        try:
            self._api_calls += 1
            book = self.client.get_order_book(token_id)
            asks = getattr(book, "asks", None) or (book.to_dict().get("asks", []) if hasattr(book, "to_dict") else [])
            if not asks:
                return 0.0
            prices = [float(o.price) if hasattr(o, "price") else float(o.get("price", 0)) for o in asks]
            return min(p for p in prices if p > 0) if prices else 0.0
        except:
            return 0.0

    def _get_best_bid(self, token_id: str) -> float:
        try:
            self._api_calls += 1
            book = self.client.get_order_book(token_id)
            bids = getattr(book, "bids", None) or (book.to_dict().get("bids", []) if hasattr(book, "to_dict") else [])
            if not bids:
                return 0.0
            prices = [float(o.price) if hasattr(o, "price") else float(o.get("price", 0)) for o in bids]
            return max(p for p in prices if p > 0) if prices else 0.0
        except:
            return 0.0

    def _show_results(self):
        if not self.all_events:
            print("\nNo multi-outcome events analyzed.")
            return

        sorted_events = sorted(self.all_events, key=lambda x: x["net_profit_pct"], reverse=True)

        print("\n" + "=" * 80)
        print("ANÁLISIS NEGRISK - MERCADOS MULTI-OUTCOME")
        print("=" * 80)
        print(f"{'#':<3} {'N':>3} {'Σ(NO)':>8} {'Pago':>6} {'Bruto':>8} {'Neto':>8} {'%':>7} {'Evento':<30}")
        print("-" * 80)

        for i, e in enumerate(sorted_events[:15], 1):
            status = "✓" if e["is_profitable"] else " "
            event_short = e["event"][:28]
            print(
                f"{status}{i:<2} "
                f"{e['n_outcomes']:>3} "
                f"${e['total_no_cost']:>7.3f} "
                f"${e['guaranteed_payout']:>5} "
                f"${e['gross_profit']:>+7.3f} "
                f"${e['net_profit']:>+7.3f} "
                f"{e['net_profit_pct']:>+6.2f}% "
                f"{event_short}"
            )

        # Detailed view of top events
        print("\n" + "-" * 80)
        print("DETALLE TOP 5:")
        print("-" * 80)

        for i, e in enumerate(sorted_events[:5], 1):
            print(f"\n{i}. {e['event'][:70]}")
            print(f"   N={e['n_outcomes']} | Σ(YES)={e['total_yes_sum']:.3f} | Σ(NO)={e['total_no_cost']:.3f}")
            print(f"   Pago garantizado: ${e['guaranteed_payout']} | Profit: ${e['net_profit']:+.4f} ({e['net_profit_pct']:+.2f}%)")
            print(f"   Outcomes (ordenados por NO price):")
            for j, o in enumerate(e["outcomes"][:6], 1):
                print(f"      {j}. NO=${o['no_ask']:.3f} YES=${o['yes_bid']:.3f} | {o['title']}")
            if len(e["outcomes"]) > 6:
                print(f"      ... +{len(e['outcomes'])-6} más")

        print("\n" + "-" * 80)
        profitable = len([e for e in self.all_events if e["is_profitable"]])
        print(f"Eventos analizados: {len(self.all_events)} | Rentables: {profitable} | API calls: {self._api_calls}")

    def print_summary(self):
        print("\n" + "=" * 80)
        if self.opportunities:
            print(f"OPORTUNIDADES NEGRISK: {len(self.opportunities)}")
            for opp in self.opportunities:
                print(f"\n  → {opp['event'][:60]}")
                print(f"    Comprar NO en {opp['n_outcomes']} outcomes = ${opp['total_no_cost']:.4f}")
                print(f"    Profit: ${opp['net_profit']:.4f} ({opp['net_profit_pct']:.2f}%)")
        else:
            print("NO HAY OPORTUNIDADES NEGRISK RENTABLES")
            print("=" * 80)


def create_client():
    load_dotenv()
    private_key = os.getenv("POLY_PRIVATE_KEY")
    funder = os.getenv("POLY_FUNDER_ADDRESS")
    if not private_key:
        sys.exit("Error: POLY_PRIVATE_KEY not set")
    client = ClobClient("https://clob.polymarket.com", key=private_key, chain_id=137, funder=funder, signature_type=1 if funder else 0)
    if all(os.getenv(k) for k in ["POLY_API_KEY", "POLY_API_SECRET", "POLY_API_PASSPHRASE"]):
        client.set_api_creds(ApiCreds(api_key=os.getenv("POLY_API_KEY"), api_secret=os.getenv("POLY_API_SECRET"), api_passphrase=os.getenv("POLY_API_PASSPHRASE")))
    return client


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-profit", type=float, default=0.5)
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=120)
    args = parser.parse_args()

    print("=" * 80)
    print("NEGRISK MULTI-OUTCOME ARBITRAGE SCANNER")
    print(f"Min profit: {args.min_profit}% | Markets: {args.limit}")
    print("=" * 80 + "\n")

    client = create_client()
    gamma = GammaClient()
    scanner = NegRiskScanner(client, gamma, args.min_profit)

    try:
        if args.once:
            scanner.scan(args.limit)
            scanner.print_summary()
        else:
            n = 0
            while True:
                n += 1
                print(f"\n{'='*80}\nSCAN #{n}\n{'='*80}")
                scanner.scan(args.limit)
                scanner.print_summary()
                print(f"\nNext: {args.interval}s...")
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

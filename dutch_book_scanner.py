#!/usr/bin/env python3
"""
Dutch Book Arbitrage Scanner for Polymarket.

Detects risk-free arbitrage opportunities where YES + NO prices < 1.0

Strategy: If you can buy YES for $0.48 and NO for $0.50 = $0.98 total,
you're guaranteed $1.00 at settlement = $0.02 profit (2.04% return)

Usage:
    python dutch_book_scanner.py              # Scan all markets
    python dutch_book_scanner.py --min-profit 0.02  # Min 2% profit
    python dutch_book_scanner.py --exclude-crypto   # Skip crypto markets
    python dutch_book_scanner.py --once       # Single scan, then exit
"""

import argparse
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

from bot.gamma_client import GammaClient

# Polymarket fee structure (approximate)
# Non-crypto markets typically have lower effective fees
TAKER_FEE = 0.01  # 1% taker fee
MIN_PROFIT_AFTER_FEES = 0.015  # 1.5% minimum profit to cover fees + slippage

# Crypto market keywords (higher fees, more competitive)
CRYPTO_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
    "xrp", "crypto", "doge", "memecoin", "token", "defi",
    "15-minute", "1-hour", "price above", "price below"
]


def is_crypto_market(question: str) -> bool:
    """Check if market is crypto-related based on question text."""
    q_lower = question.lower()
    return any(kw in q_lower for kw in CRYPTO_KEYWORDS)


class DutchBookScanner:
    """Scanner for Dutch Book arbitrage opportunities."""

    def __init__(
        self,
        client: ClobClient,
        gamma: GammaClient,
        min_profit: float = MIN_PROFIT_AFTER_FEES,
        exclude_crypto: bool = True,
        verbose: bool = True,
    ):
        self.client = client
        self.gamma = gamma
        self.min_profit = min_profit
        self.exclude_crypto = exclude_crypto
        self.verbose = verbose
        self.opportunities_found = []
        self.near_misses = []  # Markets close to arbitrage
        self._api_calls = 0

    def log(self, msg: str):
        """Print timestamped log message."""
        if self.verbose:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] {msg}")

    def scan(self, limit: int = 100) -> List[Dict]:
        """
        Scan markets for Dutch Book opportunities.

        Returns list of opportunities with profit > min_profit.
        """
        self.log(f"Fetching top {limit} markets from Gamma API...")
        markets = self.gamma.get_markets(
            active=True,
            closed=False,
            limit=limit,
            order="volume24hr",
            ascending=False,
        )

        self.log(f"Found {len(markets)} active markets")
        opportunities = []
        near_misses = []
        skipped_crypto = 0
        skipped_no_tokens = 0
        skipped_no_orderbook = 0
        all_market_data = []

        for i, market in enumerate(markets):
            question = market.get("question", "")
            clob_ids = market.get("clob_token_ids", [])

            # Skip crypto markets if requested
            if self.exclude_crypto and is_crypto_market(question):
                skipped_crypto += 1
                continue

            # Need exactly 2 tokens (YES/NO) for Dutch Book
            if len(clob_ids) != 2:
                skipped_no_tokens += 1
                continue

            yes_token = str(clob_ids[0])
            no_token = str(clob_ids[1])

            # Get orderbooks for both tokens
            yes_ask = self._get_best_ask(yes_token)
            no_ask = self._get_best_ask(no_token)

            if yes_ask <= 0 or no_ask <= 0:
                skipped_no_orderbook += 1
                continue

            # Calculate Dutch Book opportunity
            total_cost = yes_ask + no_ask
            gross_profit = 1.0 - total_cost

            # Account for fees (pay fee on both buys)
            fee_cost = total_cost * TAKER_FEE
            net_profit = gross_profit - fee_cost
            profit_pct = (net_profit / total_cost) * 100 if total_cost > 0 else 0

            market_data = {
                "question": question,
                "yes_token": yes_token,
                "no_token": no_token,
                "yes_ask": yes_ask,
                "no_ask": no_ask,
                "total_cost": total_cost,
                "gross_profit": gross_profit,
                "net_profit": net_profit,
                "profit_pct": profit_pct,
                "volume_24h": market.get("volume_24h", 0),
                "liquidity": market.get("liquidity", 0),
                "timestamp": datetime.now().isoformat(),
            }
            all_market_data.append(market_data)

            # Categorize the market
            if net_profit >= self.min_profit:
                opportunities.append(market_data)
                self.log(f"  *** OPPORTUNITY: {question[:50]}... ({profit_pct:.2f}%)")
            elif gross_profit > -0.02:  # Within 2% of breakeven
                near_misses.append(market_data)

            # Progress update
            if (i + 1) % 10 == 0:
                self.log(f"  Scanned {i+1}/{len(markets)} markets...")

            # Rate limiting
            if i % 10 == 9:
                time.sleep(0.3)

        self.log(
            f"\nScan complete: {len(markets)} total, "
            f"{skipped_crypto} crypto skipped, "
            f"{skipped_no_tokens} non-binary, "
            f"{skipped_no_orderbook} no orderbook"
        )
        self.log(f"Markets analyzed: {len(all_market_data)}")
        self.log(f"Opportunities (>{self.min_profit*100:.1f}%): {len(opportunities)}")
        self.log(f"Near misses (within 2%): {len(near_misses)}")

        self.opportunities_found.extend(opportunities)
        self.near_misses = near_misses

        # Show best markets (closest to arbitrage)
        self._show_best_markets(all_market_data)

        return opportunities

    def _show_best_markets(self, all_data: List[Dict]):
        """Show top markets closest to Dutch Book arbitrage."""
        if not all_data:
            return

        # Sort by total cost (lowest = closest to arbitrage)
        sorted_data = sorted(all_data, key=lambda x: x["total_cost"])

        print("\n" + "-" * 60)
        print("TOP 10 MARKETS CLOSEST TO DUTCH BOOK ARBITRAGE:")
        print("-" * 60)
        print(f"{'#':<3} {'YES':>6} {'NO':>6} {'TOTAL':>7} {'GROSS':>7} {'NET':>7} {'Question':<40}")
        print("-" * 60)

        for i, m in enumerate(sorted_data[:10], 1):
            q_short = m["question"][:38] + ".." if len(m["question"]) > 40 else m["question"]
            print(
                f"{i:<3} "
                f"{m['yes_ask']:>6.3f} "
                f"{m['no_ask']:>6.3f} "
                f"{m['total_cost']:>7.4f} "
                f"{m['gross_profit']:>+7.4f} "
                f"{m['net_profit']:>+7.4f} "
                f"{q_short:<40}"
            )

        # Statistics
        costs = [m["total_cost"] for m in all_data]
        print("-" * 60)
        print(f"Average total cost: {sum(costs)/len(costs):.4f}")
        print(f"Min total cost: {min(costs):.4f}")
        print(f"Max total cost: {max(costs):.4f}")
        print(f"Markets with cost < 1.00: {sum(1 for c in costs if c < 1.0)}")
        print(f"Markets with cost < 1.01: {sum(1 for c in costs if c < 1.01)}")
        print(f"Markets with cost < 1.02: {sum(1 for c in costs if c < 1.02)}")

    def _get_best_ask(self, token_id: str) -> float:
        """Get the best (lowest) ask price for a token."""
        try:
            self._api_calls += 1
            book = self.client.get_order_book(token_id)
            asks = getattr(book, "asks", None)

            if asks is None and hasattr(book, "to_dict"):
                asks = book.to_dict().get("asks", [])

            if not asks:
                return 0.0

            prices = []
            for order in asks:
                if hasattr(order, "price"):
                    prices.append(float(order.price))
                elif isinstance(order, dict) and "price" in order:
                    prices.append(float(order["price"]))

            return min(prices) if prices else 0.0

        except Exception as e:
            if "no orderbook" not in str(e).lower():
                pass  # Silent error
            return 0.0

    def print_summary(self):
        """Print summary of all opportunities found."""
        print("\n" + "=" * 60)
        if not self.opportunities_found:
            print("RESULTADO: NO HAY OPORTUNIDADES DE DUTCH BOOK")
            print("=" * 60)
            print("\nEsto es normal por varias razones:")
            print("1. Bots HFT capturan oportunidades en <50ms")
            print("2. Market makers mantienen YES+NO cerca de 1.00")
            print("3. Fees (1%) eliminan márgenes pequeños")
            print(f"\nAPI calls: {self._api_calls}")
        else:
            print(f"OPORTUNIDADES ENCONTRADAS: {len(self.opportunities_found)}")
            print("=" * 60)
            for i, opp in enumerate(self.opportunities_found, 1):
                print(f"\n{i}. {opp['question'][:60]}...")
                print(f"   YES @ {opp['yes_ask']:.3f} + NO @ {opp['no_ask']:.3f} = {opp['total_cost']:.3f}")
                print(f"   Profit: ${opp['net_profit']:.4f} ({opp['profit_pct']:.2f}%)")


def create_client() -> Tuple[ClobClient, str]:
    """Create authenticated CLOB client."""
    load_dotenv()

    host = "https://clob.polymarket.com"
    chain_id = 137

    private_key = os.getenv("POLY_PRIVATE_KEY")
    funder = os.getenv("POLY_FUNDER_ADDRESS")

    if not private_key:
        print("Error: POLY_PRIVATE_KEY not set in .env")
        sys.exit(1)

    sig_type = 1 if funder else 0

    client = ClobClient(
        host,
        key=private_key,
        chain_id=chain_id,
        funder=funder,
        signature_type=sig_type,
    )

    api_key = os.getenv("POLY_API_KEY")
    api_secret = os.getenv("POLY_API_SECRET")
    api_passphrase = os.getenv("POLY_API_PASSPHRASE")

    if api_key and api_secret and api_passphrase:
        client.set_api_creds(ApiCreds(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
        ))

    return client, "Magic Link" if funder else "EOA"


def main():
    parser = argparse.ArgumentParser(description="Dutch Book Arbitrage Scanner")
    parser.add_argument("--min-profit", type=float, default=MIN_PROFIT_AFTER_FEES)
    parser.add_argument("--exclude-crypto", action="store_true", default=True)
    parser.add_argument("--include-crypto", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("-q", "--quiet", action="store_true")

    args = parser.parse_args()
    exclude_crypto = not args.include_crypto

    print("=" * 60)
    print("DUTCH BOOK ARBITRAGE SCANNER - DRY RUN")
    print("=" * 60)
    print(f"Min profit: {args.min_profit * 100:.1f}% | Crypto: {'Included' if not exclude_crypto else 'Excluded'}")
    print(f"Markets: {args.limit} | Mode: {'Once' if args.once else 'Continuous'}")
    print("=" * 60)

    client, auth_type = create_client()
    gamma = GammaClient()
    print(f"Auth: {auth_type}\n")

    scanner = DutchBookScanner(
        client=client,
        gamma=gamma,
        min_profit=args.min_profit,
        exclude_crypto=exclude_crypto,
        verbose=not args.quiet,
    )

    try:
        if args.once:
            scanner.scan(limit=args.limit)
            scanner.print_summary()
        else:
            scan_count = 0
            while True:
                scan_count += 1
                print(f"\n{'='*60}")
                print(f"SCAN #{scan_count} - {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'='*60}")
                scanner.scan(limit=args.limit)
                scanner.print_summary()
                print(f"\nNext scan in {args.interval}s... (Ctrl+C to stop)")
                time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopped.")
        scanner.print_summary()


if __name__ == "__main__":
    main()

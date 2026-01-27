import os
import logging
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import argparse
import time

# ... (imports)

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Polymarket Python Client")
    parser.add_argument("--filter", type=str, help="Filter markets by question text (case-insensitive)")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of results displayed")
    parser.add_argument("--book", type=str, help="Get Orderbook for a specific Token ID")
    parser.add_argument("--monitor", action="store_true", help="Continuous monitoring (Poll mode)")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds")
    parser.add_argument("--balance", action="store_true", help="Get account balance")
    args = parser.parse_args()

    logger.info("Starting Polymarket Client...")

    # 1. Load credentials
    host = "https://clob.polymarket.com"
    key = os.getenv("POLY_API_KEY")
    secret = os.getenv("POLY_API_SECRET")
    passphrase = os.getenv("POLY_API_PASSPHRASE")
    chain_id = 137  # Polygon Mainnet
    
    # Private key is optional for just reading markets, but needed for orders
    private_key = os.getenv("POLY_PRIVATE_KEY")
    
    # Check if private_key is the placeholder or empty
    if private_key and (private_key == "your_private_key" or not private_key.startswith("0x")):
        logger.warning("POLY_PRIVATE_KEY is not set or is invalid (must start with 0x). Continuing without it (Read-Only mode might be limited).")
        private_key = None

    # Fundere Address (Proxy) for Magic Link / Gnosis Safe users
    funder = os.getenv("POLY_FUNDER_ADDRESS")

    if not all([key, secret, passphrase]):
        logger.error("Missing API credentials in .env file.")
        return

    # Sanitize inputs (remove whitespace)
    key = key.strip() if key else None
    secret = secret.strip() if secret else None
    passphrase = passphrase.strip() if passphrase else None
    private_key = private_key.strip() if private_key else None
    funder = funder.strip() if funder else None

    try:
        # 2. Initialize Client
        creds = ApiCreds(
            api_key=key,
            api_secret=secret,
            api_passphrase=passphrase,
        )

        # Determine signature type
        # 2 for Gnosis Safe (Magic Link), 0 for EOA (MetaMask)
        sig_type = 2 if funder else 0
        
        client = ClobClient(
            host=host,
            key=private_key,
            chain_id=chain_id,
            creds=creds,
            signature_type=sig_type,
            funder=funder if funder else private_key, 
        )
        logger.info("Client initialized successfully.")

        if args.balance:
            logger.info("Fetching Account Balance...")
            if not private_key:
                logger.error("Private Key is required to fetch balance/allowance (and to trade). Please set POLY_PRIVATE_KEY in .env.")
                return

            try:
                # Based on documentation/common usage patterns
                # This returns the collateral (USDC) balance and allowance
                # NOTE: Polymarket uses a wrapper/proxy, so we check the proxy allowance/balance too usually.
                # But let's start with basic get_balance_allowance or similar.
                # If py_clob_client follows standard, it might have get_balance_allowance(params)
                # Let's try inspecting or using a safe method.
                # Actually, standard usage is often: client.get_balance_allowance(params=...)
                # But simpler method might be client.get_collateral_balance() or similar?
                # Let's inspect `client` methods to be sure or try the most standard usage.
                # Search result mentioned `account_balance()`.
                
                # Let's look for available methods in client first to avoid errors.
                # logger.info(f"Client methods: {[m for m in dir(client) if 'balance' in m]}")
                
                # We will try getting the balance allowances
                balance = client.get_balance_allowance(
                    params=BalanceAllowanceParams(
                        asset_type=AssetType.COLLATERAL,
                        signature_type=sig_type
                    )
                )
                print(f"\n--- Account Balance ---")
                print(f"Balance: {balance}")
                
            except Exception as e:
                logger.error(f"Error fetching balance: {e}")
            return

        # 3. Handling Orderbook Request
        if args.book:
            token_id = args.book
            
            while True:
                logger.info(f"Fetching Orderbook for Token ID: {token_id}")
                try:
                    order_book = client.get_order_book(token_id)
                    
                    # Display Bids and Asks
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"\n--- Order Book for {token_id} at {timestamp} ---")
                    
                    try:
                        # [ASKS]
                        print("\n[ASKS] (Sellers - Lowest first)")
                        asks = getattr(order_book, 'asks', [])
                        # Fallback to dict if needed
                        if not asks and hasattr(order_book, 'to_dict'):
                             asks = order_book.to_dict().get('asks', [])
                        
                        if not asks:
                            print("  No asks.")
                        else:
                            for ask in asks[:5]: 
                                price = ask.price if hasattr(ask, 'price') else ask.get('price')
                                size = ask.size if hasattr(ask, 'size') else ask.get('size')
                                print(f"  Price: {price} | Size: {size}")

                        # [BIDS]
                        print("\n[BIDS] (Buyers - Highest first)")
                        bids = getattr(order_book, 'bids', [])
                        if not bids and hasattr(order_book, 'to_dict'):
                             bids = order_book.to_dict().get('bids', [])

                        if not bids:
                            print("  No bids.")
                        else:
                            for bid in bids[:5]:
                                price = bid.price if hasattr(bid, 'price') else bid.get('price')
                                size = bid.size if hasattr(bid, 'size') else bid.get('size')
                                print(f"  Price: {price} | Size: {size}")

                    except Exception as e:
                        logger.error(f"Error parsing orderbook: {e}")
                
                except Exception as e:
                    logger.error(f"Error fetching orderbook: {e}")

                if not args.monitor:
                    break
                
                print(f"\nWaiting {args.interval} seconds...")
                time.sleep(args.interval)
            
            return

            print("\n[BIDS] (Buyers - Highest first)")
            bids = order_book.get('bids', [])
            if not bids:
                print("  No bids.")
            for bid in bids[:5]: # Show top 5
                print(f"  Price: {bid.get('price')} | Size: {bid.get('size')}")
            
            return

        # 4. Fetch Markets (Default behavior)
        logger.info("Fetching markets...")
        # using get_sampling_markets to get full metadata (question, etc.)
        resp = client.get_sampling_markets(next_cursor="")
        markets = resp.get('data', [])
        
        logger.info(f"Retrieved {len(markets)} markets in total.")

        # 4. Filter and Display
        count = 0
        logger.info(f"--- Top Markets (Filter: '{args.filter if args.filter else 'None'}') ---")
        
        for market in markets:
            question = market.get('question', market.get('title', 'No Question'))
            
            # Filter logic
            if args.filter:
                if args.filter.lower() not in question.lower():
                    continue

            print(f"- [ID: {market.get('condition_id')}] {question}")
            # Simplified display of tokens (outcomes)
            if market.get('tokens'):
                print(f"  Tokens: {market.get('tokens')}")
            
            count += 1
            if count >= args.limit:
                break
        
        if count == 0:
            print("No markets found matching the filter.")

    except Exception as e:
        logger.error(f"Error connecting to Polymarket: {e}")

if __name__ == "__main__":
    main()


import os
import logging
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import argparse

# ... (imports)

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Polymarket Python Client")
    parser.add_argument("--filter", type=str, help="Filter markets by question text (case-insensitive)")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of results displayed")
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

    if not all([key, secret, passphrase]):
        logger.error("Missing API credentials in .env file.")
        return

    try:
        # 2. Initialize Client
        creds = ApiCreds(
            api_key=key,
            api_secret=secret,
            api_passphrase=passphrase,
        )

        client = ClobClient(
            host=host,
            key=private_key,
            chain_id=chain_id,
            creds=creds,
            signature_type=1,  # 1 for EOA (External Owned Account), 2 for Poly Proxy/Gnosis Safe
            funder=private_key, # Use private key as funder for gasless transactions if supported
        )
        logger.info("Client initialized successfully.")

        # 3. Fetch Markets
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
            count += 1
            if count >= args.limit:
                break
        
        if count == 0:
            print("No markets found matching the filter.")

    except Exception as e:
        logger.error(f"Error connecting to Polymarket: {e}")

if __name__ == "__main__":
    main()


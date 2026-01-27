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

def main():
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

        # 3. Test Connection (Ping)
        logger.info("Testing connection...")
        resp = client.get_sampling_simplified_markets(next_cursor="")
        # Simple health check endpoint or getting markets usually confirms access
        
        logger.info(f"Connection successful! Retrieved {len(resp.get('data', []))} markets.")
        
        # Example: Print first market title
        if resp.get('data'):
            first_market = resp['data'][0]
            logger.info(f"Sample Market: {first_market.get('question')}")

    except Exception as e:
        logger.error(f"Error connecting to Polymarket: {e}")

if __name__ == "__main__":
    main()

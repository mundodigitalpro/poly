
import os
import logging
from dotenv import load_dotenv
from py_clob_client.client import ClobClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    host = "https://clob.polymarket.com"
    chain_id = 137
    private_key = os.getenv("POLY_PRIVATE_KEY")
    funder = os.getenv("POLY_FUNDER_ADDRESS")

    if not private_key:
        logger.error("POLY_PRIVATE_KEY not found in .env")
        return

    # Sanitize
    private_key = private_key.strip()
    if funder:
        funder = funder.strip()

    logger.info("Initializing Client for Key Generation...")
    
    try:
        # Initialize Client WITHOUT L2 Creds, just L1
        # Try signature_type=0 (EOA) - Maybe we just need keys for the signer?
        sig_type = 0
        
        client = ClobClient(
            host=host,
            key=private_key,
            chain_id=chain_id,
            signature_type=sig_type,
            # funder=funder if funder else private_key 
            # Don't pass funder for type 0 usually, or pass it as None
        )

        logger.info("Creating NEW API Key...")
        resp = client.create_api_key()
        
        print("\n" + "="*50)
        print("SUCCESS! New API Credentials Generated")
        print("="*50)
        print(f"POLY_API_KEY={resp.get('apiKey')}")
        print(f"POLY_API_SECRET={resp.get('secret')}")
        print(f"POLY_API_PASSPHRASE={resp.get('passphrase')}")
        print("="*50)
        print("\nACTION REQUIRED: Replace the values in your .env file with these new ones.")

    except Exception as e:
        logger.error(f"Failed to create API Keys: {e}")

if __name__ == "__main__":
    main()

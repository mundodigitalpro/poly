#!/usr/bin/env python3
"""
Generate User API Credentials from your Private Key
Based on official docs: https://docs.polymarket.com/quickstart/first-order
"""
import os
import logging
from dotenv import load_dotenv
from py_clob_client.client import ClobClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

print("=" * 70)
print("POLYMARKET - USER API CREDENTIALS GENERATOR")
print("=" * 70)
print("\nBased on official documentation:")
print("https://docs.polymarket.com/quickstart/first-order#step-2")
print("")

# Load private key
private_key = os.getenv("POLY_PRIVATE_KEY")
funder = os.getenv("POLY_FUNDER_ADDRESS")

if not private_key:
    print("❌ ERROR: POLY_PRIVATE_KEY not found in .env")
    exit(1)

if private_key == "your_private_key" or not private_key.startswith("0x"):
    print("❌ ERROR: Invalid POLY_PRIVATE_KEY (must start with 0x)")
    exit(1)

print(f"✓ Private Key found: {private_key[:6]}...{private_key[-4:]}")

# Determine signature type
if funder:
    print(f"✓ Funder Address found: {funder}")
    print("  → Using signature_type=2 (Magic Link/Gnosis Safe)")
    sig_type = 2
    funder_param = funder
else:
    print("  → Using signature_type=0 (EOA/MetaMask)")
    sig_type = 0
    # For EOA, funder is the wallet address itself
    # We need to derive it from private key
    from eth_account import Account
    account = Account.from_key(private_key)
    funder_param = account.address
    print(f"  → Derived wallet address: {funder_param}")

print("\n" + "─" * 70)
print("STEP 1: Initializing client...")
print("─" * 70)

try:
    # Initialize client WITHOUT API credentials first
    # This matches Step 1 from the official docs
    host = "https://clob.polymarket.com"
    chain_id = 137
    
    client = ClobClient(
        host=host,
        key=private_key,
        chain_id=chain_id,
        signature_type=sig_type,
        funder=funder_param,
    )
    
    print("✓ Client initialized (without API creds)")
    
    print("\n" + "─" * 70)
    print("STEP 2: Deriving User API Credentials...")
    print("─" * 70)
    print("This will create or retrieve your API key...")
    
    # This is the key method from the official docs
    # It creates new credentials or retrieves existing ones
    api_creds = client.create_or_derive_api_creds()
    
    print("\n" + "═" * 70)
    print("✅ SUCCESS! USER API CREDENTIALS GENERATED")
    print("═" * 70)
    
    print(f"\nAPI Key:        {api_creds.api_key}")
    print(f"API Secret:     {api_creds.api_secret}")
    print(f"API Passphrase: {api_creds.api_passphrase}")
    
    print("\n" + "═" * 70)
    print("NEXT STEPS:")
    print("═" * 70)
    print("\n1. Update your .env file with THESE credentials:")
    print(f"\n   POLY_API_KEY={api_creds.api_key}")
    print(f"   POLY_API_SECRET={api_creds.api_secret}")
    print(f"   POLY_API_PASSPHRASE={api_creds.api_passphrase}")
    
    print("\n2. Keep your Private Key:")
    print(f"   POLY_PRIVATE_KEY={private_key[:6]}...{private_key[-4:]}")
    
    if sig_type == 2:
        print(f"\n3. Keep your Funder Address (Magic Link):")
        print(f"   POLY_FUNDER_ADDRESS={funder}")
    else:
        print(f"\n3. Remove POLY_FUNDER_ADDRESS (you're using EOA/MetaMask)")
    
    print("\n4. Test the connection:")
    print("   python test_api_connection.py")
    
    print("\n" + "─" * 70)
    print("NOTE: These are USER API credentials (for trading)")
    print("NOT Builder API credentials (those are for order attribution)")
    print("─" * 70)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nPossible causes:")
    print("1. Your private key is invalid")
    print("2. Network connection issues")
    print("3. Your wallet needs to be registered on Polymarket first")
    print("\nTry accessing https://polymarket.com/ and connect your wallet first")

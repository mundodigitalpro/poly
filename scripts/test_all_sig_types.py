#!/usr/bin/env python3
"""
Test ALL signature types with proper funder configuration
Following: https://docs.polymarket.com/developers/CLOB/authentication
"""
import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType
from eth_account import Account

load_dotenv()

host = "https://clob.polymarket.com"
chain_id = 137
private_key = os.getenv("POLY_PRIVATE_KEY")
api_key = os.getenv("POLY_API_KEY")
api_secret = os.getenv("POLY_API_SECRET")
api_passphrase = os.getenv("POLY_API_PASSPHRASE")
funder_from_env = os.getenv("POLY_FUNDER_ADDRESS")

# Derive address from private key
account = Account.from_key(private_key)
derived_address = account.address

api_creds = ApiCreds(
    api_key=api_key,
    api_secret=api_secret,
    api_passphrase=api_passphrase,
)

print("=" * 70)
print("COMPREHENSIVE SIGNATURE TYPE TEST")
print("=" * 70)
print(f"\nDerived address (from private key): {derived_address}")
print(f"Funder address (from .env):         {funder_from_env}")
print(f"API Key:                             {api_key}")
print("")

# Test all combinations
test_configs = [
    # For EOA wallets (MetaMask)
    {
        "name": "EOA (sig_type=0, funder=derived_address)",
        "signature_type": 0,
        "funder": derived_address
    },
    # For smart contract wallets with proxy
    {
        "name": "Proxy Wallet (sig_type=1, funder=env funder)",
        "signature_type": 1,
        "funder": funder_from_env
    },
    # For Gnosis Safe / magic link
    {
        "name": "Gnosis Safe (sig_type=2, funder=env funder)",
        "signature_type": 2,
        "funder": funder_from_env
    },
]

for i, config in enumerate(test_configs, 1):
    print(f"\n{'═' * 70}")
    print(f"TEST {i}/{len(test_configs)}: {config['name']}")
    print(f"{'═' * 70}")
    print(f"  signature_type = {config['signature_type']}")
    print(f"  funder = {config['funder']}")
    print("")
    
    try:
        client = ClobClient(
            host=host,
            chain_id=chain_id,
            key=private_key,
            creds=api_creds,
            signature_type=config['signature_type'],
            funder=config['funder']
        )
        
        print(f"✓ Client initialized")
        
        # Try balance check
        try:
            balance = client.get_balance_allowance(
                params=BalanceAllowanceParams(
                    asset_type=AssetType.COLLATERAL,
                    signature_type=config['signature_type']
                )
            )
            print( f"\n🎉 ✅ SUCCESS!")
            print(f"{'─' * 70}")
            print(f"Balance: {balance}")
            print(f"{'─' * 70}")
            print(f"\n🔧 WORKING CONFIGURATION:")
            print(f"   signature_type = {config['signature_type']}")
            print(f"   funder = {config['funder']}")
            print(f"\n📝 Update poly_client.py to use these values")
            break
            
        except Exception as e:
            if "401" in str(e):
                print(f"❌ 401 Unauthorized - API creds don't work with this config")
            else:
                print(f"❌ Error: {e}")
    
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")

else:
    print(f"\n{'═' * 70}")
    print(f"❌ NONE OF THE CONFIGURATIONS WORKED")
    print(f"{'═' * 70}")
    print(f"\nThis suggests the API credentials themselves are invalid.")
    print( f"\nNext steps:")
    print(f"1. Double-check you're using the CORRECT wallet in Polymarket")
    print(f"2. Visit https://polymarket.com/ and connect your wallet")
    print(f"3. Make sure the private key in .env matches that wallet")
    print(f"4. Run: python generate_user_api_keys.py")

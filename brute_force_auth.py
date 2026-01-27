
import os
import logging
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

host = "https://clob.polymarket.com"
chain_id = 137
key = os.getenv("POLY_API_KEY").strip()
secret = os.getenv("POLY_API_SECRET").strip()
passphrase = os.getenv("POLY_API_PASSPHRASE").strip()
private_key = os.getenv("POLY_PRIVATE_KEY").strip()
proxy_funder = os.getenv("POLY_FUNDER_ADDRESS").strip()

creds = ApiCreds(api_key=key, api_secret=secret, api_passphrase=passphrase)

combinations = [
    {"name": "EOA (Sig=0, No Funder)", "sig": 0, "funder": None},
    {"name": "Proxy 1 (Sig=1, Funder=Proxy)", "sig": 1, "funder": proxy_funder},
    {"name": "Proxy 2 (Sig=2, Funder=Proxy)", "sig": 2, "funder": proxy_funder},
    # Edge case: Maybe keys are for Signer but we use incorrect sig?
    {"name": "EOA forcing Proxy Funder (Sig=0, Funder=Proxy)", "sig": 0, "funder": proxy_funder},
]

print("Starting Brute Force Auth Check...")
print(f"Proxy Address: {proxy_funder}")
print(f"Signer Key Starts: {private_key[:6]}")
print("-" * 60)

for combo in combinations:
    print(f"Testing: {combo['name']}...")
    try:
        funder_val = combo['funder'] if combo['funder'] else private_key # client often needs some funder param or defaults
        # But for sig=0 better to rely on internal default or passing PK as funder behaves like EOA in some versions
        
        client = ClobClient(
            host=host,
            key=private_key,
            chain_id=chain_id,
            creds=creds,
            signature_type=combo['sig'],
            funder=combo['funder'] if combo['funder'] else private_key
        )
        
        # Try to fetch balance
        try:
             # We test getting balance for COLLATERAL
             # We must pass the SAME signature type to the params in recent versions
             bal = client.get_balance_allowance(
                 params=BalanceAllowanceParams(
                     asset_type=AssetType.COLLATERAL,
                     signature_type=combo['sig']
                 )
             )
             print(f"SUCCESS! >>> Balance: {bal}")
             print(f"WINNING CONFIG: {combo}")
             break
        except Exception as e:
            print(f"FAILED request: {e}")

    except Exception as e:
        print(f"FAILED init: {e}")
    print("-" * 60)

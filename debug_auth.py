
import os
from dotenv import load_dotenv
from eth_account import Account

load_dotenv()

pk = os.getenv("POLY_PRIVATE_KEY")
if not pk:
    print("No Private Key found.")
    exit()

if not pk.startswith("0x"):
    pk = "0x" + pk

try:
    account = Account.from_key(pk)
    print(f"Private Key format: Valid")
    print(f"Derived Address (Signer): {account.address}")
except Exception as e:
    print(f"Error deriving address: {e}")

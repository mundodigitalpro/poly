
import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType
import inspect

load_dotenv()

print("\nClient Methods:")
try:
    print([m for m in dir(client) if 'key' in m or 'create' in m])
except Exception as e:
    print(e)

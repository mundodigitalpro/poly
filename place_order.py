#!/usr/bin/env python3
"""
Place a test order on Polymarket
"""
import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs, PartialCreateOrderOptions
from py_clob_client.order_builder.constants import BUY

load_dotenv()

# Configuration
TOKEN_ID = "94192784911459194325909253314484842244405314804074606736702592885535642919725"
MARKET_QUESTION = "Will the next Prime Minister of Hungary be Péter Magyar?"
PRICE = 0.52  # Precio al que queremos comprar
SIZE = 2  # 2 shares ≈ $1

print("=" * 60)
print("POLYMARKET - TEST ORDER")
print("=" * 60)
print()
print(f"📊 Market: {MARKET_QUESTION}")
print(f"🎯 Side: BUY (YES)")
print(f"💰 Price: ${PRICE}")
print(f"📦 Size: {SIZE} shares")
print(f"💵 Total: ~${PRICE * SIZE:.2f}")
print()

# Initialize client
creds = ApiCreds(
    api_key=os.getenv('POLY_API_KEY'),
    api_secret=os.getenv('POLY_API_SECRET'),
    api_passphrase=os.getenv('POLY_API_PASSPHRASE'),
)

client = ClobClient(
    host='https://clob.polymarket.com',
    chain_id=137,
    key=os.getenv('POLY_PRIVATE_KEY'),
    creds=creds,
    signature_type=2,
    funder=os.getenv('POLY_FUNDER_ADDRESS')
)

print("✓ Client initialized")
print()

# Get market info
print("Fetching market info...")
try:
    book = client.get_order_book(TOKEN_ID)
    print(f"✓ Order book retrieved")
    
    asks = getattr(book, 'asks', [])
    bids = getattr(book, 'bids', [])
    
    if asks:
        best_ask = asks[0]
        print(f"  Best ASK (sell offers): ${best_ask.price}")
    if bids:
        best_bid = bids[0]
        print(f"  Best BID (buy offers): ${best_bid.price}")
        
except Exception as e:
    print(f"⚠ Could not get orderbook: {e}")

print()
print("-" * 60)
print("PLACING ORDER...")
print("-" * 60)

try:
    # Create order args
    order_args = OrderArgs(
        token_id=TOKEN_ID,
        price=PRICE,
        size=SIZE,
        side=BUY,
    )
    
    # Create options
    options = PartialCreateOrderOptions(
        tick_size="0.01",
        neg_risk=False,
    )
    
    # Place order
    result = client.create_and_post_order(order_args, options)
    
    print()
    print("🎉 ORDER PLACED SUCCESSFULLY!")
    print(f"   Result: {result}")
    print()
    
    # Check open orders
    print("Checking open orders...")
    orders = client.get_orders()
    print(f"   Open orders: {len(orders)}")
    for order in orders[:3]:
        print(f"   - {order}")
    
except Exception as e:
    error_str = str(e).lower()
    print(f"❌ Error: {e}")
    
    if "balance" in error_str or "insufficient" in error_str or "allowance" in error_str:
        print()
        print("💡 Parece que no tienes suficiente balance USDC.")
        print("   Deposita fondos en tu wallet de Polymarket primero:")
        print(f"   https://polygonscan.com/address/{os.getenv('POLY_FUNDER_ADDRESS')}")
    elif "invalid signature" in error_str:
        print()
        print("💡 Error de firma. Esto puede ocurrir con Magic Link.")
        print("   Intenta regenerar las API keys: python generate_user_api_keys.py")

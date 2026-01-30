#!/usr/bin/env python3
"""
Verify wallet address matches between private key and funder
"""
import os
from dotenv import load_dotenv
from eth_account import Account

load_dotenv()

private_key = os.getenv("POLY_PRIVATE_KEY")
funder_from_env = os.getenv("POLY_FUNDER_ADDRESS")

print("=" * 70)
print("WALLET ADDRESS VERIFICATION")
print("=" * 70)

# Derive address from private key
account = Account.from_key(private_key)
derived_address = account.address

print(f"\nPrivate Key: {private_key[:6]}...{private_key[-4:]}")
print(f"Derived Address (from private key): {derived_address}")
print(f"Funder Address (from .env):         {funder_from_env}")

print("\n" + "─" * 70)
if derived_address.lower() == funder_from_env.lower():
    print("✅ MATCH: Addresses match! (EOA wallet)")
    print("\nYou're using a regular wallet (MetaMask-style).")
    print("You should NOT need POLY_FUNDER_ADDRESS in your .env")
    print("\nRecommendation: Remove POLY_FUNDER_ADDRESS from .env")
else:
    print("❌ MISMATCH: Addresses don't match!")
    print("\nThis means you're using a Smart Contract wallet (Magic Link/Gnosis Safe)")
    print(f"\n  Your signing key: {derived_address}")
    print(f"  Your funding address (proxy): {funder_from_env}")
    print("\nThis is NORMAL for Magic Link users.")
    print("The private key is for SIGNING, the funder is where FUNDS are stored.")
print("─" * 70)

# Additional check
print("\n" + "═" * 70)
print("IMPORTANT: API Key Wallet Association")
print("═" * 70)
print("\nThe API credentials were generated FROM the private key:")
print(f"  {private_key[:6]}...{private_key[-4:]}")
print(f"\nWhich derives to wallet address:")
print(f"  {derived_address}")
print(f"\nIf you want to use the funder address:")
print(f"  {funder_from_env}")
print(f"\nYou might need to:")
print(f"1. Use signature_type=2")
print(f"2. Make sure the private key is the SIGNER for that funder address")
print("═" * 70)

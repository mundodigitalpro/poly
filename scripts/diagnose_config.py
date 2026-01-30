#!/usr/bin/env python3
"""
Diagnostic script to check API key configuration
"""
import os
from dotenv import load_dotenv

print("=" * 60)
print("POLYMARKET API CONFIGURATION DIAGNOSTIC")
print("=" * 60)

# Check if .env file exists
if os.path.exists('.env'):
    print("✓ .env file found")
else:
    print("✗ .env file NOT found")
    exit(1)

load_dotenv()

# Check each required variable
required_vars = {
    'POLY_API_KEY': 'API Key',
    'POLY_API_SECRET': 'API Secret',
    'POLY_API_PASSPHRASE': 'API Passphrase',
}

optional_vars = {
    'POLY_PRIVATE_KEY': 'Private Key (needed for trading)',
    'POLY_FUNDER_ADDRESS': 'Funder Address (for Magic Link/Proxy wallets)',
}

print("\n--- REQUIRED CREDENTIALS ---")
all_good = True
for var, desc in required_vars.items():
    value = os.getenv(var)
    if value and value != f"your_{var.lower().replace('poly_', '')}":
        print(f"✓ {desc}: Set (length={len(value)})")
    else:
        print(f"✗ {desc}: NOT SET or placeholder")
        all_good = False

print("\n--- OPTIONAL CREDENTIALS ---")
for var, desc in optional_vars.items():
    value = os.getenv(var)
    if value and value not in [f"your_{var.lower().replace('poly_', '')}", ""]:
        if var == 'POLY_PRIVATE_KEY' and not value.startswith('0x'):
            print(f"⚠ {desc}: Set but INVALID (must start with 0x)")
        else:
            print(f"✓ {desc}: Set (length={len(value)})")
    else:
        print(f"- {desc}: Not set")

print("\n--- ANALYSIS ---")
if not all_good:
    print("❌ Configuration is INCOMPLETE")
    print("\nACTION REQUIRED:")
    print("1. Go to https://polymarket.com/settings?tab=builder")
    print("2. Under 'Project Keys', click 'Create API Key'")
    print("3. Copy the API Key, Secret, and Passphrase")
    print("4. Update your .env file with these values")
else:
    print("✓ All required credentials are set")
    print("\nPossible issues:")
    print("1. API Key might be from the wrong section:")
    print("   - ❌ DON'T use 'API Keys' (these are old/different)")
    print("   - ✓ USE 'Project Keys' from Builder tab")
    print("2. Signature type mismatch:")
    funder = os.getenv('POLY_FUNDER_ADDRESS')
    if funder:
        print("   - You have POLY_FUNDER_ADDRESS set (signature_type=2)")
        print("   - This is for Magic Link / Gnosis Safe wallets")
    else:
        print("   - No POLY_FUNDER_ADDRESS (signature_type=0)")
        print("   - This is for regular MetaMask/EOA wallets")
        print("   - If you use Magic Link, you NEED to set POLY_FUNDER_ADDRESS")

print("=" * 60)

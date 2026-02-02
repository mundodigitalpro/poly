# Read-Only Diagnostic Test Report
Date: Mon Feb  2 16:47:17 CET 2026

## Environment & Config Diagnosis
```bash
venv/bin/python scripts/diagnose_config.py
```
### Result:
```
============================================================
POLYMARKET API CONFIGURATION DIAGNOSTIC
============================================================
✓ .env file found

--- REQUIRED CREDENTIALS ---
✓ API Key: Set (length=36)
✓ API Secret: Set (length=44)
✓ API Passphrase: Set (length=64)

--- OPTIONAL CREDENTIALS ---
✓ Private Key (needed for trading): Set (length=66)
✓ Funder Address (for Magic Link/Proxy wallets): Set (length=42)

--- ANALYSIS ---
✓ All required credentials are set

Possible issues:
1. API Key might be from the wrong section:
   - ❌ DON'T use 'API Keys' (these are old/different)
   - ✓ USE 'Project Keys' from Builder tab
2. Signature type mismatch:
   - You have POLY_FUNDER_ADDRESS set (signature_type=2)
   - This is for Magic Link / Gnosis Safe wallets
============================================================
```

## Wallet Verification
```bash
venv/bin/python scripts/verify_wallet.py
```
### Result:
```
======================================================================
WALLET ADDRESS VERIFICATION
======================================================================

Private Key: 0x67d4...0168
Derived Address (from private key): 0x54BDc4E70Db9F57C1b6Fb44Dc09AfEdc4981D682
Funder Address (from .env):         0x65c34ed362a0af863c3e88fbb3f3ebaed464b5e5

──────────────────────────────────────────────────────────────────────
❌ MISMATCH: Addresses don't match!

This means you're using a Smart Contract wallet (Magic Link/Gnosis Safe)

  Your signing key: 0x54BDc4E70Db9F57C1b6Fb44Dc09AfEdc4981D682
  Your funding address (proxy): 0x65c34ed362a0af863c3e88fbb3f3ebaed464b5e5

This is NORMAL for Magic Link users.
The private key is for SIGNING, the funder is where FUNDS are stored.
──────────────────────────────────────────────────────────────────────

══════════════════════════════════════════════════════════════════════
IMPORTANT: API Key Wallet Association
══════════════════════════════════════════════════════════════════════

The API credentials were generated FROM the private key:
  0x67d4...0168

Which derives to wallet address:
  0x54BDc4E70Db9F57C1b6Fb44Dc09AfEdc4981D682

If you want to use the funder address:
  0x65c34ed362a0af863c3e88fbb3f3ebaed464b5e5

You might need to:
1. Use signature_type=2
2. Make sure the private key is the SIGNER for that funder address
══════════════════════════════════════════════════════════════════════
```

## Bot Status
```bash
bash scripts/status_bot.sh
```
### Result:
```
================================================================================
ESTADO DE LOS BOTS POLYMARKET
================================================================================

🤖 Bot Principal (main_bot.py)
-------------------------------------------
Estado: ❌ DETENIDO

📱 Bot de Telegram (telegram_bot.py)
-------------------------------------------
Estado: ✅ CORRIENDO
PID: 693921
Iniciado: Mon Feb  2 13:42:02 2026
CPU: 0.0%
Memoria: 0.5%

💼 Posiciones Actuales
-------------------------------------------
Posiciones abiertas: 5

📋 Últimas Actividades (últimas 5 líneas de log)
-------------------------------------------
No se encontraron archivos de log

⚙️  Configuración Actual
-------------------------------------------
Modo dry_run: true
WebSocket: 
Concurrent orders: 
Min days to resolve: 2 días

================================================================================
COMANDOS ÚTILES
================================================================================

Ver logs en tiempo real:
  tail -f logs/bot_monitor_*.log

Reiniciar bots:
  bash scripts/restart_bot.sh

Detener bots:
  bash scripts/stop_bot.sh

Ejecutar diagnóstico de mercados:
  python tools/diagnose_market_filters.py

================================================================================
```

## Position Analysis
```bash
venv/bin/python tools/analyze_positions.py
```
### Result:
```
📡 Fetching live prices from Polymarket...

==============================================================================================================
📊 POSITION ANALYSIS REPORT (LIVE PRICES)
   Generated: 2026-02-02 16:47:18
==============================================================================================================
   Positions: 5 | Live prices: 5/5

   💰 Unrealized P&L: $0.0037
   📈 Winning: 1 | 📉 Losing: 4

   🎯 Closest to TP: 5017830659580006... (+6.8%)
   ⚠️  Closest to SL: 4643411015584103... (+8.7%)

--------------------------------------------------------------------------------------------------------------
Token                Entry    Now     TP     SL      P&L     →TP     →SL Status
--------------------------------------------------------------------------------------------------------------
● 5017830659580006...  0.610  0.640  0.683  0.549    +4.9%   +6.8%  +14.2% 
● 9173793195407946...  0.683  0.682  0.765  0.615    -0.1%  +12.2%   +9.9% 
● 4294579598662620...  0.800  0.796  0.920  0.704    -0.5%  +15.6%  +11.6% 
● 4642980931570803...  0.740  0.730  0.851  0.651    -1.4%  +16.6%  +10.8% 
● 4643411015584103...  0.690  0.680  0.773  0.621    -1.4%  +13.6%   +8.7% 
--------------------------------------------------------------------------------------------------------------

Legend: ● = Live price | ○ = Entry price (API unavailable)
==============================================================================================================
```

## Simulate Fills
```bash
venv/bin/python tools/simulate_fills.py
```
### Result:
```

============================================================
  SIMULATING TP/SL FILLS - 2026-02-02 16:47:18
============================================================
Positions: 5

Position: 917379319540...
  Entry: $0.6830 | TP: $0.7650 | SL: $0.6147
  Current: $0.6820 | P&L: -0.15% ($-0.0004) 🔴
  Status: HOLDING
  Distance: TP +12.16% | SL +9.87%

Position: 464341101558...
  Entry: $0.6900 | TP: $0.7728 | SL: $0.6210
  Current: $0.6800 | P&L: -1.45% ($-0.0036) 🔴
  Status: HOLDING
  Distance: TP +13.65% | SL +8.68%

Position: 464298093157...
  Entry: $0.7400 | TP: $0.8510 | SL: $0.6512
  Current: $0.7300 | P&L: -1.35% ($-0.0034) 🔴
  Status: HOLDING
  Distance: TP +16.58% | SL +10.79%

Position: 501783065958...
  Entry: $0.6100 | TP: $0.6832 | SL: $0.5490
  Current: $0.6400 | P&L: +4.92% ($+0.0123) 🟢
  Status: HOLDING
  Distance: TP +6.75% | SL +14.22%

Position: 429457959866...
  Entry: $0.8000 | TP: $0.9200 | SL: $0.7040
  Current: $0.7960 | P&L: -0.50% ($-0.0013) 🔴
  Status: HOLDING
  Distance: TP +15.58% | SL +11.56%

============================================================
SUMMARY
============================================================
Take Profits: 0
Stop Losses: 0
No fills triggered yet.

```

## Market Filters Diagnosis (Limit 10)
```bash
venv/bin/python tools/diagnose_market_filters.py --show-all --limit 10
```
### Result:
```
usage: diagnose_market_filters.py [-h] [--show-all] [--csv]
diagnose_market_filters.py: error: unrecognized arguments: --limit 10
```

## Whale Tracker Leaderboard
```bash
venv/bin/python tools/whale_tracker.py --leaderboard
```
### Result:
```
======================================================================
POLYMARKET WHALE TRACKER
======================================================================
Min whale size: $500


TOP TRADERS (from 100 trades):
----------------------------------------------------------------------
#   Name                       Volume   Trades        Avg      B/S
----------------------------------------------------------------------
1   Trading4Fridge       $       932        1 $      932 0/    1
2   Roundfaced           $       148        1 $      148 1/    0
3   0x31D3D09D2B8bD1B9   $       108        1 $      108 0/    1
4   pompome              $       100        1 $      100 0/    1
5   0x1979ae6B7E6534dE   $        91        1 $       91 1/    0
6   Poissonic            $        64        1 $       64 1/    0
7   swisstony            $        60        2 $       30 2/    0
8   0xaeA5496f171C7053   $        51        2 $       25 0/    2
9   NovaRays             $        50        1 $       50 0/    1
10  Anonymous            $        50        1 $       50 1/    0
11  suraxy               $        50        1 $       50 1/    0
12  MEV-PM               $        47        1 $       47 1/    0
13  macrosteaks          $        42        1 $       42 1/    0
14  Yangmoney            $        40        1 $       40 1/    0
15  0xdbdd45150249e229   $        38        1 $       38 1/    0
16  0xfAfCAC925217d6F7   $        35        1 $       35 0/    1
17  randyomar            $        29        3 $       10 3/    0
18  suryakun             $        28        1 $       28 1/    0
19  0x51518622c24dF7F8   $        24        1 $       24 1/    0
20  jjajjajajja          $        24        1 $       24 1/    0
```


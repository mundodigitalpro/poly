# Trending Whales Guide

Cómo encontrar y trackear traders trending de Polymarket usando datos de social media.

## 🎯 Objetivo

Descubrir wallets de traders que están siendo mencionados en X.com (Twitter), Reddit, y otras plataformas para agregarlos a tu lista de tracked wallets.

---

## 🛠️ Herramientas Disponibles

### 1. `find_trending_whales.py` - Trending basado en curación

Busca traders conocidos de social media y correlaciona con datos de Polymarket.

**Uso:**
```bash
# Buscar en todas las plataformas
python tools/find_trending_whales.py

# Solo Twitter
python tools/find_trending_whales.py --platform twitter

# Solo Reddit
python tools/find_trending_whales.py --platform reddit

# Exportar top 5 a config snippet
python tools/find_trending_whales.py --export config --top 5

# Exportar a JSON
python tools/find_trending_whales.py --export json

# Ambos
python tools/find_trending_whales.py --export both --top 10
```

**Output ejemplo:**
```
🔥 TRENDING WHALES (Social Media + Polymarket Data)
==================================================================================
Rank   Name                 Mentions   Volume       Trades   Last Active
----------------------------------------------------------------------------------
1      Theo4                23         $125,450     342      2026-02-01
2      Fredi9999            17         $98,230      287      2026-02-01
3      zubairpolymarket     11         $45,670      156      2026-02-01
4      domer                10         $38,920      134      2026-01-31
5      Taran                9          $32,100      98       2026-02-01
==================================================================================

📋 Top Wallet Addresses:
1. 0xABC123456789...
   Theo4 (23 mentions, $125,450 volume)
2. 0xDEF987654321...
   Fredi9999 (17 mentions, $98,230 volume)

📝 CONFIG.JSON SNIPPET (Copy to config.json):
==================================================================================
{
  "whale_copy_trading": {
    "tracked_wallets": {
      "enabled": true,
      "wallets": [
        "0xABC123456789...",
        "0xDEF987654321...",
        "0x111222333444..."
      ],
      "priority_over_ranking": true,
      "bypass_score_requirement": false
    }
  }
}
```

---

### 2. `live_social_search.py` - Búsqueda en tiempo real (Template)

Template para búsqueda en tiempo real usando APIs de Twitter y Reddit.

**Uso:**
```bash
# Buscar en ambas plataformas
python tools/live_social_search.py

# Buscar query específica
python tools/live_social_search.py --query "best polymarket trader"

# Solo Twitter
python tools/live_social_search.py --platform twitter --days 7

# Solo Reddit
python tools/live_social_search.py --platform reddit --days 30
```

**Output ejemplo:**
```
🔍 LIVE SOCIAL MEDIA SEARCH - Polymarket Traders
======================================================================
Query: polymarket trader
Lookback: 7 days
Platform: both

🐦 Searching X.com for: 'polymarket trader' (last 7 days)
----------------------------------------------------------------------
  ✅ @Theo4: 12 mentions
     Context: Top trader on NPR article, +$22M lifetime
  ✅ @Fredi9999: 10 mentions
     Context: Top trader on leaderboard

🔴 Searching Reddit r/polymarket for: 'polymarket' (last 7 days)
----------------------------------------------------------------------
  ✅ u/Theo4: 15 mentions
     - r/polymarket: Who are the best traders to follow?
     - r/polymarket: Theo4 just made $500k on Trump market

📊 AGGREGATED MENTIONS
======================================================================
1. Theo4: 27 total mentions
2. Fredi9999: 18 total mentions
3. domer: 10 total mentions
```

---

### 3. `find_whale_wallet.py` - Buscar wallet específica

Una vez identificado el nombre del trader, encontrar su wallet.

**Uso:**
```bash
# Buscar wallet de Theo4
python tools/find_whale_wallet.py --name "Theo4"

# Buscar en market específico
python tools/find_whale_wallet.py --market "Trump"

# Ver top traders por volumen
python tools/find_whale_wallet.py --top 10
```

---

## 🎯 Flujo de Trabajo Recomendado

### Paso 1: Identificar Trending Traders
```bash
python tools/find_trending_whales.py --platform all
```

### Paso 2: Verificar Wallets
```bash
# Para cada trader trending
python tools/find_whale_wallet.py --name "Theo4"
python tools/find_whale_wallet.py --name "Fredi9999"
```

### Paso 3: Exportar Config
```bash
python tools/find_trending_whales.py --export config --top 5
```

### Paso 4: Copiar a config.json
```bash
# Abrir config.json y pegar el snippet en whale_copy_trading section
vim config.json  # o nano, code, etc.
```

### Paso 5: Activar Tracking
```json
{
  "whale_copy_trading": {
    "enabled": true,  // ← Activar
    "tracked_wallets": {
      "enabled": true,  // ← Activar
      "wallets": [
        "0xABC123...",  // Wallets del paso 3
        "0xDEF456..."
      ]
    }
  }
}
```

### Paso 6: Verificar
```bash
# Test en dry-run
python tools/test_whale_copy.py --test-profiler

# Debería mostrar ⭐ TRACKED en el leaderboard
```

---

## 📊 Fuentes de Datos

### Traders Conocidos (Curados)

**Según investigación de NPR, DataWallet, X.com:**

| Trader | Lifetime P&L | Fuente | Social |
|--------|--------------|---------|--------|
| **Theo4** | +$22M | NPR | @Theo4 |
| **Fredi9999** | +$22M | NPR | - |
| **zubairpolymarket** | Unknown | X.com | @zubairpolymarket |
| **khalidh** | Unknown | X.com | @khalidh |
| **domer** | Unknown | Reddit | u/domer |
| **Taran** | Unknown | X.com | @taranmayer |

### Dónde Buscar Manualmente

**X.com (Twitter):**
- Search: "polymarket trader"
- Search: "polymarket whale"
- Follow: @polymarket official account
- Check replies to popular markets

**Reddit:**
- r/polymarket
- r/prediction_markets
- Search: "best trader", "whale", "leaderboard"

**Medium/Blogs:**
- Search: "Polymarket trading strategy"
- MONOLITH articles

**Polymarket Forum:**
- https://polymarket.com/community (si existe)

---

## 🔧 Habilitar Búsqueda en Tiempo Real (Opcional)

Para habilitar búsqueda real-time con APIs:

### Twitter API Setup

1. **Crear app en Twitter:**
   - Ir a: https://developer.twitter.com/
   - Create App
   - Get API Keys

2. **Instalar dependencias:**
   ```bash
   pip install tweepy
   ```

3. **Agregar credenciales a .env:**
   ```env
   TWITTER_API_KEY=your_api_key
   TWITTER_API_SECRET=your_api_secret
   TWITTER_ACCESS_TOKEN=your_access_token
   TWITTER_ACCESS_SECRET=your_access_secret
   ```

4. **Descomentar código en `live_social_search.py`:**
   ```python
   # En live_social_search.py, buscar línea:
   # # UNCOMMENT FOR REAL TWITTER API
   # import tweepy
   # auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
   # ...
   ```

### Reddit API Setup

1. **Crear app en Reddit:**
   - Ir a: https://reddit.com/prefs/apps
   - Create app
   - Copy credentials

2. **Instalar dependencias:**
   ```bash
   pip install praw
   ```

3. **Agregar credenciales a .env:**
   ```env
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   REDDIT_USER_AGENT='polymarket-whale-tracker v1.0'
   ```

4. **Descomentar código en `live_social_search.py`:**
   ```python
   # En live_social_search.py, buscar línea:
   # # UNCOMMENT FOR REAL REDDIT API
   # import praw
   # reddit = praw.Reddit(...)
   # ...
   ```

---

## 💡 Tips y Best Practices

### 1. Verificar Siempre el Volumen
No solo confíes en mentions - verifica que el trader tenga volumen real:
```bash
python tools/find_whale_wallet.py --name "Trader" | grep "Volume"
```

### 2. Cross-Reference
Verifica el trader en múltiples fuentes:
- X.com mentions
- Reddit discussions
- Polymarket leaderboard
- Recent trades

### 3. Actualizar Regularmente
Traders trending cambian cada semana:
```bash
# Ejecutar cada semana
python tools/find_trending_whales.py --export config --top 5
```

### 4. Start Small
Empieza trackeando 2-3 traders, no 20:
```json
"wallets": [
  "0xWallet1",  // Theo4 - probado
  "0xWallet2"   // Fredi9999 - probado
]
```

### 5. Monitor Performance
Después de 1-2 semanas, evalúa:
```bash
python tools/test_whale_copy.py --live-demo
# Ver si las wallets tracked están generando buenos signals
```

---

## 🎁 Ejemplos Prácticos

### Ejemplo 1: Quick Setup (5 minutos)

```bash
# 1. Encontrar trending
python tools/find_trending_whales.py --export config --top 3

# 2. Copiar output al clipboard

# 3. Pegar en config.json
# Editar whale_copy_trading.tracked_wallets section

# 4. Activar
# enabled: true

# 5. Verificar
python tools/test_whale_copy.py --test-profiler
```

### Ejemplo 2: Research Profundo (30 minutos)

```bash
# 1. Buscar menciones
python tools/live_social_search.py --days 30

# 2. Para cada trader mencionado
python tools/find_whale_wallet.py --name "Trader1"
python tools/find_whale_wallet.py --name "Trader2"

# 3. Verificar en leaderboard
python tools/whale_tracker.py --leaderboard

# 4. Analizar volumen por market
python tools/find_whale_wallet.py --market "Trump"
python tools/find_whale_wallet.py --market "Bitcoin"

# 5. Seleccionar top 3-5 basado en:
#    - Social mentions (>10)
#    - Volume ($10k+)
#    - Recent activity (<7 days)
#    - Diversidad de markets (>10)

# 6. Agregar a config y testear
```

### Ejemplo 3: Monitoreo Continuo (Semanal)

```bash
#!/bin/bash
# weekly_whale_update.sh

echo "=== Weekly Whale Tracking Update ==="

# 1. Trending check
python tools/find_trending_whales.py > trending_$(date +%Y%m%d).txt

# 2. Current tracked wallets performance
python tools/test_whale_copy.py --test-profiler > profiler_$(date +%Y%m%d).txt

# 3. Compare and update if needed
# Review outputs and update config.json

echo "Reports saved"
```

---

## 📚 Referencias

**NPR Article (Top Traders):**
- https://www.npr.org/2026/01/17/nx-s1-5672615/kalshi-polymarket-prediction-market-boom-traders-slang-glossary

**DataWallet (Win Rates):**
- https://www.datawallet.com/crypto/top-polymarket-trading-strategies

**X.com Searches:**
- https://x.com/search?q=polymarket%20trader
- https://x.com/search?q=polymarket%20whale

**Reddit:**
- https://reddit.com/r/polymarket

---

## ✅ Checklist de Setup

- [ ] Ejecutar `find_trending_whales.py`
- [ ] Identificar top 3-5 traders
- [ ] Verificar wallets con `find_whale_wallet.py`
- [ ] Copiar wallets a `config.json`
- [ ] Activar `tracked_wallets.enabled: true`
- [ ] Testear con `test_whale_copy.py --test-profiler`
- [ ] Verificar ⭐ TRACKED marker en leaderboard
- [ ] Configurar monitoreo semanal

---

**Fecha:** 2026-02-01
**Versión:** 1.0

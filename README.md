# Polymarket Python Client

Cliente Python para trading en Polymarket via API.

## ✅ Estado

**Operativo** - Trading funcionando con Magic Link ✅
**Bot Autónomo (v0.13.0)** - En producción (develop branch) ✅
**🐋 Whale Copy Trading (v0.13.0)** - Core infrastructure completada, pending integration ⚙️

## 🚀 Inicio Rápido

### 1. Instalación

```bash
cd poly
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuración

```bash
cp .env.example .env
```

#### Para Magic Link (Gmail):

1. Ve a https://polymarket.com → Settings → Export Private Key
2. Copia la private key y la dirección de tu perfil

```env
POLY_API_KEY=auto_generado
POLY_API_SECRET=auto_generado
POLY_API_PASSPHRASE=auto_generado

POLY_PRIVATE_KEY=0x...tu_private_key
POLY_FUNDER_ADDRESS=0x...tu_direccion_perfil
```

### 3. Generar API Credentials

```bash
python generate_user_api_keys.py
```

## 📋 Comandos

```bash
# Ver estado de cuenta (orders/trades)
python poly_client.py --balance

# Listar mercados
python poly_client.py --limit 10

# Filtrar mercados
python poly_client.py --filter "Trump"

# Ver orderbook
python poly_client.py --book <TOKEN_ID>

# Monitoreo en tiempo real
python poly_client.py --book <TOKEN_ID> --monitor --interval 5

# Bot autónomo (single loop / dry run)
python main_bot.py --once

# Bot autónomo (loop continuo)
python main_bot.py
```

## 📈 Trading

Edita `place_order.py` con el mercado y precio deseado:

```bash
python place_order.py
```

## 🔑 Signature Types

| Tipo | Uso |
|------|-----|
| `signature_type=1` | **Magic Link** (Gmail/email) ← Lo más común |
| `signature_type=0` | MetaMask / Hardware wallets (EOA) |
| `signature_type=2` | Browser wallet proxy (raro) |

Notas rápidas:
- Magic Link requiere `POLY_FUNDER_ADDRESS` y usa `signature_type=1`.
- EOA/MetaMask no usa funder y usa `signature_type=0`.
- `poly_client.py` auto-detecta, pero en `place_order.py` verifica el `signature_type`.

## 🔧 Troubleshooting

### Error 401: Unauthorized
```bash
python generate_user_api_keys.py
```

### Error: Invalid Signature
Verifica que usas `signature_type=1` para Magic Link.

### Verificar configuración
```bash
python scripts/verify_wallet.py
python scripts/diagnose_config.py
python scripts/test_all_sig_types.py
```

## 🤖 Bot Autónomo (En Desarrollo)

Plan completo en `bot_plan.md` para un bot de trading 24/7:
- Monitoreo automático de mercados con filtros inteligentes
- Gestión de posiciones con TP/SL dinámico
- Sistema de scoring para selección de mejores mercados
- 10 protecciones de seguridad (blacklist temporal, daily loss limit, etc.)
- Persistencia de datos y stats tracking
- Rollout por fases: Dry run → Paper → Micro ($0.25) → Normal ($1.00)

**Estado**: Implementado (Beta v0.10.0) ✅ | Fase 2 completada ✅ | Extended Dry Run en progreso 🔄

Para iniciar el bot en modo simulación:
```bash
python main_bot.py
# O para una sola ejecución:
python main_bot.py --once
```

Ver también: `CLAUDE.md` y `GEMINI.md` para contexto técnico del proyecto.

## 🐋 Whale Copy Trading (v0.13.0)

Sistema de copy trading que sigue automáticamente a los top traders de Polymarket basándose en volumen de trading y actividad.

### Características Principales

- **Volume-Weighted Ranking**: Identifica top 20 whales basado en volumen, consistencia, diversidad y recencia
- **Real-Time Monitoring**: Polling cada 30s para detectar trades de whales whitelisted
- **11 Validaciones de Riesgo**: Checks exhaustivos antes de copiar cualquier trade
- **Whale Consensus**: Detecta cuando 3+ whales operan en el mismo market (señal fuerte)
- **Dual Mode**: Opera junto a la estrategia original del bot (configurable)

### Quick Start

```bash
# Ver leaderboard de whales
python tools/whale_tracker.py --leaderboard

# 🆕 Encontrar wallet de un trader específico
python tools/find_whale_wallet.py --name "Theo4"
python tools/find_whale_wallet.py --market "Trump"
python tools/find_whale_wallet.py --top 10

# Ver señales de copy trading
python tools/whale_tracker.py --signals

# Testear el sistema completo
python tools/test_whale_copy.py --live-demo

# Activar whale copy trading (editar config.json primero)
# "whale_copy_trading": { "enabled": true }
python main_bot.py  # (pending integration)
```

### Configuración

```json
{
  "whale_copy_trading": {
    "enabled": false,  // Activar manualmente cuando esté listo
    "mode": "hybrid",  // original + whale copy
    "tracked_wallets": {  // 🆕 Trackear wallets específicas
      "enabled": false,
      "wallets": [
        "0x123..."  // Agregar wallet address aquí
      ],
      "priority_over_ranking": true,  // Copiar siempre estas wallets
      "bypass_score_requirement": false  // Respetar score mínimo
    },
    "copy_rules": {
      "copy_position_size": 0.50,  // $0.50 por copy trade
      "max_copies_per_day": 10,
      "require_whale_score_above": 70
    },
    "risk_management": {
      "max_copy_allocation": 5.0,  // Max $5 en copy trades
      "stop_if_daily_loss": 2.0,    // Stop si pierde $2/día
      "exit_strategy": "hybrid"     // Follow whale + TP/SL
    }
  }
}
```

**🆕 Cómo encontrar wallets:**
1. Buscar por nombre: `python tools/find_whale_wallet.py --name "Theo4"`
2. Por market: `python tools/find_whale_wallet.py --market "Trump"`
3. Top traders: `python tools/find_whale_wallet.py --top 10`
4. Copiar wallet address del output
5. Agregar a `config.json` → `tracked_wallets.wallets`

### Módulos

- `bot/whale_profiler.py` - Volume-weighted ranking system (+ tracked wallets)
- `bot/whale_monitor.py` - Real-time signal detection
- `bot/whale_copy_engine.py` - Decision logic + execution
- `tools/test_whale_copy.py` - Testing framework
- `tools/find_whale_wallet.py` - 🆕 Wallet finder (by name/market)

### Estrategia de Selección

**Sin win-rate data** (no disponible en API), usamos heurísticas proxy:

1. **Volume Score (40%)**: Whales con >$10k volumen probablemente rentables
2. **Consistency (30%)**: Min 50 trades para validar actividad sostenida
3. **Diversity (20%)**: Trading en 20+ markets diferentes = expertise
4. **Recency (10%)**: Activo en últimas 24h = trader activo

### Risk Management (11 Checks)

Antes de copiar, el sistema valida:
1. ✅ Whale en whitelist (score >70)
2. ✅ Trade <10 minutos (freshness)
3. ✅ Solo BUY (configurable)
4. ✅ Size entre $500-$50k
5. ✅ Pasa market filters
6. ✅ Capital disponible
7. ✅ <10 copies hoy
8. ✅ <$5 allocation total
9. ✅ Min 3 markets diversification
10. ✅ Daily loss <$2
11. ✅ No blacklisted

### Exit Strategy

**Hybrid** (default): Follow whale + TP/SL backstop
- Monitor whale para detectar cuando vende → copiar la venta
- Backstop TP/SL si whale nunca vende
- Max hold: 7 días → auto-exit

### Documentación

- `docs/WHALE_COPY_TRADING_DESIGN.md` - Arquitectura completa (606 líneas)
- `docs/ESTRATEGIAS_REALES_2026.md` - Research backing (458 líneas)
- Top whales: +$22M lifetime (Theo4, Fredi9999 según NPR)

### Estado Actual

- ✅ **Phase 1 (Core Infrastructure)**: Completada
- ⏳ **Phase 2 (Integration)**: Pending - integración con main_bot.py
- ⏳ **Phase 3 (Testing)**: Pending - 20+ trades dry-run
- ⏳ **Phase 4 (Production)**: Pending - activación real

## 📁 Estructura

```
poly/
├── poly_client.py              # Cliente principal CLI
├── main_bot.py                 # Bot autónomo (loop principal)
├── place_order.py              # Script para órdenes manuales
├── auto_sell.py                # Bot de auto-venta con protecciones
├── config.json                 # Configuración del bot
│
├── bot/                        # Módulos core del bot
│   ├── config.py               # Carga de configuración
│   ├── gamma_client.py         # Cliente Gamma API (volumen/liquidez)
│   ├── logger.py               # Sistema de logging
│   ├── market_scanner.py       # Escaneo y scoring de mercados
│   ├── position_manager.py     # Gestión de posiciones
│   ├── strategy.py             # Lógica de estrategia (TP/SL)
│   ├── trader.py               # Ejecución de órdenes
│   ├── whale_service.py        # Integración whale tracking
│   ├── whale_profiler.py       # 🐋 Volume-weighted ranking
│   ├── whale_monitor.py        # 🐋 Real-time signal detection
│   └── whale_copy_engine.py    # 🐋 Copy trading logic
│
├── scripts/                    # Utilidades de setup
│   ├── generate_user_api_keys.py
│   ├── verify_wallet.py
│   ├── diagnose_config.py
│   └── test_all_sig_types.py
│
├── tools/                      # Herramientas de análisis
│   ├── whale_tracker.py        # Tracker de ballenas
│   ├── find_whale_wallet.py    # 🆕 Wallet finder (by name/market)
│   ├── test_whale_copy.py      # 🐋 Whale copy testing suite
│   ├── dutch_book_scanner.py   # Escaneo arbitraje YES/NO
│   ├── negrisk_scanner.py      # Escaneo multi-outcome
│   └── analyze_positions.py    # Análisis de riesgo
│
├── docs/                       # Documentación
│   ├── bot_plan.md             # Diseño del bot autónomo
│   ├── WHALE_COPY_TRADING_DESIGN.md  # 🐋 Arquitectura whale copy
│   ├── ESTRATEGIAS_REALES_2026.md    # 🐋 Research de estrategias
│   ├── proposals/              # Propuestas de features
│   └── team/                   # Docs del equipo AI
│
├── tests/                      # Tests unitarios (pytest)
├── data/                       # Datos runtime (positions, blacklist)
├── logs/                       # Logs diarios
│
├── README.md                   # Este archivo
├── CHANGELOG.md                # Historial de versiones
├── AGENTS.md                   # Memoria Codex
├── CLAUDE.md                   # Memoria Claude
├── GEMINI.md                   # Memoria Gemini
├── .env                        # Credenciales (NO commitear)
└── .env.example                # Plantilla
```

## ✅ Testing

Tests unitarios con pytest (estrategia y position manager):

```bash
pip install pytest
python -m pytest
```

## 🐳 Docker

```bash
docker-compose up --build -d
docker-compose logs -f
```

## 🔐 Seguridad

- **NUNCA** compartas tu private key
- **NUNCA** commitees `.env`
- Regenera credentials con `python generate_user_api_keys.py`

## 📚 Recursos

- [py-clob-client (GitHub)](https://github.com/Polymarket/py-clob-client)
- [Polymarket Docs](https://docs.polymarket.com/)

## 📝 Licencia

MIT

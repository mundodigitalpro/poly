# Polymarket Python Client

Cliente Python para trading en Polymarket via API.

## ✅ Estado

**Operativo** - Trading funcionando con Magic Link ✅  
**Bot Autónomo (Beta v0.10.0)** - Fase 2 (Integración y Testing) completada ✅

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
│   └── whale_service.py        # Integración whale tracking
│
├── scripts/                    # Utilidades de setup
│   ├── generate_user_api_keys.py
│   ├── verify_wallet.py
│   ├── diagnose_config.py
│   └── test_all_sig_types.py
│
├── tools/                      # Herramientas de análisis
│   ├── whale_tracker.py        # Tracker de ballenas
│   ├── dutch_book_scanner.py   # Escaneo arbitraje YES/NO
│   ├── negrisk_scanner.py      # Escaneo multi-outcome
│   └── analyze_positions.py    # Análisis de riesgo
│
├── docs/                       # Documentación
│   ├── bot_plan.md             # Diseño del bot autónomo
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

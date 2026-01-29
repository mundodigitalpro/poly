# Polymarket Python Client

Cliente Python para trading en Polymarket via API.

## ✅ Estado

**Operativo** - Trading funcionando con Magic Link ✅

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
# Ver estado de cuenta
python poly_client.py --balance

# Listar mercados
python poly_client.py --limit 10

# Filtrar mercados
python poly_client.py --filter "Trump"

# Ver orderbook
python poly_client.py --book <TOKEN_ID>

# Monitoreo en tiempo real
python poly_client.py --book <TOKEN_ID> --monitor --interval 5
```

## � Trading

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

## 🔧 Troubleshooting

### Error 401: Unauthorized
```bash
python generate_user_api_keys.py
```

### Error: Invalid Signature
Verifica que usas `signature_type=1` para Magic Link.

### Verificar configuración
```bash
python verify_wallet.py
python diagnose_config.py
```

## 🤖 Bot Autónomo (En Desarrollo)

Plan completo en `bot_plan.md` para un bot de trading 24/7:
- Monitoreo automático de mercados con filtros inteligentes
- Gestión de posiciones con TP/SL dinámico
- Sistema de scoring para selección de mejores mercados
- 10 protecciones de seguridad (blacklist temporal, daily loss limit, etc.)
- Persistencia de datos y stats tracking
- Rollout por fases: Dry run → Paper → Micro ($0.25) → Normal ($1.00)

**Estado**: Diseño completo ✅ | Implementación pendiente

Ver también: `CLAUDE.md` para contexto técnico del proyecto.

## 📁 Estructura

```
poly/
├── poly_client.py              # Cliente principal
├── place_order.py              # Script para órdenes manuales
├── auto_sell.py                # Bot de auto-venta con protecciones
├── generate_user_api_keys.py   # Genera API credentials
├── verify_wallet.py            # Verifica wallet
├── bot_plan.md                 # Plan detallado del bot autónomo
├── CLAUDE.md                   # Guía para Claude Code
├── .env                        # Credenciales (NO commitear)
├── .env.example                # Plantilla
├── Dockerfile                  # Docker
└── docker-compose.yml          # Docker Compose
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

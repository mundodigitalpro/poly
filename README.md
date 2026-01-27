# Polymarket Python Client

Cliente Python para interactuar con la API de Polymarket (CLOB - Central Limit Order Book).

## ✅ Estado

**Operativo** - Autenticación y consultas funcionando correctamente.

## 🚀 Inicio Rápido

### 1. Instalación

```bash
# Clonar y entrar al directorio
cd poly

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración

Copia el archivo de ejemplo y configura tus credenciales:

```bash
cp .env.example .env
```

#### Para usuarios de Magic Link (Gmail):

1. Ve a https://polymarket.com e inicia sesión con Gmail
2. Ve a Settings y busca "Export Private Key" o similar
3. Copia la private key que te muestra Magic Link
4. Tu wallet address (funder) es la que aparece en tu perfil

```env
# Credenciales generadas automáticamente (ver sección Troubleshooting)
POLY_API_KEY=tu_api_key
POLY_API_SECRET=tu_api_secret
POLY_API_PASSPHRASE=tu_api_passphrase

# Private Key del signer de Magic Link
POLY_PRIVATE_KEY=0x...

# Dirección de tu perfil (Proxy Wallet)
POLY_FUNDER_ADDRESS=0x...
```

### 3. Generar API Credentials

**IMPORTANTE**: Las API credentials se generan automáticamente desde tu private key:

```bash
python generate_user_api_keys.py
```

Esto mostrará las credenciales correctas para tu `.env`.

## 📋 Uso

### Ver estado de cuenta
```bash
python poly_client.py --balance
```

### Listar mercados populares
```bash
python poly_client.py --limit 10
```

### Filtrar mercados por texto
```bash
python poly_client.py --filter "Trump" --limit 5
python poly_client.py --filter "Bitcoin"
```

### Ver orderbook de un token
```bash
python poly_client.py --book <TOKEN_ID>
```

### Monitoreo en tiempo real
```bash
python poly_client.py --book <TOKEN_ID> --monitor --interval 5
```

## 🐳 Docker

```bash
# Construir e iniciar
docker-compose up --build -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

## 🔧 Troubleshooting

### Error 401: Unauthorized / Invalid API Key

**Causa**: Las API credentials no coinciden con tu wallet.

**Solución**:
```bash
# Regenerar credenciales
python generate_user_api_keys.py

# Copiar los valores mostrados a .env
# Probar
python poly_client.py --balance
```

### Magic Link: Arquitectura de Wallets

Con Magic Link (login con Gmail), tienes dos direcciones:

| Tipo | Descripción |
|------|-------------|
| **Signer** | Deriva de tu private key. Firma transacciones. |
| **Funder/Proxy** | Tu dirección de perfil. Contiene los fondos. |

Esto es **normal**. Configura:
- `POLY_PRIVATE_KEY` = Private key del signer
- `POLY_FUNDER_ADDRESS` = Dirección de tu perfil

### Verificar configuración
```bash
python verify_wallet.py
python diagnose_config.py
```

## 📁 Estructura del Proyecto

```
poly/
├── poly_client.py          # Cliente principal
├── .env                    # Credenciales (NO commitear)
├── .env.example            # Plantilla de credenciales
├── requirements.txt        # Dependencias Python
├── Dockerfile              # Contenedor Docker
├── docker-compose.yml      # Orquestación Docker
│
├── # Herramientas de diagnóstico
├── generate_user_api_keys.py   # Genera API credentials
├── verify_wallet.py            # Verifica wallet/private key
├── diagnose_config.py          # Verifica .env
├── test_all_sig_types.py       # Prueba configuraciones
│
└── # Documentación
    ├── README.md               # Este archivo
    └── CHANGELOG.md            # Historial de cambios
```

## 🔐 Seguridad

- **NUNCA** compartas tu private key
- **NUNCA** commitees el archivo `.env`
- Las API credentials son específicas de tu wallet
- Si sospechas que fueron comprometidas, regenera con `generate_user_api_keys.py`

## 📚 Recursos

- [Documentación oficial de Polymarket](https://docs.polymarket.com/)
- [Quickstart: First Order](https://docs.polymarket.com/quickstart/first-order)
- [Autenticación CLOB](https://docs.polymarket.com/developers/CLOB/authentication)
- [py-clob-client en GitHub](https://github.com/Polymarket/py-clob-client)

## 📝 Licencia

MIT

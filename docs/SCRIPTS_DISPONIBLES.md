# 🛠️ Scripts Disponibles

Guía completa de todos los scripts de gestión del bot.

---

## 🚀 Inicio y Reinicio

### `restart_bot.sh` - Reinicio Completo ⭐

Reinicia ambos bots (principal + Telegram) con la configuración más reciente.

```bash
bash scripts/restart_bot.sh
```

**Qué hace**:
1. ✅ Detiene bot principal (si está corriendo)
2. ✅ Detiene bot de Telegram (si está corriendo)
3. ✅ Descarga últimos cambios del repo
4. ✅ Verifica configuración (filtros, dry_run, WebSocket, etc.)
5. ✅ Inicia bot de Telegram en background (si está configurado)
6. ✅ Inicia bot principal en foreground

**Salida esperada**:
```
🚀 INICIANDO BOTS CON NUEVA CONFIGURACIÓN
===============================================================================

Filtros activos:
  • min_days_to_resolve: 2 días
  • max_days_to_resolve: 30 días
  • WebSocket: Habilitado
  • Concurrent Orders: Habilitado
  • Bot de Telegram: Habilitado

📱 Iniciando bot de Telegram en background...
   ✓ Bot de Telegram iniciado (PID: 12345)
   Logs: tail -f logs/telegram_bot.log

🤖 Iniciando bot principal...
```

---

### `start_telegram_bot.sh` - Solo Bot de Telegram

Inicia únicamente el bot de comandos de Telegram.

```bash
bash scripts/start_telegram_bot.sh
```

**Cuándo usar**:
- Quieres control remoto del bot principal vía Telegram
- El bot principal ya está corriendo
- Solo necesitas monitoreo vía Telegram

**Opciones**:
- Foreground: Mantiene terminal abierta, muestra logs en vivo
- Background: Corre en segundo plano, logs en archivo

---

## 🛑 Detención

### `stop_bot.sh` - Detener Ambos Bots

Detiene de forma segura el bot principal y el bot de Telegram.

```bash
bash scripts/stop_bot.sh
```

**Qué hace**:
1. ✅ Envía SIGINT (Ctrl+C) al bot principal
2. ✅ Espera cierre limpio (15 segundos)
3. ✅ Si no responde, envía SIGTERM
4. ✅ Si aún no responde, fuerza con SIGKILL
5. ✅ Repite proceso para bot de Telegram

**Salida esperada**:
```
🛑 Deteniendo bots Polymarket...

✓ Bot principal encontrado (PID: 12345)
  Enviando señal de detención (SIGINT)...
  ✅ Bot principal detenido correctamente

✓ Bot de Telegram encontrado (PID: 12346)
  Deteniendo...
  ✅ Bot de Telegram detenido

✅ Proceso de detención completado
```

---

## 📊 Monitoreo

### `status_bot.sh` - Estado de los Bots ⭐

Muestra estado completo de ambos bots, posiciones, configuración y logs recientes.

```bash
bash scripts/status_bot.sh
```

**Información mostrada**:
- Estado de bot principal (PID, CPU, memoria, tiempo de ejecución)
- Estado de bot de Telegram (PID, configuración)
- Número de posiciones abiertas
- Últimas 5 líneas de log
- Configuración actual (dry_run, WebSocket, filtros)
- Comandos útiles

**Salida esperada**:
```
===============================================================================
ESTADO DE LOS BOTS POLYMARKET
===============================================================================

🤖 Bot Principal (main_bot.py)
-------------------------------------------
Estado: ✅ CORRIENDO
PID: 12345
Iniciado: Fri Jan 31 10:30:00 2026
CPU: 2.5%
Memoria: 1.2%

📱 Bot de Telegram (telegram_bot.py)
-------------------------------------------
Estado: ✅ CORRIENDO
PID: 12346
Iniciado: Fri Jan 31 10:30:05 2026
CPU: 0.5%
Memoria: 0.8%

💼 Posiciones Actuales
-------------------------------------------
Posiciones abiertas: 3

📋 Últimas Actividades (últimas 5 líneas de log)
-------------------------------------------
[INFO] Monitoring 3 positions...
[INFO] Position 12345: price=0.52 tp=0.60 sl=0.44
[INFO] Scanning markets...
[INFO] ✓ Candidate: Will Bitcoin... | days=7 | score=82.3
[INFO] Next scan in 120 seconds

⚙️  Configuración Actual
-------------------------------------------
Modo dry_run: true
WebSocket: true
Concurrent orders: true
Min days to resolve: 2 días
```

---

## 🔍 Diagnóstico

### `quick_validate_fix.sh` - Validación Rápida del Fix

Valida que el filtro de mercados resueltos esté correctamente implementado.

```bash
bash scripts/quick_validate_fix.sh
```

**Verificaciones**:
- ✅ config.json tiene min_days_to_resolve
- ✅ Código de rechazo implementado en market_scanner.py
- ✅ Detección de mercados pasados de fecha
- ✅ Logging mejorado
- ✅ Dependencias instaladas

**Salida esperada**:
```
✅ config.json tiene 'min_days_to_resolve: 2'
✅ Código de rechazo implementado
✅ Comparación de días implementada
✅ Detección de fecha pasada implementada
✅ Logging de días en candidatos implementado

Fix de mercados resueltos: ✅ CORRECTAMENTE IMPLEMENTADO
```

---

## 🧪 Testing

### `test_websocket.sh` - Test de WebSocket

Prueba la conexión WebSocket en modo dry-run.

```bash
bash scripts/test_websocket.sh
```

**Qué hace**:
1. Hace backup de config.json
2. Habilita WebSocket temporalmente
3. Ejecuta bot en modo dry-run
4. Restaura config al salir

**Cuándo usar**:
- Primera vez configurando WebSocket
- Debugging de conexión WebSocket
- Validar que no haya disconnect loops

---

## 🔧 Herramientas Python

### `diagnose_market_filters.py` - Diagnóstico de Filtros ⭐

Analiza mercados reales y muestra por qué son aceptados/rechazados.

```bash
python tools/diagnose_market_filters.py

# Exportar a CSV
python tools/diagnose_market_filters.py --csv
```

**Salida esperada**:
```
[1/50] Analyzing market...
  Question: Will Trump win the 2024 election?
  Token: 21742633...
  Volume: $1,250.50 | Liquidity: $5,200.00
  Days to resolve: 15
  Bid: 0.52 | Ask: 0.54 | Odds: 0.53
  Spread: 3.77%
  ✅ ACCEPTED: score=78.5

[2/50] Analyzing market...
  Question: Will it rain tomorrow in NYC?
  Days to resolve: 1
  ❌ REJECTED: days_too_soon (days=1 < 2)

SUMMARY
===============================================================================
✅ Accepted: 12
❌ Rejected: 38

Rejection reasons:
  • days_too_soon (1 < 2): 15
  • spread_too_wide: 8
  • odds_out_of_range: 7
```

---

### `simulate_fills.py` - Simulación de TP/SL

Simula qué posiciones serían cerradas si estuviera en modo real.

```bash
# Una vez
python tools/simulate_fills.py

# Continuo cada 5 minutos
python tools/simulate_fills.py --loop 300
```

**Salida**:
```
Position abc123...
  Entry: 0.50 | TP: 0.60 | SL: 0.44
  Current: 0.62
  ✅ TAKE PROFIT hit! (+20% gain)

Results saved to: data/simulation_results.json
```

---

### `telegram_alerts.py` - Alertas de Telegram

Envía alertas y resúmenes vía Telegram.

```bash
# Test de conexión
python tools/telegram_alerts.py --test

# Monitoreo continuo
python tools/telegram_alerts.py --monitor

# Resumen diario
python tools/telegram_alerts.py --summary
```

---

### `test_websocket_standalone.py` - Test WebSocket Aislado

Prueba WebSocket sin ejecutar el bot completo.

```bash
# Test de 60 segundos
python scripts/test_websocket_standalone.py

# Test de 5 minutos
python scripts/test_websocket_standalone.py --duration 300

# Con token IDs específicos
python scripts/test_websocket_standalone.py --tokens TOKEN_ID_1 TOKEN_ID_2
```

---

## 📋 Resumen de Scripts

| Script | Tipo | Uso Frecuente | Descripción Corta |
|--------|------|---------------|-------------------|
| **restart_bot.sh** | Bash | ⭐⭐⭐ | Reinicia todo (principal + Telegram) |
| **stop_bot.sh** | Bash | ⭐⭐⭐ | Detiene todo |
| **status_bot.sh** | Bash | ⭐⭐⭐ | Ver estado de bots |
| **start_telegram_bot.sh** | Bash | ⭐⭐ | Solo inicia Telegram |
| **quick_validate_fix.sh** | Bash | ⭐ | Valida fix de mercados |
| **diagnose_market_filters.py** | Python | ⭐⭐⭐ | Diagnóstico de filtros |
| **simulate_fills.py** | Python | ⭐⭐ | Simula TP/SL |
| **telegram_alerts.py** | Python | ⭐ | Alertas manuales |
| **test_websocket.sh** | Bash | ⭐ | Test WebSocket |
| **test_websocket_standalone.py** | Python | ⭐ | Test WebSocket aislado |

---

## 🎯 Workflows Comunes

### Inicio del Día

```bash
# 1. Verificar estado
bash scripts/status_bot.sh

# 2. Si no está corriendo, iniciar
bash scripts/restart_bot.sh

# 3. Verificar logs en tiempo real
tail -f logs/bot_monitor_*.log
```

---

### Después de Actualizar Código

```bash
# 1. Pull cambios
git pull origin claude/investigate-article-implementation-CG7Bb

# 2. Reiniciar para aplicar cambios
bash scripts/restart_bot.sh

# 3. Verificar que filtro esté activo
bash scripts/quick_validate_fix.sh
```

---

### Debugging de Problemas

```bash
# 1. Ver estado actual
bash scripts/status_bot.sh

# 2. Ver logs completos
tail -100 logs/bot_monitor_*.log

# 3. Diagnosticar filtros de mercado
python tools/diagnose_market_filters.py

# 4. Validar WebSocket
python scripts/test_websocket_standalone.py --duration 60
```

---

### Testing de Nueva Configuración

```bash
# 1. Detener bot
bash scripts/stop_bot.sh

# 2. Editar config.json
nano config.json

# 3. Validar cambios
bash scripts/quick_validate_fix.sh

# 4. Reiniciar con nueva configuración
bash scripts/restart_bot.sh

# 5. Monitorear primeros 5 minutos
tail -f logs/bot_monitor_*.log | grep -E "Candidate|Rejected"
```

---

### Apagar Todo Antes de Cerrar Servidor

```bash
# 1. Detener bots
bash scripts/stop_bot.sh

# 2. Verificar que se detuvieron
bash scripts/status_bot.sh

# 3. Hacer backup de posiciones
cp data/positions.json data/positions_backup_$(date +%Y%m%d).json
```

---

## 🔗 Ubicación de Scripts

```
/home/user/poly/
├── scripts/
│   ├── restart_bot.sh              ← Reinicio completo
│   ├── stop_bot.sh                 ← Detener todo
│   ├── status_bot.sh               ← Ver estado
│   ├── start_telegram_bot.sh       ← Solo Telegram
│   ├── quick_validate_fix.sh       ← Validar fix
│   ├── test_websocket.sh           ← Test WebSocket
│   └── test_websocket_standalone.py ← Test WebSocket aislado
│
└── tools/
    ├── diagnose_market_filters.py  ← Diagnóstico de filtros
    ├── simulate_fills.py           ← Simulación TP/SL
    ├── telegram_alerts.py          ← Alertas Telegram
    ├── telegram_bot.py             ← Bot de comandos
    └── whale_tracker.py            ← Tracking de whales
```

---

## ❓ FAQ

**P: ¿Cuál script uso para reiniciar el bot?**
R: `bash scripts/restart_bot.sh` - reinicia todo automáticamente.

**P: ¿Cómo verifico si el bot está corriendo?**
R: `bash scripts/status_bot.sh` - muestra estado completo.

**P: ¿Cómo detengo el bot?**
R: `bash scripts/stop_bot.sh` - detiene de forma segura.

**P: ¿El bot de Telegram se inicia automáticamente?**
R: Sí, si tienes TELEGRAM_BOT_TOKEN configurado en .env, `restart_bot.sh` lo inicia.

**P: ¿Cómo veo los logs en tiempo real?**
R: `tail -f logs/bot_monitor_*.log` (principal) o `tail -f logs/telegram_bot.log` (Telegram).

**P: ¿Pierdo posiciones al reiniciar?**
R: No, están guardadas en data/positions.json y se cargan al iniciar.

**P: ¿Cómo valido que el fix de mercados resueltos funciona?**
R: `python tools/diagnose_market_filters.py` - muestra qué mercados se rechazan.

---

**Script más importante**: `bash scripts/restart_bot.sh`

Este script hace todo lo necesario para reiniciar con la configuración actualizada. 🚀

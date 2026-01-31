#!/bin/bash
# Script para verificar el estado de los bots

echo "================================================================================"
echo "ESTADO DE LOS BOTS POLYMARKET"
echo "================================================================================"
echo ""

cd /home/user/poly

# 1. Bot principal
echo "🤖 Bot Principal (main_bot.py)"
echo "-------------------------------------------"
BOT_PID=$(pgrep -f "python.*main_bot.py" || true)

if [ -z "$BOT_PID" ]; then
    echo "Estado: ❌ DETENIDO"
else
    echo "Estado: ✅ CORRIENDO"
    echo "PID: $BOT_PID"

    # Tiempo de ejecución
    START_TIME=$(ps -o lstart= -p $BOT_PID)
    echo "Iniciado: $START_TIME"

    # Uso de CPU y memoria
    CPU=$(ps -o %cpu= -p $BOT_PID | tr -d ' ')
    MEM=$(ps -o %mem= -p $BOT_PID | tr -d ' ')
    echo "CPU: ${CPU}%"
    echo "Memoria: ${MEM}%"
fi

echo ""

# 2. Bot de Telegram
echo "📱 Bot de Telegram (telegram_bot.py)"
echo "-------------------------------------------"
TELEGRAM_PID=$(pgrep -f "python.*telegram_bot.py" || true)

if [ -z "$TELEGRAM_PID" ]; then
    echo "Estado: ❌ DETENIDO"

    # Verificar si está configurado
    if [ -f ".env" ]; then
        if grep -q "TELEGRAM_BOT_TOKEN" .env && grep -q "TELEGRAM_CHAT_ID" .env; then
            TOKEN=$(grep "TELEGRAM_BOT_TOKEN" .env | cut -d '=' -f2 | tr -d ' ')
            if [ ! -z "$TOKEN" ]; then
                echo "Configuración: ✓ Telegram configurado (puede iniciarse)"
            else
                echo "Configuración: ⚠️  TOKEN vacío en .env"
            fi
        else
            echo "Configuración: ⚠️  No configurado en .env"
        fi
    fi
else
    echo "Estado: ✅ CORRIENDO"
    echo "PID: $TELEGRAM_PID"

    # Tiempo de ejecución
    START_TIME=$(ps -o lstart= -p $TELEGRAM_PID)
    echo "Iniciado: $START_TIME"

    # Uso de CPU y memoria
    CPU=$(ps -o %cpu= -p $TELEGRAM_PID | tr -d ' ')
    MEM=$(ps -o %mem= -p $TELEGRAM_PID | tr -d ' ')
    echo "CPU: ${CPU}%"
    echo "Memoria: ${MEM}%"
fi

echo ""

# 3. Posiciones actuales
echo "💼 Posiciones Actuales"
echo "-------------------------------------------"
if [ -f "data/positions.json" ]; then
    POS_COUNT=$(python3 -c "import json; print(len(json.load(open('data/positions.json'))))" 2>/dev/null || echo "Error")
    echo "Posiciones abiertas: $POS_COUNT"
else
    echo "Archivo positions.json no encontrado"
fi

echo ""

# 4. Últimas líneas de log
echo "📋 Últimas Actividades (últimas 5 líneas de log)"
echo "-------------------------------------------"
LATEST_LOG=$(ls -t logs/bot_monitor_*.log 2>/dev/null | head -1)
if [ ! -z "$LATEST_LOG" ]; then
    echo "Archivo: $LATEST_LOG"
    echo ""
    tail -5 "$LATEST_LOG"
else
    echo "No se encontraron archivos de log"
fi

echo ""

# 5. Configuración actual
echo "⚙️  Configuración Actual"
echo "-------------------------------------------"
if [ -f "config.json" ]; then
    DRY_RUN=$(grep '"dry_run"' config.json | grep -o 'true\|false')
    WEBSOCKET=$(grep '"use_websocket"' config.json | grep -o 'true\|false')
    CONCURRENT=$(grep '"use_concurrent_orders"' config.json | grep -o 'true\|false')
    MIN_DAYS=$(grep '"min_days_to_resolve"' config.json | grep -o '[0-9]\+' || echo "N/A")

    echo "Modo dry_run: $DRY_RUN"
    echo "WebSocket: $WEBSOCKET"
    echo "Concurrent orders: $CONCURRENT"
    echo "Min days to resolve: $MIN_DAYS días"
else
    echo "config.json no encontrado"
fi

echo ""
echo "================================================================================"
echo "COMANDOS ÚTILES"
echo "================================================================================"
echo ""
echo "Ver logs en tiempo real:"
echo "  tail -f logs/bot_monitor_*.log"
echo ""
echo "Reiniciar bots:"
echo "  bash scripts/restart_bot.sh"
echo ""
echo "Detener bots:"
echo "  bash scripts/stop_bot.sh"
echo ""
echo "Ejecutar diagnóstico de mercados:"
echo "  python tools/diagnose_market_filters.py"
echo ""
echo "================================================================================"

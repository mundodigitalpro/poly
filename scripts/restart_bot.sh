#!/bin/bash
# Script de reinicio del bot Polymarket
# Detiene el bot actual y lo reinicia con la nueva configuración

set -e

echo "================================================================================"
echo "REINICIO DEL BOT POLYMARKET"
echo "================================================================================"
echo ""

cd /home/josejordan/poly

# 1. Buscar proceso del bot
echo "🔍 Buscando procesos del bot..."
BOT_PID=$(pgrep -f "python.*main_bot.py" || true)

if [ -z "$BOT_PID" ]; then
    echo "ℹ️  No se encontró ningún bot en ejecución"
else
    echo "✓ Bot encontrado (PID: $BOT_PID)"

    # 2. Detener bot
    echo ""
    echo "🛑 Deteniendo bot..."
    kill -SIGINT $BOT_PID || kill -SIGTERM $BOT_PID || true

    # Esperar a que se detenga (max 10 segundos)
    for i in {1..10}; do
        if ! ps -p $BOT_PID > /dev/null 2>&1; then
            echo "✓ Bot detenido correctamente"
            break
        fi
        echo "   Esperando... ($i/10)"
        sleep 1
    done

    # Forzar si no se detuvo
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo "⚠️  Forzando detención..."
        kill -9 $BOT_PID || true
        sleep 1
    fi
fi

# 2. Detener bots de Telegram para evitar duplicados
echo ""
echo "🔍 Buscando procesos del bot de Telegram..."
TELEGRAM_PIDS=$(pgrep -f "python.*telegram_bot.py" || true)

if [ -z "$TELEGRAM_PIDS" ]; then
    echo "ℹ️  No se encontró ningún bot de Telegram en ejecución"
else
    echo "✓ Bot(s) de Telegram encontrados (PID: $TELEGRAM_PIDS)"
    echo ""
    echo "🛑 Deteniendo bot(s) de Telegram..."
    for PID in $TELEGRAM_PIDS; do
        kill -SIGINT $PID || kill -SIGTERM $PID || true
    done

    # Esperar a que se detengan (max 10 segundos)
    for i in {1..10}; do
        if ! pgrep -f "python.*telegram_bot.py" > /dev/null; then
            echo "✓ Bot(s) de Telegram detenido(s) correctamente"
            break
        fi
        echo "   Esperando... ($i/10)"
        sleep 1
    done

    # Forzar si no se detuvieron
    if pgrep -f "python.*telegram_bot.py" > /dev/null; then
        echo "⚠️  Forzando detención..."
        pkill -9 -f "python.*telegram_bot.py" || true
        sleep 1
    fi
fi

# 3. Pull últimos cambios
echo ""
echo "📥 Descargando últimos cambios..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "   Rama actual: $CURRENT_BRANCH"
git fetch origin $CURRENT_BRANCH
git pull origin $CURRENT_BRANCH
echo "✓ Cambios descargados"

# 4. Verificar configuración
echo ""
echo "⚙️  Verificando configuración..."
if grep -q "min_days_to_resolve.*2" config.json; then
    echo "✓ Filtro min_days_to_resolve: 2 (ACTIVO)"
else
    echo "⚠️  WARNING: min_days_to_resolve no configurado"
fi

if grep -q '"dry_run".*true' config.json; then
    echo "✓ Modo: DRY RUN (sin trading real)"
elif grep -q '"dry_run".*false' config.json; then
    echo "⚠️  Modo: TRADING REAL (con dinero real)"
    read -p "¿Continuar con trading real? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Reinicio cancelado"
        exit 1
    fi
else
    echo "⚠️  WARNING: dry_run no encontrado en config.json"
fi

if grep -q '"use_websocket".*true' config.json; then
    echo "✓ WebSocket: HABILITADO"
else
    echo "ℹ️  WebSocket: DESHABILITADO"
fi

if grep -q '"use_concurrent_orders".*true' config.json; then
    echo "✓ Concurrent Orders: HABILITADO"
else
    echo "ℹ️  Concurrent Orders: DESHABILITADO"
fi

# 5. Verificar que no haya otro bot corriendo
echo ""
echo "🔍 Verificación final..."
if pgrep -f "python.*main_bot.py" > /dev/null; then
    echo "⚠️  ERROR: Bot todavía está corriendo. Detén manualmente:"
    echo "   pkill -9 -f 'python.*main_bot.py'"
    exit 1
fi
echo "✓ Ningún bot en ejecución"

# 6. Verificar configuración de Telegram
echo ""
echo "🔍 Verificando configuración de Telegram..."
TELEGRAM_ENABLED=false

if [ -f ".env" ]; then
    if grep -q "TELEGRAM_BOT_TOKEN" .env && grep -q "TELEGRAM_CHAT_ID" .env; then
        # Verificar que no estén vacías
        TOKEN=$(grep "TELEGRAM_BOT_TOKEN" .env | cut -d '=' -f2 | tr -d ' ')
        CHAT_ID=$(grep "TELEGRAM_CHAT_ID" .env | cut -d '=' -f2 | tr -d ' ')

        if [ ! -z "$TOKEN" ] && [ ! -z "$CHAT_ID" ]; then
            TELEGRAM_ENABLED=true
            echo "✓ Telegram configurado - bot de comandos se iniciará"
        else
            echo "ℹ️  Telegram no configurado - solo bot principal"
        fi
    else
        echo "ℹ️  Telegram no configurado - solo bot principal"
    fi
else
    echo "ℹ️  Archivo .env no encontrado - solo bot principal"
fi

# 7. Iniciar bots
echo ""
echo "================================================================================"
echo "🚀 INICIANDO BOTS CON NUEVA CONFIGURACIÓN"
echo "================================================================================"
echo ""
echo "Filtros activos:"
echo "  • min_days_to_resolve: 2 días"
echo "  • max_days_to_resolve: 30 días"
echo "  • WebSocket: Habilitado"
echo "  • Concurrent Orders: Habilitado"
if [ "$TELEGRAM_ENABLED" = true ]; then
    echo "  • Bot de Telegram: Habilitado"
fi
echo "  • Argumentos extra: $@"
echo ""
echo "================================================================================"
echo ""

# Iniciar bot de Telegram en background si está configurado
if [ "$TELEGRAM_ENABLED" = true ]; then
    echo "📱 Iniciando bot de Telegram en background..."
    nohup venv/bin/python tools/telegram_bot.py > logs/telegram_bot.log 2>&1 &
    TELEGRAM_PID=$!
    sleep 2

    if ps -p $TELEGRAM_PID > /dev/null 2>&1; then
        echo "   ✓ Bot de Telegram iniciado (PID: $TELEGRAM_PID)"
        echo "   Logs: tail -f logs/telegram_bot.log"
    else
        echo "   ⚠️  ERROR: Bot de Telegram no pudo iniciar"
        echo "   Ver logs: cat logs/telegram_bot.log"
    fi
    echo ""
fi

# Iniciar bot principal
echo "🤖 Iniciando bot principal..."
echo ""
echo "Presiona Ctrl+C para detener"
echo ""
echo "================================================================================"
echo ""

# Iniciar bot principal (foreground) con argumentos pasados al script
venv/bin/python main_bot.py "$@"

# Si el bot principal se detiene, detener también Telegram
if [ "$TELEGRAM_ENABLED" = true ] && [ ! -z "$TELEGRAM_PID" ]; then
    echo ""
    echo "🛑 Deteniendo bot de Telegram..."
    kill $TELEGRAM_PID 2>/dev/null || true
fi

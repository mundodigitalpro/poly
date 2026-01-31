#!/bin/bash
# Script de reinicio del bot Polymarket
# Detiene el bot actual y lo reinicia con la nueva configuración

set -e

echo "================================================================================"
echo "REINICIO DEL BOT POLYMARKET"
echo "================================================================================"
echo ""

cd /home/user/poly

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

# 3. Pull últimos cambios
echo ""
echo "📥 Descargando últimos cambios..."
git fetch origin claude/investigate-article-implementation-CG7Bb
git pull origin claude/investigate-article-implementation-CG7Bb
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

# 6. Reiniciar bot
echo ""
echo "================================================================================"
echo "🚀 INICIANDO BOT CON NUEVA CONFIGURACIÓN"
echo "================================================================================"
echo ""
echo "Filtros activos:"
echo "  • min_days_to_resolve: 2 días"
echo "  • max_days_to_resolve: 30 días"
echo "  • WebSocket: Habilitado"
echo "  • Concurrent Orders: Habilitado"
echo ""
echo "El bot se está iniciando..."
echo "Presiona Ctrl+C para detener"
echo ""
echo "================================================================================"
echo ""

# Iniciar bot
python main_bot.py

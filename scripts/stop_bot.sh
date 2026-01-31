#!/bin/bash
# Script para detener el bot de forma segura

echo "🛑 Deteniendo bot Polymarket..."
echo ""

# Buscar proceso
BOT_PID=$(pgrep -f "python.*main_bot.py" || true)

if [ -z "$BOT_PID" ]; then
    echo "ℹ️  No hay ningún bot en ejecución"
    exit 0
fi

echo "✓ Bot encontrado (PID: $BOT_PID)"
echo ""

# Detener con SIGINT (Ctrl+C) para cierre limpio
echo "Enviando señal de detención (SIGINT)..."
kill -SIGINT $BOT_PID

# Esperar a que se detenga (max 15 segundos)
for i in {1..15}; do
    if ! ps -p $BOT_PID > /dev/null 2>&1; then
        echo ""
        echo "✅ Bot detenido correctamente"
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo ""
echo ""
echo "⚠️  Bot no respondió a SIGINT, intentando SIGTERM..."
kill -SIGTERM $BOT_PID

# Esperar otros 5 segundos
for i in {1..5}; do
    if ! ps -p $BOT_PID > /dev/null 2>&1; then
        echo ""
        echo "✅ Bot detenido correctamente"
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo ""
echo ""
echo "⚠️  Bot no respondió a SIGTERM, forzando detención (SIGKILL)..."
kill -9 $BOT_PID

sleep 1

if ! ps -p $BOT_PID > /dev/null 2>&1; then
    echo "✅ Bot detenido forzadamente"
else
    echo "❌ ERROR: No se pudo detener el bot (PID: $BOT_PID)"
    echo "   Intenta manualmente: sudo kill -9 $BOT_PID"
    exit 1
fi

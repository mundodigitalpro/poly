#!/bin/bash
# Script para detener el bot de forma segura

echo "🛑 Deteniendo bots Polymarket..."
echo ""

# 1. Buscar y detener bot principal
BOT_PID=$(pgrep -f "python.*main_bot.py" || true)

if [ -z "$BOT_PID" ]; then
    echo "ℹ️  Bot principal no está en ejecución"
else
    echo "✓ Bot principal encontrado (PID: $BOT_PID)"

    # Detener con SIGINT (Ctrl+C) para cierre limpio
    echo "  Enviando señal de detención (SIGINT)..."
    kill -SIGINT $BOT_PID

    # Esperar a que se detenga (max 15 segundos)
    for i in {1..15}; do
        if ! ps -p $BOT_PID > /dev/null 2>&1; then
            echo "  ✅ Bot principal detenido correctamente"
            break
        fi
        echo -n "."
        sleep 1
    done

    # Si no se detuvo, intentar SIGTERM
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo ""
        echo "  ⚠️  Bot no respondió a SIGINT, intentando SIGTERM..."
        kill -SIGTERM $BOT_PID

        for i in {1..5}; do
            if ! ps -p $BOT_PID > /dev/null 2>&1; then
                echo "  ✅ Bot principal detenido correctamente"
                break
            fi
            echo -n "."
            sleep 1
        done
    fi

    # Si aún no se detuvo, forzar
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo ""
        echo "  ⚠️  Bot no respondió a SIGTERM, forzando detención (SIGKILL)..."
        kill -9 $BOT_PID
        sleep 1

        if ! ps -p $BOT_PID > /dev/null 2>&1; then
            echo "  ✅ Bot principal detenido forzadamente"
        else
            echo "  ❌ ERROR: No se pudo detener el bot (PID: $BOT_PID)"
        fi
    fi
fi

echo ""

# 2. Buscar y detener bot de Telegram
TELEGRAM_PID=$(pgrep -f "python.*telegram_bot.py" || true)

if [ -z "$TELEGRAM_PID" ]; then
    echo "ℹ️  Bot de Telegram no está en ejecución"
else
    echo "✓ Bot de Telegram encontrado (PID: $TELEGRAM_PID)"
    echo "  Deteniendo..."

    kill -SIGINT $TELEGRAM_PID || kill -SIGTERM $TELEGRAM_PID || kill -9 $TELEGRAM_PID

    sleep 2

    if ! ps -p $TELEGRAM_PID > /dev/null 2>&1; then
        echo "  ✅ Bot de Telegram detenido"
    else
        echo "  ⚠️  Forzando detención de bot Telegram..."
        kill -9 $TELEGRAM_PID
        sleep 1
    fi
fi

echo ""
echo "================================================================================"
echo "✅ Proceso de detención completado"
echo "================================================================================"

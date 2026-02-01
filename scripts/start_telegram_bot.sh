#!/bin/bash
# Script para iniciar solo el bot de Telegram

set -e

echo "================================================================================"
echo "INICIAR BOT DE TELEGRAM"
echo "================================================================================"
echo ""

cd /home/josejordan/poly

# 1. Verificar si ya está corriendo
TELEGRAM_PID=$(pgrep -f "python.*telegram_bot.py" || true)

if [ ! -z "$TELEGRAM_PID" ]; then
    echo "⚠️  El bot de Telegram ya está corriendo (PID: $TELEGRAM_PID)"
    echo ""
    read -p "¿Detenerlo y reiniciar? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Deteniendo bot existente..."
        kill -SIGINT $TELEGRAM_PID || kill -9 $TELEGRAM_PID
        sleep 2
    else
        echo "Operación cancelada"
        exit 0
    fi
fi

# 2. Verificar configuración
echo "🔍 Verificando configuración..."

if [ ! -f ".env" ]; then
    echo "❌ ERROR: Archivo .env no encontrado"
    echo ""
    echo "Crea el archivo .env con:"
    echo "  cp .env.example .env"
    echo ""
    echo "Y añade:"
    echo "  TELEGRAM_BOT_TOKEN=tu_token_aqui"
    echo "  TELEGRAM_CHAT_ID=tu_chat_id_aqui"
    exit 1
fi

if ! grep -q "TELEGRAM_BOT_TOKEN" .env; then
    echo "❌ ERROR: TELEGRAM_BOT_TOKEN no encontrado en .env"
    exit 1
fi

if ! grep -q "TELEGRAM_CHAT_ID" .env; then
    echo "❌ ERROR: TELEGRAM_CHAT_ID no encontrado en .env"
    exit 1
fi

TOKEN=$(grep "TELEGRAM_BOT_TOKEN" .env | cut -d '=' -f2 | tr -d ' ')
CHAT_ID=$(grep "TELEGRAM_CHAT_ID" .env | cut -d '=' -f2 | tr -d ' ')

if [ -z "$TOKEN" ] || [ -z "$CHAT_ID" ]; then
    echo "❌ ERROR: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID están vacíos"
    exit 1
fi

echo "✓ Configuración de Telegram OK"
echo ""

# 3. Verificar dependencias
echo "🔍 Verificando dependencias..."
if python3 -c "from dotenv import load_dotenv" 2>/dev/null; then
    echo "✓ python-dotenv instalado"
else
    echo "⚠️  Instalando python-dotenv..."
    pip install -q python-dotenv
fi
echo ""

# 4. Crear directorio de logs si no existe
mkdir -p logs

# 5. Iniciar bot
echo "================================================================================"
echo "🚀 INICIANDO BOT DE TELEGRAM"
echo "================================================================================"
echo ""
echo "Comandos disponibles en Telegram:"
echo "  /status    - Estado del bot"
echo "  /positions - Posiciones actuales"
echo "  /simulate  - Simulación de TP/SL"
echo "  /summary   - Resumen diario"
echo "  /balance   - Saldo de cuenta"
echo "  /help      - Ayuda"
echo ""
echo "Logs: logs/telegram_bot.log"
echo ""
echo "Presiona Ctrl+C para detener"
echo ""
echo "================================================================================"
echo ""

# Opción: Background o Foreground
read -p "¿Iniciar en background? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Iniciar en background
    nohup python tools/telegram_bot.py > logs/telegram_bot.log 2>&1 &
    TELEGRAM_PID=$!

    sleep 2

    if ps -p $TELEGRAM_PID > /dev/null 2>&1; then
        echo "✅ Bot de Telegram iniciado en background (PID: $TELEGRAM_PID)"
        echo ""
        echo "Ver logs en tiempo real:"
        echo "  tail -f logs/telegram_bot.log"
        echo ""
        echo "Detener bot:"
        echo "  kill $TELEGRAM_PID"
        echo "  # o"
        echo "  bash scripts/stop_bot.sh"
    else
        echo "❌ ERROR: Bot no pudo iniciar"
        echo "Ver logs:"
        echo "  cat logs/telegram_bot.log"
        exit 1
    fi
else
    # Iniciar en foreground
    python tools/telegram_bot.py
fi

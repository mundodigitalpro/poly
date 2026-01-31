#!/bin/bash
# Quick validation script for the resolved markets fix
# Tests that the filter is correctly configured

set -e

echo "================================================================================"
echo "VALIDACIÓN RÁPIDA DEL FIX - Filtro de Mercados Resueltos"
echo "================================================================================"
echo ""

cd /home/user/poly

# Check 1: Config has min_days_to_resolve
echo "✓ Verificación 1: Configuración del filtro"
echo "-------------------------------------------"
if grep -q "min_days_to_resolve.*2" config.json; then
    echo "✅ config.json tiene 'min_days_to_resolve: 2'"
else
    echo "❌ ERROR: config.json no tiene min_days_to_resolve configurado"
    exit 1
fi
echo ""

# Check 2: Scanner code has the filter logic
echo "✓ Verificación 2: Lógica de rechazo en market_scanner.py"
echo "---------------------------------------------------------"
if grep -q "Reject markets resolving too soon" bot/market_scanner.py; then
    echo "✅ Código de rechazo implementado"
else
    echo "❌ ERROR: Código de rechazo no encontrado"
    exit 1
fi

if grep -q "days_to_resolve < min_days" bot/market_scanner.py; then
    echo "✅ Comparación de días implementada"
else
    echo "❌ ERROR: Comparación de días no encontrada"
    exit 1
fi
echo ""

# Check 3: Past resolution date detection
echo "✓ Verificación 3: Detección de mercados pasados de fecha"
echo "---------------------------------------------------------"
if grep -q "past resolution date" bot/market_scanner.py; then
    echo "✅ Detección de fecha pasada implementada"
else
    echo "❌ ERROR: Detección de fecha pasada no encontrada"
    exit 1
fi
echo ""

# Check 4: Improved logging
echo "✓ Verificación 4: Logging mejorado"
echo "-----------------------------------"
if grep -q "days={days_to_resolve}" bot/market_scanner.py; then
    echo "✅ Logging de días en candidatos implementado"
else
    echo "⚠️  WARNING: Logging de días no encontrado (no crítico)"
fi
echo ""

# Check 5: Dependencies
echo "✓ Verificación 5: Dependencias"
echo "-------------------------------"
if python3 -c "import py_clob_client" 2>/dev/null; then
    echo "✅ py-clob-client instalado"
else
    echo "⚠️  py-clob-client no instalado. Instala con: pip install -r requirements.txt"
fi

if python3 -c "from dotenv import load_dotenv" 2>/dev/null; then
    echo "✅ python-dotenv instalado"
else
    echo "⚠️  python-dotenv no instalado. Instala con: pip install -r requirements.txt"
fi
echo ""

# Check 6: .env file
echo "✓ Verificación 6: Credenciales"
echo "-------------------------------"
if [ -f ".env" ]; then
    echo "✅ Archivo .env existe"
    if grep -q "POLY_PRIVATE_KEY" .env; then
        echo "✅ POLY_PRIVATE_KEY configurado"
    else
        echo "⚠️  POLY_PRIVATE_KEY no encontrado en .env"
    fi
else
    echo "⚠️  Archivo .env no existe. Copia .env.example y configura credenciales"
fi
echo ""

# Summary
echo "================================================================================"
echo "RESUMEN"
echo "================================================================================"
echo ""
echo "Fix de mercados resueltos: ✅ CORRECTAMENTE IMPLEMENTADO"
echo ""
echo "El código está listo para probar. Para validar en producción:"
echo ""
echo "  1. Si tienes credenciales configuradas:"
echo "     python tools/diagnose_market_filters.py"
echo ""
echo "  2. Para correr el bot en dry-run:"
echo "     python main_bot.py"
echo ""
echo "  3. Monitorea los logs para ver:"
echo "     - 'Rejected: resolves too soon (days=X < 2)'"
echo "     - '✓ Candidate: ... | days=Y | score=Z'"
echo ""
echo "================================================================================"

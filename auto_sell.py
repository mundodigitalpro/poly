#!/usr/bin/env python3
"""
Auto-Sell Bot v2 - Con protecciones de seguridad
- Verifica precio inicial antes de empezar
- Requiere confirmación antes de vender
- Precio mínimo de seguridad
"""
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions
from py_clob_client.order_builder.constants import SELL

load_dotenv()

# ============ CONFIGURACIÓN ============
TOKEN_ID = "94192784911459194325909253314484842244405314804074606736702592885535642919725"
MARKET_NAME = "Hungary PM - Peter Magyar (YES)"

TAKE_PROFIT = 0.60        # Vender si BID >= este precio
STOP_LOSS = 0.45          # Alertar si BID <= este precio
MIN_ACCEPTABLE = 0.30     # NUNCA vender por debajo de este precio
SHARES_TO_SELL = 2        # Cantidad de shares a vender
CHECK_INTERVAL = 10       # Segundos entre cada revisión
REQUIRE_CONFIRMATION = True  # Pedir confirmación antes de vender
# =======================================

def get_best_bid(client, token_id):
    """Obtiene el mejor precio de compra (BID) actual"""
    book = client.get_order_book(token_id)
    bids = getattr(book, 'bids', [])
    if bids:
        return float(bids[0].price)
    return 0.0

def get_best_ask(client, token_id):
    """Obtiene el mejor precio de venta (ASK) actual"""
    book = client.get_order_book(token_id)
    asks = getattr(book, 'asks', [])
    if asks:
        return float(asks[0].price)
    return 0.0

def sell_shares(client, token_id, price, size):
    """Ejecuta la orden de venta"""
    order_args = OrderArgs(
        token_id=token_id,
        price=price,
        size=size,
        side=SELL,
    )
    
    options = PartialCreateOrderOptions(
        tick_size="0.01",
        neg_risk=False,
    )
    
    result = client.create_and_post_order(order_args, options)
    return result

def confirm_action(message):
    """Pide confirmación al usuario"""
    print()
    print("⚠️  " + message)
    response = input("¿Continuar? (s/n): ").strip().lower()
    return response == 's' or response == 'si' or response == 'y' or response == 'yes'

def main():
    print("=" * 60)
    print("🤖 AUTO-SELL BOT v2 (CON PROTECCIONES)")
    print("=" * 60)
    print()
    print(f"📊 Mercado: {MARKET_NAME}")
    print(f"🎯 Take Profit: ${TAKE_PROFIT}")
    print(f"🛑 Stop Loss Alert: ${STOP_LOSS}")
    print(f"🚫 Precio Mínimo: ${MIN_ACCEPTABLE} (NUNCA vender por debajo)")
    print(f"📦 Shares a vender: {SHARES_TO_SELL}")
    print(f"⏱️  Intervalo: cada {CHECK_INTERVAL} segundos")
    print(f"✅ Confirmación requerida: {'Sí' if REQUIRE_CONFIRMATION else 'No'}")
    print()
    
    # Inicializar cliente
    print("Iniciando cliente...")
    client = ClobClient(
        host='https://clob.polymarket.com',
        chain_id=137,
        key=os.getenv('POLY_PRIVATE_KEY'),
        signature_type=1,
        funder=os.getenv('POLY_FUNDER_ADDRESS')
    )
    client.set_api_creds(client.create_or_derive_api_creds())
    print("✅ Cliente listo")
    print()
    
    # ===== VERIFICACIÓN INICIAL DE SEGURIDAD =====
    print("🔍 VERIFICACIÓN INICIAL DE MERCADO...")
    print("-" * 60)
    
    best_bid = get_best_bid(client, TOKEN_ID)
    best_ask = get_best_ask(client, TOKEN_ID)
    spread = best_ask - best_bid if best_ask > 0 and best_bid > 0 else 0
    
    print(f"   Best BID (compradores): ${best_bid:.2f}")
    print(f"   Best ASK (vendedores):  ${best_ask:.2f}")
    print(f"   Spread:                 ${spread:.2f}")
    print()
    
    # Alertas de seguridad
    warnings = []
    
    if best_bid < MIN_ACCEPTABLE:
        warnings.append(f"⚠️  BID actual (${best_bid:.2f}) está MUY POR DEBAJO del mínimo aceptable (${MIN_ACCEPTABLE})")
    
    if best_bid < STOP_LOSS:
        warnings.append(f"⚠️  BID actual (${best_bid:.2f}) ya está por debajo del stop loss (${STOP_LOSS})")
    
    if spread > 0.20:
        warnings.append(f"⚠️  Spread muy alto (${spread:.2f}) - Mercado ilíquido")
    
    if warnings:
        print("🚨 ALERTAS DE SEGURIDAD:")
        for w in warnings:
            print(f"   {w}")
        print()
        
        if not confirm_action("El mercado tiene condiciones adversas. ¿Iniciar monitoreo de todos modos?"):
            print("Bot cancelado por el usuario.")
            return
    
    print()
    print("Iniciando monitoreo...")
    print("Presiona Ctrl+C para detener")
    print("-" * 60)
    
    try:
        while True:
            now = datetime.now().strftime("%H:%M:%S")
            best_bid = get_best_bid(client, TOKEN_ID)
            
            status = "📊 HOLDING"
            action_type = None
            
            if best_bid >= TAKE_PROFIT:
                status = "🎉 TAKE PROFIT ALCANZADO!"
                action_type = "take_profit"
            elif best_bid <= STOP_LOSS and best_bid >= MIN_ACCEPTABLE:
                status = "⚠️  STOP LOSS - Esperando confirmación"
                action_type = "stop_loss"
            elif best_bid < MIN_ACCEPTABLE:
                status = "🚫 BID muy bajo - NO se venderá automáticamente"
            
            print(f"[{now}] Best BID: ${best_bid:.2f} | {status}")
            
            if action_type:
                print()
                
                # Verificar precio mínimo
                if best_bid < MIN_ACCEPTABLE:
                    print(f"🚫 BID (${best_bid:.2f}) por debajo del mínimo (${MIN_ACCEPTABLE})")
                    print("   No se ejecutará la venta. Revisa el mercado manualmente.")
                    time.sleep(CHECK_INTERVAL)
                    continue
                
                # Pedir confirmación si está activado
                if REQUIRE_CONFIRMATION:
                    msg = f"Vender {SHARES_TO_SELL} shares a ${best_bid:.2f} ({action_type.upper()})"
                    if not confirm_action(msg):
                        print("Venta cancelada. Continuando monitoreo...")
                        time.sleep(CHECK_INTERVAL)
                        continue
                
                # Ejecutar venta
                print("=" * 60)
                print(f"🚨 EJECUTANDO VENTA ({action_type.upper()})")
                print("=" * 60)
                
                try:
                    result = sell_shares(client, TOKEN_ID, best_bid, SHARES_TO_SELL)
                    print()
                    print("✅ VENTA EJECUTADA!")
                    print(f"   Result: {result}")
                    print()
                    print("Bot detenido. ¡Misión cumplida!")
                    break
                except Exception as e:
                    print(f"❌ Error vendiendo: {e}")
                    print("Continuando monitoreo...")
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print()
        print("🛑 Bot detenido por el usuario")

if __name__ == "__main__":
    main()

# Análisis: 15min-btc-polymarket-trading-bot

## Resumen del Repositorio

**Repo**: https://github.com/gabagool222/15min-btc-polymarket-trading-bot

Bot de arbitraje para mercados BTC UP/DOWN de 15 minutos en Polymarket. Ejecuta una estrategia de **arbitraje puro**: compra ambos lados (UP + DOWN) cuando el costo total < $1.00, garantizando ganancias independientemente del resultado.

---

## Funcionalidades Clave del Bot BTC

### 1. Cliente WebSocket para Latencia Baja
**Archivo**: `src/wss_market.py`

```
URL: wss://ws-subscriptions-clob.polymarket.com
Tipo mensaje: {"assets_ids": [...], "type": "MARKET"}
Eventos: "book" (snapshot), "price_change" (delta)
```

**Características**:
- Mantiene libro L2 agregado en memoria
- Reconexión automática con backoff
- Ping/Pong cada 10 segundos
- Debounce de 50ms para evitar spam de evaluaciones

**Estado actual en poly**: No implementado (usa polling HTTP)

### 2. Ejecución de Órdenes Pareadas (Paralelas)
**Archivo**: `src/trading.py`

```python
# Pre-firma todas las órdenes primero (parte lenta)
signed_orders = [sign(order) for order in orders]
# Envío en batch único
response = client.post_orders(signed_orders)
```

**Características**:
- Pre-firma para minimizar latencia entre órdenes
- Batch posting en una sola llamada API
- Fallback a envío secuencial si batch falla

**Estado actual en poly**: Órdenes individuales secuenciales

### 3. Manejo de Ejecuciones Parciales (Leg Risk)
**Archivo**: `src/btc_15m_arb_bot.py`

```
Si solo una pierna se llena:
  1. Intentar cancelar orden pendiente
  2. Ejecutar venta de cobertura con orden FAK (fill-and-kill)
  3. Registrar exposición residual
```

**Verificación robusta**:
- Polling de estado con timeout configurable (3s default)
- Estados terminales: filled, canceled, rejected, expired
- Tolerancia numérica (1e-9) para comparar fills

**Estado actual en poly**: Verificación básica, sin manejo de leg risk

### 4. Descubrimiento Automático de Mercados Temporales
**Archivo**: `src/market_lookup.py`

```python
def next_slug(slug: str) -> str:
    # btc-will-548400 → btc-will-549300 (+900 segundos)
    prefix, num = re.match(r"(.+-)(\d+)$", slug).groups()
    return f"{prefix}{int(num) + 900}"
```

**Métodos de descubrimiento**:
1. Slugs calculados (timestamp + 900s)
2. API Gamma: filtro `btc-updown-15m-*`
3. Web scraping: `/crypto/15M`

**Estado actual en poly**: Scanning general sin lógica temporal

### 5. Análisis de Profundidad del Libro (Walk the Book)
**Archivo**: `src/btc_15m_arb_bot.py`

```python
def check_arbitrage():
    # Calcula "worst fill price" caminando el libro hasta llenar order_size
    worst_price_up = walk_book(asks_up, order_size)
    worst_price_down = walk_book(asks_down, order_size)

    if worst_price_up + worst_price_down <= threshold:
        # Ganancia garantizada
        profit_per_share = 1.00 - (worst_price_up + worst_price_down)
```

**Estado actual en poly**: Solo usa best bid/ask, no considera slippage

### 6. Modos de Operación Híbridos
- **Polling HTTP**: Compatible, mayor latencia
- **WebSocket**: Baja latencia, actualizaciones push

**Configuración**:
```
USE_WSS=true/false
WS_URL=wss://ws-subscriptions-clob.polymarket.com
```

---

## Comparativa: Tu Bot vs Bot BTC

| Característica | Tu Bot (poly) | Bot BTC |
|----------------|---------------|---------|
| Fuente de datos | Gamma API + CLOB | CLOB + WebSocket |
| Latencia | Alta (polling) | Baja (WebSocket) |
| Órdenes | Secuenciales | Paralelas (pre-sign) |
| Slippage | No calculado | Walk the book |
| Leg risk | No manejado | Cobertura automática |
| Mercados | Generales | Específicos 15min |
| Estrategia | TP/SL probabilístico | Arbitraje puro |
| Dry run | Sí | Sí |

---

## Funcionalidades Recomendadas para Incorporar

### Alta Prioridad

#### 1. Cliente WebSocket (`bot/wss_client.py`)
**Por qué**: Reduce latencia de ~30s (polling) a ~50ms (push)
**Impacto**: Crítico para capturar oportunidades antes que competidores

```python
class PolyWebSocketClient:
    async def subscribe(self, token_ids: List[str]):
        await ws.send(json.dumps({
            "assets_ids": token_ids,
            "type": "MARKET"
        }))

    async def run(self):
        async for message in ws:
            event = json.loads(message)
            if event["event_type"] == "book":
                self._apply_snapshot(event)
            elif event["event_type"] == "price_change":
                self._apply_delta(event)
            yield (event["asset_id"], event["event_type"])
```

#### 2. Ejecución Paralela con Pre-firma (`bot/trader.py`)
**Por qué**: Minimiza tiempo entre órdenes, reduce riesgo de ejecución parcial

```python
def execute_paired_orders(self, orders: List[OrderArgs]) -> List[TradeFill]:
    # Pre-sign (slow part)
    signed = [self.client.sign_order(o) for o in orders]
    # Batch post (fast part)
    return self.client.post_orders(signed)
```

#### 3. Walk the Book para Calcular Slippage (`bot/market_scanner.py`)
**Por qué**: Evita trades donde el slippage consume el profit esperado

```python
def walk_book(orders: List, size: float) -> Tuple[float, float]:
    """Calcula precio promedio ponderado para llenar 'size'."""
    filled = 0.0
    total_cost = 0.0
    for order in sorted(orders, key=lambda x: x.price):
        take = min(order.size, size - filled)
        total_cost += take * order.price
        filled += take
        if filled >= size:
            break
    vwap = total_cost / filled if filled > 0 else 0
    return vwap, filled
```

### Media Prioridad

#### 4. Manejo de Leg Risk (`bot/trader.py`)
**Por qué**: Protege contra exposición no deseada en trades multi-leg

```python
def handle_partial_fill(self, filled_order, pending_order):
    # Cancelar orden pendiente
    self.client.cancel_order(pending_order.id)
    # Venta de cobertura inmediata
    self.execute_sell(
        token_id=filled_order.token_id,
        price=best_bid - 0.01,  # Agresivo para salir
        size=filled_order.filled_size,
        order_type="FAK"  # Fill-and-kill
    )
```

#### 5. Soporte para Mercados Temporales (15min, 1h)
**Por qué**: Expande el universo de oportunidades

```python
def discover_temporal_markets(self, pattern: str = "btc-updown-*"):
    """Encuentra mercados BTC UP/DOWN activos."""
    gamma_markets = self.gamma_client.search(pattern)
    return [m for m in gamma_markets if self._is_active_window(m)]
```

### Baja Prioridad (Nice to Have)

#### 6. Estrategia de Arbitraje Puro
**Por qué**: Complementa tu estrategia actual de TP/SL

```python
def check_dutch_book(self, yes_ask: float, no_ask: float) -> Optional[float]:
    """Detecta oportunidad de arbitraje YES+NO < $1."""
    total_cost = yes_ask + no_ask
    if total_cost < 0.99:  # Threshold configurable
        return 1.00 - total_cost  # Profit garantizado
    return None
```

**Nota**: Ya tienes `tools/dutch_book_scanner.py` que confirmó que estas oportunidades son raras/inexistentes en mercados normales. Los mercados BTC 15min pueden tener más ineficiencias por su corta duración.

---

## Plan de Implementación Sugerido

### Fase 1: WebSocket Client (1-2 días)
1. Crear `bot/wss_client.py` basado en `wss_market.py`
2. Integrar como modo alternativo en `main_bot.py`
3. Agregar config: `ws_enabled`, `ws_url`

### Fase 2: Improved Order Execution (1 día)
1. Agregar `execute_paired_orders()` a `BotTrader`
2. Implementar pre-signing
3. Agregar fallback a secuencial

### Fase 3: Slippage Calculation (0.5 días)
1. Agregar `walk_book()` a `MarketScanner`
2. Usar VWAP en lugar de best ask para decisiones

### Fase 4: Leg Risk Handling (0.5 días)
1. Agregar `handle_partial_fill()` a `BotTrader`
2. Integrar con ejecución de pares

---

## Configuración Sugerida (`config.json`)

```json
{
  "websocket": {
    "enabled": false,
    "url": "wss://ws-subscriptions-clob.polymarket.com",
    "ping_interval": 10,
    "reconnect_delay": 5
  },
  "execution": {
    "use_parallel_orders": false,
    "pre_sign_orders": true,
    "leg_risk_protection": true,
    "fak_sell_offset": 0.01
  },
  "slippage": {
    "enabled": true,
    "max_slippage_percent": 2.0,
    "use_vwap": true
  }
}
```

---

## Conclusión

El bot BTC 15min tiene varias técnicas avanzadas que mejorarían tu bot:

1. **WebSocket** - Mayor impacto, reduce latencia dramáticamente
2. **Pre-sign + Batch** - Mejora velocidad de ejecución
3. **Walk the Book** - Previene trades con slippage excesivo
4. **Leg Risk** - Protección para operaciones complejas

La estrategia de arbitraje puro (YES+NO < $1) es específica para mercados binarios de corta duración y probablemente no sea viable para mercados generales (como ya confirmaste con `dutch_book_scanner.py`).

Recomiendo empezar con el **WebSocket client** ya que proporciona el mayor beneficio con implementación relativamente simple.

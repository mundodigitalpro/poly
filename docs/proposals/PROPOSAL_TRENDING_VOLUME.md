# Propuesta: Mejoras de Trending y Volumen

**Autor**: AMP (Arquitecto Suplente)  
**Fecha**: 2026-01-30  
**Estado**: Propuesta para revisión del equipo  
**Prioridad**: Medium

---

## 1. Problema Actual

### 1.1 Volumen no disponible
El bot actualmente muestra `volume=0.0` en todos los candidatos:
```
New candidate score=43.91 odds=0.345 spread=2.9% volume=0.0
```

**Causa raíz**: La API CLOB (`get_sampling_markets`) no incluye campos de volumen.

### 1.2 Sin criterio de popularidad
El bot selecciona mercados sin considerar:
- Volumen de trading (liquidez real)
- Actividad reciente (trending)
- Interés del mercado

---

## 2. Análisis de APIs Disponibles

### 2.1 CLOB API (actual)
```
Endpoint: https://clob.polymarket.com
Método: get_sampling_markets()
```

**Campos disponibles**: ❌ Sin volumen
```python
['condition_id', 'question', 'tokens', 'end_date_iso', 
 'active', 'closed', 'tags', ...]
# NO incluye: volume, liquidity, trades
```

### 2.2 Gamma API (alternativa) ✅
```
Endpoint: https://gamma-api.polymarket.com
Método: GET /markets
```

**Campos disponibles**: ✅ Volumen completo
```python
['volumeNum',      # Volumen total USD
 'volume24hr',     # Volumen últimas 24h
 'volume1wk',      # Volumen última semana
 'volume1mo',      # Volumen último mes
 'liquidityNum',   # Liquidez actual
 'lastTradePrice', # Último precio
 'oneDayPriceChange',  # Cambio 24h
 'oneWeekPriceChange', # Cambio 7d
 'bestBid', 'bestAsk', # Mejores precios
 'spread',         # Spread actual
 'clobTokenIds',   # Token IDs para CLOB
 ...]
```

### 2.3 Comparativa

| Campo | CLOB API | Gamma API |
|-------|----------|-----------|
| Token IDs | ✅ | ✅ |
| Orderbook | ✅ | ❌ |
| Volume | ❌ | ✅ |
| Liquidity | ❌ | ✅ |
| Price changes | ❌ | ✅ |
| Best bid/ask | ❌ | ✅ |
| Trading enabled | ✅ | ❌ |

---

## 3. Datos de Ejemplo (Gamma API)

### Top 10 mercados por volumen:
```
 1. Vol: $1,102,485 | 24h: $1,995  | Trump deport 250k-500k
 2. Vol: $1,009,156 | 24h: $10,209 | Trump deport <250k
 3. Vol: $  733,564 | 24h: $1,177  | Trump deport 750k+
 4. Vol: $  463,772 | 24h: $2,853  | Trump deport 500k-750k
 5. Vol: $  441,595 | 24h: $2,730  | Trump deport 750k-1M
```

**Observación**: Estos mercados tienen liquidez real ($1k-$14k) y volumen 24h activo.

---

## 4. Propuestas de Implementación

### Opción A: Híbrido Gamma + CLOB (Recomendada)
```
┌──────────────────────────────────────────────────┐
│  1. Gamma API: Obtener mercados con volumen      │
│     GET /markets?active=true&closed=false        │
│     Filtrar por: volumeNum, volume24hr           │
│                                                  │
│  2. Extraer clobTokenIds de respuesta            │
│                                                  │
│  3. CLOB API: Verificar orderbook                │
│     get_order_book(token_id)                     │
│     Validar: spread, liquidez real               │
│                                                  │
│  4. Ejecutar trade via CLOB                      │
└──────────────────────────────────────────────────┘
```

**Ventajas**:
- Datos de volumen reales para scoring
- Mantiene trading via CLOB (requerido)
- Mejor selección de mercados

**Desventajas**:
- Requiere 2 APIs
- Más complejidad

### Opción B: Solo Gamma para discovery
```
Gamma API → Filtrar top mercados → CLOB para todo lo demás
```

**Ventajas**:
- Más simple
- Reduce calls a CLOB

**Desventajas**:
- Datos de Gamma pueden estar desactualizados

### Opción C: Cache de volumen
```
Cron job: Cada 5 min, actualizar cache de volúmenes desde Gamma
Bot: Lee cache local para scoring
```

**Ventajas**:
- Mínimo impacto en latencia
- Datos consistentes

**Desventajas**:
- Más infraestructura

---

## 5. Criterios de Trending Propuestos

### 5.1 Nuevo Score con Volumen

```python
def calculate_market_score(
    spread_percent,
    volume_24h,      # NUEVO: de Gamma API
    liquidity,       # NUEVO: de Gamma API
    odds,
    days_to_resolve,
):
    # Weights ajustados
    spread_weight = 30      # Reducido de 40
    volume_weight = 25      # NUEVO
    liquidity_weight = 15   # NUEVO
    odds_weight = 20        # Igual
    time_weight = 10        # Igual
    
    # Volume score: $10k+ = 100 puntos
    volume_score = min(100, (volume_24h / 10000) * 100)
    
    # Liquidity score: $5k+ = 100 puntos
    liquidity_score = min(100, (liquidity / 5000) * 100)
    
    # ... resto igual
```

### 5.2 Filtros Mínimos

```python
market_filters = {
    "min_volume_24h": 500,    # Mínimo $500 en 24h
    "min_liquidity": 1000,    # Mínimo $1k liquidez
    "min_odds": 0.30,
    "max_odds": 0.70,
    "max_spread_percent": 5.0,
}
```

---

## 6. Cambios Requeridos

### 6.1 Nuevos archivos
```
bot/gamma_client.py    # Cliente para Gamma API
```

### 6.2 Modificaciones
```
bot/market_scanner.py  # Integrar datos de Gamma
bot/strategy.py        # Nuevo scoring con volumen
config.json            # Nuevos filtros
```

### 6.3 Config propuesta
```json
{
  "market_filters": {
    "min_odds": 0.30,
    "max_odds": 0.70,
    "max_spread_percent": 5.0,
    "min_volume_24h": 500,      // NUEVO
    "min_liquidity": 1000,      // NUEVO
    "max_days_to_resolve": 30
  },
  "gamma_api": {
    "enabled": true,
    "base_url": "https://gamma-api.polymarket.com",
    "cache_ttl_seconds": 300
  }
}
```

---

## 7. Estimación de Esfuerzo

| Tarea | Tiempo | Asignación |
|-------|--------|------------|
| `gamma_client.py` | 1-2h | CODEX |
| Integrar en scanner | 2-3h | CODEX |
| Actualizar strategy | 1h | CODEX |
| Tests | 1-2h | CODEX |
| Documentación | 30min | AMP |
| **Total** | **5-8h** | |

---

## 8. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Gamma API no oficial | Fallback a CLOB-only si falla |
| Rate limits Gamma | Cache de 5 min |
| Datos desactualizados | Validar con orderbook CLOB |

---

## 9. Recomendación

**Implementar Opción A (Híbrido)** con la siguiente secuencia:

1. **Fase 1**: Crear `gamma_client.py` básico
2. **Fase 2**: Integrar volumen en scoring (sin cambiar flujo)
3. **Fase 3**: Añadir filtros de liquidez
4. **Fase 4**: Optimizar con cache si necesario

---

## 10. Próximos Pasos

- [ ] CLAUDE: Revisar propuesta arquitectónica
- [ ] CODEX: Implementar `gamma_client.py`
- [ ] GEMINI: Probar integración
- [ ] AMP: Coordinar y documentar

---

**Nota**: Esta propuesta fue elaborada por AMP durante su período de evaluación como Arquitecto suplente.

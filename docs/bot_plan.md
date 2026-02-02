# Plan: Bot Autónomo de Trading - Polymarket (v0.15.1)

## 🎯 Objetivo
Bot que opera de forma autónoma en un VPS, buscando oportunidades (High Probability Harvesting + Whale Copying), gestionando posiciones con take profit/stop loss dinámico y protegiendo el capital.

## 📊 Estado Actual: Fase 4 (Optimización)
- **Versión**: v0.15.1
- **Estrategia**: Híbrida (Scanner + Whale Copy)
- **Modo**: Dry Run (Simulación)
- **Foco**: Maximizar Win Rate (>60%) antes de arriesgar capital real.

## 🔍 Criterios de Selección (Actualizados v0.15.1)

### Filtros de Mercado:
1.  **Odds**: 0.60 - 0.80 (Zona de alta probabilidad).
    *   *Descartado*: 0.30-0.60 por baja rentabilidad en tests.
2.  **Liquidez**: Spread < 5% (Crítico para evitar slippage).
3.  **Volumen**: >$100 (Gamma API) + >$500 volumen 24h.
4.  **Tiempo**: Resolución > 2 días y < 30 días.

### Estrategias Activas:
1.  **Market Scanner**: Busca ineficiencias en rangos de 60-80%.
2.  **Whale Copy Engine**: Replica trades de ballenas probadas (Top 20 volumen).

## 🏗️ Arquitectura del Sistema

```mermaid
graph TD
    A[Main Bot Loop] --> B(Market Scanner)
    A --> C(Whale Copy Engine)
    A --> D(Position Manager)
    
    B -->|Gamma API| E[Market Data]
    B -->|CLOB API| F[Orderbook]
    
    C -->|Data API| G[Whale Trades]
    C -->|Profiler| H[Leaderboard]
    
    D -->|WebSocket| I[Real-time Monitoring]
    I -->|Concurrent Ops| J[Execute TP/SL]
    
    K[Telegram Bot] -->|Commands| A
    L[Telegram Alerts] <-- Events -- A
```

### Componentes Clave:
*   **Scanner**: Híbrido Gamma (Discovery) + CLOB (Trading).
*   **Whale Copy**: Ranking por volumen ponderado, validación de 11 pasos.
*   **Ejecución**: WebSocket para latencia <100ms, órdenes concurrentes (Pre-signed batches).
*   **Gestión**: Scripts unificados (`restart_bot.sh`, `stop_bot.sh`).

## 🔄 Roadmap de Fases (Actualizado)

### ✅ Fase 1: Core & Infraestructura
*   [x] Módulos base (Trader, Position Manager, Config).
*   [x] Gamma API Integration.
*   [x] WebSocket Monitoring.

### ✅ Fase 2: Integración & Testing
*   [x] Telegram Bot & Alerts.
*   [x] Scripts de gestión (Docker/VPS ready).
*   [x] Bug fixes críticos (Stop Loss, Market Resolution).

### ✅ Fase 3: Whale Copy & Dry Run Inicial
*   [x] Motor de copia de ballenas.
*   [x] Dry Run de 14 horas.
*   [x] Análisis de resultados (-$0.23 PnL, ajuste de filtros).

### 🔄 Fase 4: Optimización (ACTUAL)
*   [ ] Validar nuevo rango de odds (0.60-0.80).
*   [ ] Conseguir PnL positivo sostenido en Dry Run.
*   [ ] Afinar thresholds de Whale Copy.

### 🔜 Fase 5: Micro Trading (Live)
*   [ ] Activar dinero real ($0.25 - $0.50 por trade).
*   [ ] Operar 1 semana supervisada.
*   [ ] Escalamiento gradual si ROI > 0.

## ⚙️ Configuración Crítica (`config.json`)

```json
{
  "market_filters": {
    "min_odds": 0.60,
    "max_odds": 0.80,
    "min_days_to_resolve": 2
  },
  "whale_copy_trading": {
    "enabled": true,
    "mode": "hybrid",
    "copy_rules": {
      "copy_position_size": 0.50,
      "max_copies_per_day": 10
    }
  },
  "bot": {
    "dry_run": true,
    "use_websocket": true
  }
}
```

## 🛡️ Líneas de Defensa
1.  **Capital**: Límite diario de pérdida ($3).
2.  **Técnica**: Verificación de Slippage (Walk the Book).
3.  **Lógica**: Filtro de "Días para resolver" (>2).
4.  **Emergencia**: Telegram Alerts en tiempo real.

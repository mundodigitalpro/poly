# Propuesta: Integración de LLM para Mejora de Decisiones del Bot

**Fecha:** 2026-02-03  
**Autor:** Amp (AI Assistant)  
**Estado:** Propuesta  
**Prioridad:** Alta  

---

## 1. Resumen Ejecutivo

El bot de trading actual tiene una estructura sólida (filtros de mercado, TP/SL dinámico, gestión de posiciones), pero **carece de una señal real (edge)** para tomar decisiones de entrada. 

Esta propuesta plantea integrar un LLM (Large Language Model) para:
- Analizar mercados y generar señales de trading
- Evaluar noticias y sentiment en tiempo real
- Validar decisiones antes de ejecutar trades
- Mejorar la selección de mercados con contexto semántico

---

## 2. Problema Actual

### 2.1 Diagnóstico

| Aspecto | Estado Actual | Problema |
|---------|---------------|----------|
| Selección de mercados | Filtros numéricos (odds, volumen, spread) | No considera contexto del evento |
| Señal de entrada | Ninguna (compra si pasa filtros) | Sin edge = trading aleatorio |
| Análisis de riesgo | TP/SL fijo por rango de odds | No considera volatilidad del evento |
| Correlación | No detectada | 5/10 posiciones del mismo evento |

### 2.2 Resultado Observado

- **10 posiciones abiertas**, todas en pérdida
- **Alta correlación**: 5 posiciones relacionadas con Seahawks Super Bowl
- **Sin criterio de entrada**: el bot compra cualquier mercado que pase filtros

---

## 3. Solución Propuesta

### 3.1 Arquitectura de Integración LLM

```
┌─────────────────────────────────────────────────────────────────┐
│                         MAIN BOT LOOP                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   Market    │───▶│   Market    │───▶│    LLM Analyst      │ │
│  │   Scanner   │    │   Filters   │    │    (NEW MODULE)     │ │
│  └─────────────┘    └─────────────┘    └──────────┬──────────┘ │
│                                                    │            │
│                                         ┌──────────▼──────────┐ │
│                                         │  Decision Engine    │ │
│                                         │  - Entry signal     │ │
│                                         │  - Confidence score │ │
│                                         │  - Risk assessment  │ │
│                                         └──────────┬──────────┘ │
│                                                    │            │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────▼──────────┐ │
│  │  Position   │◀───│   Trader    │◀───│   Trade Executor    │ │
│  │  Manager    │    │             │    │   (if confidence    │ │
│  └─────────────┘    └─────────────┘    │    >= threshold)    │ │
│                                         └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Nuevo Módulo: `bot/llm_analyst.py`

```python
"""
LLM Analyst Module - Provides AI-powered market analysis and trading signals.
"""

import os
import json
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class SignalType(Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"
    SKIP = "skip"

@dataclass
class MarketAnalysis:
    signal: SignalType
    confidence: float  # 0.0 - 1.0
    reasoning: str
    risk_factors: list[str]
    suggested_size_multiplier: float  # 0.5 - 2.0
    correlation_warning: Optional[str]

class LLMAnalyst:
    """
    Analyzes markets using LLM for trading decisions.
    """
    
    def __init__(self, config: dict):
        self.provider = config.get("llm.provider", "openai")
        self.model = config.get("llm.model", "gpt-4o-mini")
        self.api_key = os.getenv("LLM_API_KEY")
        self.max_tokens = config.get("llm.max_tokens", 500)
        self.temperature = config.get("llm.temperature", 0.3)
        self.min_confidence = config.get("llm.min_confidence", 0.7)
        
    async def analyze_market(
        self,
        question: str,
        current_odds: float,
        volume_24h: float,
        spread_percent: float,
        days_to_resolve: int,
        current_positions: list[dict],
    ) -> MarketAnalysis:
        """
        Analyze a market and return trading signal with confidence.
        """
        prompt = self._build_analysis_prompt(
            question, current_odds, volume_24h, 
            spread_percent, days_to_resolve, current_positions
        )
        
        response = await self._call_llm(prompt)
        return self._parse_response(response)
    
    async def validate_entry(
        self,
        market: dict,
        proposed_size: float,
        current_portfolio: list[dict],
    ) -> Tuple[bool, str]:
        """
        Final validation before executing a trade.
        Returns (should_trade, reason).
        """
        prompt = self._build_validation_prompt(
            market, proposed_size, current_portfolio
        )
        
        response = await self._call_llm(prompt)
        return self._parse_validation(response)
    
    async def detect_correlations(
        self,
        new_market: dict,
        existing_positions: list[dict],
    ) -> Optional[str]:
        """
        Detect if new market is correlated with existing positions.
        """
        prompt = self._build_correlation_prompt(new_market, existing_positions)
        response = await self._call_llm(prompt)
        return self._parse_correlation(response)
    
    def _build_analysis_prompt(self, question, odds, volume, spread, days, positions) -> str:
        return f"""You are a prediction market trading analyst. Analyze this market and provide a trading signal.

MARKET:
- Question: {question}
- Current odds (YES): {odds:.2%}
- 24h Volume: ${volume:,.0f}
- Spread: {spread:.1f}%
- Days to resolution: {days}

CURRENT PORTFOLIO ({len(positions)} positions):
{self._format_positions(positions)}

TASK:
1. Assess if the current odds represent good value
2. Consider market liquidity and spread
3. Check for correlation with existing positions
4. Provide a trading signal

RESPOND IN JSON:
{{
    "signal": "strong_buy|buy|hold|sell|skip",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "risk_factors": ["factor1", "factor2"],
    "size_multiplier": 0.5-2.0,
    "correlation_warning": "warning if correlated with existing positions, null otherwise"
}}"""

    def _format_positions(self, positions: list[dict]) -> str:
        if not positions:
            return "None"
        return "\n".join([
            f"- {p.get('question', 'Unknown')[:50]}: entry={p.get('entry_price', 0):.2f}"
            for p in positions[:5]
        ])
```

---

## 4. Casos de Uso

### 4.1 Análisis de Mercado Pre-Entrada

```python
# En market_scanner.py o main_bot.py
analyst = LLMAnalyst(config)

for market in filtered_markets:
    analysis = await analyst.analyze_market(
        question=market["question"],
        current_odds=market["best_ask"],
        volume_24h=market["volume_24h"],
        spread_percent=market["spread"],
        days_to_resolve=market["days_to_resolve"],
        current_positions=position_manager.get_all_positions(),
    )
    
    if analysis.signal in [SignalType.BUY, SignalType.STRONG_BUY]:
        if analysis.confidence >= config.get("llm.min_confidence", 0.7):
            # Proceed with trade
            size = base_size * analysis.suggested_size_multiplier
            await trader.execute_buy(market, size)
        else:
            logger.info(f"Skipping {market['question']}: low confidence {analysis.confidence}")
    else:
        logger.info(f"Skipping {market['question']}: signal={analysis.signal.value}")
```

### 4.2 Detección de Correlación

```python
# Antes de abrir nueva posición
correlation = await analyst.detect_correlations(
    new_market=candidate_market,
    existing_positions=current_positions,
)

if correlation:
    # Verificar límite de exposición por cluster
    cluster_exposure = calculate_cluster_exposure(correlation, current_positions)
    if cluster_exposure >= config.get("risk.max_cluster_exposure", 2.0):
        logger.warning(f"Skipping: max exposure reached for cluster '{correlation}'")
        continue
```

### 4.3 Validación Final Pre-Trade

```python
# Última verificación antes de ejecutar
should_trade, reason = await analyst.validate_entry(
    market=market,
    proposed_size=calculated_size,
    current_portfolio=all_positions,
)

if not should_trade:
    logger.info(f"Trade blocked by LLM: {reason}")
    continue
```

### 4.4 Análisis de Noticias (Avanzado)

```python
# Integración con fuentes de noticias
async def analyze_with_news(self, market: dict) -> MarketAnalysis:
    # Buscar noticias recientes sobre el evento
    news = await self.fetch_recent_news(market["question"])
    
    prompt = f"""
    MARKET: {market['question']}
    CURRENT ODDS: {market['odds']:.2%}
    
    RECENT NEWS:
    {self._format_news(news)}
    
    Based on this news, should the odds be higher or lower?
    Is this a trading opportunity?
    """
    
    return await self._call_llm(prompt)
```

---

## 5. Proveedores de LLM

### 5.1 Comparativa

| Proveedor | Modelo | Coste/1K tokens | Latencia | Calidad | Free Tier |
|-----------|--------|-----------------|----------|---------|-----------|
| **OpenAI** | gpt-4o-mini | $0.00015 in / $0.0006 out | ~500ms | Muy buena | No |
| **OpenAI** | gpt-4o | $0.0025 in / $0.01 out | ~1s | Excelente | No |
| **Anthropic** | claude-3-haiku | $0.00025 in / $0.00125 out | ~600ms | Muy buena | No |
| **Google** | gemini-1.5-flash | $0.000075 in / $0.0003 out | ~400ms | Buena | **Sí (gratis)** |
| **Groq** | llama-3.1-8b | Gratis (rate limited) | ~100ms | Aceptable | **Sí** |
| **Ollama** | llama3.2 / mistral | Gratis (local) | Variable | Buena | **Sí (local)** |

### 5.2 Recomendación

**Para desarrollo/testing:**
- **Gemini 1.5 Flash** (gratis, buena calidad)
- **Groq** (gratis, muy rápido)

**Para producción:**
- **gpt-4o-mini** (mejor balance coste/calidad)
- **Claude 3 Haiku** (alternativa comparable)

### 5.3 Coste Estimado en Producción

```
Asumiendo:
- 100 análisis de mercado/día
- ~800 tokens promedio por análisis (prompt + respuesta)
- Usando gpt-4o-mini

Coste diario: 100 × 0.8K × ($0.00015 + $0.0006) = $0.06/día
Coste mensual: ~$1.80/mes

Con gpt-4o (modelo premium):
Coste mensual: ~$30/mes
```

---

## 6. Configuración Propuesta

### 6.1 Nuevas variables en `config.json`

```json
{
  "llm": {
    "enabled": true,
    "provider": "openai",
    "model": "gpt-4o-mini",
    "max_tokens": 500,
    "temperature": 0.3,
    "min_confidence": 0.7,
    "timeout_seconds": 10,
    "retry_attempts": 2,
    "cache_ttl_seconds": 300,
    "fallback_on_error": "skip"
  },
  "llm_rules": {
    "require_analysis_for_entry": true,
    "require_validation_for_large_trades": true,
    "large_trade_threshold": 2.0,
    "detect_correlations": true,
    "max_cluster_exposure": 2.0
  }
}
```

### 6.2 Nuevas variables en `.env`

```bash
# LLM Configuration
LLM_API_KEY=sk-...  # OpenAI API key
# or
GOOGLE_API_KEY=...  # For Gemini
# or
ANTHROPIC_API_KEY=... # For Claude
```

---

## 7. Plan de Implementación

### Fase 1: MVP (1-2 días)
- [ ] Crear `bot/llm_analyst.py` con clase base
- [ ] Implementar `analyze_market()` básico
- [ ] Integrar con un proveedor (recomendado: Gemini por ser gratis)
- [ ] Añadir logging de decisiones LLM
- [ ] Tests unitarios básicos

### Fase 2: Integración (1-2 días)
- [ ] Modificar `main_bot.py` para usar LLMAnalyst
- [ ] Implementar detección de correlaciones
- [ ] Añadir cache de análisis (evitar llamadas repetidas)
- [ ] Métricas de uso y coste

### Fase 3: Validación (3-5 días)
- [ ] Ejecutar en `dry_run` comparando decisiones LLM vs bot actual
- [ ] Analizar tasa de acierto de señales
- [ ] Ajustar prompts según resultados
- [ ] Documentar patrones exitosos

### Fase 4: Producción (1 día)
- [ ] Configurar proveedor de producción
- [ ] Implementar fallbacks y manejo de errores
- [ ] Alertas de Telegram para decisiones LLM
- [ ] Monitoreo de costes

---

## 8. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| API no disponible | Media | Alto | Fallback a reglas actuales |
| Latencia alta | Media | Medio | Cache + timeout + async |
| Coste excesivo | Baja | Medio | Rate limiting + modelo económico |
| Alucinaciones LLM | Media | Alto | Validar JSON + confidence threshold |
| Overfitting a prompts | Media | Medio | A/B testing de prompts |

---

## 9. Métricas de Éxito

### KPIs a Monitorear

1. **Tasa de acierto**: % de señales BUY que resultan en TP vs SL
2. **Sharpe ratio**: Retorno ajustado por riesgo con/sin LLM
3. **Correlación detectada**: % de trades bloqueados por correlación
4. **Coste por trade**: Coste LLM / trades ejecutados
5. **Latencia promedio**: Tiempo de análisis LLM

### Criterio de Go/No-Go para Producción

- Tasa de acierto LLM > 55% en dry_run (2 semanas)
- Coste < $5/mes
- Latencia < 2 segundos promedio

---

## 10. Próximos Pasos

1. **Decisión del equipo**: Aprobar propuesta y seleccionar proveedor
2. **Setup de API key**: Crear cuenta y configurar credenciales
3. **Implementar Fase 1**: Desarrollar módulo base
4. **Testing en dry_run**: Validar durante 1-2 semanas
5. **Revisión de resultados**: Analizar métricas y decidir go-live

---

## Anexo A: Ejemplo de Prompt Completo

```
You are an expert prediction market analyst. Your job is to evaluate trading opportunities.

MARKET ANALYSIS REQUEST:
========================
Question: Will the Seattle Seahawks win Super Bowl 2026?
Current YES odds: 67.9%
24h Volume: $45,230
Bid-Ask Spread: 2.1%
Days to resolution: 5

CURRENT PORTFOLIO (10 positions):
- Seahawks vs. Patriots: entry=0.69, current=0.67 (-2.9%)
- Spread: Seahawks (-5.5): entry=0.48, current=0.47 (-2.1%)
- Spread: Seahawks (-4.5): entry=0.51, current=0.50 (-2.0%)
- Will People's Party win Thai election: entry=0.66, current=0.64 (-3.0%)
- US not strike Iran by Feb 28: entry=0.77, current=0.70 (-9.1%)

EVALUATION CRITERIA:
1. Is the current price good value? Consider implied probability vs your estimate.
2. Is the market liquid enough? (volume, spread)
3. Is there dangerous correlation with existing positions?
4. What is the risk/reward given the time to resolution?

RESPOND IN STRICT JSON FORMAT:
{
    "signal": "strong_buy|buy|hold|sell|skip",
    "confidence": 0.0-1.0,
    "reasoning": "one paragraph explanation",
    "risk_factors": ["list", "of", "risks"],
    "size_multiplier": 0.5-2.0,
    "correlation_warning": "string or null"
}
```

---

## Anexo B: Referencias

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Anthropic Claude API](https://docs.anthropic.com)
- [Google Gemini API](https://ai.google.dev/docs)
- [Polymarket API Documentation](https://docs.polymarket.com)

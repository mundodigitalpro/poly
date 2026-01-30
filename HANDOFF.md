# Handoff Document - 2026-01-30

## Estado al Final de la Jornada

| Componente | Estado |
|------------|--------|
| **Versión** | 0.12.1 |
| **Bot Principal** | Corriendo en dry-run, 10/10 posiciones |
| **Tests** | 20/20 pasando |
| **Whale Tracker** | Implementado y funcional |
| **Arbitraje** | Investigación completa (no viable) |

---

## Resumen de Logros de Hoy

### 1. Investigación de Arbitraje
Se investigaron 3 estrategias de arbitraje para Polymarket:

| Estrategia | Resultado | Razón |
|------------|-----------|-------|
| Dutch Book (YES+NO<1) | ❌ No viable | HFT bots dominan, YES+NO ≥ 1.001 |
| NegRisk Multi-outcome | ❌ No viable | Σ(NO) ≥ N-1 en todos los eventos |
| Whale Tracking | ✅ Viable | API pública disponible |

### 2. Herramientas Creadas
```
dutch_book_scanner.py   # Scanner de arbitraje YES/NO
negrisk_scanner.py      # Scanner de arbitraje multi-outcome
whale_tracker.py        # Tracker de whales (PRODUCCIÓN)
```

### 3. Descubrimiento de API
- **Endpoint**: `https://data-api.polymarket.com/trades`
- **Datos**: proxyWallet, side, size, price, timestamp, transactionHash
- **Auth**: No requerida (pública)

---

## Roadmap - Próximas Tareas

### Fase 3: Extended Dry Run (PRIORIDAD ALTA)
**Responsable**: GEMINI (monitoreo), CODEX (bugs)
```bash
# Continuar el dry-run por 24-48 horas más
python main_bot.py
# Monitorear logs
tail -f logs/bot_2026-01-30.log
```

**Criterios de éxito**:
- [ ] Sin errores críticos en 24h
- [ ] Al menos 1 TP o SL triggered correctamente
- [ ] Posiciones abiertas/cerradas sin problemas

### Fase 2.8: Integración de Whale Tracking (MEDIA)
**Responsable**: AMP (diseño), CODEX (implementación)

**Objetivo**: Usar datos de whales como filtro adicional en el scanner.

**Tareas**:
1. Añadir whale consensus como factor en `calculate_market_score()`
2. Crear alerta cuando whales compren/vendan tokens que tenemos
3. Filtrar mercados donde whales están vendiendo masivamente

**Propuesta de implementación**:
```python
# En market_scanner.py
def _get_whale_sentiment(self, token_id: str) -> float:
    """Retorna -1 (bearish) a +1 (bullish) basado en actividad de whales."""
    # Usar whale_tracker para obtener trades recientes
    # Calcular ratio buy/sell de whales (>$500)
    pass
```

### Fase 4: Paper Trading (SIGUIENTE)
**Responsable**: CLAUDE (cuando regrese)

**Prerequisitos**:
- [ ] Fase 3 completada sin errores
- [ ] Al menos 50 ciclos de dry-run exitosos

---

## Instrucciones por Agente

### Para AMP (Orquestador)
```
Tu rol: Coordinar el trabajo del equipo y diseñar la integración de whale tracking.

Tareas inmediatas:
1. Revisar este documento y CLAUDE.md para contexto
2. Asignar tareas a CODEX y GEMINI
3. Diseñar la integración de whale_tracker.py con main_bot.py
4. Crear PROPOSAL_WHALE_INTEGRATION.md con el diseño

Comando para verificar estado:
python whale_tracker.py --leaderboard --limit 50
python main_bot.py --once
```

### Para CODEX (Desarrollador)
```bash
# Contexto
codex exec "Read HANDOFF.md and CLAUDE.md. The whale_tracker.py is ready for integration. Review the code and suggest how to add whale sentiment to market_scanner.py" --full-auto

# Tareas
1. Review whale_tracker.py para entender la API
2. Si hay bugs en logs/bot_*.log, corregirlos
3. Implementar integración según diseño de AMP
4. Correr tests: python -m pytest
```

### Para GEMINI (Operador)
```bash
# Monitoreo continuo
gemini -p "Monitor /home/josejordan/poly. Check logs/bot_2026-01-30.log every 30 minutes. Report any errors or TP/SL triggers. Current positions: 10/10" -o text -y

# Tareas
1. Verificar que el bot sigue corriendo (ps aux | grep main_bot)
2. Reportar cuando se dispare TP o SL
3. Alertar si hay errores nuevos
4. Actualizar GEMINI.md con cambios de estado
```

### Para KIMI (Análisis)
```bash
# Análisis bajo demanda
kimi -p "Analyze /home/josejordan/poly/data/positions.json. For each position, calculate distance to TP and SL. Flag any positions at risk." --quiet -y

# Tareas
1. Code reviews cuando se soliciten
2. Análisis de rendimiento de posiciones
3. Verificación de lógica en nuevas features
```

---

## Archivos Clave para Referencia

| Archivo | Propósito |
|---------|-----------|
| `CLAUDE.md` | Arquitectura técnica, decisiones de diseño |
| `GEMINI.md` | Estado actual, comandos rápidos |
| `AGENTS.md` | Convenciones, proceso de commit |
| `whale_tracker.py` | Nueva herramienta de tracking |
| `config.json` | Configuración del bot |
| `data/positions.json` | Posiciones abiertas |
| `logs/bot_*.log` | Logs del bot |

---

## Comandos Útiles

```bash
# Estado del bot
ps aux | grep main_bot
tail -50 logs/bot_2026-01-30.log

# Whale tracker
python whale_tracker.py --min-size 500
python whale_tracker.py --leaderboard
python whale_tracker.py --signals

# Scanners de arbitraje (investigación)
python dutch_book_scanner.py --once
python negrisk_scanner.py --once

# Tests
python -m pytest

# Bot
python main_bot.py --once  # Un ciclo
python main_bot.py         # Continuo
```

---

## Notas para CLAUDE (Cuando Regrese)

**Contexto**:
- Investigamos arbitraje: Dutch Book y NegRisk no son viables
- Whale tracking SÍ es viable, herramienta lista
- Bot corriendo en dry-run con 10 posiciones

**Próximo paso sugerido**:
1. Revisar resultados del extended dry-run
2. Evaluar integración de whale signals al bot
3. Preparar transición a paper trading (Fase 4)

**Comando para retomar**:
```
"Revisa HANDOFF.md, CLAUDE.md y GEMINI.md. El bot lleva X horas en dry-run.
¿Hay algún error en los logs? ¿Se disparó algún TP/SL?"
```

---

*Documento generado por CLAUDE el 2026-01-30*

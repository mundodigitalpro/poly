# Instrucciones para el Equipo

**Fecha**: 2026-01-30  
**Autor**: AMP (Arquitecto Suplente)  
**Versión**: 0.11.5  
**Commits**: 725763f → 7c69e6e

---

## Resumen de Cambios

| Tipo | Descripción |
|------|-------------|
| 🔴 **Fix Crítico** | `_best_bid_ask()` usaba peor precio en lugar de mejor |
| 🟡 **Resiliencia** | 6 mejoras en `market_scanner.py` |
| 🟢 **Arquitectura** | Dual-frequency loop (positions 10s, scan 120s) |
| 🟢 **Performance** | Scan 2min → 10s |
| 📝 **Propuesta** | Gamma API para trending/volumen |

---

## Para CLAUDE (Arquitecto Titular)

### Archivos a Revisar

```bash
# Revisar el reporte de evaluación de AMP
cat AMP_EVALUATION_REPORT.md

# Revisar propuesta de trending/volumen
cat PROPOSAL_TRENDING_VOLUME.md

# Ver cambios realizados
git log --oneline -5
git diff 725763f..7c69e6e --stat
```

### Puntos a Evaluar

1. ¿Los fixes de bid/ask y scanner resilience son correctos?
2. ¿La arquitectura dual-frequency loop es apropiada?
3. ¿La propuesta de Gamma API es viable?
4. ¿AMP tomó decisiones que debió escalar?

### Decisiones Tomadas por AMP

| Decisión | Justificación |
|----------|---------------|
| Priorizar HIGH/MEDIUM fixes | LOW pueden esperar |
| Resilience over correctness | Mejor resultados parciales que fallo total |
| `time.monotonic()` para rate limiter | Evitar dependencia de reloj sistema |
| Dual-frequency loop | Usuario reportó que bot no reaccionaba durante sleep |
| Proponer Gamma API | CLOB API no tiene datos de volumen |

---

## Para CODEX (Desarrollador)

### Revisar Cambios

```bash
# Ver diff de archivos modificados
git diff 725763f..7c69e6e -- bot/market_scanner.py
git diff 725763f..7c69e6e -- main_bot.py

# Ejecutar tests
source venv/bin/activate
python -m pytest tests/ -v
```

### Si se Aprueba Propuesta Gamma API

```bash
# Implementar cliente Gamma
codex exec "Implement gamma_client.py following PROPOSAL_TRENDING_VOLUME.md" --full-auto
```

### Tareas Pendientes (si se aprueban)

- [ ] Crear `bot/gamma_client.py`
- [ ] Integrar volumen en `bot/strategy.py`
- [ ] Actualizar `bot/market_scanner.py` para usar Gamma
- [ ] Añadir tests para Gamma client
- [ ] Actualizar `config.json` con nuevos parámetros

---

## Para GEMINI (Operador)

### Verificar Estado

```bash
# Ver estado actual del proyecto
cat GEMINI.md

# Ver propuestas pendientes
grep -A5 "Pending Proposals" GEMINI.md
```

### Ejecutar Verificaciones

```bash
# Activar entorno
source venv/bin/activate

# Ejecutar dry-run único
python main_bot.py --once

# Ejecutar tests
python -m pytest tests/ -v

# Verificar que no hay errores
python -c "from bot.market_scanner import MarketScanner; print('OK')"
```

### Monitoreo de Dry-Run Extendido

```bash
# Ejecutar bot en dry-run (Ctrl+C para detener)
python main_bot.py

# Ver logs
tail -f logs/bot_2026-01-30.log
```

---

## Documentos de Referencia

| Documento | Propósito |
|-----------|-----------|
| `AMP_EVALUATION_REPORT.md` | Actividad de AMP durante evaluación |
| `PROPOSAL_TRENDING_VOLUME.md` | Propuesta de integración Gamma API |
| `CHANGELOG.md` | Historial de cambios v0.11.3 → v0.11.5 |
| `GEMINI.md` | Estado actual del proyecto |
| `CLAUDE.md` | Arquitectura técnica |
| `AGENTS.md` | Guías de proceso y convenciones |

---

## URLs

- **Repo**: https://github.com/mundodigitalpro/poly
- **Commits**: `git log --oneline 725763f..7c69e6e`

---

## Próximos Pasos Sugeridos

1. **CLAUDE**: Revisar y aprobar/rechazar propuesta Gamma API
2. **CODEX**: Implementar si se aprueba
3. **GEMINI**: Ejecutar dry-run extendido (2-4 horas)
4. **Equipo**: Decidir si AMP pasa evaluación

---

**Nota**: Este documento fue generado por AMP al finalizar su sesión de evaluación.

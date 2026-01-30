# Plan de Recuperación y Optimización del Bot (2026-01-30)

Este documento detalla el análisis del incidente ocurrido durante la prueba de 7hs y los pasos a seguir para corregir los fallos críticos detectados.

## 1. Análisis del Incidente
**Evento:** Reinicio inesperado del sistema durante el test de larga duración.
**Hallazgo Crítico en Logs:**
Se observó una repetición sistemática de errores bloqueantes al intentar ejecutar Stop Losses:
```text
ERROR - Sell failed for [TOKEN]...: Sell price 0.0010 below minimum allowed 0.1510
```

### Diagnóstico de Causa Raíz
1.  **Bloqueo de Seguridad Mal Diseñado:** En `bot/trader.py`, el método `execute_sell` impone una restricción rígida:
    ```python
    min_price = entry_price * self.min_sell_ratio  # Default ratio = 0.5
    if price < min_price: raise ValueError(...)
    ```
2.  **Colapso del Stop Loss:** Cuando una posición cae más del 50% (ej. de 0.30 a 0.01 por falta de liquidez o crash), el bot **se niega a vender** para protegerse, lo cual es el comportamiento opuesto al deseado en un Stop Loss (donde la prioridad es salir a cualquier precio).
3.  **Consecuencia:** El bot acumula posiciones "tóxicas" con pérdidas del >90% y agota su capacidad operativa (`max_positions reached`).

## 2. Estrategia de Solución

### A. Corrección Inmediata (Hotfix)
El objetivo es permitir que el Stop Loss se ejecute siempre, independientemente de la caída del precio.
*   **Modificar `bot/trader.py`:** Añadir un parámetro opcional `bypass_safety_checks=False` a `execute_sell`.
*   **Lógica:** Si es una venta de emergencia (STOP_LOSS), ignorar `min_sell_ratio`.

### B. Mejora de la Estrategia de Entrada
El hecho de que tengamos posiciones cayendo a 0.001 o 0.01 sugiere que estamos entrando en mercados sin liquidez o muy volátiles.
*   **Revisar `market_scanner.py`:** Endurecer los filtros de liquidez mínima y spread antes de entrar.

## 3. Plan de Trabajo y Asignación

### CLAUDE (Arquitecto)
- [x] Validar si la lógica de `min_sell_ratio` tiene sentido mantenerla para Take Profits o ventas normales.
  - **Decisión**: SÍ, mantenerla para TP y ventas normales. Solo bypass para Stop Loss.
- [ ] Definir el umbral de liquidez mínima para evitar "rug pulls" o crashes a 0.
  - **Pendiente**: Revisar filtros de `market_scanner.py` para fase posterior.

### CODEX (Desarrollador)
- [x] **Implementar Fix en `bot/trader.py`**:
    - Añadido `is_emergency_exit: bool = False` a `execute_sell()`.
    - Actualizado `main_bot.py:166` para pasar flag en Stop Loss (no `position_manager.py`).
- [x] **Test**: Creado `tests/test_stop_loss_emergency_exit.py` - simula caída 90%, test PASSED.

### GEMINI (Operador)
- [x] **Ejecución**: Cambios aplicados por CODEX.
- [ ] **Limpieza**: Ejecutar el bot en modo `dry-run` para verificar posiciones.
- [ ] **Documentación**: Registrar el incidente y fix en `CHANGELOG.md`.

## 4. Pasos Siguientes
1.  Aplicar el parche en `trader.py`.
2.  Verificar limpieza de posiciones.
3.  Reiniciar el test de estabilidad (monitorizando las primeras 2 horas).

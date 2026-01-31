# 🔄 Cómo Reiniciar el Bot

**Última actualización**: 2026-01-31

---

## ⚡ Reinicio Rápido (Recomendado)

### Opción 1: Script Automático

```bash
cd /home/user/poly
bash scripts/restart_bot.sh
```

**Esto hará**:
1. ✅ Detiene el bot actual de forma segura
2. ✅ Descarga los últimos cambios del repo
3. ✅ Verifica la configuración (filtros, dry_run, etc.)
4. ✅ Reinicia el bot con la nueva configuración

---

## 🛑 Solo Detener el Bot

Si solo quieres detener el bot sin reiniciar:

```bash
bash scripts/stop_bot.sh
```

O manualmente:

```bash
# Encontrar el proceso
pgrep -f "python.*main_bot.py"

# Detener con Ctrl+C limpio
pkill -SIGINT -f "python.*main_bot.py"

# O forzar si no responde
pkill -9 -f "python.*main_bot.py"
```

---

## 🔧 Reinicio Manual (Paso a Paso)

### 1. Detener el bot actual

```bash
# Si está en terminal activa: presiona Ctrl+C

# Si está en background:
pkill -SIGINT -f "python.*main_bot.py"

# Verificar que se detuvo
pgrep -f "python.*main_bot.py" || echo "✓ Bot detenido"
```

### 2. Descargar últimos cambios

```bash
cd /home/user/poly
git pull origin claude/investigate-article-implementation-CG7Bb
```

### 3. Verificar configuración

```bash
# Ver configuración actual
cat config.json | grep -A 10 "market_filters"
cat config.json | grep -A 5 "trading"

# Verificar que el fix esté activo
grep "min_days_to_resolve" config.json
```

**Deberías ver**:
```json
"min_days_to_resolve": 2,
```

### 4. Iniciar el bot

```bash
python main_bot.py
```

---

## ⚙️ Verificar Configuración Antes de Reiniciar

### Verificación rápida

```bash
bash scripts/quick_validate_fix.sh
```

### Verificación manual

```bash
# Ver filtros de mercado
grep -A 15 "market_filters" config.json

# Ver configuración de trading
grep -A 10 "trading" config.json
```

**Configuración recomendada**:
```json
{
  "market_filters": {
    "min_days_to_resolve": 2,    ← NUEVO: evita mercados resueltos
    "max_days_to_resolve": 30,
    "min_volume_24h": 500,
    "min_liquidity": 1000
  },
  "trading": {
    "use_concurrent_orders": true,
    "use_websocket": true,
    "dry_run": true              ← true = no trading real
  }
}
```

---

## 📊 Qué Monitorear Después del Reinicio

### Logs en tiempo real

```bash
# Ver logs del bot
tail -f logs/bot_monitor_*.log

# Filtrar solo candidatos aceptados/rechazados
tail -f logs/bot_monitor_*.log | grep -E "Candidate|Rejected"
```

### Verificar que el filtro funciona

**Deberías ver en los logs**:

✅ **Mercados aceptados** (con días >= 2):
```
[INFO] ✓ Candidate: Will Bitcoin hit $100k... |
       token=21742633... | odds=0.52 | spread=3.8% |
       days=7 | score=82.3
```

✅ **Mercados rechazados** (con días < 2):
```
[INFO] Rejected 12345678: resolves too soon (days=1 < 2)
```

❌ **NO deberías ver**:
```
[INFO] ✓ Candidate: ... | days=1 | score=...  ← Malo, días < 2
[INFO] ✓ Candidate: ... | days=0 | score=...  ← Muy malo
```

---

## 🚨 Troubleshooting

### El bot no se detiene

```bash
# Forzar detención
pkill -9 -f "python.*main_bot.py"

# Verificar
ps aux | grep "main_bot.py"
```

### El bot no arranca después de reiniciar

**Error común**: Dependencias faltantes

```bash
# Instalar dependencias
pip install -r requirements.txt
```

**Error común**: .env no configurado

```bash
# Verificar que existe
ls -la .env

# Si no existe, copiar ejemplo
cp .env.example .env

# Editar con tus credenciales
nano .env
```

### El filtro no parece funcionar

```bash
# Ejecutar diagnóstico
python tools/diagnose_market_filters.py

# Verificar que min_days_to_resolve esté en config
grep "min_days_to_resolve" config.json

# Si no aparece, añadirlo manualmente
nano config.json
# Añadir: "min_days_to_resolve": 2,
```

---

## 📝 Checklist de Reinicio

- [ ] Detener bot actual (`pkill` o `Ctrl+C`)
- [ ] Pull últimos cambios (`git pull`)
- [ ] Verificar `min_days_to_resolve: 2` en config
- [ ] Verificar `dry_run: true` si quieres testing
- [ ] Reiniciar bot (`python main_bot.py`)
- [ ] Monitorear logs (`tail -f logs/bot_monitor_*.log`)
- [ ] Verificar que aparezcan "Rejected: resolves too soon"
- [ ] Verificar que candidatos tengan `days >= 2`

---

## 🎯 Reinicio para Diferentes Escenarios

### Escenario 1: Testing del fix (Recomendado primero)

```bash
# 1. Asegurar dry_run=true en config.json
nano config.json
# Cambiar: "dry_run": true

# 2. Reiniciar
bash scripts/restart_bot.sh

# 3. Monitorear 1-2 horas
tail -f logs/bot_monitor_*.log | grep -E "Candidate|Rejected"

# 4. Verificar que no entren mercados con days < 2
```

### Escenario 2: Micro-trading con fix validado

```bash
# 1. Configurar para trading mínimo
nano config.json
# Cambiar:
# "dry_run": false
# "max_trade_size": 0.10
# "max_positions": 2

# 2. Reiniciar con confirmación
bash scripts/restart_bot.sh

# 3. Monitorear MUY de cerca
tail -f logs/bot_monitor_*.log
```

### Escenario 3: Volver a dry-run

```bash
# 1. Detener bot
bash scripts/stop_bot.sh

# 2. Cambiar a dry_run
nano config.json
# Cambiar: "dry_run": true

# 3. Reiniciar
python main_bot.py
```

---

## 💡 Tips Útiles

### Ver estado actual sin detener

```bash
# Ver si está corriendo
pgrep -f "python.*main_bot.py" && echo "✓ Bot corriendo" || echo "✗ Bot detenido"

# Ver últimas líneas de log
tail -50 logs/bot_monitor_*.log
```

### Reinicio en background

```bash
# Iniciar en background
nohup python main_bot.py > logs/bot_output.log 2>&1 &

# Ver logs
tail -f logs/bot_output.log
```

### Reinicio automático con cron (avanzado)

```bash
# Editar crontab
crontab -e

# Añadir (reinicia cada día a las 3 AM)
0 3 * * * cd /home/user/poly && bash scripts/restart_bot.sh >> logs/cron_restart.log 2>&1
```

---

## 🔗 Scripts Disponibles

| Script | Comando | Descripción |
|--------|---------|-------------|
| **Reinicio completo** | `bash scripts/restart_bot.sh` | Detiene, actualiza y reinicia |
| **Solo detener** | `bash scripts/stop_bot.sh` | Detiene el bot de forma segura |
| **Validar fix** | `bash scripts/quick_validate_fix.sh` | Verifica que el fix esté activo |
| **Diagnóstico** | `python tools/diagnose_market_filters.py` | Analiza mercados en tiempo real |

---

## ❓ FAQ

**P: ¿Pierdo posiciones al reiniciar?**
R: No. Las posiciones están en `data/positions.json` y se cargan al iniciar.

**P: ¿Cuánto tarda el reinicio?**
R: ~5-10 segundos (detener, pull, iniciar).

**P: ¿Puedo reiniciar con posiciones abiertas?**
R: Sí. El bot retoma el monitoreo de posiciones al iniciar.

**P: ¿El filtro se aplica a posiciones ya abiertas?**
R: No. Solo afecta nuevas entradas. Las posiciones existentes se siguen monitoreando.

**P: ¿Debo limpiar data/positions.json antes de reiniciar?**
R: Solo si las posiciones son de mercados ya resueltos (para testing limpio).

---

**Comando más usado**:

```bash
bash scripts/restart_bot.sh
```

¡Eso es todo! 🚀

# Kimi Agent Integration Proposal

**Date:** 2026-02-03  
**Status:** Draft  
**Author:** AI Team (Amp + Oracle)  
**Reviewed by:** Kimi (Moonshot AI)

## Overview

Integrate **Kimi** (Moonshot AI CLI agent) into the existing multi-agent collaboration system. This extends our current Claude/Codex/Gemini team with a fourth agent.

## Kimi CLI Summary

| Aspect | Details |
|--------|---------|
| **CLI Tool** | `kimi` |
| **Non-Interactive Command** | `kimi -p "message" --print` |
| **Auto-Approve Flag** | `-y` / `--yolo` (nota: `--print` ya lo incluye implícitamente) |
| **Session Continuity** | `-C` (continue) o `-S <session_id>` |
| **Documentation** | https://moonshotai.github.io/kimi-cli/ |
| **Prerrequisito** | `kimi login` (requiere autenticación previa) |

## Recommended Integration Pattern

### Default Mode: Stateless, Non-Interactive

```bash
kimi -p "YOUR_PROMPT" --print
```

**Rationale:**
- Deterministic (no hidden prior context)
- Easy to capture stdout
- `--print` incluye implícitamente `--yolo` (auto-aprobar acciones)
- Mirrors existing `codex exec …` and `gemini -p …` patterns

### Session Mode (Optional)

Use explicit session IDs only when multi-turn continuity is required:

```bash
kimi -p "message" --print -S "kimi-bot-risk"
```

**Guardrail:** Never rely on implicit default sessions.

## Updated Inter-Agent Communication Table

| Agent | CLI Tool | Non-Interactive Command | Auto-Approve | Best Use | Version |
|-------|----------|-------------------------|--------------|----------|---------|
| Claude | `claude` | Already in session | N/A | Architecture, decisions | Opus 4.5 |
| Codex | `codex` | `codex exec "msg" --full-auto` | `--full-auto` | Implementation, refactors | 0.92.0 |
| Gemini | `gemini` | `gemini -p "msg" -o text` | `-y` | Status, context queries | 0.26.0 |
| **Kimi** | `kimi` | `kimi -p "msg" --print` | `--print` incluye auto-approve | Fast review, analysis | Latest |

## Communication Examples

```bash
# Claude asking Kimi for a code review
kimi -p "Review bot/trader.py changes for risk/safety issues. Focus on order placement edge cases." --print

# Save Kimi output to file
kimi -p "Summarize the new TP/SL logic and potential failure modes." --print > /tmp/kimi_review.txt

# Kimi asking Codex to implement a fix
codex exec "Implement the fix for the race condition in position_manager.py that Kimi identified" --full-auto

# Kimi querying Gemini for project state
gemini -p "What is the current phase and any blockers?" -o text

# Using the unified wrapper (recommended)
./scripts/ask_agent.sh kimi "Review this code for security issues" /tmp/review.txt
```

## Kimi's Role in the Team

Dadas sus capacidades, Kimi se enfoca en:

1. **Code reviews rápidos** - Análisis de seguridad y edge cases
2. **Resumen de cambios** - Sintetizar PRs complejos
3. **Análisis de riesgo** - Revisar lógica de trading/órdenes
4. **Debugging paralelo** - Investigación de issues sin interferir con el flujo principal

**Nota:** Kimi complementa al equipo sin reemplazar - aporta análisis crítico adicional cuando sea necesario.

## Risks and Guardrails

| Risk | Impact | Guardrail |
|------|--------|-----------|
| **Session state drift** | Non-reproducible behavior | Default to stateless `--print`; explicit session IDs when needed |
| **Auto-approval safety** | Unintended repo modifications | Restrict Kimi to analysis/review roles; no file-modifying actions with `--print` |
| **Output formatting** | Inconsistent stdout capture | Standardize on `--print`; redirect to files for long outputs |
| **CLI flag drift** | Breaking changes across versions | Pin version in docs once stable |
| **Secrets leakage** | Keys exposed in prompts/logs | Never paste secrets; use redaction |
| **Authentication** | Kimi requires `kimi login` | Document in setup; verify before first use |

## Implementation Checklist

### P0 (Must have)
- [x] Crear propuesta de integración
- [x] Crear script `scripts/ask_agent.sh` para llamadas unificadas
- [x] Verificar Kimi CLI instalado (v1.6)
- [x] Actualizar `AGENTS.md` Inter-Agent Communication table to include Kimi
- [x] Verificar `kimi login` está configurado
- [x] Test: `kimi -p "hola equipo" --print`

### P1 (Should have)
- [ ] Update `CLAUDE.md` to use consistent Kimi command (`--print`)
- [ ] Update `GEMINI.md` Inter-Agent Communication section to add Kimi
- [ ] Añadir ejemplos de uso en documentación

### P2 (Nice to have)
- [ ] Script de test de conectividad entre agentes
- [ ] Pin Kimi CLI version once determined
- [ ] Add Kimi to team member list in all three memory files

## Unified Agent Wrapper Script

El script `scripts/ask_agent.sh` normaliza las llamadas a todos los agentes:

```bash
# Uso básico
./scripts/ask_agent.sh <agent> "<prompt>" [output_file]

# Ejemplos
./scripts/ask_agent.sh kimi "Review bot/trader.py for security issues"
./scripts/ask_agent.sh codex "Refactor position_manager.py" 
./scripts/ask_agent.sh gemini "What's the current status?" /tmp/status.txt
```

Ver archivo: [`scripts/ask_agent.sh`](/scripts/ask_agent.sh)

## When to Consider Advanced Path

Move beyond CLI-based integration only if:
- Automated multi-agent workflows in CI (e.g., PR bot running Kimi reviews)
- Structured JSON outputs needed for downstream tooling
- Frequent human errors in flags/quoting require enforcement

## Quick Start for Team Members

```bash
# 1. Instalar Kimi CLI (si no está instalado)
pip install kimi-cli

# 2. Autenticar
kimi login

# 3. Verificar funcionamiento
kimi -p "Hola equipo, soy Kimi" --print

# 4. Usar el wrapper
./scripts/ask_agent.sh kimi "Review the latest changes"
```

## Approval

- [x] Kimi (Self-review - CLI compatibility verified)
- [ ] Claude (Architecture review)
- [ ] Codex (Implementation feasibility)
- [ ] Gemini (Documentation consistency)
- [ ] Human team lead

---

*Generated by Amp with Oracle consultation*  
*Reviewed and updated by Kimi (Moonshot AI)*

#!/usr/bin/env bash
#
# Unified Agent Wrapper Script
# 
# Normaliza las llamadas a los diferentes agentes del equipo:
# - Claude: Arquitectura y decisiones
# - Codex: Implementación y refactors
# - Gemini: Estado y consultas de contexto
# - Kimi: Reviews rápidos y análisis
#
# Uso:
#   ./scripts/ask_agent.sh <agent> "<prompt>" [output_file]
#
# Ejemplos:
#   ./scripts/ask_agent.sh kimi "Review bot/trader.py for security issues"
#   ./scripts/ask_agent.sh codex "Refactor position_manager.py"
#   ./scripts/ask_agent.sh gemini "What's the current status?"
#   ./scripts/ask_agent.sh kimi "Analyze risk in order placement" /tmp/risk_analysis.txt
#

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Funciones de utilidad
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

# Mostrar uso
usage() {
    cat << EOF
Unified Agent Wrapper Script

Uso: $0 <agent> "<prompt>" [output_file]

Agentes disponibles:
  kimi      - Reviews rápidos, análisis de seguridad
  codex     - Implementación, refactors de código
  gemini    - Consultas de estado, contexto del proyecto
  claude    - (Interactivo) Arquitectura, decisiones complejas

Opciones:
  -h, --help     Mostrar esta ayuda
  -t, --test     Modo test: verificar conectividad sin ejecutar
  -v, --verbose  Modo verbose

Ejemplos:
  $0 kimi "Review bot/trader.py for security issues"
  $0 codex "Refactor position_manager.py extract methods"
  $0 gemini "What's the current phase and blockers?"
  $0 kimi "Analyze order placement risks" /tmp/analysis.txt

Notas:
  - Kimi requiere 'kimi login' previo
  - Claude es interactivo por defecto (no soporta --print)
  - Para output a archivo, especificar como tercer argumento

EOF
}

# Verificar que un comando existe
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "Comando '$1' no encontrado. Instálalo primero."
        return 1
    fi
    return 0
}

# Verificar conectividad con un agente
test_agent() {
    local agent=$1
    log_info "Testeando conectividad con $agent..."
    
    case $agent in
        kimi)
            if ! check_command "kimi"; then
                log_error "Kimi CLI no instalado. Ejecuta: pip install kimi-cli"
                return 1
            fi
            # Test simple - verificar que hay alguna respuesta de texto
            local kimi_output
            kimi_output=$(kimi -p "responde OK" --print 2>/dev/null | grep -E "TextPart|text=" | head -1)
            if [ -n "$kimi_output" ]; then
                log_success "Kimi responde correctamente"
                return 0
            else
                log_error "Kimi no responde. Verifica 'kimi login'"
                return 1
            fi
            ;;
        codex)
            if ! check_command "codex"; then
                log_error "Codex CLI no instalado"
                return 1
            fi
            log_warn "Codex no soporta modo non-interactivo para test"
            log_info "Codex está instalado pero requiere interacción"
            return 0
            ;;
        gemini)
            if ! check_command "gemini"; then
                log_error "Gemini CLI no instalado"
                return 1
            fi
            # Test simple
            if gemini -p "ping" -o text 2>/dev/null | head -1 | grep -q "."; then
                log_success "Gemini responde correctamente"
                return 0
            else
                log_error "Gemini no responde. Verifica configuración"
                return 1
            fi
            ;;
        claude)
            if ! check_command "claude"; then
                log_error "Claude CLI no instalado"
                return 1
            fi
            log_warn "Claude es interactivo por naturaleza"
            log_info "Claude está instalado"
            return 0
            ;;
        *)
            log_error "Agente desconocido: $agent"
            return 1
            ;;
    esac
}

# Ejecutar comando del agente
execute_agent() {
    local agent=$1
    local prompt=$2
    local output_file=${3:-}
    local verbose=${4:-false}
    
    local cmd=""
    local working_dir="$PROJECT_ROOT"
    
    case $agent in
        kimi)
            # Kimi: stateless, non-interactive
            # --print incluye auto-approve implícitamente
            cmd="kimi -p \"$prompt\" --print"
            ;;
        codex)
            # Codex: non-interactive con full-auto
            cmd="codex exec \"$prompt\" --full-auto"
            ;;
        gemini)
            # Gemini: non-interactive con auto-approve
            cmd="gemini -p \"$prompt\" -o text -y"
            ;;
        claude)
            log_error "Claude no soporta modo non-interactivo"
            log_info "Ejecuta directamente: claude"
            return 1
            ;;
        *)
            log_error "Agente desconocido: $agent"
            log_info "Agentes disponibles: kimi, codex, gemini, claude (interactivo)"
            return 1
            ;;
    esac
    
    # Ejecutar
    if [ "$verbose" = true ]; then
        log_info "Ejecutando: $cmd"
        log_info "Directorio: $working_dir"
    fi
    
    cd "$working_dir"
    
    if [ -n "$output_file" ]; then
        # Redirigir a archivo
        eval "$cmd" > "$output_file" 2>&1
        local exit_code=$?
        if [ $exit_code -eq 0 ]; then
            log_success "Output guardado en: $output_file"
        else
            log_error "Error al ejecutar (exit code: $exit_code)"
        fi
        return $exit_code
    else
        # Mostrar en stdout
        eval "$cmd"
        return $?
    fi
}

# Main
main() {
    local test_mode=false
    local verbose=false
    local agent=""
    local prompt=""
    local output_file=""
    
    # Parsear argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -t|--test)
                test_mode=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -*)
                log_error "Opción desconocida: $1"
                usage
                exit 1
                ;;
            *)
                if [ -z "$agent" ]; then
                    agent=$1
                elif [ -z "$prompt" ]; then
                    prompt=$1
                elif [ -z "$output_file" ]; then
                    output_file=$1
                else
                    log_error "Demasiados argumentos"
                    usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Validar argumentos mínimos
    if [ -z "$agent" ]; then
        log_error "Agente no especificado"
        usage
        exit 1
    fi
    
    # Convertir a lowercase
    agent=$(echo "$agent" | tr '[:upper:]' '[:lower:]')
    
    # Modo test
    if [ "$test_mode" = true ]; then
        test_agent "$agent"
        exit $?
    fi
    
    # Validar prompt
    if [ -z "$prompt" ]; then
        log_error "Prompt no especificado"
        usage
        exit 1
    fi
    
    # Ejecutar
    execute_agent "$agent" "$prompt" "$output_file" "$verbose"
}

# Ejecutar main
main "$@"

#!/usr/bin/env bash
#
# Multi-Agent Interactive Chat
#
# Permite conversaciones interactivas entre Kimi, Gemini, Claude, Codex y el usuario.
# Los agentes tienen acceso al contexto actual del proyecto leyendo GEMINI.md.
#
# Uso:
#   ./scripts/agent_chat.sh "Instrucción inicial"
#   ./scripts/agent_chat.sh  # Modo interactivo
#

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
ORANGE='\033[0;33m'
NC='\033[0m'

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
SESSION_MARKER="$LOG_DIR/agent_chat_last.txt"
HISTORY_FILE=""
PREV_HISTORY_FILE=""
CONTEXT_FILE="$PROJECT_ROOT/GEMINI.md"
CONTEXT_LINES="${CONTEXT_LINES:-50}"
CLAUDE_CONFIG="/home/josejordan/.claude"
TURN_COUNT=0
ACTIVE_AGENT="kimi"
KIMI_TIMEOUT="${KIMI_TIMEOUT:-25}"
GEMINI_TIMEOUT="${GEMINI_TIMEOUT:-25}"
CLAUDE_TIMEOUT="${CLAUDE_TIMEOUT:-30}"
CODEX_TIMEOUT="${CODEX_TIMEOUT:-45}"
STREAM_MODE="${STREAM_MODE:-1}"  # 1=streaming, 0=buffered
RUN_CMD_EXIT=0

mkdir -p "$LOG_DIR"

# Inicializar historial
init_history_files() {
    if [ -f "$SESSION_MARKER" ]; then
        PREV_HISTORY_FILE="$(cat "$SESSION_MARKER")"
    fi
    HISTORY_FILE="$LOG_DIR/chat_history_$(date +%Y%m%d_%H%M%S).txt"
    echo "$HISTORY_FILE" > "$SESSION_MARKER"
    touch "$HISTORY_FILE"
}

# Reanudar historial previo o específico
resume_history() {
    local target="${1:-}"
    if [ -n "$target" ]; then
        if [ -f "$target" ]; then
            HISTORY_FILE="$target"
            echo "$HISTORY_FILE" > "$SESSION_MARKER"
            echo -e "${GREEN}Reanudado: $HISTORY_FILE${NC}"
            return 0
        fi
        echo -e "${RED}No existe: $target${NC}"
        return 1
    fi
    if [ -n "${PREV_HISTORY_FILE:-}" ] && [ -f "$PREV_HISTORY_FILE" ]; then
        HISTORY_FILE="$PREV_HISTORY_FILE"
        echo "$HISTORY_FILE" > "$SESSION_MARKER"
        echo -e "${GREEN}Reanudado: $HISTORY_FILE${NC}"
        return 0
    fi
    echo -e "${RED}No hay sesión previa para reanudar.${NC}"
    return 1
}

# Escribir historial con lock si es posible
write_history() {
    local line="$1"
    if command -v flock >/dev/null 2>&1; then
        (
            flock -x 200
            echo "$line" >> "$HISTORY_FILE"
        ) 200>/tmp/.agent_chat_lock
    else
        echo "$line" >> "$HISTORY_FILE"
    fi
}

# Ejecutar comandos con timeout si existe
run_cmd_capture() {
    local timeout_s="$1"
    shift
    local out
    local code
    if command -v timeout >/dev/null 2>&1; then
        out=$(timeout "${timeout_s}s" "$@" 2>&1)
        code=$?
    else
        out=$("$@" 2>&1)
        code=$?
    fi
    RUN_CMD_EXIT=$code
    printf '%s' "$out"
    return 0
}

# Ejecutar comandos en modo streaming (tiempo real)
run_cmd_stream() {
    local timeout_s="$1"
    shift
    local code
    if command -v timeout >/dev/null 2>&1; then
        timeout "${timeout_s}s" "$@" 2>&1
        code=$?
    else
        "$@" 2>&1
        code=$?
    fi
    RUN_CMD_EXIT=$code
    return 0
}

# Limpiar al salir
cleanup() {
    echo -e "\n${YELLOW}Sesión finalizada. Historial guardado en: $HISTORY_FILE${NC}"
}
trap cleanup EXIT

# Cargar contexto dinámico desde GEMINI.md (Primeras 50 líneas para resumen)
get_project_context() {
    if [ -f "$CONTEXT_FILE" ]; then
        head -n "$CONTEXT_LINES" "$CONTEXT_FILE"
    else
        echo "Contexto no disponible."
    fi
}

# Mostrar banner
show_banner() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}        ${WHITE}Multi-Agent Interactive Chat${NC}                        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}     ${MAGENTA}Kimi${NC} 🤖 ${BLUE}Gemini${NC} 💎 ${ORANGE}Claude${NC} 🧠 ${RED}Codex${NC} 📝 + ${GREEN}Tú${NC} 👤          ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo -e "${WHITE}Historial: $HISTORY_FILE${NC}"
    echo ""
}

# Mostrar ayuda
show_help() {
    local stream_status
    [ "$STREAM_MODE" == "1" ] && stream_status="ON" || stream_status="OFF"
    echo -e "${WHITE}Comandos disponibles:${NC}"
    echo -e "  ${MAGENTA}/kimi${NC} <msg>    Enviar mensaje a Kimi"
    echo -e "  ${BLUE}/gemini${NC} <msg> Enviar mensaje a Gemini"
    echo -e "  ${ORANGE}/claude${NC} <msg> Enviar mensaje a Claude"
    echo -e "  ${RED}/codex${NC} <msg>  Enviar mensaje a Codex"
    echo -e "  ${YELLOW}/both${NC} <msg>   Enviar a Kimi y Gemini"
    echo -e "  ${CYAN}/all${NC} <msg>    Enviar a todos los agentes"
    echo -e "  ${CYAN}/switch${NC}       Cambiar agente activo (actual: $ACTIVE_AGENT)"
    echo -e "  ${CYAN}/stream${NC}       Alternar modo streaming (actual: $stream_status)"
    echo -e "  ${CYAN}/resume${NC} [path] Reanudar sesión previa o específica"
    echo -e "  ${CYAN}/context${NC} [edit] Ver o editar contexto"
    echo -e "  ${WHITE}/status${NC}       Ver estado"
    echo -e "  ${RED}/quit${NC}         Salir"
    echo ""
}

# Obtener historial reciente para el prompt
get_history() {
    if [ -f "$HISTORY_FILE" ]; then
        tail -15 "$HISTORY_FILE" | sed 's/^/  /'
    else
        echo "  (sin historial previo)"
    fi
}

# Wrapper genérico para llamar agentes
call_agent_generic() {
    local agent_name="$1"
    local prompt="$2"
    local color="$3"
    local icon="$4"
    local cmd_func="$5"

    local history
    history=$(get_history)
    local project_context
    project_context=$(get_project_context)

    local full_context="Eres $agent_name en un chat multiagente con otros IAs y un humano.
Proyecto: Trading Bot Polymarket (/home/josejordan/poly).
Responde MUY conciso (2-3 frases max). Si necesitas info, pregunta.

CONTEXTO ACTUAL DEL PROYECTO:
$project_context

HISTORIAL RECIENTE:
$history

NUEVO MENSAJE:"

    if [ "$STREAM_MODE" == "1" ]; then
        # Modo streaming: mostrar en tiempo real con tee para capturar
        echo -e "${color}${icon} $agent_name:${NC}" >&2
        local tmp_response
        tmp_response=$(mktemp)
        $cmd_func "$full_context" "$prompt" 2>&1 | tee "$tmp_response" >&2
        local response
        response=$(cat "$tmp_response" | tr '\n' ' ' | sed 's/  */ /g')
        rm -f "$tmp_response"
        
        if [ -z "$response" ] || [ "$response" == "null" ]; then
            response="[Sin respuesta de $agent_name]"
        fi
        
        write_history "[$agent_name] $response"
        echo "$response"
    else
        # Modo buffered original
        echo -e "${color}${icon} $agent_name pensando...${NC}" >&2
        
        local response
        response=$($cmd_func "$full_context" "$prompt")
        
        if [ -z "$response" ] || [ "$response" == "null" ]; then
            response="[Sin respuesta de $agent_name]"
        fi
        
        echo -e "${color}${icon} $agent_name:${NC} $response" >&2
        write_history "[$agent_name] $response"
        
        echo "$response"
    fi
}

# Funciones específicas de ejecución
exec_kimi() {
    local ctx="$1"
    local prmt="$2"
    
    if [ "$STREAM_MODE" == "1" ]; then
        # Modo streaming: solo mostrar texto limpio
        {
            run_cmd_stream "$KIMI_TIMEOUT" kimi -p "$ctx

$prmt" --print 2>&1 | while IFS= read -r line || [[ -n "$line" ]]; do
                # Extraer solo líneas que empiezan con text='
                if [[ "$line" == *"text='"* ]]; then
                    # Extraer contenido después de text='
                    echo "$line" | sed "s/.*text='//;s/'$//"
                fi
            done
        } || true
        [ "$RUN_CMD_EXIT" -eq 124 ] && echo "[Timeout Kimi (${KIMI_TIMEOUT}s)]"
    else
        local out
        out=$(run_cmd_capture "$KIMI_TIMEOUT" kimi -p "$ctx

$prmt" --print)
        [ "$RUN_CMD_EXIT" -eq 124 ] && echo "[Timeout Kimi (${KIMI_TIMEOUT}s)]" && return
        echo "$out" | grep -oP "text='[^']*" | head -1 | sed "s/text='//" | tr -d '\n'
    fi
}

exec_gemini() {
    local ctx="$1"
    local prmt="$2"
    
    if [ "$STREAM_MODE" == "1" ]; then
        # Modo streaming con filtro mejorado
        {
            run_cmd_stream "$GEMINI_TIMEOUT" gemini -p "$ctx

$prmt" -o text -y 2>&1 | grep -vE "^YOLO|^Loaded|^Hook|^I will|^Generating|^Using|^$|^\[|^Thinking" || true
        }
        [ "$RUN_CMD_EXIT" -eq 124 ] && echo "[Timeout Gemini (${GEMINI_TIMEOUT}s)]"
    else
        local out
        out=$(run_cmd_capture "$GEMINI_TIMEOUT" gemini -p "$ctx

$prmt" -o text -y)
        [ "$RUN_CMD_EXIT" -eq 124 ] && echo "[Timeout Gemini (${GEMINI_TIMEOUT}s)]" && return
        echo "$out" | grep -vE "^YOLO|^Loaded|^Hook|^I will|^$" | tail -3 | tr '\n' ' ' | sed 's/  */ /g'
    fi
}

exec_claude() {
    local ctx="$1"
    local prmt="$2"
    local claude_settings_args=()
    if [ -f "$CLAUDE_CONFIG/settings.json" ]; then
        claude_settings_args+=(--settings "$CLAUDE_CONFIG/settings.json")
    fi
    
    if [ "$STREAM_MODE" == "1" ]; then
        # Modo streaming con filtro mejorado
        {
            run_cmd_stream "$CLAUDE_TIMEOUT" claude -p "$ctx

$prmt" --print --allowed-tools "Read,Edit,Bash,Task" "${claude_settings_args[@]}" 2>&1 | grep -vE "^\[|^session|^Using|^$|^Starting|^Connecting" || true
        }
        [ "$RUN_CMD_EXIT" -eq 124 ] && echo "[Timeout Claude (${CLAUDE_TIMEOUT}s)]"
    else
        local out
        out=$(run_cmd_capture "$CLAUDE_TIMEOUT" claude -p "$ctx

$prmt" --print --allowed-tools "Read,Edit,Bash,Task" "${claude_settings_args[@]}")
        [ "$RUN_CMD_EXIT" -eq 124 ] && echo "[Timeout Claude (${CLAUDE_TIMEOUT}s)]" && return
        echo "$out" | grep -v "^\\[\\|starting session|^$\|^Using config" | tail -5 | tr '\n' ' ' | sed 's/  */ /g'
    fi
}

exec_codex() {
    local ctx="$1"
    local prmt="$2"
    
    if [ "$STREAM_MODE" == "1" ]; then
        # Modo streaming: capturar solo la respuesta después de "codex"
        {
            local show_output=0
            local printed_lines=""
            run_cmd_stream "$CODEX_TIMEOUT" codex exec "$ctx

$prmt" --full-auto 2>&1 | while IFS= read -r line || [[ -n "$line" ]]; do
                # Ignorar líneas vacías y metadatos
                [[ -z "$line" ]] && continue
                [[ "$line" =~ ^(OpenAI|workdir:|model:|provider:|approval:|sandbox:|reasoning|session|mcp|thinking|user|---|\*\*|tokens|[0-9,]+$) ]] && continue
                # Empezar a mostrar después de la línea "codex"
                if [[ "$line" == "codex" ]]; then
                    show_output=1
                    continue
                fi
                # Solo mostrar si estamos en modo output y no es duplicado/metadata
                if [[ "$show_output" == 1 ]]; then
                    # Evitar duplicados y líneas de tokens
                    [[ "$line" =~ ^[0-9,]+$ ]] && continue
                    [[ "$printed_lines" == *"$line"* ]] && continue
                    echo "$line"
                    printed_lines="$printed_lines|$line"
                fi
            done
        } || true
        [ "$RUN_CMD_EXIT" -eq 124 ] && echo "[Timeout Codex (${CODEX_TIMEOUT}s)]"
    else
        local out
        out=$(run_cmd_capture "$CODEX_TIMEOUT" codex exec "$ctx

$prmt" --full-auto)
        [ "$RUN_CMD_EXIT" -eq 124 ] && echo "[Timeout Codex (${CODEX_TIMEOUT}s)]" && return
        echo "$out" | grep -v "^OpenAI|^workdir:|^model:|^provider:|^approval:|^sandbox:|^reasoning|^session|^mcp|^thinking|^$\|^tokens used" | tail -1
    fi
}

# Funciones públicas
ask_kimi() { call_agent_generic "Kimi" "$1" "$MAGENTA" "🤖" exec_kimi; }
ask_gemini() { call_agent_generic "Gemini" "$1" "$BLUE" "💎" exec_gemini; }
ask_claude() { call_agent_generic "Claude" "$1" "$ORANGE" "🧠" exec_claude; }
ask_codex() { call_agent_generic "Codex" "$1" "$RED" "📝" exec_codex; }

# Mostrar estado
show_status() {
    local stream_status
    [ "$STREAM_MODE" == "1" ] && stream_status="${YELLOW}ON${NC}" || stream_status="${RED}OFF${NC}"
    echo -e "${WHITE}━━━ Estado de la sesión ━━━${NC}"
    echo -e "  Turnos: $TURN_COUNT"
    echo -e "  Agente activo: ${YELLOW}$ACTIVE_AGENT${NC}"
    echo -e "  Modo streaming: $stream_status"
    echo -e "  Historial: $HISTORY_FILE"
    echo -e "  Tamaño log: $(wc -l < "$HISTORY_FILE" 2>/dev/null || echo 0) líneas"
    echo -e "  Timeouts: kimi ${KIMI_TIMEOUT}s, gemini ${GEMINI_TIMEOUT}s, claude ${CLAUDE_TIMEOUT}s, codex ${CODEX_TIMEOUT}s"
    echo ""
}

# Mostrar contexto
show_context() {
    echo -e "${WHITE}Contexto: $CONTEXT_FILE (primeras ${CONTEXT_LINES} líneas)${NC}"
    if [ -f "$CONTEXT_FILE" ]; then
        head -n "$CONTEXT_LINES" "$CONTEXT_FILE"
    else
        echo "Contexto no disponible."
    fi
    echo ""
}

# Editar contexto
edit_context() {
    local editor="${EDITOR:-vi}"
    "$editor" "$CONTEXT_FILE"
}

# Ejecutar múltiples agentes en paralelo
run_parallel_agents() {
    local msg="$1"
    shift
    local -a agents=("$@")
    local tmp_dir
    tmp_dir=$(mktemp -d)
    local -a pids=()
    local agent
    for agent in "${agents[@]}"; do
        local err_file="$tmp_dir/${agent}.err"
        local out_file="$tmp_dir/${agent}.out"
        case "$agent" in
            kimi) (ask_kimi "$msg" >"$out_file" 2>"$err_file") & pids+=($!) ;;
            gemini) (ask_gemini "$msg" >"$out_file" 2>"$err_file") & pids+=($!) ;;
            claude) (ask_claude "$msg" >"$out_file" 2>"$err_file") & pids+=($!) ;;
            codex) (ask_codex "$msg" >"$out_file" 2>"$err_file") & pids+=($!) ;;
            *) echo -e "${RED}Agente desconocido: $agent${NC}" ;;
        esac
    done
    local pid
    for pid in "${pids[@]}"; do
        wait "$pid" || true
    done
    for agent in "${agents[@]}"; do
        cat "$tmp_dir/${agent}.err"
        [ -s "$tmp_dir/${agent}.err" ] && echo ""
    done
    rm -rf "$tmp_dir"
}

# Procesar comando
process_command() {
    local input="$1"
    local cmd="${input%% *}"
    local args="${input#* }"
    
    # Si el comando es igual a args (sin argumentos), limpiar args
    [ "$cmd" == "$args" ] && args=""

    case "$cmd" in
        /kimi) [ -n "$args" ] && ask_kimi "$args" >/dev/null || echo -e "${RED}Uso: /kimi <msg>${NC}" ;; 
        /gemini) [ -n "$args" ] && ask_gemini "$args" >/dev/null || echo -e "${RED}Uso: /gemini <msg>${NC}" ;; 
        /claude) [ -n "$args" ] && ask_claude "$args" >/dev/null || echo -e "${RED}Uso: /claude <msg>${NC}" ;; 
        /codex) [ -n "$args" ] && ask_codex "$args" >/dev/null || echo -e "${RED}Uso: /codex <msg>${NC}" ;; 
        /both)
            if [ -n "$args" ]; then
                echo -e "${YELLOW}━━━ Kimi & Gemini ━━━${NC}"
                run_parallel_agents "$args" kimi gemini
            else
                echo -e "${RED}Uso: /both <msg>${NC}"
            fi
            ;; 
        /all)
            if [ -n "$args" ]; then
                echo -e "${YELLOW}━━━ Todos los agentes ━━━${NC}"
                run_parallel_agents "$args" kimi gemini claude codex
            else
                echo -e "${RED}Uso: /all <msg>${NC}"
            fi
            ;; 
        /switch)
            case "$ACTIVE_AGENT" in
                kimi) ACTIVE_AGENT="gemini" ;; 
                gemini) ACTIVE_AGENT="claude" ;; 
                claude) ACTIVE_AGENT="codex" ;; 
                codex) ACTIVE_AGENT="kimi" ;; 
            esac
            echo -e "${GREEN}Agente activo: ${YELLOW}$ACTIVE_AGENT${NC}"
            ;; 
        /stream)
            if [ "$STREAM_MODE" == "1" ]; then
                STREAM_MODE="0"
                echo -e "${GREEN}Modo streaming: ${RED}OFF${NC} (buffered)"
            else
                STREAM_MODE="1"
                echo -e "${GREEN}Modo streaming: ${YELLOW}ON${NC} (tiempo real)"
            fi
            ;; 
        /resume) resume_history "${args:-}" ;; 
        /context)
            if [ -z "$args" ]; then
                show_context
            elif [ "$args" == "edit" ]; then
                edit_context
            else
                echo -e "${RED}Uso: /context [edit]${NC}"
            fi
            ;; 
        /status) show_status ;; 
        /help) show_help ;; 
        /quit|/exit|/q) exit 0 ;; 
        /*) echo -e "${RED}Comando desconocido: $cmd${NC}" ;; 
        *)
            TURN_COUNT=$((TURN_COUNT + 1))
            write_history "[Usuario] $input"
            case "$ACTIVE_AGENT" in
                kimi) ask_kimi "$input" >/dev/null ;; 
                gemini) ask_gemini "$input" >/dev/null ;; 
                claude) ask_claude "$input" >/dev/null ;; 
                codex) ask_codex "$input" >/dev/null ;; 
            esac
            ;; 
    esac
}

# Main loop
main() {
    cd "$PROJECT_ROOT"
    init_history_files
    if [ "${1:-}" == "--resume" ] || [ "${1:-}" == "-r" ]; then
        resume_history || true
        shift || true
    fi
    show_banner
    
    if [ -n "${1:-}" ]; then
        echo -e "${YELLOW}Iniciando con instrucción: $1${NC}"
        process_command "/all $1"
    fi
    
    while true; do
        echo -ne "${GREEN}Tú${NC} [${YELLOW}$ACTIVE_AGENT${NC}]> "
        read -r input || break
        [ -z "$input" ] && continue
        echo ""
        process_command "$input"
        echo ""
    done
}

main "$@"

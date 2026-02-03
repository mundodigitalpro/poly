#!/usr/bin/env bash
#
# Multi-Agent Interactive Chat
#
# Permite conversaciones interactivas entre Kimi, Gemini y el usuario.
# Los agentes pueden interactuar entre sí y preguntar al usuario.
#
# Uso:
#   ./scripts/agent_chat.sh "Instrucción inicial para los agentes"
#   ./scripts/agent_chat.sh  # Modo interactivo sin instrucción inicial
#
# Comandos durante la sesión:
#   /kimi <mensaje>   - Enviar mensaje directamente a Kimi
#   /gemini <mensaje> - Enviar mensaje directamente a Gemini
#   /both <mensaje>   - Enviar mensaje a ambos agentes
#   /switch           - Cambiar el agente activo
#   /status           - Ver estado de la conversación
#   /help             - Mostrar ayuda
#   /quit o /exit     - Salir
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
NC='\033[0m'

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HISTORY_FILE="/tmp/agent_chat_history_$$.txt"
TURN_COUNT=0
ACTIVE_AGENT="kimi"

# Limpiar al salir
cleanup() {
    rm -f "$HISTORY_FILE" 2>/dev/null || true
    echo -e "\n${YELLOW}Sesión finalizada.${NC}"
}
trap cleanup EXIT

# Mostrar banner
show_banner() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}        ${WHITE}Multi-Agent Interactive Chat${NC}                        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}        ${MAGENTA}Kimi${NC} 🤖 + ${BLUE}Gemini${NC} 💎 + ${RED}Codex${NC} 📝 + ${GREEN}Tú${NC} 👤              ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Mostrar ayuda
show_help() {
    echo -e "${WHITE}Comandos disponibles:${NC}"
    echo -e "  ${MAGENTA}/kimi${NC} <msg>    Enviar mensaje a Kimi"
    echo -e "  ${BLUE}/gemini${NC} <msg> Enviar mensaje a Gemini"
    echo -e "  ${RED}/codex${NC} <msg>  Enviar mensaje a Codex"
    echo -e "  ${YELLOW}/both${NC} <msg>   Enviar a Kimi y Gemini"
    echo -e "  ${CYAN}/all${NC} <msg>    Enviar a todos los agentes"
    echo -e "  ${CYAN}/switch${NC}       Cambiar agente activo (actual: $ACTIVE_AGENT)"
    echo -e "  ${WHITE}/status${NC}       Ver estado de la conversación"
    echo -e "  ${WHITE}/help${NC}         Mostrar esta ayuda"
    echo -e "  ${RED}/quit${NC}         Salir"
    echo ""
    echo -e "  ${WHITE}Escribe directamente${NC} para hablar con el agente activo (${YELLOW}$ACTIVE_AGENT${NC})"
    echo ""
}

# Obtener historial reciente
get_history() {
    if [ -f "$HISTORY_FILE" ]; then
        tail -10 "$HISTORY_FILE" | sed 's/^/  /'
    else
        echo "  (sin historial previo)"
    fi
}

# Enviar mensaje a Kimi
ask_kimi() {
    local prompt="$1"
    local history
    history=$(get_history)
    
    local context="Eres Kimi en un chat multiagente con Gemini y un humano.
Proyecto: trading bot Polymarket en /home/josejordan/poly.
Responde MUY conciso (2-3 frases max). Si necesitas info del humano, pregunta.

HISTORIAL DE LA CONVERSACIÓN:
$history

NUEVO MENSAJE:"
    
    echo -e "${MAGENTA}🤖 Kimi pensando...${NC}" >&2
    
    local raw_output
    raw_output=$(kimi -p "$context

$prompt" --print 2>&1) || true
    
    # Extraer texto de la respuesta de Kimi (formato TextPart)
    local response
    response=$(echo "$raw_output" | grep -oP "text='[^']*" | head -1 | sed "s/text='//" | tr -d '\n')
    
    if [ -z "$response" ]; then
        response="[Sin respuesta de Kimi]"
    fi
    
    echo -e "${MAGENTA}🤖 Kimi:${NC} $response" >&2
    echo "[Kimi] $response" >> "$HISTORY_FILE"
    
    echo "$response"
}

# Enviar mensaje a Gemini
ask_gemini() {
    local prompt="$1"
    local history
    history=$(get_history)
    
    local context="Eres Gemini en un chat multiagente con Kimi, Codex y un humano.
Proyecto: trading bot Polymarket en /home/josejordan/poly.
Responde MUY conciso (2-3 frases max). Si necesitas info del humano, pregunta.

HISTORIAL DE LA CONVERSACIÓN:
$history

NUEVO MENSAJE:"
    
    echo -e "${BLUE}💎 Gemini pensando...${NC}" >&2
    
    local raw_output
    raw_output=$(gemini -p "$context

$prompt" -o text -y 2>&1) || true
    
    # Filtrar líneas de log y obtener respuesta real
    local response
    response=$(echo "$raw_output" | grep -v "^YOLO\|^Loaded\|^Hook\|^I will\|^$" | tail -3 | tr '\n' ' ' | sed 's/  */ /g')
    
    if [ -z "$response" ]; then
        response="[Sin respuesta de Gemini]"
    fi
    
    echo -e "${BLUE}💎 Gemini:${NC} $response" >&2
    echo "[Gemini] $response" >> "$HISTORY_FILE"
    
    echo "$response"
}

# Enviar mensaje a Codex
ask_codex() {
    local prompt="$1"
    local history
    history=$(get_history)
    
    local context="Eres Codex en un chat multiagente con Kimi, Gemini y un humano.
Proyecto: trading bot Polymarket en /home/josejordan/poly.
Responde MUY conciso (2-3 frases max). Si necesitas info del humano, pregunta.

HISTORIAL DE LA CONVERSACIÓN:
$history

NUEVO MENSAJE:"
    
    echo -e "${RED}📝 Codex pensando...${NC}" >&2
    
    local raw_output
    raw_output=$(cd "$PROJECT_ROOT" && codex exec "$context

$prompt" --full-auto 2>&1) || true
    
    # Filtrar: extraer texto después de "codex" y antes de "tokens used"
    # O tomar la última línea no vacía que no sea metadata
    local response
    response=$(echo "$raw_output" | grep -v "^OpenAI\|^workdir:\|^model:\|^provider:\|^approval:\|^sandbox:\|^reasoning\|^session\|^mcp\|^thinking\|^$\|^tokens used" | tail -1)
    
    if [ -z "$response" ]; then
        response="[Sin respuesta de Codex]"
    fi
    
    echo -e "${RED}📝 Codex:${NC} $response" >&2
    echo "[Codex] $response" >> "$HISTORY_FILE"
    
    echo "$response"
}

# Mostrar estado
show_status() {
    echo -e "${WHITE}━━━ Estado de la sesión ━━━${NC}"
    echo -e "  Turnos: $TURN_COUNT"
    echo -e "  Agente activo: ${YELLOW}$ACTIVE_AGENT${NC}"
    echo -e "  Historial: $HISTORY_FILE"
    if [ -f "$HISTORY_FILE" ]; then
        echo -e "  Mensajes guardados: $(wc -l < "$HISTORY_FILE")"
    fi
    echo ""
}

# Procesar comando
process_command() {
    local input="$1"
    local cmd="${input%% *}"
    local args="${input#* }"
    
    case "$cmd" in
        /kimi)
            if [ -n "$args" ] && [ "$args" != "$cmd" ]; then
                ask_kimi "$args" > /dev/null
            else
                echo -e "${RED}Uso: /kimi <mensaje>${NC}"
            fi
            ;;
        /gemini)
            if [ -n "$args" ] && [ "$args" != "$cmd" ]; then
                ask_gemini "$args" > /dev/null
            else
                echo -e "${RED}Uso: /gemini <mensaje>${NC}"
            fi
            ;;
        /codex)
            if [ -n "$args" ] && [ "$args" != "$cmd" ]; then
                ask_codex "$args" > /dev/null
            else
                echo -e "${RED}Uso: /codex <mensaje>${NC}"
            fi
            ;;
        /both)
            if [ -n "$args" ] && [ "$args" != "$cmd" ]; then
                echo -e "${YELLOW}━━━ Preguntando a Kimi y Gemini ━━━${NC}"
                ask_kimi "$args" > /dev/null
                echo ""
                ask_gemini "$args" > /dev/null
            else
                echo -e "${RED}Uso: /both <mensaje>${NC}"
            fi
            ;;
        /all)
            if [ -n "$args" ] && [ "$args" != "$cmd" ]; then
                echo -e "${YELLOW}━━━ Preguntando a todos los agentes ━━━${NC}"
                ask_kimi "$args" > /dev/null
                echo ""
                ask_gemini "$args" > /dev/null
                echo ""
                ask_codex "$args" > /dev/null
            else
                echo -e "${RED}Uso: /all <mensaje>${NC}"
            fi
            ;;
        /switch)
            case "$ACTIVE_AGENT" in
                kimi) ACTIVE_AGENT="gemini" ;;
                gemini) ACTIVE_AGENT="codex" ;;
                codex) ACTIVE_AGENT="kimi" ;;
            esac
            echo -e "${GREEN}Agente activo cambiado a: ${YELLOW}$ACTIVE_AGENT${NC}"
            ;;
        /status)
            show_status
            ;;
        /help)
            show_help
            ;;
        /quit|/exit|/q)
            echo -e "${YELLOW}¡Hasta luego!${NC}"
            exit 0
            ;;
        /*)
            echo -e "${RED}Comando desconocido: $cmd${NC}"
            echo -e "Escribe ${WHITE}/help${NC} para ver comandos disponibles"
            ;;
        *)
            # Mensaje normal - enviar al agente activo
            TURN_COUNT=$((TURN_COUNT + 1))
            echo "[Usuario] $input" >> "$HISTORY_FILE"
            
            case "$ACTIVE_AGENT" in
                kimi) ask_kimi "$input" > /dev/null ;;
                gemini) ask_gemini "$input" > /dev/null ;;
                codex) ask_codex "$input" > /dev/null ;;
            esac
            ;;
    esac
}

# Colaboración entre agentes
agent_collaborate() {
    local topic="$1"
    
    echo -e "${YELLOW}━━━ Iniciando colaboración entre agentes ━━━${NC}"
    echo -e "${WHITE}Tema: $topic${NC}"
    echo ""
    
    # Kimi analiza primero
    echo -e "${MAGENTA}[Paso 1] Kimi analiza...${NC}"
    local kimi_response
    kimi_response=$(ask_kimi "Analiza esto y da tu opinión breve: $topic")
    echo ""
    
    # Gemini responde a Kimi
    echo -e "${BLUE}[Paso 2] Gemini responde a Kimi...${NC}"
    local gemini_response
    gemini_response=$(ask_gemini "Kimi dijo: '$kimi_response'. ¿Qué opinas? Añade o corrige si es necesario.")
    echo ""
    
    # Preguntar al usuario
    echo -e "${GREEN}[Paso 3] Tu turno...${NC}"
    echo -e "${WHITE}¿Tienes alguna pregunta o instrucción adicional? (Enter para continuar)${NC}"
    read -r user_input
    
    if [ -n "$user_input" ]; then
        echo ""
        echo -e "${YELLOW}━━━ Procesando tu input ━━━${NC}"
        process_command "/both $user_input"
    fi
    
    echo ""
    echo -e "${GREEN}━━━ Colaboración completada ━━━${NC}"
}

# Main loop
main() {
    cd "$PROJECT_ROOT"
    
    show_banner
    
    # Si hay argumento inicial, iniciar colaboración
    if [ -n "${1:-}" ]; then
        agent_collaborate "$1"
        echo ""
    fi
    
    show_help
    
    # Loop interactivo
    while true; do
        echo -ne "${GREEN}Tú${NC} [${YELLOW}$ACTIVE_AGENT${NC}]> "
        read -r input || break
        
        if [ -z "$input" ]; then
            continue
        fi
        
        echo ""
        process_command "$input"
        echo ""
    done
}

main "$@"

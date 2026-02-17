#!/usr/bin/env bash
set -euo pipefail

URL="${WHISPERFLOW_URL:-http://localhost:8181}"
API_KEY="${WHISPERFLOW_API_KEY:-}"
CONFIG_FILE="${WHISPERFLOW_CONFIG:-/app/config/whisperflow.json}"

# Build auth header
AUTH_HEADER=()
if [[ -n "${API_KEY}" ]]; then
    AUTH_HEADER=(-H "Authorization: Bearer ${API_KEY}")
fi

show_config() {
    if [[ -f "${CONFIG_FILE}" ]]; then
        echo "=== Config File (${CONFIG_FILE}) ==="
        cat "${CONFIG_FILE}" | jq .
    else
        echo "No config file found at ${CONFIG_FILE}"
    fi
    echo ""
    echo "=== Service Status ==="
    curl -sf --max-time 5 "${AUTH_HEADER[@]}" "${URL}/health" 2>/dev/null \
        && echo "" \
        || echo "Service not reachable at ${URL}"
    echo ""
    echo "=== Environment ==="
    echo "WHISPERFLOW_URL=${URL}"
    echo "WHISPERFLOW_API_KEY=${API_KEY:+(set)}"
    echo "WHISPERFLOW_CONFIG=${CONFIG_FILE}"
}

# Parse arguments
ACTION="--show"
PROVIDER=""
MODEL=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --show)      ACTION="show"; shift ;;
        --provider)  PROVIDER="$2"; shift 2 ;;
        --model)     MODEL="$2"; shift 2 ;;
        -*)          echo "Unknown option: $1" >&2; exit 1 ;;
        *)           echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

case "${ACTION}" in
    show|--show)
        show_config
        ;;
esac

# Apply settings if provided
if [[ -n "${PROVIDER}" || -n "${MODEL}" ]]; then
    CONFIG="{}"
    if [[ -f "${CONFIG_FILE}" ]]; then
        CONFIG=$(cat "${CONFIG_FILE}")
    fi
    if [[ -n "${PROVIDER}" ]]; then
        CONFIG=$(echo "${CONFIG}" | jq --arg p "${PROVIDER}" '.provider = $p')
        echo "Provider set to: ${PROVIDER}"
    fi
    if [[ -n "${MODEL}" ]]; then
        CONFIG=$(echo "${CONFIG}" | jq --arg m "${MODEL}" '.model = $m')
        echo "Model set to: ${MODEL}"
    fi
    mkdir -p "$(dirname "${CONFIG_FILE}")"
    echo "${CONFIG}" | jq . > "${CONFIG_FILE}"
    echo "Config saved to ${CONFIG_FILE}"
fi

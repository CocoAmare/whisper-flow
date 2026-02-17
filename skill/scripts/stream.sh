#!/usr/bin/env bash
set -euo pipefail

# Defaults
URL="${WHISPERFLOW_URL:-http://localhost:8181}"
API_KEY="${WHISPERFLOW_API_KEY:-}"
WS_URL=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --url)    WS_URL="$2"; shift 2 ;;
        --token)  API_KEY="$2"; shift 2 ;;
        -*)       echo "Unknown option: $1" >&2; exit 1 ;;
        *)        echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

# Build WebSocket URL from HTTP URL if not overridden
if [[ -z "${WS_URL}" ]]; then
    WS_URL=$(echo "${URL}" | sed 's|^http|ws|')/ws
fi

# Append token as query param if set
if [[ -n "${API_KEY}" ]]; then
    WS_URL="${WS_URL}?token=${API_KEY}"
fi

echo "Connecting to ${WS_URL%\?*}" >&2
echo "Send raw PCM audio (16kHz, mono, int16) to stdin." >&2
echo "Transcription results will appear on stdout as JSON." >&2
echo "Press Ctrl+C to stop." >&2

# Use websocat if available, fall back to curl
if command -v websocat &>/dev/null; then
    websocat --binary "${WS_URL}"
else
    echo "Error: websocat is required for WebSocket streaming." >&2
    echo "Install: cargo install websocat" >&2
    echo "  or:    apt install websocat" >&2
    echo "  or:    brew install websocat" >&2
    exit 1
fi

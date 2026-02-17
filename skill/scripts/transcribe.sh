#!/usr/bin/env bash
set -euo pipefail

# Defaults
URL="${WHISPERFLOW_URL:-http://localhost:8181}"
API_KEY="${WHISPERFLOW_API_KEY:-}"
MODEL="tiny.en.pt"
INPUT=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)  MODEL="$2"; shift 2 ;;
        --url)    URL="$2"; shift 2 ;;
        --key)    API_KEY="$2"; shift 2 ;;
        -*)       echo "Unknown option: $1" >&2; exit 1 ;;
        *)        INPUT="$1"; shift ;;
    esac
done

if [[ -z "${INPUT}" ]]; then
    echo "Usage: transcribe.sh <audio-file> [--model tiny.en.pt] [--url http://host:port]" >&2
    exit 1
fi

if [[ ! -f "${INPUT}" ]]; then
    echo "File not found: ${INPUT}" >&2
    exit 1
fi

# Build auth header
AUTH_HEADER=()
if [[ -n "${API_KEY}" ]]; then
    AUTH_HEADER=(-H "Authorization: Bearer ${API_KEY}")
fi

# Send to WhisperFlow
response=$(curl -sf --max-time 120 \
    "${AUTH_HEADER[@]}" \
    -F "model_name=${MODEL}" \
    -F "files=@${INPUT}" \
    "${URL}/transcribe_pcm_chunk") || {
    echo "Transcription request failed" >&2
    exit 1
}

# Extract text from JSON response
echo "${response}" | jq -r '.text // empty'

#!/usr/bin/env bash
set -euo pipefail

URL="${WHISPERFLOW_URL:-http://localhost:8181}"

response=$(curl -sf --max-time 5 "${URL}/health" 2>&1) || {
    echo "WhisperFlow is not reachable at ${URL}" >&2
    exit 1
}

echo "${response}"

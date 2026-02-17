| name | description | homepage | metadata |
|------|-------------|----------|----------|
| whisperflow | Real-time speech-to-text transcription powered by WhisperFlow. Transcribe audio files, stream live audio via WebSocket, check service health, and configure transcription settings. Works with local Whisper models, Ollama, or LM Studio backends. | https://github.com/dimastatz/whisper-flow | openclaw: emoji: mic, requires: bins: curl jq, requires: env: WHISPERFLOW_URL, primaryEnv: WHISPERFLOW_API_KEY |

# WhisperFlow

Real-time speech transcription service running in a separate container.

## Connection

WhisperFlow runs at `$WHISPERFLOW_URL` (default: `http://whisperflow:8181` on Docker network, or `http://localhost:8181` locally). All endpoints except `/health` require a Bearer token when `WHISPERFLOW_API_KEY` is set.

## Health Check

Verify the service is running:

```bash
{baseDir}/scripts/health.sh
```

## Transcribe an Audio File

Transcribe a local audio file (WAV, PCM, or any format with raw PCM data):

```bash
{baseDir}/scripts/transcribe.sh /path/to/audio.wav
```

Options:
- `--model tiny.en.pt` — select model (default: tiny.en.pt)
- `--url http://host:port` — override WhisperFlow URL

The script returns the transcribed text to stdout.

## Stream Audio via WebSocket

For real-time transcription of a continuous audio stream:

```bash
{baseDir}/scripts/stream.sh
```

Options:
- `--url ws://host:port/ws` — override WebSocket URL
- `--token TOKEN` — override API key for WebSocket auth

Streams JSON results: `{"is_partial": true/false, "data": {"text": "..."}, "time": 123.4}`

Partial results update as speech is recognized. When `is_partial` is `false`, the segment is finalized.

## Configuration

View or update the running configuration:

```bash
# Check current config
{baseDir}/scripts/configure.sh --show

# Set provider and model
{baseDir}/scripts/configure.sh --provider whisper --model tiny.en.pt
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WHISPERFLOW_URL` | Yes | Base URL of the WhisperFlow service |
| `WHISPERFLOW_API_KEY` | No | Bearer token for API authentication. Auto-generated on first run if not set. |

## Docker Setup

WhisperFlow runs in its own container. Add to your docker-compose.yml:

```yaml
services:
  whisperflow:
    build: https://github.com/dimastatz/whisper-flow.git
    ports:
      - "8181:8181"
    environment:
      - WHISPERFLOW_API_KEY=${WHISPERFLOW_API_KEY}
    volumes:
      - whisperflow-config:/app/config
      - whisperflow-models:/app/models
```

Then set in your OpenClaw environment:
```
WHISPERFLOW_URL=http://whisperflow:8181
WHISPERFLOW_API_KEY=<your-key-or-auto-generated>
```

## Audio Format

WhisperFlow expects 16 kHz, mono, 16-bit signed PCM. The transcribe script handles WAV files directly. For other formats, convert first:

```bash
ffmpeg -i input.mp3 -ar 16000 -ac 1 -f s16le output.pcm
```

## Supported Providers

| Provider | Status | Notes |
|----------|--------|-------|
| Whisper (local) | Available | Default. Uses bundled tiny.en.pt model. |
| Ollama | Planned | Configure via OLLAMA_URL |
| LM Studio | Planned | Configure via LMSTUDIO_URL |

## MCP Server

WhisperFlow can also be accessed as an MCP server for any MCP-compatible client. Add to your mcporter config:

```json
{
  "whisperflow": {
    "url": "http://whisperflow:8181/mcp",
    "auth": {
      "type": "bearer",
      "token": "${WHISPERFLOW_API_KEY}"
    }
  }
}
```

Or for Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "whisperflow": {
      "command": "curl",
      "args": ["-N", "http://localhost:8181/mcp/sse"]
    }
  }
}
```

MCP tools exposed: `transcribe_audio`, `list_models`, `get_health`, `get_config`.

Note: MCP endpoints are planned for a future release. Use the skill scripts in the meantime.

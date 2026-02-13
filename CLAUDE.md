# CLAUDE.md

This file provides guidance for AI assistants working with the WhisperFlow codebase.

## Project Overview

WhisperFlow is a Python library and server for real-time speech transcription powered by OpenAI Whisper. It uses a tumbling window streaming architecture to deliver low-latency (~275ms) transcription with ~7% Word Error Rate. Audio is expected in 16 kHz, mono, 16-bit signed PCM format.

## Repository Structure

```
whisperflow/                  # Main package
  __init__.py                 # Package version (1.0.0)
  transcriber.py              # Whisper model loading and PCM transcription (sync + async)
  streaming.py                # Tumbling window streaming logic, TranscribeSession class
  fast_server.py              # FastAPI app: /health, /transcribe_pcm_chunk, /ws endpoints
  chat_room.py                # Real-time conversation loop (STT -> processing -> TTS)
  audio/
    microphone.py             # Audio capture, playback, and silence detection (PyAudio)
  models/
    tiny.en.pt                # Pre-downloaded Whisper model (~75 MB)

tests/                        # Test suite
  utils.py                    # TestClient wrapper, resource loading helpers
  test_transcriber.py         # Model loading and transcription accuracy tests
  test_streaming.py           # Windowing logic, WebSocket, and API endpoint tests
  test_chat_room.py           # ChatRoom orchestration tests
  audio/
    test_audio.py             # Hardware-dependent audio tests (skipped in CI)
  benchmark/
    test_benchmark.py         # WebSocket streaming performance and WER benchmarks
  resources/
    3081-166546-0000.wav      # LibriSpeech test audio sample
    3081-166546-0000.json     # Ground truth transcription for WER validation

docs/                         # Project documentation and plans
.github/workflows/            # CI/CD (GitHub Actions)
```

## Build & Development Commands

All commands use `run.sh` as the entry point:

```bash
# Full local setup: create venv, install deps, format, lint, test
./run.sh -local

# Run formatter + linter + tests (assumes venv already exists)
./run.sh -test

# Build and run Docker containers
./run.sh -docker

# Run benchmark tests (starts server on port 8181, runs benchmarks, stops server)
./run.sh -benchmark

# Start the FastAPI server on port 8181
./run.sh -run-server

# Build and test the Python wheel package
./run.sh -test-package
```

## Testing

**Framework:** pytest with pytest-asyncio for async test support.

**Run tests:**
```bash
# Activate venv first, then:
pytest --ignore=tests/benchmark --cov-fail-under=95 --cov whisperflow -v tests
```

**Test categories:**
- **Unit tests** (`tests/test_*.py`): Core transcriber, streaming, and API tests. Always run.
- **Audio tests** (`tests/audio/`): Require audio hardware. Skipped in CI and Docker.
- **Benchmark tests** (`tests/benchmark/`): Require a running server on port 8181. Run separately via `./run.sh -benchmark`.

**Quality thresholds enforced in CI:**
- Code coverage: >= 95% (via `--cov-fail-under=95`)
- pylint score: >= 9.9/10 (via `pylint --fail-under=9.9`)
- Black formatting must pass with no changes

## Code Style & Linting

- **Formatter:** Black (v23.3.0) - applied to both `whisperflow/` and `tests/` directories
- **Linter:** pylint (v3.0.3) with a minimum score of 9.9/10
- Run both before committing:
  ```bash
  black whisperflow tests
  pylint --fail-under=9.9 whisperflow tests
  ```

## Architecture

### Streaming Pipeline

1. Audio arrives as raw PCM byte chunks (16 kHz, mono, int16)
2. `TranscribeSession` queues incoming chunks and runs a background `transcribe()` coroutine
3. The coroutine uses a tumbling window approach: accumulates chunks, runs Whisper transcription, and detects segment boundaries when consecutive results stabilize
4. Partial results are sent back immediately; final results are sent when a segment closes

### Key Components

- **`transcriber.py`**: Stateless transcription functions. Models are cached in a global `models` dict and lazy-loaded. GPU (CUDA) used automatically when available.
- **`streaming.py`**: Stateful `TranscribeSession` class that manages the producer-consumer transcription loop. Accepts `transcribe_async` and `send_back_async` callbacks via dependency injection.
- **`fast_server.py`**: FastAPI application with three endpoints:
  - `GET /health` - version check
  - `POST /transcribe_pcm_chunk` - one-shot transcription of uploaded audio
  - `WS /ws` - WebSocket for real-time streaming transcription
- **`chat_room.py`**: Orchestrator for full duplex conversation (mic -> STT -> process -> TTS -> speaker)

### Audio Format

All audio must be: 16 kHz sample rate, mono channel, 16-bit signed PCM (int16). Default chunk size is 4096 bytes.

## CI/CD

GitHub Actions workflow (`.github/workflows/docker-image.yml`) triggers on push/PR to `main`:
- **test job**: Builds `Dockerfile.test` which runs Black, pylint, and pytest inside a Docker container
- **build job**: Builds the production `Dockerfile`

## Dependencies

Key runtime dependencies: `openai-whisper`, `fastapi`, `uvicorn`, `PyAudio`, `torch`, `numpy`

Key dev dependencies: `pytest`, `pytest-asyncio`, `pytest-cov`, `black`, `pylint`, `jiwer` (WER calculation), `httpx`, `websocket-client`

System-level: Python 3.8+ (tested with 3.11/3.12), PortAudio (`portaudio19-dev`), build tools

## Conventions for AI Assistants

- Run `black whisperflow tests` before committing any Python changes
- Ensure `pylint --fail-under=9.9 whisperflow tests` passes
- Maintain >= 95% code coverage; add tests for new functionality
- Use `pytest-asyncio` (`@pytest.mark.asyncio`) for async test functions
- Audio hardware tests should be marked to skip in CI (`@pytest.mark.skip(reason="requires audio hardware")`)
- Use `# pragma: no cover` for code paths that require hardware (microphone/speaker access)
- Follow existing patterns: small focused modules, async-first design, dependency injection for testability
- The Whisper model file (`whisperflow/models/tiny.en.pt`) is a large binary; avoid modifying or re-downloading it
- Test audio resources live in `tests/resources/`; use `tests/utils.load_resource()` to load them

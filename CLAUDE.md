# CLAUDE.md

This file provides guidance for AI assistants working with the WhisperFlow codebase.

## Project Overview

WhisperFlow is a Python library and FastAPI service for real-time speech transcription powered by OpenAI Whisper. It uses a tumbling window streaming architecture to deliver low-latency (~275ms) transcription with ~7% Word Error Rate. Audio is expected in 16 kHz, mono, 16-bit signed PCM format.

**Version:** 1.0.0
**Python:** >=3.8 (tested with 3.11 in Docker, 3.12 locally)

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
  examples/
    mic_transcribe.py         # Example: stream mic audio to server via WebSocket
  resources/
    3081-166546-0000.wav      # LibriSpeech test audio sample
    3081-166546-0000.json     # Ground truth transcription for WER validation

Dockerfile                    # Production image (pip install whisperflow from PyPI)
Dockerfile.test               # CI image (copies source, runs black+pylint+pytest)
requirements.txt              # Pinned dependencies
setup.py                      # Package build configuration
run.sh                        # Dev script: -local, -test, -run-server, -benchmark, -docker
docs/                         # Project documentation and plans
.github/
  workflows/docker-image.yml  # CI: builds both Docker images on push/PR to main
  dependabot.yml              # Dependabot for devcontainers only
```

## Build & Development Commands

All commands use `run.sh` as the entry point:

```bash
# Full local setup: create venv, install deps, format, lint, test
./run.sh -local

# Run formatter + linter + tests (assumes venv already exists)
./run.sh -test

# Start the FastAPI server on port 8181
./run.sh -run-server

# Build and run Docker containers
./run.sh -docker

# Run benchmark tests (starts server on port 8181, runs benchmarks, stops server)
./run.sh -benchmark

# Build and test the Python wheel package
./run.sh -test-package
```

### Running Tests Directly

```bash
source .venv/bin/activate

# Unit tests (excludes hardware-dependent and benchmark tests)
pytest --ignore=tests/benchmark --ignore=tests/audio --cov-fail-under=95 --cov whisperflow -v tests

# Single test file
pytest tests/test_transcriber.py -v
```

## Testing

**Framework:** pytest with pytest-asyncio for async test support.

**Test categories:**
- **Unit tests** (`tests/test_*.py`): Core transcriber, streaming, and API tests. Always run.
- **Audio tests** (`tests/audio/`): Require audio hardware. Skipped in CI and Docker.
- **Benchmark tests** (`tests/benchmark/`): Require a running server on port 8181. Run separately via `./run.sh -benchmark`.

**Testing conventions:**
- Decorate async tests with `@pytest.mark.asyncio`
- Use `@pytest.mark.timeout(N)` for tests with potential hangs
- Test resources (audio files, ground truth JSON) live in `tests/resources/`
- Use `tests.utils.load_resource(name)` to load test audio and expected results
- Use `tests.utils.TestClient` (re-exported from `starlette.testclient`) for API tests
- Hardware-dependent tests go in `tests/audio/` and are excluded from CI
- Use `# pragma: no cover` for code paths that require hardware (microphone/speaker access)

**Quality thresholds enforced in CI:**
- Code coverage: >= 95% (via `--cov-fail-under=95`)
- pylint score: >= 9.9/10 (via `pylint --fail-under=9.9`)
- Black formatting must pass with no changes

## Code Style & Linting

- **Formatter:** Black (v23.3.0) — applied to both `whisperflow/` and `tests/` directories
- **Linter:** pylint (v3.0.3) with a minimum score of 9.9/10
- Run both before committing:
  ```bash
  black whisperflow tests
  pylint --fail-under=9.9 whisperflow tests
  ```

## Architecture

### Streaming Pipeline

1. **Client** connects via WebSocket to `/ws`
2. **fast_server.py** accepts connection, creates a `TranscribeSession`
3. Client sends raw PCM audio bytes (16kHz, mono, int16)
4. **streaming.py** queues chunks and runs a transcription loop:
   - Collects queued chunks into a growing window
   - Calls the Whisper model on the full window
   - Emits `is_partial: true` results as text evolves
   - When text stabilizes (same result for `max_cycles` iterations), emits `is_partial: false` and resets the window
5. Results are sent back as JSON over the WebSocket

### Key Components

- **`transcriber.py`**: Stateless transcription functions. Models are cached in a global `models` dict and lazy-loaded. GPU (CUDA) used automatically when available.
- **`streaming.py`**: Stateful `TranscribeSession` class that manages the producer-consumer transcription loop. Accepts `transcribe_async` and `send_back_async` callbacks via dependency injection.
- **`fast_server.py`**: FastAPI application with three endpoints:
  - `GET /health` — version check
  - `POST /transcribe_pcm_chunk` — one-shot transcription of uploaded audio
  - `WS /ws` — WebSocket for real-time streaming transcription
- **`chat_room.py`**: Orchestrator for full duplex conversation (mic -> STT -> process -> TTS -> speaker)

### Audio Format

All audio must be: 16 kHz sample rate, mono channel, 16-bit signed PCM (int16). Default chunk size is 4096 bytes.

### Model

The default model is `tiny.en.pt` (English-only, fastest). Models are loaded from `whisperflow/models/` using `whisper.load_model()`.

## CI/CD

GitHub Actions workflow (`.github/workflows/docker-image.yml`) triggers on push/PR to `main`:
- **test job**: Builds `Dockerfile.test` which runs Black, pylint, and pytest inside a Docker container
- **build job**: Builds the production `Dockerfile`

## Dependencies

Key runtime dependencies (from `requirements.txt`):
- `fastapi==0.108.0` + `uvicorn[standard]==0.30.1` — Web framework and ASGI server
- `openai-whisper==20231117` — Speech recognition model
- `PyAudio==0.2.14` — Audio I/O (requires system `portaudio19-dev`)
- `python-multipart==0.0.9` — Multipart form parsing for file uploads
- `torch`, `numpy` — ML runtime

Key dev dependencies:
- `pytest==7.3.2`, `pytest-asyncio==0.23.7`, `pytest-cov==4.1.0`
- `black==23.3.0`, `pylint==3.0.3`
- `jiwer==3.0.4` — Word Error Rate calculation for accuracy tests
- `httpx==0.27.0`, `websocket-client==1.8.0` — HTTP/WebSocket test clients

System-level: Python 3.8+ (tested with 3.11/3.12), PortAudio (`portaudio19-dev`), build tools

## Known Security Considerations

A security audit (`SECURITY_AUDIT.md`) has been conducted. Key items to be aware of when developing:

- The `model_name` parameter in `/transcribe_pcm_chunk` is user-controlled and used in file path construction — always validate against an allowlist
- No authentication exists on any endpoint — do not deploy publicly without adding auth
- The `sessions` dict in `fast_server.py` is never cleaned up — sessions should be removed on disconnect
- `Dockerfile.test` uses `&` instead of `&&` — quality gates may not actually block the build
- Dependencies have known CVEs — check `SECURITY_AUDIT.md` for details

## Conventions for AI Assistants

- Run `black whisperflow tests` before committing any Python changes
- Ensure `pylint --fail-under=9.9 whisperflow tests` passes
- Run `pytest --ignore=tests/benchmark --ignore=tests/audio --cov-fail-under=95 --cov whisperflow -v tests` to verify tests pass with coverage
- Maintain >= 95% code coverage; add tests for new functionality
- Use `pytest-asyncio` (`@pytest.mark.asyncio`) for async test functions
- Audio hardware tests should be marked to skip in CI (`@pytest.mark.skip(reason="requires audio hardware")`)
- Follow existing patterns: small focused modules, async-first design, dependency injection for testability
- The Whisper model file (`whisperflow/models/tiny.en.pt`) is a large binary; do not modify or re-download it
- Do not add dependencies without updating `requirements.txt` with pinned versions
- Async functions should use `asyncio` patterns consistent with existing code (no `trio`, no `anyio`)
- The project uses no type checking tool (no mypy/pyright) — type hints are used informally
- There is no `pyproject.toml` — build config is in `setup.py`
- Test audio resources live in `tests/resources/`; use `tests.utils.load_resource()` to load them

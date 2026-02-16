# WhisperFlow: Complete Setup and Installation Guide

This guide walks you through every step of installing, configuring, and running WhisperFlow. Each step explains **what** it does, **why** it is needed, and **how** it affects your system.

---

## Table of Contents

1. [What is WhisperFlow?](#1-what-is-whisperflow)
2. [Use Cases](#2-use-cases)
3. [System Requirements](#3-system-requirements)
4. [Step 1: Install System-Level Dependencies](#4-step-1-install-system-level-dependencies)
5. [Step 2: Clone the Repository](#5-step-2-clone-the-repository)
6. [Step 3: Create a Python Virtual Environment](#6-step-3-create-a-python-virtual-environment)
7. [Step 4: Install Python Dependencies](#7-step-4-install-python-dependencies)
8. [Step 5: Verify the Installation](#8-step-5-verify-the-installation)
9. [Step 6: Run the Tests](#9-step-6-run-the-tests)
10. [Step 7: Start the Server](#10-step-7-start-the-server)
11. [Step 8: Configure Authentication](#11-step-8-configure-authentication)
12. [Step 9: Connect a Client](#12-step-9-connect-a-client)
13. [Docker Installation (Alternative)](#13-docker-installation-alternative)
14. [Configuration Reference](#14-configuration-reference)
15. [What Gets Installed on Your Computer](#15-what-gets-installed-on-your-computer)
16. [Uninstallation](#16-uninstallation)
17. [Troubleshooting](#17-troubleshooting)

---

## 1. What is WhisperFlow?

WhisperFlow is a Python library and HTTP/WebSocket server that converts speech to text in real time. It wraps OpenAI's Whisper speech recognition model and adds a streaming layer on top of it.

Without WhisperFlow, Whisper only works in batch mode: you give it a complete audio file and it returns the full transcript after processing the entire file. WhisperFlow changes this by accepting small chunks of audio as they arrive (via a WebSocket connection) and returning partial transcription results immediately, then finalizing each sentence segment when the text stabilizes.

The core architecture is a **tumbling window**: audio chunks accumulate in a buffer, the Whisper model transcribes the entire buffer on each cycle, and when two consecutive transcription cycles produce identical text, the segment is considered final, the buffer is cleared, and a new segment begins.

**Performance characteristics:**
- Latency: ~275ms between partial results (on Apple M1 with tiny.en model)
- Accuracy: ~7% Word Error Rate (WER) on LibriSpeech test data
- Model size: ~75 MB on disk for tiny.en (the default, English-only model)
- RAM usage: ~200-400 MB at runtime (model + PyTorch runtime)
- Audio format: 16 kHz sample rate, mono channel, 16-bit signed PCM (int16)

---

## 2. Use Cases

WhisperFlow is designed for scenarios where you need speech converted to text as the person is still speaking, rather than after they finish:

**Live captioning / subtitles**
Stream microphone audio from a browser or desktop app to WhisperFlow over WebSocket, display partial results as captions that update in real time, and show the final text when each sentence completes. Useful for accessibility in video calls, live events, or classroom settings.

**Voice-controlled applications**
Feed microphone input to WhisperFlow and use the transcription output to trigger commands or fill form fields. The partial results let you show the user what is being recognized while they speak, and the final result triggers the action.

**Meeting transcription**
Record a meeting's audio and stream it to WhisperFlow for a live transcript. Each finalized segment becomes a line in the transcript. Can be combined with speaker diarization (identifying who is speaking) as a post-processing step.

**Language learning tools**
Students speak into a microphone, WhisperFlow transcribes in real time, and the application compares the transcription against expected text to provide pronunciation feedback.

**Podcast / video indexing**
Stream audio from media files through WhisperFlow to generate searchable text transcripts with timing information, enabling full-text search across audio/video libraries.

**Call center analytics**
Transcribe phone calls in real time for sentiment analysis, compliance monitoring, or agent assistance systems that suggest responses based on what the caller is saying.

---

## 3. System Requirements

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Any x86_64 or ARM64 | Multi-core (4+) for concurrent sessions |
| RAM | 1 GB free | 2+ GB free |
| GPU | Not required | NVIDIA GPU with CUDA for faster inference |
| Disk | 500 MB free | 1 GB free |
| Microphone | Not required for server | Required only for the example client |

**Why these requirements:** The Whisper tiny.en model is ~75 MB on disk and ~200 MB in RAM when loaded. PyTorch adds another ~100-200 MB of runtime overhead. Each concurrent WebSocket session adds memory proportional to its audio buffer (~1-2 MB). GPU is optional because the tiny model is fast enough on CPU, but larger models (small, medium, large) benefit significantly from CUDA acceleration.

### Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.8 or higher (3.11-3.12 recommended) | Runtime for all application code |
| pip | 20.0 or higher | Python package installer |
| git | Any recent version | Cloning the repository |
| PortAudio | 19+ | C library required by PyAudio for microphone access |
| Build tools (gcc, make) | Any recent version | Compiling C extensions (PyAudio, numpy) |

---

## 4. Step 1: Install System-Level Dependencies

These are programs and libraries installed at the operating system level, outside of Python. They are needed because some Python packages (PyAudio, numpy) contain C code that must be compiled during installation.

### macOS

```bash
brew install portaudio
```

**What this does:**
- Installs the PortAudio library to `/usr/local/lib/libportaudio.dylib` (Intel) or `/opt/homebrew/lib/libportaudio.dylib` (Apple Silicon)
- Installs C header files to `/usr/local/include/portaudio.h` or `/opt/homebrew/include/portaudio.h`
- These headers and library files are needed when `pip install PyAudio` compiles its C extension

**How it affects your system:**
- Adds ~2 MB of files under your Homebrew prefix
- Does not run any background services or daemons
- Does not modify your shell configuration
- Can be removed later with `brew uninstall portaudio`

**If you don't have Homebrew**, install it first:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Ubuntu / Debian Linux

```bash
sudo apt-get update && sudo apt-get install -y portaudio19-dev python3-dev build-essential
```

**What each package does:**

- `portaudio19-dev`: Installs the PortAudio shared library (`/usr/lib/x86_64-linux-gnu/libportaudio.so`) and development headers (`/usr/include/portaudio.h`). The `-dev` suffix means it includes the C header files needed for compilation, not just the runtime library. PyAudio's C extension `#include`s these headers during `pip install`.

- `python3-dev`: Installs Python C development headers (e.g., `/usr/include/python3.11/Python.h`). Many Python packages with C extensions (numpy, PyAudio) need to `#include <Python.h>` during compilation to interface with the Python runtime. Without this, `pip install` for these packages fails with "Python.h: No such file or directory".

- `build-essential`: A meta-package that installs `gcc` (the C compiler), `g++` (the C++ compiler), `make`, and `libc6-dev` (C standard library headers). These are the fundamental tools needed to compile any C/C++ code. pip uses them when building packages from source.

**How it affects your system:**
- `apt-get update` downloads the latest package index from your configured repositories to `/var/lib/apt/lists/`. This is metadata only (package names, versions, sizes), not the packages themselves. It takes a few MB of disk space.
- The three packages install files under `/usr/lib/`, `/usr/include/`, and `/usr/bin/`. Total disk usage is ~50-100 MB (most of that is `build-essential`).
- No background services are started.
- These packages may already be installed if you have done any C development on this machine.

### Fedora / RHEL / CentOS

```bash
sudo dnf install portaudio-devel python3-devel gcc make
```

**What this does:** Same as the Ubuntu packages but using Fedora's package manager and naming conventions. `portaudio-devel` is Fedora's equivalent of `portaudio19-dev`, and `python3-devel` is Fedora's equivalent of `python3-dev`.

### Windows

On Windows, PyAudio's pre-built wheels typically include PortAudio, so no separate system install is needed. If you encounter build errors:

1. Install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Or install a pre-built PyAudio wheel: `pip install pipwin && pipwin install pyaudio`

### Verifying system dependencies

After installing, verify PortAudio is available:

```bash
# macOS
brew info portaudio

# Linux
dpkg -l | grep portaudio    # Debian/Ubuntu
rpm -qa | grep portaudio    # Fedora/RHEL
```

---

## 5. Step 2: Clone the Repository

```bash
git clone https://github.com/dimastatz/whisper-flow.git
cd whisper-flow
```

**What this does:**
- `git clone` downloads the entire repository (source code, tests, the pre-trained Whisper model file, and git history) to a new directory called `whisper-flow/` in your current location.
- `cd whisper-flow` changes your working directory into the cloned repository.

**How it affects your system:**
- Creates a `whisper-flow/` directory containing ~100 MB of files. The bulk of this is `whisperflow/models/tiny.en.pt` (~75 MB), which is the pre-trained Whisper model weights. This file is included in the repository so you don't need to download it separately or have an internet connection at model-load time.
- The `.git/` subdirectory contains the full version history (~20 MB). This is used by git for version tracking and can be deleted if you don't need git features.
- No files are modified outside this directory. No system configuration is changed.

**What's in the repository:**

```
whisper-flow/
  whisperflow/              # The actual Python package (this is what runs)
    __init__.py             # Package version: "1.0.0"
    transcriber.py          # Loads the Whisper model and transcribes audio
    streaming.py            # Manages the tumbling window and session state
    fast_server.py          # The FastAPI HTTP + WebSocket server
    chat_room.py            # Optional: full-duplex mic-to-speaker conversation loop
    audio/
      microphone.py         # Optional: PyAudio helpers for mic capture/playback
    models/
      tiny.en.pt            # Pre-trained Whisper model weights (~75 MB)
  tests/                    # Test suite (not needed for production)
  requirements.txt          # Pinned Python dependency versions
  run.sh                    # Convenience script for common tasks
  Dockerfile                # Production Docker image definition
  Dockerfile.test           # CI/test Docker image definition
  setup.py                  # Python package build configuration
```

---

## 6. Step 3: Create a Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**What this does:**

`python3 -m venv .venv` creates a **virtual environment** — an isolated copy of the Python interpreter and its package directory inside `.venv/`:

```
.venv/
  bin/                  # (or Scripts/ on Windows)
    python              # Symlink to system Python
    pip                 # pip, scoped to this venv
    activate            # Shell script that sets PATH
  lib/
    python3.XX/
      site-packages/    # Where packages installed in this venv go
  pyvenv.cfg            # Config pointing to the base Python
```

`source .venv/bin/activate` modifies your **current shell session** (and only your current session) by:
1. Prepending `.venv/bin/` to your `$PATH` environment variable, so `python` and `pip` resolve to the venv copies instead of the system ones.
2. Setting the `$VIRTUAL_ENV` environment variable to the venv path.
3. Modifying your shell prompt to show `(.venv)` as a visual reminder.

**Why this is necessary:**

Without a virtual environment, `pip install` installs packages into your system Python's `site-packages` directory (e.g., `/usr/lib/python3.11/site-packages/`). This causes problems:

1. **Version conflicts**: If another project on your machine needs `fastapi==0.100.0` and WhisperFlow needs `fastapi==0.108.0`, they can't coexist in the same `site-packages`.
2. **System Python contamination**: On Linux, the system Python is used by OS tools (like `apt` internals). Installing packages into it can break your operating system.
3. **Reproducibility**: You can't be sure which installed packages are for WhisperFlow vs. other projects.

The virtual environment isolates everything. WhisperFlow's packages go in `.venv/lib/python3.XX/site-packages/` and don't touch your system Python.

**How it affects your system:**
- Creates a `.venv/` directory (~15 MB initially, ~500 MB after dependencies are installed) inside the `whisper-flow/` directory.
- The `activate` script only affects your current terminal session. Opening a new terminal gives you a clean shell with no venv active.
- No system files are modified. No global configuration is changed.
- To deactivate: run `deactivate` in the terminal, or just close the terminal.

---

## 7. Step 4: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**What `pip install --upgrade pip` does:**

Updates pip itself to the latest version within the venv. Older pip versions may fail to resolve complex dependency trees or may not support newer wheel formats. This only upgrades pip inside `.venv/` — your system pip is not affected.

**What `pip install -r requirements.txt` does:**

Reads the `requirements.txt` file and installs every listed package at the exact pinned version. Here is what each package is, why it's needed, and what it does to your system:

### Runtime Dependencies (needed to run WhisperFlow)

| Package | Version | What it does | Why WhisperFlow needs it |
|---------|---------|-------------|--------------------------|
| `fastapi` | 0.108.0 | Web framework for building HTTP and WebSocket APIs | WhisperFlow's server (`fast_server.py`) is a FastAPI application. FastAPI handles URL routing, request parsing, WebSocket upgrade, and JSON serialization. |
| `uvicorn[standard]` | 0.30.1 | ASGI server that runs FastAPI applications | FastAPI defines the application logic, but it needs a server to listen on a network port and handle TCP connections. Uvicorn is that server. The `[standard]` extra installs `uvloop` (faster event loop) and `httptools` (faster HTTP parsing) for better performance. |
| `openai-whisper` | 20231117 | OpenAI's Whisper speech recognition model | The core ML model that converts audio to text. WhisperFlow wraps this library and adds streaming on top. Installing this also installs `torch` (PyTorch) as a dependency. |
| `python-multipart` | 0.0.18 | Multipart form data parser | Required by FastAPI's `File(...)` and `Form(...)` parameters. The `/transcribe_pcm_chunk` endpoint accepts file uploads via multipart form encoding, which this library parses. |
| `PyAudio` | 0.2.14 | Python bindings for PortAudio (audio I/O) | Used by the optional `microphone.py` module for capturing audio from a microphone and playing audio through speakers. Not needed if you only use the server endpoints. This is a C extension — pip compiles it against the PortAudio headers you installed in Step 1. |
| `torch` | (transitive) | PyTorch deep learning framework | Installed automatically as a dependency of `openai-whisper`. Provides the tensor operations and neural network runtime that Whisper's model uses for inference. This is the largest single dependency (~800 MB - 2 GB depending on your platform and whether CUDA support is included). |
| `numpy` | (transitive) | Numerical array operations | Used to convert raw PCM bytes to float32 arrays that Whisper can process. Also a transitive dependency of torch and whisper. |

### Development / Testing Dependencies (only needed for development)

| Package | Version | What it does |
|---------|---------|-------------|
| `pytest` | 7.3.2 | Test runner framework |
| `pytest-asyncio` | 0.23.7 | Enables `async def` test functions |
| `pytest-cov` | 4.1.0 | Measures code coverage during tests |
| `pytest-timeout` | 2.3.1 | Prevents tests from hanging indefinitely |
| `pytest-benchmark` | 4.0.0 | Performance benchmarking for tests |
| `black` | 23.3.0 | Code formatter (enforces consistent style) |
| `pylint` | 3.0.3 | Static analysis linter (catches bugs and style issues) |
| `pylint-fail-under` | 0.3.0 | Makes pylint exit with error if score is below threshold |
| `httpx` | 0.27.0 | HTTP client used in tests to call the API |
| `websocket-client` | 1.8.0 | WebSocket client used in benchmark tests |
| `jiwer` | 3.0.4 | Calculates Word Error Rate for accuracy benchmarks |
| `pandas` | 2.2.2 | Data analysis for benchmark result processing |

**How it affects your system:**

- All packages are installed into `.venv/lib/python3.XX/site-packages/`. Nothing is installed system-wide.
- Total disk usage is ~1.5-3 GB (mostly PyTorch). PyTorch is large because it includes compiled C++/CUDA libraries for tensor math.
- If you have an NVIDIA GPU with CUDA drivers installed, PyTorch will automatically detect and use it. This does not install CUDA drivers — those must already be present on your system. If no GPU is found, PyTorch uses CPU only.
- pip may compile C extensions (PyAudio, numpy) during installation. This uses the compiler and headers from Step 1. Compilation output goes into the venv, not your system directories.
- pip caches downloaded packages in `~/.cache/pip/` (Linux/macOS) or `%LOCALAPPDATA%\pip\Cache` (Windows). This takes ~500 MB - 1 GB and speeds up future installs. You can clear it with `pip cache purge` if disk space is a concern.

---

## 8. Step 5: Verify the Installation

Run these commands to confirm everything installed correctly:

```bash
# Verify Python can import the package
python -c "import whisperflow; print(f'WhisperFlow v{whisperflow.__version__}')"
# Expected output: WhisperFlow v1.0.0

# Verify the Whisper model can be loaded
python -c "
import whisperflow.transcriber as ts
model = ts.get_model()
print(f'Model loaded successfully. Device: {next(model.parameters()).device}')
"
# Expected output: Model loaded successfully. Device: cpu
# (or Device: cuda:0 if you have an NVIDIA GPU)

# Verify FastAPI can start
python -c "
from whisperflow.fast_server import app
print(f'Routes: {[r.path for r in app.routes if hasattr(r, \"path\")]}')
"
# Expected output: Routes: ['/health', '/transcribe_pcm_chunk', '/ws', ...]
```

**What these checks verify:**

1. **Import check**: Confirms the `whisperflow` package is on the Python path and its `__init__.py` loads correctly.
2. **Model load check**: Confirms the `tiny.en.pt` model file is present at the expected path (`whisperflow/models/tiny.en.pt`), that PyTorch can deserialize it, and that CUDA detection works. This is the most likely step to fail — if the model file is missing or corrupted, you'll see a `FileNotFoundError` or `RuntimeError`.
3. **FastAPI check**: Confirms that all imports in `fast_server.py` resolve correctly, that FastAPI can parse the route decorators, and that the application object is constructed.

---

## 9. Step 6: Run the Tests

```bash
# Run the full quality gate: formatter + linter + tests with coverage
./run.sh -test
```

Or run tests directly:

```bash
pytest --ignore=tests/benchmark --ignore=tests/audio --cov-fail-under=95 --cov whisperflow -v tests
```

**What each part of this command does:**

- `pytest`: The test runner. It discovers all files named `test_*.py` under the `tests/` directory, collects all functions named `test_*` inside them, and runs each one.

- `--ignore=tests/benchmark`: Skips the benchmark test directory. Benchmark tests require a running WhisperFlow server on port 8181 and measure latency/accuracy. They are slow (~30 seconds) and not needed to verify correctness.

- `--ignore=tests/audio`: Skips the audio hardware test directory. These tests require a physical microphone and speaker connected to the machine. They will fail in CI environments, headless servers, or machines without audio hardware.

- `--cov whisperflow`: Enables code coverage measurement for the `whisperflow` package. During the test run, pytest tracks which lines of source code in `whisperflow/` are executed by at least one test. The result is a coverage percentage.

- `--cov-fail-under=95`: Makes the test run fail if code coverage is below 95%. This is a quality gate — it ensures that nearly all code paths are tested. The current codebase has ~97% coverage.

- `-v`: Verbose output. Shows each test name and its PASS/FAIL status instead of just dots.

**What the tests actually do:**

- **test_transcriber.py**: Loads the Whisper model, transcribes a sample LibriSpeech audio file, and checks that the Word Error Rate is below 10%. Also tests edge cases: empty input, odd-length bytes, path traversal attacks on model names.

- **test_streaming.py**: Tests the tumbling window logic with mock transcribers. Verifies that the window cap works, that sessions can be stopped with a timeout, and that the WebSocket endpoint accepts connections and returns transcription results.

- **test_auth.py**: Tests the API key authentication system. Verifies that endpoints reject requests without valid Bearer tokens when `WHISPERFLOW_API_KEY` is configured, and that everything works without auth when the env var is unset.

- **test_chat_room.py**: Tests the ChatRoom orchestrator that chains mic input -> transcription -> processing -> speaker output.

**How it affects your system:**
- Tests run entirely in-process. No network ports are opened (the test client communicates with FastAPI directly via ASGI, not over TCP).
- The Whisper model is loaded into RAM during tests (~200 MB). It is released when tests complete.
- No files are written outside the project directory (pytest may create a `.pytest_cache/` directory and `__pycache__/` directories for compiled Python bytecode).

---

## 10. Step 7: Start the Server

```bash
./run.sh -run-server
```

Or directly:

```bash
uvicorn whisperflow.fast_server:app --host 0.0.0.0 --port 8181
```

**What each part of this command does:**

- `uvicorn`: The ASGI server process. It creates a TCP socket, binds it to the specified address and port, and listens for incoming HTTP and WebSocket connections.

- `whisperflow.fast_server:app`: Tells uvicorn to import the module `whisperflow.fast_server` and use the variable `app` (which is a FastAPI instance) as the ASGI application to serve.

- `--host 0.0.0.0`: Binds the server to all network interfaces. This means the server accepts connections from any IP address, not just localhost. **This is important**: if your machine is on a network, other machines can connect to it on port 8181. For local development only, use `--host 127.0.0.1` instead to restrict access to your machine only.

- `--port 8181`: The TCP port number to listen on. Port 8181 was chosen to avoid conflicts with common services (80 for HTTP, 443 for HTTPS, 8080 for various dev servers, 8000 for Django). If port 8181 is already in use by another process, uvicorn will fail with "Address already in use" — change the port number or stop the other process.

**What happens when the server starts:**

1. Uvicorn creates a TCP socket on `0.0.0.0:8181`.
2. Python imports `whisperflow.fast_server`, which imports `whisperflow.transcriber` and `whisperflow.streaming`.
3. The Whisper model (`tiny.en.pt`) is **not** loaded yet — it is lazy-loaded on the first request. This makes server startup fast (~1-2 seconds).
4. Uvicorn prints `Uvicorn running on http://0.0.0.0:8181` and begins accepting connections.
5. On the first transcription request (HTTP or WebSocket), `get_model()` is called, which loads the ~75 MB model file from disk into RAM. This takes 2-5 seconds and uses ~200 MB of RAM. The model stays in memory for all subsequent requests.

**Server endpoints:**

| Endpoint | Method | Auth Required | Purpose |
|----------|--------|---------------|---------|
| `/health` | GET | No | Returns the server version string. Use this to check if the server is running. |
| `/transcribe_pcm_chunk` | POST | Yes (if API key set) | Upload a PCM audio file for one-shot transcription. Returns the full text. |
| `/ws` | WebSocket | Yes (if API key set) | Real-time streaming transcription. Send audio chunks, receive partial/final results. |
| `/docs` | GET | No | Auto-generated Swagger UI for the API. Useful for manual testing. |

**How it affects your system:**
- One `uvicorn` process runs in the foreground, using ~200-400 MB of RAM (Python + PyTorch + model).
- TCP port 8181 is occupied until you stop the server (Ctrl+C).
- The server is single-process by default. It uses Python's asyncio event loop for concurrency (many concurrent WebSocket connections are fine, but CPU-bound transcription is offloaded to a thread pool).
- No files are written. No system configuration is changed.
- Uvicorn logs each request to stdout/stderr.

**To stop the server:** Press `Ctrl+C` in the terminal where it's running.

---

## 11. Step 8: Configure Authentication

By default, WhisperFlow runs with **no authentication** — any client can connect and use the API. To add API key authentication:

```bash
# Set the API key as an environment variable, then start the server
export WHISPERFLOW_API_KEY="your-secret-key-here"
uvicorn whisperflow.fast_server:app --host 0.0.0.0 --port 8181
```

**What this does:**

`export WHISPERFLOW_API_KEY="..."` sets an environment variable in your current shell session. When uvicorn starts the FastAPI application, `fast_server.py` reads this variable at import time:

```python
_API_KEY = os.environ.get("WHISPERFLOW_API_KEY")
```

If the variable is set (non-empty), all endpoints except `/health` require authentication:

- **HTTP endpoints** (`/transcribe_pcm_chunk`): Clients must include an `Authorization: Bearer <your-key>` header. Requests without it, or with the wrong key, get a `401 Unauthorized` response.

- **WebSocket endpoint** (`/ws`): Clients must include the token as a query parameter: `ws://host:8181/ws?token=<your-key>`. Connections without a valid token are accepted and then immediately closed with WebSocket status code 1008 (Policy Violation). The token is passed as a query parameter because the WebSocket protocol (as implemented in browsers) does not support custom HTTP headers during the upgrade handshake.

**Security notes:**

- The API key comparison uses `hmac.compare_digest()` for constant-time comparison, which prevents timing attacks (where an attacker measures response time to guess the key character by character).
- The WebSocket token appears in the URL query string, which means it may appear in server access logs and reverse proxy logs. In production, consider placing the server behind a reverse proxy (like nginx) that strips query parameters from access logs.
- The API key is read once at process startup. Changing the environment variable after the server is running has no effect — you must restart the server.
- There is no minimum key length enforced. Use a strong, random key (at least 32 characters). Generate one with: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

**How it affects your system:**
- The `export` command only affects your current shell session and any child processes started from it. It does not persist across reboots or new terminal sessions.
- To make it permanent, add the `export` line to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) — but be aware this puts a secret in a plaintext file.
- In Docker, pass it as: `docker run -e WHISPERFLOW_API_KEY="your-key" ...`
- In production, use your platform's secrets manager (AWS Secrets Manager, Kubernetes Secrets, etc.).

---

## 12. Step 9: Connect a Client

### Quick test with curl (HTTP endpoint)

```bash
# Without auth
curl -X POST http://localhost:8181/transcribe_pcm_chunk \
  -F "model_name=tiny.en.pt" \
  -F "files=@tests/resources/3081-166546-0000.wav"

# With auth
curl -X POST http://localhost:8181/transcribe_pcm_chunk \
  -H "Authorization: Bearer your-secret-key-here" \
  -F "model_name=tiny.en.pt" \
  -F "files=@tests/resources/3081-166546-0000.wav"
```

**What this does:** Sends the sample LibriSpeech WAV file to the batch transcription endpoint. The server loads the Whisper model (if not already loaded), transcribes the entire file, and returns a JSON response with the transcribed text.

### WebSocket streaming client (Python example)

```python
import asyncio
import websockets
import json

async def stream_audio():
    # Read a sample audio file
    with open("tests/resources/3081-166546-0000.wav", "rb") as f:
        audio_data = f.read()

    # Connect to the WebSocket endpoint
    # Add ?token=your-key if auth is enabled
    async with websockets.connect("ws://localhost:8181/ws") as ws:
        # Send audio in 4096-byte chunks (simulating real-time streaming)
        chunk_size = 4096
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            await ws.send(chunk)
            await asyncio.sleep(0.05)  # Simulate real-time pacing

            # Check for transcription results (non-blocking)
            try:
                result = await asyncio.wait_for(ws.recv(), timeout=0.01)
                data = json.loads(result)
                status = "FINAL" if not data["is_partial"] else "partial"
                print(f"[{status}] {data['data']['text']}")
            except asyncio.TimeoutError:
                pass  # No result yet, keep sending

        # Wait for remaining results
        await asyncio.sleep(2)
        while True:
            try:
                result = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(result)
                status = "FINAL" if not data["is_partial"] else "partial"
                print(f"[{status}] {data['data']['text']}")
            except asyncio.TimeoutError:
                break

asyncio.run(stream_audio())
```

**What this does:**

1. Opens a WebSocket connection to the server.
2. Reads a WAV audio file and sends it in 4096-byte chunks (the default chunk size WhisperFlow expects).
3. Between sends, checks for transcription results. The server sends JSON messages with `is_partial: true` for in-progress transcriptions and `is_partial: false` when a segment is finalized.
4. The `asyncio.sleep(0.05)` simulates real-time audio pacing. In a real application, you would send audio chunks as they are captured from the microphone.

**Audio format requirements:** The audio must be 16 kHz, mono, 16-bit signed PCM. If your audio is in a different format (e.g., 44.1 kHz stereo MP3), you must convert it before sending. Using ffmpeg:

```bash
ffmpeg -i input.mp3 -ar 16000 -ac 1 -f s16le -acodec pcm_s16le output.pcm
```

---

## 13. Docker Installation (Alternative)

If you prefer not to install system dependencies and Python packages directly on your machine, you can run WhisperFlow in a Docker container.

### Production Docker image

```bash
docker build -t whisperflow-image --file Dockerfile .
docker run -d --name whisperflow -p 8181:8181 whisperflow-image
```

**What each command does:**

`docker build -t whisperflow-image --file Dockerfile .`
- Reads the `Dockerfile` in the current directory.
- Creates a container based on `python:3.11-slim-bookworm` (a minimal Debian-based image with Python pre-installed).
- Installs system dependencies (PortAudio, build tools) inside the container.
- Runs `pip install whisperflow` to install the published PyPI package inside the container.
- Tags the resulting image as `whisperflow-image`.
- The image is stored in your local Docker image cache (~3-5 GB).

`docker run -d --name whisperflow -p 8181:8181 whisperflow-image`
- `-d`: Runs the container in the background (detached mode).
- `--name whisperflow`: Gives the container a human-readable name for easier management.
- `-p 8181:8181`: Maps port 8181 on your host machine to port 8181 inside the container. Without this, the server would be listening inside the container but unreachable from outside.
- The container starts uvicorn on port 8181 (defined in the Dockerfile's CMD).

**With authentication:**
```bash
docker run -d --name whisperflow -p 8181:8181 \
  -e WHISPERFLOW_API_KEY="your-secret-key-here" \
  whisperflow-image
```

**How Docker affects your system:**
- Docker images and containers are stored in Docker's data directory (`/var/lib/docker/` on Linux, `~/Library/Containers/com.docker.docker/` on macOS). This uses 3-5 GB of disk space per image.
- The container runs as an isolated process. It has its own filesystem, network namespace, and process tree. It cannot access files on your host machine unless you explicitly mount volumes.
- Port 8181 on your host is forwarded to the container. Other ports are not exposed.
- The container runs as root inside its namespace (this is a known item from the security audit — the container is not hardened with a non-root user).

**Managing the container:**
```bash
docker logs whisperflow          # View server logs
docker stop whisperflow          # Stop the server
docker start whisperflow         # Restart it
docker rm whisperflow            # Remove the container
docker rmi whisperflow-image     # Remove the image
```

### Test Docker image (for development)

```bash
docker build -t whisperflow-test --file Dockerfile.test .
```

This builds an image that copies the source code, creates a venv, installs dependencies, runs `black` (formatter), `pylint` (linter), and `pytest` (tests) — all during the build step. If any quality gate fails, the Docker build fails. This is used in CI to verify code quality.

---

## 14. Configuration Reference

WhisperFlow is configured entirely through environment variables and source code constants. There is no configuration file.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPERFLOW_API_KEY` | Not set (auth disabled) | When set, all endpoints except `/health` require this key as a Bearer token (HTTP) or query parameter (WebSocket). |

### Source Code Constants (change in code if needed)

| Constant | Location | Default | Description |
|----------|----------|---------|-------------|
| `_MAX_WINDOW_CHUNKS` | `streaming.py:18` | `500` | Maximum number of audio chunks held in the transcription window before old chunks are discarded. At 4096 bytes/chunk and 16 kHz mono int16, 500 chunks is ~64 seconds of audio. Increase for longer segments; decrease to reduce memory usage. |
| `timeout` | `streaming.py:84` (param to `stop()`) | `10` seconds | How long to wait for a transcription session to finish when a client disconnects. If the session is mid-transcription and doesn't finish in this time, the task is forcefully cancelled. Increase if you use larger Whisper models (medium, large) that take longer per inference. |
| `max_cycles` | `streaming.py:61` (param to `should_close_segment()`) | `1` | How many consecutive identical transcription results are needed before a segment is finalized. Higher values = more stable final results but higher latency. |
| Server port | `run.sh` / `Dockerfile` | `8181` | The TCP port uvicorn listens on. Change in the uvicorn command if 8181 conflicts with another service. |
| Server bind address | `run.sh` / `Dockerfile` | `0.0.0.0` | Which network interface to bind to. Use `127.0.0.1` for local-only access, `0.0.0.0` to accept connections from any interface. |
| Default model | `transcriber.py:17` | `tiny.en.pt` | The Whisper model loaded when no model name is specified. The model file must exist in `whisperflow/models/`. |

---

## 15. What Gets Installed on Your Computer

Here is a complete summary of everything that gets installed or created, and where:

### System-level (Step 1)

| What | Where | Size | Removable? |
|------|-------|------|------------|
| PortAudio library | `/usr/lib/` or Homebrew prefix | ~2 MB | Yes: `apt remove portaudio19-dev` / `brew uninstall portaudio` |
| Python dev headers | `/usr/include/python3.XX/` | ~5 MB | Yes: `apt remove python3-dev` |
| Build tools (gcc, make) | `/usr/bin/` | ~50 MB | Yes: `apt remove build-essential` (but many other packages may need them) |

### Project-level (Steps 2-4)

| What | Where | Size | Removable? |
|------|-------|------|------------|
| Repository clone | `whisper-flow/` | ~100 MB | Yes: `rm -rf whisper-flow/` |
| Python virtual environment | `whisper-flow/.venv/` | ~1.5-3 GB | Yes: `rm -rf .venv/` |
| pip download cache | `~/.cache/pip/` | ~500 MB - 1 GB | Yes: `pip cache purge` |
| pytest cache | `whisper-flow/.pytest_cache/` | ~1 MB | Yes: `rm -rf .pytest_cache/` |
| Python bytecode cache | `whisper-flow/**/__pycache__/` | ~5 MB | Yes: `find . -name __pycache__ -exec rm -rf {} +` |

### Docker (if used)

| What | Where | Size | Removable? |
|------|-------|------|------------|
| Docker image | Docker data directory | ~3-5 GB | Yes: `docker rmi whisperflow-image` |
| Docker container | Docker data directory | ~10 MB (overlay) | Yes: `docker rm whisperflow` |

### Nothing is installed to:
- Your system Python's site-packages
- Your home directory (except pip cache)
- Any global configuration files
- Any system services or startup items
- Any cron jobs or scheduled tasks

---

## 16. Uninstallation

### Remove WhisperFlow completely

```bash
# 1. Stop the server if running
# Press Ctrl+C in the server terminal, or:
kill $(lsof -t -i:8181) 2>/dev/null || true

# 2. Remove the project directory (includes venv and all source)
rm -rf /path/to/whisper-flow

# 3. Clear pip's download cache (optional, saves ~500 MB - 1 GB)
pip cache purge

# 4. Remove system dependencies (optional — other software may need them)
# Ubuntu/Debian:
sudo apt-get remove portaudio19-dev python3-dev build-essential
# macOS:
brew uninstall portaudio
```

### Remove Docker artifacts

```bash
docker stop whisperflow 2>/dev/null
docker rm whisperflow 2>/dev/null
docker rmi whisperflow-image 2>/dev/null
docker rmi whisperflow-test 2>/dev/null
```

---

## 17. Troubleshooting

### "portaudio.h: No such file or directory" during pip install

**Cause:** PortAudio development headers are not installed.
**Fix:** Install them (Step 1): `sudo apt-get install portaudio19-dev` or `brew install portaudio`

### "Python.h: No such file or directory" during pip install

**Cause:** Python development headers are not installed.
**Fix:** `sudo apt-get install python3-dev` (Linux) — macOS Xcode command line tools include these by default.

### "Address already in use" when starting the server

**Cause:** Another process is already listening on port 8181.
**Fix:** Either stop the other process (`kill $(lsof -t -i:8181)`) or use a different port (`--port 8182`).

### "CUDA out of memory" or "torch.cuda.OutOfMemoryError"

**Cause:** The GPU doesn't have enough VRAM for the model.
**Fix:** WhisperFlow defaults to the tiny model which needs ~200 MB VRAM. If you manually loaded a larger model, switch back to tiny, or force CPU: set `CUDA_VISIBLE_DEVICES=""` before starting the server.

### Model loading takes a long time or fails

**Cause:** The `tiny.en.pt` file may be missing or corrupted.
**Fix:** Check that `whisperflow/models/tiny.en.pt` exists and is ~75 MB. If it's missing, re-clone the repository. Do not try to download it separately — the file is included in the git repository.

### WebSocket connection closes immediately

**Cause:** If authentication is enabled (`WHISPERFLOW_API_KEY` is set), connections without a valid token are closed with code 1008.
**Fix:** Include the token in the URL: `ws://host:8181/ws?token=your-key`

### Tests fail with "ModuleNotFoundError: No module named 'whisperflow'"

**Cause:** The virtual environment is not activated, or you're running pytest from outside the project directory.
**Fix:** `cd whisper-flow && source .venv/bin/activate && pytest ...`

### Coverage below 95%

**Cause:** New code was added without corresponding tests.
**Fix:** Add tests for the new code paths. Run `pytest --cov whisperflow --cov-report=term-missing` to see which lines are uncovered.

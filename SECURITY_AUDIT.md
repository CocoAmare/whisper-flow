# Security Audit Report — Whisper Flow

**Date:** 2026-02-13
**Scope:** Full codebase review + git history analysis
**Repository:** https://github.com/dimastatz/whisper-flow
**Version Audited:** 1.0.0 (commit `0433ca7`)

---

## Executive Summary

Whisper Flow is a Python-based real-time audio transcription service using OpenAI Whisper,
FastAPI, and WebSockets. The audit identified **13 security findings** across the codebase,
dependencies, and infrastructure configuration:

| Severity | Count |
|----------|-------|
| CRITICAL | 1     |
| HIGH     | 4     |
| MEDIUM   | 4     |
| LOW      | 4     |

The most severe issue is a **chained path traversal + insecure deserialization vulnerability**
that allows unauthenticated remote code execution via the `/transcribe_pcm_chunk` endpoint.

---

## Git History Analysis

The git history (55 commits, 2 contributors) was searched for:
- Leaked secrets, API keys, credentials, private keys (AWS, GitHub, OpenAI patterns)
- Deleted sensitive files (.env, .pem, .key, certificates)
- Hardcoded passwords or tokens in config files

**Result:** No secrets, credentials, or sensitive data found in git history. Only two files
were deleted historically: `docs/imgs/test.drawio` and `.github/workflows/python-app.yml`
(a removed CI pipeline), neither of which contained sensitive data.

---

## Findings

### CRITICAL-01: Path Traversal Leading to Remote Code Execution

**Severity:** CRITICAL
**CVSS 3.1 Estimate:** 9.8 (Network/Low/None/None)
**Files:** `whisperflow/fast_server.py:24-30`, `whisperflow/transcriber.py:16-22`

**Description:**
The `/transcribe_pcm_chunk` POST endpoint accepts a `model_name` form field from the user
and passes it directly to `ts.get_model(model_name)`. The `get_model()` function constructs
a file path using unsanitized input:

```python
# fast_server.py:24-30
@app.post("/transcribe_pcm_chunk", response_model=dict)
def transcribe_pcm_chunk(
    model_name: str = Form(...), files: List[UploadFile] = File(...)
):
    model = ts.get_model(model_name)  # User-controlled model_name
    ...

# transcriber.py:16-22
def get_model(file_name="tiny.en.pt") -> Whisper:
    if file_name not in models:
        path = os.path.join(os.path.dirname(__file__), f"./models/{file_name}")
        models[file_name] = whisper.load_model(path)  # Uses torch.load(weights_only=False)
```

An attacker can supply path traversal payloads like `../../attacker_model.pt` to load
arbitrary `.pt` files. Since `whisper.load_model()` internally calls `torch.load()` with
`weights_only=False`, loading a crafted `.pt` file triggers **pickle deserialization**,
enabling arbitrary Python code execution on the server.

**Attack Chain:**
1. Attacker uploads or places a malicious `.pt` file accessible to the server
2. Attacker sends POST to `/transcribe_pcm_chunk` with `model_name=../../path/to/malicious.pt`
3. Server loads the file via `torch.load()` with pickle deserialization
4. Arbitrary code executes with server process privileges (root in Docker)

**Remediation:**
- Validate `model_name` against an allowlist of known model filenames
- Reject any input containing `/`, `..`, or path separator characters
- Use `weights_only=True` when loading PyTorch models where possible
- Run the server as a non-root user

---

### HIGH-01: No Authentication or Authorization

**Severity:** HIGH
**Files:** `whisperflow/fast_server.py` (all endpoints)

**Description:**
All endpoints (`GET /health`, `POST /transcribe_pcm_chunk`, `WebSocket /ws`) are completely
unauthenticated. Any network-reachable client can:
- Use the transcription service without restriction
- Open unlimited WebSocket connections
- Send unlimited audio data for transcription
- Consume server GPU/CPU resources

**Remediation:**
- Implement API key authentication or OAuth2
- Add rate limiting (e.g., using `slowapi` or a reverse proxy)
- Add WebSocket connection limits per client
- Consider IP allowlisting for internal deployments

---

### HIGH-02: Denial of Service via Unbounded Resource Consumption

**Severity:** HIGH
**CVSS 3.1 Estimate:** 7.5
**Files:** `whisperflow/fast_server.py:14`, `whisperflow/streaming.py:67-75`

**Description:**
Multiple vectors for resource exhaustion exist:

1. **Session Memory Leak** (`fast_server.py:14,48`): The `sessions` dict accumulates
   `TranscribeSession` objects on each WebSocket connection but never removes them after
   disconnect, causing unbounded memory growth.

2. **Unbounded Audio Queue** (`streaming.py:74-75`): `queue.put_nowait(chunk)` adds chunks
   without any size limit. An attacker can flood the WebSocket with data faster than
   transcription can process it, exhausting server memory.

3. **No WebSocket Message Size Limit**: The `websocket_endpoint` does not configure
   `max_size`, allowing arbitrarily large individual messages.

4. **No Upload Size Limit**: The `/transcribe_pcm_chunk` endpoint does not limit file
   upload sizes.

**Remediation:**
- Remove sessions from the `sessions` dict on disconnect
- Implement queue size limits (e.g., `Queue(maxsize=N)`)
- Configure WebSocket `max_size` parameter
- Add request body size limits via middleware or reverse proxy
- Implement connection-level and global rate limiting

---

### HIGH-03: Dependency Vulnerabilities (python-multipart, Starlette)

**Severity:** HIGH
**Affected Dependencies:**

| Package | Version | CVE | CVSS | Description |
|---------|---------|-----|------|-------------|
| python-multipart | 0.0.9 | CVE-2024-53981 | 7.5 | Boundary parsing DoS — malformed multipart boundaries cause excessive CPU usage and event loop stalling |
| Starlette (via FastAPI 0.108.0) | <0.39.2 | CVE-2024-47874 | 8.7 | Critical multipart parsing vulnerability |
| Starlette (via FastAPI 0.108.0) | <0.49.1 | CVE-2025-62727 | — | Critical security vulnerability |

**Remediation:**
- Upgrade `python-multipart` to `>=0.0.18`
- Upgrade `fastapi` to the latest version (currently 0.115+)
- Implement automated dependency scanning (e.g., `pip-audit`, Dependabot for pip)

---

### HIGH-04: Insecure Deserialization in Model Loading

**Severity:** HIGH
**Files:** `whisperflow/transcriber.py:20`

**Description:**
The `openai-whisper` library (version 20231117) uses `torch.load()` without
`weights_only=True` when loading model files. This means any `.pt` file loaded by the
application is deserialized via Python's `pickle` module, which can execute arbitrary code.

Even the bundled `tiny.en.pt` model (73MB, committed to the repository) is loaded this way.
If an attacker can modify this file (supply chain attack, compromised build, or via
CRITICAL-01), they achieve code execution.

**Remediation:**
- Monitor openai-whisper for updates that add `weights_only=True` support
- Consider converting models to SafeTensors format
- Verify model file integrity with checksums before loading
- Restrict file system permissions on model files

---

### MEDIUM-01: Docker Container Runs as Root

**Severity:** MEDIUM
**Files:** `Dockerfile`, `Dockerfile.test`

**Description:**
Neither Dockerfile includes a `USER` directive. The application runs as root inside the
container. If the application is compromised (e.g., via CRITICAL-01), the attacker has
root privileges within the container.

Additionally:
- No `HEALTHCHECK` is defined
- The production `Dockerfile` installs from PyPI without version pinning
  (`pip install whisperflow` without `==version`)

**Remediation:**
```dockerfile
RUN useradd -r -s /bin/false appuser
USER appuser
HEALTHCHECK --interval=30s --timeout=10s CMD curl -f http://localhost:8888/health || exit 1
```

---

### MEDIUM-02: No TLS/HTTPS or CORS Configuration

**Severity:** MEDIUM
**Files:** `whisperflow/fast_server.py`, `run.sh:50,58`

**Description:**
- The server binds to `0.0.0.0` (all interfaces) on ports 8181/8888
- No TLS termination is configured; all traffic is plaintext HTTP/WS
- No CORS middleware is configured on the FastAPI app
- Audio data (potentially sensitive speech) is transmitted unencrypted
- WebSocket connections are over `ws://` not `wss://`

**Remediation:**
- Deploy behind a TLS-terminating reverse proxy (nginx, Caddy, cloud LB)
- Add CORS middleware with explicit origin allowlist:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(CORSMiddleware, allow_origins=["https://your-domain.com"])
  ```
- Bind to `127.0.0.1` in development, use reverse proxy for production

---

### MEDIUM-03: Dockerfile.test Build Quality Gate Bypass

**Severity:** MEDIUM
**Files:** `Dockerfile.test:22-25`

**Description:**
The Dockerfile.test uses `&` (shell background operator) instead of `&&` (shell AND
chaining):

```dockerfile
RUN rm -rf .venv & python3 -m venv .venv & source .venv/bin/activate \
    & pip install --upgrade pip & pip install -r ./requirements.txt \
    & black whisperflow tests & pylint --fail-under=9.9 whisperflow tests \
    & pytest --ignore=tests/benchmark --ignore=tests/audio --cov-fail-under=95 --cov whisperflow -v tests
```

This runs all commands as background processes simultaneously. The `RUN` directive succeeds
regardless of whether `black`, `pylint`, or `pytest` pass. The CI quality gates (linting,
formatting, 95% code coverage) are effectively **non-functional** in the Docker test build.

**Remediation:**
Replace `&` with `&&` so each step must succeed before the next runs.

---

### MEDIUM-04: CI/CD Security Gaps

**Severity:** MEDIUM
**Files:** `.github/workflows/docker-image.yml`, `.github/dependabot.yml`

**Description:**
- Uses `actions/checkout@v3` instead of current `v4`
- No dependency vulnerability scanning in the CI pipeline
- No SAST (static analysis security testing) integration
- No container image scanning
- Dependabot is configured only for the `devcontainers` ecosystem — Python packages
  (`pip`) are not monitored for updates or security patches

**Remediation:**
- Update to `actions/checkout@v4`
- Add `pip-audit` or `safety` to the CI pipeline
- Add Dependabot configuration for `pip` ecosystem
- Consider adding container scanning (Trivy, Snyk Container)
- Add CodeQL or Semgrep for SAST

---

### LOW-01: Production Code Imports Test Framework

**Severity:** LOW
**Files:** `whisperflow/chat_room.py:8,41,44`

**Description:**
The production module `chat_room.py` imports `pytest` (line 8) and uses `assert` (line 41).
The `pytest.mark.skip` decorator is applied to the `main()` function (line 44).

- `pytest` is a test dependency that should not be required in production
- `assert` statements are removed when Python runs with `-O` (optimize) flag
- This creates an unnecessary dependency and fragile runtime behavior

**Remediation:**
- Remove `import pytest` from production code
- Replace `assert` with explicit `if/raise` for runtime checks
- Move test-specific code to the `tests/` directory

---

### LOW-02: Shell Script Input Handling

**Severity:** LOW
**Files:** `run.sh:17`

**Description:**
The `run.sh` script uses unquoted variable expansion `$1` in `if` conditions:
```bash
elif [ $1 = "-local" ]; then
```
This is vulnerable to word splitting and globbing if the argument contains spaces or special
characters. Since this is a local development script, the practical risk is minimal.

**Remediation:**
Quote variable references: `"$1"`

---

### LOW-03: No Dependency Update Mechanism for Python Packages

**Severity:** LOW
**Files:** `requirements.txt`, `.github/dependabot.yml`

**Description:**
All 17 Python dependencies are pinned to exact versions with no automated update mechanism.
Dependabot only monitors the `devcontainers` ecosystem. Security patches for Python
packages will not be automatically detected or applied.

**Remediation:**
Add pip ecosystem to `.github/dependabot.yml`:
```yaml
- package-ecosystem: "pip"
  directory: "/"
  schedule:
    interval: "weekly"
```

---

### LOW-04: setup.py Uses Deprecated pkg_resources

**Severity:** LOW
**Files:** `setup.py:4`

**Description:**
`setup.py` uses `from pkg_resources import parse_requirements`, which is deprecated in
favor of `importlib.metadata`. The `pkg_resources` module is part of `setuptools` and has
known performance issues and is being phased out.

**Remediation:**
- Migrate to `pyproject.toml` with modern build system
- Or replace `pkg_resources` with `importlib.metadata`

---

## Summary of Recommendations (Priority Order)

1. **Immediately** validate and sanitize the `model_name` input in `/transcribe_pcm_chunk`
   to prevent path traversal (CRITICAL-01)
2. **Immediately** upgrade `python-multipart` to >=0.0.18 and `fastapi` to latest (HIGH-03)
3. **Short-term** add authentication and rate limiting to all endpoints (HIGH-01)
4. **Short-term** fix the session memory leak and add queue size limits (HIGH-02)
5. **Short-term** add a non-root USER to Dockerfiles (MEDIUM-01)
6. **Short-term** fix `&` → `&&` in Dockerfile.test to restore quality gates (MEDIUM-03)
7. **Medium-term** deploy behind TLS-terminating reverse proxy, add CORS (MEDIUM-02)
8. **Medium-term** add pip-audit, Dependabot for pip, and SAST to CI/CD (MEDIUM-04)
9. **Medium-term** verify model file integrity with checksums (HIGH-04)
10. **Ongoing** keep all dependencies updated, monitor for new CVEs

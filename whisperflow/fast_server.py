"""fast api declaration"""

import os
import hmac
import logging
from typing import List
from fastapi import FastAPI, WebSocket, Form, File, UploadFile, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.websockets import WebSocketDisconnect
from starlette.status import WS_1008_POLICY_VIOLATION

from whisperflow import __version__
import whisperflow.streaming as st
import whisperflow.transcriber as ts

app = FastAPI()
sessions = {}

_API_KEY = os.environ.get("WHISPERFLOW_API_KEY")
_bearer_scheme = HTTPBearer(auto_error=False)


def _check_api_key(key: str) -> bool:
    """validate an API key against the configured key (constant-time)"""
    return _API_KEY is not None and hmac.compare_digest(key, _API_KEY)


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    """dependency that enforces Bearer token auth when WHISPERFLOW_API_KEY is set"""
    if _API_KEY is None:
        return
    if credentials is None or not _check_api_key(credentials.credentials):
        from fastapi import HTTPException  # pylint: disable=import-outside-toplevel

        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health", response_model=str)
def health():
    """health function on API"""
    return f"Whisper Flow V{__version__}"


@app.post(
    "/transcribe_pcm_chunk",
    response_model=dict,
    dependencies=[Depends(require_auth)],
)
def transcribe_pcm_chunk(
    model_name: str = Form(...), files: List[UploadFile] = File(...)
):
    """transcribe chunk"""
    model = ts.get_model(model_name)
    content = files[0].file.read()
    return ts.transcribe_pcm_chunks(model, [content])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default=None)):
    """websocket implementation"""
    if _API_KEY is not None:
        if token is None or not _check_api_key(token):
            await websocket.accept()
            await websocket.close(code=WS_1008_POLICY_VIOLATION)
            return

    model = ts.get_model()
    session = None

    async def transcribe_async(chunks: list):
        return await ts.transcribe_pcm_chunks_async(model, chunks)

    async def send_back_async(data: dict):
        try:
            await websocket.send_json(data)
        except Exception:  # pylint: disable=broad-except
            pass  # client disconnected mid-send

    try:
        await websocket.accept()
        session = st.TranscribeSession(transcribe_async, send_back_async)
        sessions[session.id] = session

        while True:
            data = await websocket.receive_bytes()
            session.add_chunk(data)
    except WebSocketDisconnect:
        if session:
            sessions.pop(session.id, None)
            await session.stop()
    except Exception as exception:  # pragma: no cover
        logging.error(exception)
        if session:
            sessions.pop(session.id, None)
            await session.stop()
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()

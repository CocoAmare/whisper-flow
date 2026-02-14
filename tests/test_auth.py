"""test API key authentication"""

from unittest.mock import patch

import pytest
from starlette.status import WS_1008_POLICY_VIOLATION
import tests.utils as ut
import whisperflow.fast_server as fs


TEST_API_KEY = "test-secret-key-12345"


@patch.object(fs, "_API_KEY", TEST_API_KEY)
def test_health_no_auth_required():
    """health endpoint should work without auth even when API key is set"""
    client = ut.TestClient(fs.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert "Whisper Flow" in response.text


@patch.object(fs, "_API_KEY", TEST_API_KEY)
def test_transcribe_rejected_without_key():
    """transcribe endpoint should reject requests without API key"""
    client = ut.TestClient(fs.app)
    res = ut.load_resource("3081-166546-0000")
    files = [("files", ("audio.pcm", res["audio"], "application/octet-stream"))]
    data = {"model_name": "tiny.en.pt"}
    response = client.post("/transcribe_pcm_chunk", files=files, data=data)
    assert response.status_code == 401


@patch.object(fs, "_API_KEY", TEST_API_KEY)
def test_transcribe_rejected_with_wrong_key():
    """transcribe endpoint should reject requests with wrong API key"""
    client = ut.TestClient(fs.app)
    res = ut.load_resource("3081-166546-0000")
    files = [("files", ("audio.pcm", res["audio"], "application/octet-stream"))]
    data = {"model_name": "tiny.en.pt"}
    response = client.post(
        "/transcribe_pcm_chunk",
        files=files,
        data=data,
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401


@patch.object(fs, "_API_KEY", TEST_API_KEY)
def test_transcribe_accepted_with_valid_key():
    """transcribe endpoint should accept requests with valid API key"""
    client = ut.TestClient(fs.app)
    res = ut.load_resource("3081-166546-0000")
    files = [("files", ("audio.pcm", res["audio"], "application/octet-stream"))]
    data = {"model_name": "tiny.en.pt"}
    response = client.post(
        "/transcribe_pcm_chunk",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
    )
    assert response.status_code == 200
    assert "text" in response.json()


@patch.object(fs, "_API_KEY", TEST_API_KEY)
def test_ws_rejected_without_token():
    """websocket should be accepted then closed with 1008 when no token"""
    client = ut.TestClient(fs.app)
    with pytest.raises(Exception) as exc_info:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_text()  # triggers the close frame
    assert str(WS_1008_POLICY_VIOLATION) in str(exc_info.value)


@patch.object(fs, "_API_KEY", TEST_API_KEY)
def test_ws_rejected_with_wrong_token():
    """websocket should be accepted then closed with 1008 for wrong token"""
    client = ut.TestClient(fs.app)
    with pytest.raises(Exception) as exc_info:
        with client.websocket_connect("/ws?token=wrong-key") as websocket:
            websocket.receive_text()  # triggers the close frame
    assert str(WS_1008_POLICY_VIOLATION) in str(exc_info.value)


@patch.object(fs, "_API_KEY", TEST_API_KEY)
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_ws_accepted_with_valid_token():
    """websocket should connect when valid token is provided"""
    client = ut.TestClient(fs.app)
    with client.websocket_connect(f"/ws?token={TEST_API_KEY}") as websocket:
        res = ut.load_resource("3081-166546-0000")
        websocket.send_bytes(res["audio"][:4096])
        websocket.close()
    assert client


def test_transcribe_works_without_api_key_configured():
    """when WHISPERFLOW_API_KEY is not set, endpoints work without auth"""
    assert fs._API_KEY is None  # pylint: disable=protected-access
    client = ut.TestClient(fs.app)
    res = ut.load_resource("3081-166546-0000")
    files = [("files", ("audio.pcm", res["audio"], "application/octet-stream"))]
    data = {"model_name": "tiny.en.pt"}
    response = client.post("/transcribe_pcm_chunk", files=files, data=data)
    assert response.status_code == 200

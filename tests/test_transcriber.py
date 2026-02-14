"""test transcriber"""

import pytest
from jiwer import wer
import tests.utils as ut

import whisperflow.fast_server as fr
import whisperflow.transcriber as tr


def test_load_model():
    """test load model from disl"""
    model = tr.get_model()
    assert model is not None

    resource = ut.load_resource("3081-166546-0000")

    result = tr.transcribe_pcm_chunks(model, [resource["audio"]])
    expected = resource["expected"]["final_ground_truth"]

    error = wer(result["text"].lower(), expected.lower())
    assert error < 0.1


def test_transcribe_chunk():
    """test transcribe pcm chunk"""
    resource = ut.load_resource("3081-166546-0000")
    client = ut.TestClient(fr.app)
    response = client.get("/health")
    assert response.status_code == 200

    path = ut.get_resource_path("3081-166546-0000", "wav")
    with open(path, "br") as file:
        response = client.post(
            url="/transcribe_pcm_chunk",
            data={"model_name": "tiny.en.pt"},
            files=[("files", file)],
        )

    assert response.status_code == 200

    expected = resource["expected"]["final_ground_truth"]
    error = wer(response.json()["text"].lower(), expected.lower())
    assert error < 0.1


def test_get_model_path_traversal():
    """test that path traversal attempts are rejected"""
    with pytest.raises(ValueError, match="Invalid model name"):
        tr.get_model("../../etc/passwd")
    with pytest.raises(ValueError, match="Invalid model name"):
        tr.get_model("subdir/model.pt")


def test_transcribe_empty_chunks():
    """test that empty chunks return empty text"""
    model = tr.get_model()
    result = tr.transcribe_pcm_chunks(model, [])
    assert result == {"text": ""}
    result = tr.transcribe_pcm_chunks(model, [b""])
    assert result == {"text": ""}


def test_transcribe_odd_length_bytes():
    """test that odd-length audio data is handled gracefully"""
    model = tr.get_model()
    # 3 bytes is odd, should be truncated to 2 bytes
    result = tr.transcribe_pcm_chunks(model, [b"\x00\x00\x01"])
    assert "text" in result
    # single byte should be truncated to empty
    result = tr.transcribe_pcm_chunks(model, [b"\x01"])
    assert result == {"text": ""}


@pytest.mark.asyncio
async def test_transcribe_chunk_async():
    """test transcribe async"""
    model = tr.get_model()
    assert model is not None
    resource = ut.load_resource("3081-166546-0000")
    result = await tr.transcribe_pcm_chunks_async(model, [resource["audio"]])
    expected = resource["expected"]["final_ground_truth"]
    error = wer(result["text"].lower(), expected.lower())
    assert error < 0.1

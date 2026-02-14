"""test scenario module"""

import asyncio
from queue import Queue

import pytest
import tests.utils as ut
import whisperflow.streaming as st
import whisperflow.fast_server as fs
import whisperflow.transcriber as ts


@pytest.mark.asyncio
async def test_simple():
    """test asyncio"""

    queue, should_stop = Queue(), [False]
    queue.put(1)

    async def dummy_transcriber(items: list) -> dict:
        await asyncio.sleep(0.1)
        if queue.qsize() == 0:
            should_stop[0] = True
        return {"text": str(len(items))}

    async def dummy_segment_closed(text: str) -> None:
        await asyncio.sleep(0.01)
        print(text)

    await st.transcribe(should_stop, queue, dummy_transcriber, dummy_segment_closed)
    assert queue.qsize() == 0


@pytest.mark.asyncio
async def test_transcribe_streaming(chunk_size=4096):
    """test streaming"""

    model = ts.get_model()
    queue, should_stop = Queue(), [False]
    res = ut.load_resource("3081-166546-0000")
    chunks = [
        res["audio"][i : i + chunk_size]
        for i in range(0, len(res["audio"]), chunk_size)
    ]

    async def dummy_transcriber(items: list) -> str:
        await asyncio.sleep(0.01)
        result = ts.transcribe_pcm_chunks(model, items)
        return result

    result = []

    async def dummy_segment_closed(text: str) -> None:
        await asyncio.sleep(0.01)
        result.append(text)

    task = asyncio.create_task(
        st.transcribe(should_stop, queue, dummy_transcriber, dummy_segment_closed)
    )

    for chunk in chunks:
        queue.put(chunk)
        await asyncio.sleep(0.01)

    await asyncio.sleep(1)
    should_stop[0] = True
    await task

    assert len(result) > 0


def test_streaming():
    """test hugging face image generation"""
    queue = Queue()
    queue.put(1)
    queue.put(2)
    res = st.get_all(queue)
    assert res == [1, 2]

    res = st.get_all(None)
    assert not res


@pytest.mark.asyncio
async def test_window_cap():
    """test that the transcription window is capped at _MAX_WINDOW_CHUNKS"""
    queue, should_stop = Queue(), [False]
    transcribe_calls = []

    # Fill queue beyond the cap
    for i in range(st._MAX_WINDOW_CHUNKS + 100):  # pylint: disable=protected-access
        queue.put(i)

    async def counting_transcriber(items: list) -> dict:
        transcribe_calls.append(len(items))
        should_stop[0] = True
        return {"text": "x"}

    async def dummy_segment_closed(_text: str) -> None:
        pass

    await st.transcribe(should_stop, queue, counting_transcriber, dummy_segment_closed)
    max_cap = st._MAX_WINDOW_CHUNKS  # pylint: disable=protected-access
    assert transcribe_calls[0] <= max_cap


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_session_stop_timeout():
    """test that session.stop() doesn't hang when task is slow"""
    call_count = [0]

    async def slow_transcriber(_items: list) -> dict:
        call_count[0] += 1
        await asyncio.sleep(100)  # simulate very slow transcription
        return {"text": ""}

    async def dummy_send(_data: dict) -> None:
        pass

    session = st.TranscribeSession(slow_transcriber, dummy_send)
    session.add_chunk(b"\x00\x00")
    await asyncio.sleep(0.1)  # let the loop start
    await session.stop(timeout=1)
    assert session.task.done()


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_ws(chunk_size=4096):
    """test health api"""
    client = ut.TestClient(fs.app)
    with client.websocket_connect("/ws") as websocket:
        res = ut.load_resource("3081-166546-0000")
        chunks = [
            res["audio"][i : i + chunk_size]
            for i in range(0, len(res["audio"]), chunk_size)
        ]

        for chunk in chunks:
            websocket.send_bytes(chunk)

        await asyncio.sleep(3)
        websocket.close()

    assert client


def test_health():
    """test health endpoint"""
    client = ut.TestClient(fs.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert "Whisper Flow" in response.text


def test_transcribe_pcm_chunk():
    """test transcribe pcm chunk endpoint"""
    client = ut.TestClient(fs.app)
    res = ut.load_resource("3081-166546-0000")
    files = [("files", ("audio.pcm", res["audio"], "application/octet-stream"))]
    data = {"model_name": "tiny.en.pt"}
    response = client.post("/transcribe_pcm_chunk", files=files, data=data)
    assert response.status_code == 200
    result = response.json()
    assert "text" in result
    assert len(result["text"]) > 0

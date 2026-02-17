"""test scenario module"""

import time
import uuid
import asyncio
import logging
from queue import Queue, Full
from typing import Callable


def get_all(queue: Queue) -> list:
    """get_all from queue"""
    res = []
    while queue and not queue.empty():
        res.append(queue.get())
    return res


_MAX_WINDOW_CHUNKS = 500  # ~1 MB at 2048 B/chunk, ~16 s at 16 kHz
_MAX_QUEUE_SIZE = _MAX_WINDOW_CHUNKS * 2  # buffer up to 2 windows worth


async def transcribe(
    should_stop: list,
    queue: Queue,
    transcriber: Callable[[list], str],
    segment_closed: Callable[[dict], None],
    data_event=None,
):
    """the transcription loop"""
    window, prev_result, cycles = [], {}, 0

    while not should_stop[0]:
        # When idle, wait efficiently instead of busy-polling
        if not window and queue.empty():
            if data_event is not None:
                data_event.clear()
                if queue.empty():
                    try:
                        await asyncio.wait_for(data_event.wait(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
            else:
                await asyncio.sleep(0.5)
                continue

        start = time.time()
        await asyncio.sleep(0.01)
        window.extend(get_all(queue))

        # Prevent unbounded window growth
        if len(window) > _MAX_WINDOW_CHUNKS:
            window = window[-_MAX_WINDOW_CHUNKS:]

        if not window:
            continue

        result = {
            "is_partial": True,
            "data": await transcriber(window),
            "time": (time.time() - start) * 1000,
        }

        if should_close_segment(result, prev_result, cycles):
            window, prev_result, cycles = [], {}, 0
            result["is_partial"] = False
        elif result["data"]["text"] == prev_result.get("data", {}).get("text", ""):
            cycles += 1
        else:
            cycles = 0
            prev_result = result

        if result["data"]["text"]:
            await segment_closed(result)


def should_close_segment(result: dict, prev_result: dict, cycles, max_cycles=1):
    """return if segment should be closed"""
    return cycles >= max_cycles and result["data"]["text"] == prev_result.get(
        "data", {}
    ).get("text", "")


class TranscribeSession:  # pylint: disable=too-few-public-methods
    """transcription state"""

    def __init__(self, transcribe_async, send_back_async) -> None:
        """ctor"""
        self.id = uuid.uuid4()  # pylint: disable=invalid-name
        self.queue = Queue(maxsize=_MAX_QUEUE_SIZE)
        self.should_stop = [False]
        self._data_event = asyncio.Event()
        self.task = asyncio.create_task(
            transcribe(
                self.should_stop,
                self.queue,
                transcribe_async,
                send_back_async,
                self._data_event,
            )
        )

    def add_chunk(self, chunk: bytes):
        """add new chunk"""
        try:
            self.queue.put_nowait(chunk)
        except Full:
            logging.warning("Transcription queue full, dropping chunk")
        self._data_event.set()

    async def stop(self, timeout=10):
        """stop session with timeout to prevent indefinite hangs"""
        self.should_stop[0] = True
        self._data_event.set()  # wake the loop if it's waiting
        try:
            await asyncio.wait_for(self.task, timeout=timeout)
        except asyncio.TimeoutError:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

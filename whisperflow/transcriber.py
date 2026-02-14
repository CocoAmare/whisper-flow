"""transcriber"""

import os
import asyncio
import threading

import torch
import numpy as np

import whisper
from whisper import Whisper

models = {}
_models_lock = threading.Lock()


def get_model(file_name="tiny.en.pt") -> Whisper:
    """load models from disk"""
    if file_name in models:
        return models[file_name]
    with _models_lock:
        if file_name in models:
            return models[file_name]
        base_name = os.path.basename(file_name)
        if base_name != file_name or ".." in file_name:
            raise ValueError(f"Invalid model name: {file_name}")
        models_dir = os.path.join(os.path.dirname(__file__), "models")
        path = os.path.join(models_dir, base_name)
        if not os.path.normpath(path).startswith(os.path.normpath(models_dir)):
            raise ValueError(f"Invalid model name: {file_name}")
        models[file_name] = whisper.load_model(path).to(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
    return models[file_name]


def transcribe_pcm_chunks(
    model: Whisper, chunks: list, lang="en", temperature=0.1, log_prob=-0.5
) -> dict:
    """transcribes pcm chunks list"""
    raw = b"".join(chunks)
    if not raw:
        return {"text": ""}
    arr = np.frombuffer(raw, np.int16).flatten().astype(np.float32) / 32768.0
    return model.transcribe(
        arr,
        fp16=False,
        language=lang,
        logprob_threshold=log_prob,
        temperature=temperature,
    )


async def transcribe_pcm_chunks_async(
    model: Whisper, chunks: list, lang="en", temperature=0.1, log_prob=-0.5
) -> dict:
    """transcribes pcm chunks async"""
    return await asyncio.get_running_loop().run_in_executor(
        None, transcribe_pcm_chunks, model, chunks, lang, temperature, log_prob
    )

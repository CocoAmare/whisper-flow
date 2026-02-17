"""whisper provider — wraps the existing local Whisper transcription"""

import os
import whisperflow.transcriber as ts
from whisperflow.providers.base import TranscriptionProvider


class WhisperProvider(TranscriptionProvider):
    """local Whisper model provider"""

    def __init__(self, model_name="tiny.en.pt", **_kwargs):
        self._model_name = model_name
        self._model = None

    def _get_model(self):
        """lazy-load the model"""
        if self._model is None:
            self._model = ts.get_model(self._model_name)
        return self._model

    def transcribe(self, audio_bytes: bytes, **kwargs) -> dict:
        """transcribe raw PCM audio bytes using local Whisper"""
        model = self._get_model()
        return ts.transcribe_pcm_chunks(model, [audio_bytes], **kwargs)

    async def transcribe_async(self, audio_bytes: bytes, **kwargs) -> dict:
        """async transcription using the thread pool executor"""
        model = self._get_model()
        return await ts.transcribe_pcm_chunks_async(model, [audio_bytes], **kwargs)

    def list_models(self) -> list:
        """return list of .pt files in the models directory"""
        models_dir = os.path.join(os.path.dirname(ts.__file__), "models")
        if not os.path.isdir(models_dir):
            return []
        return [f for f in os.listdir(models_dir) if f.endswith(".pt")]

    def get_model_name(self) -> str:
        """return the currently active model name"""
        return self._model_name

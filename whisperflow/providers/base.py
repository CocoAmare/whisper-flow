"""abstract base class for transcription providers"""

from abc import ABC, abstractmethod


class TranscriptionProvider(ABC):
    """interface that all transcription providers must implement"""

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, **kwargs) -> dict:
        """transcribe raw PCM audio bytes and return a result dict with 'text' key"""

    @abstractmethod
    async def transcribe_async(self, audio_bytes: bytes, **kwargs) -> dict:
        """async version of transcribe"""

    @abstractmethod
    def list_models(self) -> list:
        """return list of available models for this provider"""

    @abstractmethod
    def get_model_name(self) -> str:
        """return the currently active model name"""

"""provider registry — maps provider names to classes"""

from whisperflow.providers.base import TranscriptionProvider
from whisperflow.providers.whisper_provider import WhisperProvider

_PROVIDERS = {
    "whisper": WhisperProvider,
}


def get_provider(name="whisper", **kwargs) -> TranscriptionProvider:
    """return a provider instance by name"""
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {list(_PROVIDERS.keys())}"
        )
    return cls(**kwargs)


def list_providers() -> list:
    """return list of available provider names"""
    return list(_PROVIDERS.keys())

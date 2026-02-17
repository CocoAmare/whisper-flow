"""test provider abstraction layer"""

import pytest
from jiwer import wer
import tests.utils as ut
from whisperflow import providers


def test_list_providers():
    """test that providers are registered"""
    available = providers.list_providers()
    assert "whisper" in available


def test_get_provider():
    """test getting a provider by name"""
    provider = providers.get_provider("whisper")
    assert provider is not None
    assert provider.get_model_name() == "tiny.en.pt"


def test_get_unknown_provider():
    """test that unknown provider raises ValueError"""
    with pytest.raises(ValueError, match="Unknown provider"):
        providers.get_provider("nonexistent")


def test_whisper_provider_list_models():
    """test listing available Whisper models"""
    provider = providers.get_provider("whisper")
    model_list = provider.list_models()
    assert isinstance(model_list, list)
    assert "tiny.en.pt" in model_list


def test_whisper_provider_transcribe():
    """test transcription through the provider interface"""
    provider = providers.get_provider("whisper")
    resource = ut.load_resource("3081-166546-0000")
    result = provider.transcribe(resource["audio"])
    expected = resource["expected"]["final_ground_truth"]
    error = wer(result["text"].lower(), expected.lower())
    assert error < 0.1


@pytest.mark.asyncio
async def test_whisper_provider_transcribe_async():
    """test async transcription through the provider interface"""
    provider = providers.get_provider("whisper")
    resource = ut.load_resource("3081-166546-0000")
    result = await provider.transcribe_async(resource["audio"])
    expected = resource["expected"]["final_ground_truth"]
    error = wer(result["text"].lower(), expected.lower())
    assert error < 0.1

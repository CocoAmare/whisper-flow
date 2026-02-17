"""test configuration management"""

import os
import json
import tempfile

import whisperflow.config as cfg


def test_load_default_config():
    """test loading config when no file exists returns defaults"""
    config = cfg.load_config("/tmp/nonexistent/whisperflow.json")
    assert config["provider"] == "whisper"
    assert config["model"] == "tiny.en.pt"
    assert config["sensitivity"] == 500
    assert "whisper" in config["providers"]
    assert "ollama" in config["providers"]


def test_save_and_load_config():
    """test saving and reloading config"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_config.json")
        config = cfg.load_config(path)
        config["provider"] = "ollama"
        config["model"] = "custom-model"
        cfg.save_config(config, path)

        reloaded = cfg.load_config(path)
        assert reloaded["provider"] == "ollama"
        assert reloaded["model"] == "custom-model"
        # defaults still present
        assert reloaded["sensitivity"] == 500


def test_load_config_backfills_missing_keys():
    """test that loading a partial config backfills defaults"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "partial.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"provider": "ollama"}, fh)

        config = cfg.load_config(path)
        assert config["provider"] == "ollama"
        assert config["model"] == "tiny.en.pt"  # backfilled
        assert "providers" in config  # backfilled


def test_get_or_generate_api_key_from_env(monkeypatch):
    """test that env var takes priority"""
    monkeypatch.setenv("WHISPERFLOW_API_KEY", "test-key-123")
    key = cfg.get_or_generate_api_key("/tmp/nonexistent.json")
    assert key == "test-key-123"


def test_get_or_generate_api_key_from_config():
    """test that api_key is read from config file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "config.json")
        config = {"api_key": "existing-key-456"}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(config, fh)

        # clear env var if set
        key = cfg.get_or_generate_api_key(path)
        assert key == "existing-key-456"


def test_get_or_generate_api_key_generates_new(monkeypatch):
    """test that a new key is generated when none exists"""
    monkeypatch.delenv("WHISPERFLOW_API_KEY", raising=False)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "config.json")
        key = cfg.get_or_generate_api_key(path)
        assert key.startswith("wf-")
        assert len(key) > 10

        # verify it was persisted
        with open(path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
        assert saved["api_key"] == key

        # calling again returns the same key
        key2 = cfg.get_or_generate_api_key(path)
        assert key2 == key

"""configuration management for WhisperFlow"""

import os
import json
import secrets
import logging

_DEFAULT_CONFIG_PATH = os.environ.get(
    "WHISPERFLOW_CONFIG",
    os.path.join(os.path.dirname(__file__), "..", "config", "whisperflow.json"),
)

_DEFAULT_CONFIG = {
    "provider": "whisper",
    "model": "tiny.en.pt",
    "sensitivity": 500,
    "mode": "always_on",
    "providers": {
        "whisper": {"models_dir": "./models"},
        "ollama": {"url": "http://ollama:11434", "model": "whisper"},
        "lmstudio": {"url": "http://localhost:1234", "model": "whisper-1"},
    },
}


def load_config(path=None):
    """load config from disk, creating defaults if missing"""
    path = path or _DEFAULT_CONFIG_PATH
    path = os.path.abspath(path)

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
        # backfill any missing keys from defaults
        for key, value in _DEFAULT_CONFIG.items():
            config.setdefault(key, value)
        return config

    return dict(_DEFAULT_CONFIG)


def save_config(config, path=None):
    """save config to disk"""
    path = path or _DEFAULT_CONFIG_PATH
    path = os.path.abspath(path)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)


def get_or_generate_api_key(config_path=None):
    """return the API key from env, config, or generate a new one"""
    # 1. Environment variable takes priority
    env_key = os.environ.get("WHISPERFLOW_API_KEY")
    if env_key:
        return env_key

    # 2. Check config file
    config = load_config(config_path)
    if config.get("api_key"):
        return config["api_key"]

    # 3. Generate a new key and persist it
    new_key = "wf-" + secrets.token_urlsafe(32)
    config["api_key"] = new_key
    save_config(config, config_path)
    logging.info("Generated new API key: %s", new_key)
    logging.info("Set WHISPERFLOW_API_KEY=%s or find it in the config file", new_key)
    return new_key

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from _selfhost_config import ConfigError, load_selfhost_config, settings_payload, write_settings


def test_load_selfhost_config_reads_key_file_and_warns_on_http(tmp_path, monkeypatch):
    key_file = tmp_path / "key"
    key_file.write_text("secret-key\n")
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "MEM0_PROVIDER": "selfhost",
                "MEM0_SELFHOST_API_URL": "http://127.0.0.1:8000/",
                "MEM0_SELFHOST_API_KEY_FILE": str(key_file),
                "MEM0_USER_ID": "user-1",
                "MEM0_PROJECT_ID": "project-1",
            }
        )
    )
    monkeypatch.delenv("MEM0_SELFHOST_API_KEY", raising=False)

    config = load_selfhost_config(settings_path)

    assert config.transport == "http"
    assert config.api_url == "http://127.0.0.1:8000"
    assert config.api_key == "secret-key"
    assert config.api_key_source == f"file:{key_file}"
    assert config.user_id == "user-1"
    assert config.project_id == "project-1"
    assert any("plaintext" in warning for warning in config.warnings())


def test_load_selfhost_config_env_key_takes_precedence(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "MEM0_SELFHOST_API_URL": "https://mem0.example.com",
                "MEM0_SELFHOST_API_KEY": "settings-key",
            }
        )
    )
    monkeypatch.setenv("MEM0_SELFHOST_API_KEY", "env-key")

    config = load_selfhost_config(settings_path)

    assert config.transport == "https"
    assert config.api_key == "env-key"
    assert config.api_key_source == "env:MEM0_SELFHOST_API_KEY"


def test_load_selfhost_config_requires_http_url(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"MEM0_SELFHOST_API_URL": "mem0.example.com"}))

    with pytest.raises(ConfigError, match="must start with"):
        load_selfhost_config(settings_path)


def test_write_settings_merges_non_secret_payload(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"auto_save": True}))

    payload = settings_payload(
        api_url="https://mem0.example.com/",
        transport="https",
        user_id="user-1",
        project_id="project-1",
        api_key_file="/home/me/.mem0/key",
    )
    written = write_settings(payload, settings_path)

    assert written["auto_save"] is True
    assert written["MEM0_PROVIDER"] == "selfhost"
    assert written["MEM0_SELFHOST_API_URL"] == "https://mem0.example.com"
    assert written["MEM0_SELFHOST_API_KEY_FILE"] == "/home/me/.mem0/key"
    assert "MEM0_SELFHOST_API_KEY" not in written

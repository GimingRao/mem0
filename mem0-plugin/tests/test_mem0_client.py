"""Tests for provider config and unified client helpers."""

from __future__ import annotations

import json

import pytest


def test_create_client_defaults_to_cloud(monkeypatch):
    from _mem0_client import CLOUD_API_URL, create_client

    monkeypatch.delenv("MEM0_PROVIDER", raising=False)
    monkeypatch.delenv("MEM0_SELFHOST_API_URL", raising=False)
    monkeypatch.delenv("MEM0_API_KEY", raising=False)

    client = create_client()

    assert client.provider == "cloud"
    assert client.api_url == CLOUD_API_URL


def test_selfhost_config_reads_key_file_and_env_wins(monkeypatch, tmp_path):
    import _mem0_client
    from _mem0_client import create_client

    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "provider": "cloud",
                "selfhost_api_url": "https://settings.example.com",
                "selfhost_api_key": "settings-key",
            }
        ),
        encoding="utf-8",
    )
    key_file = tmp_path / "key"
    key_file.write_text("file-key\n", encoding="utf-8")
    monkeypatch.setattr(_mem0_client, "SETTINGS_PATH", settings_path)
    monkeypatch.setenv("MEM0_PROVIDER", "selfhost")
    monkeypatch.setenv("MEM0_SELFHOST_API_URL", "https://env.example.com")
    monkeypatch.setenv("MEM0_SELFHOST_API_KEY_FILE", str(key_file))
    monkeypatch.setenv("MEM0_SELFHOST_API_KEY", "env-key")

    client = create_client()

    assert client.provider == "selfhost"
    assert client.api_url == "https://env.example.com"
    assert client.api_key == "file-key"


def test_selfhost_config_reads_installer_uppercase_settings(monkeypatch, tmp_path):
    import _mem0_client
    from _mem0_client import create_client

    key_file = tmp_path / "selfhost-api-key"
    key_file.write_text("settings-file-key\n", encoding="utf-8")
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "MEM0_PROVIDER": "selfhost",
                "MEM0_SELFHOST_API_URL": "https://mem0.example.com",
                "MEM0_SELFHOST_API_KEY_FILE": str(key_file),
                "MEM0_SELFHOST_TRANSPORT": "ssh",
                "MEM0_SELFHOST_SSH_HOST": "mem0-box",
                "MEM0_SELFHOST_SSH_USER": "ubuntu",
                "MEM0_SELFHOST_SSH_PORT": "2222",
                "MEM0_SELFHOST_REMOTE_API_URL": "http://127.0.0.1:8000",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(_mem0_client, "SETTINGS_PATH", settings_path)
    for key in (
        "MEM0_PROVIDER",
        "MEM0_SELFHOST_API_URL",
        "MEM0_SELFHOST_API_KEY",
        "MEM0_SELFHOST_API_KEY_FILE",
        "MEM0_SELFHOST_TRANSPORT",
    ):
        monkeypatch.delenv(key, raising=False)

    client = create_client()

    assert client.provider == "selfhost"
    assert client.api_url == "https://mem0.example.com"
    assert client.api_key == "settings-file-key"
    assert client.transport == "ssh"
    assert client.ssh_host == "mem0-box"
    assert client.ssh_user == "ubuntu"
    assert client.ssh_port == 2222
    assert client.remote_api_url == "http://127.0.0.1:8000"


def test_selfhost_config_requires_url_and_key(monkeypatch):
    from _mem0_client import create_client

    monkeypatch.setenv("MEM0_PROVIDER", "selfhost")
    monkeypatch.delenv("MEM0_SELFHOST_API_URL", raising=False)
    monkeypatch.delenv("MEM0_SELFHOST_API_KEY", raising=False)
    monkeypatch.delenv("MEM0_SELFHOST_API_KEY_FILE", raising=False)

    with pytest.raises(ValueError, match="MEM0_SELFHOST_API_URL"):
        create_client()


def test_redaction_masks_api_keys():
    from _mem0_client import redact_mapping, redact_secret

    assert redact_secret("m0sk_abcdefghijklmnopqrstuvwxyz") == "m0sk...wxyz"
    assert redact_mapping({"selfhost_api_key": "abcdef1234567890", "api_url": "https://x"}) == {
        "selfhost_api_key": "abcd...7890",
        "api_url": "https://x",
    }


def test_build_metadata_writes_normal_type_to_metadata():
    from _mem0_client import build_metadata

    metadata = build_metadata({"source": "manual"}, memory_type="decision", app_id="proj", project_id="proj")

    assert metadata == {"source": "manual", "type": "decision", "app_id": "proj", "project_id": "proj"}

"""Self-hosted Mem0 plugin configuration helpers.

The installer and diagnostics share this module so secret handling and
transport normalization stay in one place.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SETTINGS_PATH = Path.home() / ".mem0" / "settings.json"
DEFAULT_KEY_FILE = Path.home() / ".mem0" / "selfhost-api-key"
VALID_TRANSPORTS = {"http", "https", "ssh"}


class ConfigError(ValueError):
    """Raised when required self-host configuration is missing or invalid."""


@dataclass(frozen=True)
class SelfhostConfig:
    provider: str
    transport: str
    api_url: str
    api_key: str | None
    api_key_source: str
    user_id: str
    project_id: str | None
    timeout: float
    ssh_host: str | None = None
    ssh_user: str | None = None
    ssh_port: int | None = None
    ssh_key: str | None = None
    remote_api_url: str | None = None

    @property
    def auth_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def request_api_url(self) -> str:
        return self.remote_api_url if self.transport == "ssh" and self.remote_api_url else self.api_url

    def warnings(self) -> list[str]:
        warnings: list[str] = []
        parsed = urlparse(self.api_url)
        if self.transport == "http" or parsed.scheme == "http":
            warnings.append("HTTP sends X-API-Key in plaintext; use only for demos or trusted networks.")
        if self.transport == "https" and parsed.scheme != "https":
            warnings.append("Transport is https but api_url is not an https URL.")
        if self.transport == "ssh" and not self.ssh_host:
            warnings.append("SSH transport requires MEM0_SELFHOST_SSH_HOST or settings.ssh_host.")
        if not self.api_key:
            warnings.append("No API key configured; authenticated self-host endpoints will fail.")
        return warnings


def _read_settings(path: Path = SETTINGS_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _first_value(settings: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = os.environ.get(key)
        if value:
            return value
    for key in keys:
        value = settings.get(key)
        if value:
            return str(value)
    return None


def _read_key(settings: dict[str, Any]) -> tuple[str | None, str]:
    inline_key = _first_value(settings, "MEM0_SELFHOST_API_KEY")
    if inline_key:
        return inline_key, "env:MEM0_SELFHOST_API_KEY" if os.environ.get("MEM0_SELFHOST_API_KEY") else "settings"

    key_file = _first_value(settings, "MEM0_SELFHOST_API_KEY_FILE")
    if not key_file:
        return None, "missing"
    try:
        key = Path(key_file).expanduser().read_text().strip()
    except OSError:
        return None, f"unreadable:{key_file}"
    if not key:
        return None, f"empty:{key_file}"
    return key, f"file:{key_file}"


def _normalize_transport(raw_transport: str | None, api_url: str | None) -> str:
    if raw_transport:
        transport = raw_transport.lower().strip()
    else:
        scheme = urlparse(api_url or "").scheme.lower()
        transport = "https" if scheme == "https" else "http"
    if transport not in VALID_TRANSPORTS:
        raise ConfigError(f"Unsupported MEM0_SELFHOST_TRANSPORT={transport!r}; expected http, https, or ssh.")
    return transport


def _as_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"Invalid MEM0_SELFHOST_SSH_PORT={value!r}; expected integer.") from exc


def _as_float(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"Invalid MEM0_SELFHOST_TIMEOUT={value!r}; expected number.") from exc


def load_selfhost_config(settings_path: Path = SETTINGS_PATH) -> SelfhostConfig:
    settings = _read_settings(settings_path)
    provider = (_first_value(settings, "MEM0_PROVIDER") or "selfhost").lower()
    api_url = _first_value(settings, "MEM0_SELFHOST_API_URL")
    if not api_url:
        raise ConfigError("MEM0_SELFHOST_API_URL is required for self-host diagnostics.")

    parsed = urlparse(api_url)
    if parsed.scheme not in {"http", "https"}:
        raise ConfigError("MEM0_SELFHOST_API_URL must start with http:// or https://.")

    transport = _normalize_transport(_first_value(settings, "MEM0_SELFHOST_TRANSPORT"), api_url)
    api_key, api_key_source = _read_key(settings)
    user_id = _first_value(settings, "MEM0_USER_ID") or os.environ.get("USER") or "default"
    project_id = _first_value(settings, "MEM0_PROJECT_ID")
    timeout = _as_float(_first_value(settings, "MEM0_SELFHOST_TIMEOUT"), 10.0)

    ssh_host = _first_value(settings, "MEM0_SELFHOST_SSH_HOST")
    ssh_user = _first_value(settings, "MEM0_SELFHOST_SSH_USER")
    ssh_port = _as_int(_first_value(settings, "MEM0_SELFHOST_SSH_PORT"))
    ssh_key = _first_value(settings, "MEM0_SELFHOST_SSH_KEY")
    remote_api_url = _first_value(settings, "MEM0_SELFHOST_REMOTE_API_URL") or "http://127.0.0.1:8000"

    return SelfhostConfig(
        provider=provider,
        transport=transport,
        api_url=api_url.rstrip("/"),
        api_key=api_key,
        api_key_source=api_key_source,
        user_id=user_id,
        project_id=project_id,
        timeout=timeout,
        ssh_host=ssh_host,
        ssh_user=ssh_user,
        ssh_port=ssh_port,
        ssh_key=ssh_key,
        remote_api_url=remote_api_url.rstrip("/") if remote_api_url else None,
    )


def redact_key(value: str | None) -> str:
    if not value:
        return "NOT_SET"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def settings_payload(
    *,
    api_url: str,
    transport: str,
    user_id: str | None,
    project_id: str | None,
    api_key_file: str | None,
    ssh_host: str | None = None,
    ssh_user: str | None = None,
    ssh_port: str | None = None,
    ssh_key: str | None = None,
    remote_api_url: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "MEM0_PROVIDER": "selfhost",
        "MEM0_SELFHOST_API_URL": api_url.rstrip("/"),
        "MEM0_SELFHOST_TRANSPORT": transport,
    }
    if user_id:
        payload["MEM0_USER_ID"] = user_id
    if project_id:
        payload["MEM0_PROJECT_ID"] = project_id
    if api_key_file:
        payload["MEM0_SELFHOST_API_KEY_FILE"] = api_key_file
    if ssh_host:
        payload["MEM0_SELFHOST_SSH_HOST"] = ssh_host
    if ssh_user:
        payload["MEM0_SELFHOST_SSH_USER"] = ssh_user
    if ssh_port:
        payload["MEM0_SELFHOST_SSH_PORT"] = ssh_port
    if ssh_key:
        payload["MEM0_SELFHOST_SSH_KEY"] = ssh_key
    if remote_api_url:
        payload["MEM0_SELFHOST_REMOTE_API_URL"] = remote_api_url.rstrip("/")
    return payload


def write_settings(payload: dict[str, Any], path: Path = SETTINGS_PATH) -> dict[str, Any]:
    existing = _read_settings(path)
    existing.update(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n")
    return existing

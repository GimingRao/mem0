"""Unified Mem0 client API for plugin hooks and MCP bridge."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

try:
    from _identity import resolve_api_key
except ImportError:
    def resolve_api_key() -> str:
        return os.environ.get("MEM0_API_KEY", "").strip()

import _selfhost


CLOUD_API_URL = "https://api.mem0.ai"
DEFAULT_TIMEOUT = 15
SETTINGS_PATH = Path.home() / ".mem0" / "settings.json"


@dataclass
class Mem0Client:
    provider: str
    api_url: str
    api_key: str
    timeout: int = DEFAULT_TIMEOUT
    transport: str = "http"
    ssh_host: str = ""
    ssh_user: str = ""
    ssh_port: int | None = None
    ssh_key: str = ""
    remote_api_url: str = ""

    @property
    def is_selfhost(self) -> bool:
        return self.provider == "selfhost"


def _read_key_file(path: str) -> str:
    if not path:
        return ""
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _read_settings() -> dict[str, Any]:
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _setting(settings: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = settings.get(key)
        if value in (None, ""):
            value = settings.get(key.upper())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def redact_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def redact_mapping(values: dict[str, Any]) -> dict[str, Any]:
    redacted = {}
    for key, value in values.items():
        if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower():
            redacted[key] = redact_secret(str(value)) if value else value
        else:
            redacted[key] = value
    return redacted


def create_client() -> Mem0Client:
    settings = _read_settings()
    selfhost_url = (
        os.environ.get("MEM0_SELFHOST_API_URL", "").strip()
        or _setting(settings, "selfhost_api_url", "api_url", "mem0_selfhost_api_url", "MEM0_SELFHOST_API_URL")
    )
    provider = (
        os.environ.get("MEM0_PROVIDER", "").strip()
        or _setting(settings, "provider", "mem0_provider", "MEM0_PROVIDER")
        or ("selfhost" if selfhost_url else "cloud")
    ).lower()
    api_url = selfhost_url if provider == "selfhost" else os.environ.get("MEM0_API_URL", CLOUD_API_URL).strip()
    key_file = (
        os.environ.get("MEM0_SELFHOST_API_KEY_FILE", "").strip()
        or _setting(settings, "selfhost_api_key_file", "api_key_file", "mem0_selfhost_api_key_file", "MEM0_SELFHOST_API_KEY_FILE")
    )
    api_key = (
        (_read_key_file(key_file) if provider == "selfhost" else "")
        or (os.environ.get("MEM0_SELFHOST_API_KEY", "").strip() if provider == "selfhost" else "")
        or (_setting(settings, "selfhost_api_key", "api_key", "mem0_selfhost_api_key", "MEM0_SELFHOST_API_KEY") if provider == "selfhost" else "")
        or resolve_api_key()
    )
    transport = (
        os.environ.get("MEM0_SELFHOST_TRANSPORT", "").strip()
        or _setting(settings, "selfhost_transport", "transport", "mem0_selfhost_transport", "MEM0_SELFHOST_TRANSPORT")
        or "http"
    ).lower()
    timeout = int(os.environ.get("MEM0_TIMEOUT", DEFAULT_TIMEOUT))
    if provider not in {"cloud", "selfhost"}:
        raise ValueError("MEM0_PROVIDER must be 'cloud' or 'selfhost'")
    if provider == "selfhost":
        if transport not in {"http", "https", "direct-http", "ssh"}:
            raise ValueError(f"Unsupported MEM0_SELFHOST_TRANSPORT: {transport}")
        if not api_url:
            raise ValueError("MEM0_SELFHOST_API_URL is required when MEM0_PROVIDER=selfhost")
        if not api_key:
            raise ValueError("MEM0_SELFHOST_API_KEY or MEM0_SELFHOST_API_KEY_FILE is required when MEM0_PROVIDER=selfhost")
    ssh_port_raw = os.environ.get("MEM0_SELFHOST_SSH_PORT", "").strip() or _setting(settings, "selfhost_ssh_port", "MEM0_SELFHOST_SSH_PORT")
    ssh_port = int(ssh_port_raw) if ssh_port_raw else None
    return Mem0Client(
        provider=provider,
        api_url=api_url.rstrip("/"),
        api_key=api_key,
        timeout=timeout,
        transport=transport,
        ssh_host=os.environ.get("MEM0_SELFHOST_SSH_HOST", "").strip() or _setting(settings, "selfhost_ssh_host", "MEM0_SELFHOST_SSH_HOST"),
        ssh_user=os.environ.get("MEM0_SELFHOST_SSH_USER", "").strip() or _setting(settings, "selfhost_ssh_user", "MEM0_SELFHOST_SSH_USER"),
        ssh_port=ssh_port,
        ssh_key=os.environ.get("MEM0_SELFHOST_SSH_KEY", "").strip() or _setting(settings, "selfhost_ssh_key", "MEM0_SELFHOST_SSH_KEY"),
        remote_api_url=(
            os.environ.get("MEM0_SELFHOST_REMOTE_API_URL", "").strip()
            or _setting(settings, "selfhost_remote_api_url", "MEM0_SELFHOST_REMOTE_API_URL")
        ).rstrip("/"),
    )


def _headers(client: Mem0Client) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if client.api_key:
        headers["Authorization"] = f"Token {client.api_key}"
        if client.is_selfhost:
            headers["X-API-Key"] = client.api_key
    return headers


def _cloud_request(client: Mem0Client, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    url = f"{client.api_url}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers(client), method=method)
    try:
        with urllib.request.urlopen(req, timeout=client.timeout) as resp:
            raw = resp.read()
            if not raw:
                return {"status": "success"}
            if not isinstance(raw, (str, bytes, bytearray)):
                return {"status": "success"}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"status": "error", "message": f"{exc.code} {body[:500]}"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, TypeError) as exc:
        return {"status": "error", "message": str(exc)}


def _selfhost_config(client: Mem0Client) -> _selfhost.SelfhostConfig:
    return _selfhost.SelfhostConfig(
        api_url=client.api_url,
        api_key=client.api_key,
        timeout=client.timeout,
        transport=client.transport,
        ssh_host=client.ssh_host,
        ssh_user=client.ssh_user,
        ssh_port=client.ssh_port,
        ssh_key=client.ssh_key,
        remote_api_url=client.remote_api_url,
    )


def _call_selfhost(func, *args, **kwargs) -> dict[str, Any]:
    try:
        result = func(*args, **kwargs)
        return result if isinstance(result, dict) else {"results": result, "status": "success"}
    except _selfhost.SelfhostError as exc:
        return {"status": "error", "message": str(exc)}


def normalize_results(data: Any) -> list[dict[str, Any]]:
    return _selfhost.normalize_list(data)


def normalize_memory(data: Any) -> dict[str, Any]:
    return _selfhost.normalize_memory(data)


def build_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    memory_type: str = "",
    source: str = "",
    user_id: str = "",
    app_id: str = "",
    project_id: str = "",
    session_id: str = "",
    branch: str = "",
) -> dict[str, Any]:
    meta = dict(metadata or {})
    if memory_type and not meta.get("type"):
        meta["type"] = memory_type
    if source and not meta.get("source"):
        meta["source"] = source
    if session_id and not meta.get("session_id"):
        meta["session_id"] = session_id
    if branch and not meta.get("branch"):
        meta["branch"] = branch
    if app_id and not meta.get("app_id"):
        meta["app_id"] = app_id
    if project_id and not meta.get("project_id"):
        meta["project_id"] = project_id
    if user_id and not meta.get("user_id"):
        meta["user_id"] = user_id
    return meta


def add_memory(
    messages: list[dict[str, Any]] | str,
    *,
    user_id: str,
    app_id: str = "",
    metadata: dict[str, Any] | None = None,
    infer: bool | None = None,
    run_id: str = "",
    expiration_date: str | date | None = None,
    client: Mem0Client | None = None,
    **extra: Any,
) -> dict[str, Any]:
    client = client or create_client()
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    payload: dict[str, Any] = {"messages": messages, "user_id": user_id, "metadata": metadata or {}}
    if app_id:
        payload["app_id"] = app_id
    if run_id and not client.is_selfhost:
        payload["run_id"] = run_id
    elif run_id:
        payload["metadata"] = build_metadata(payload["metadata"], session_id=run_id)
    if infer is not None:
        payload["infer"] = infer
    if expiration_date:
        payload["expiration_date"] = expiration_date.isoformat() if hasattr(expiration_date, "isoformat") else expiration_date
    payload.update({k: v for k, v in extra.items() if v is not None})
    if client.is_selfhost:
        return _call_selfhost(_selfhost.add_memory, _selfhost_config(client), payload)
    return _cloud_request(client, "POST", "/v3/memories/add/", payload)


def search_memories(
    query: str,
    *,
    user_id: str = "",
    app_id: str = "",
    filters: dict[str, Any] | None = None,
    top_k: int = 10,
    threshold: float | None = 0.0,
    client: Mem0Client | None = None,
    **extra: Any,
) -> dict[str, Any]:
    client = client or create_client()
    if filters is None:
        clauses = []
        if user_id:
            clauses.append({"user_id": user_id})
        if app_id:
            clauses.append({"app_id": app_id})
        filters = {"AND": clauses} if clauses else None
    payload: dict[str, Any] = {"query": query, "top_k": top_k}
    if filters:
        payload["filters"] = filters
    if threshold is not None:
        payload["threshold"] = threshold
    payload.update({k: v for k, v in extra.items() if v is not None})
    if client.is_selfhost:
        return _call_selfhost(_selfhost.search_memories, _selfhost_config(client), payload)
    data = _cloud_request(client, "POST", "/v3/memories/search/", payload)
    return {"results": normalize_results(data), "status": data.get("status", "success") if isinstance(data, dict) else "success"}


def get_memories(
    *,
    user_id: str = "",
    app_id: str = "",
    filters: dict[str, Any] | None = None,
    page: int = 1,
    page_size: int = 100,
    client: Mem0Client | None = None,
) -> dict[str, Any]:
    client = client or create_client()
    if filters is None:
        clauses = []
        if user_id:
            clauses.append({"user_id": user_id})
        if app_id:
            clauses.append({"app_id": app_id})
        filters = {"AND": clauses} if clauses else None
    payload = {"filters": filters or {}, "page": page, "page_size": page_size}
    if client.is_selfhost:
        return _call_selfhost(_selfhost.get_memories, _selfhost_config(client), payload)
    qs = urllib.parse.urlencode({"page": page, "page_size": page_size})
    data = _cloud_request(client, "POST", f"/v3/memories/?{qs}", {"filters": filters or {}})
    if isinstance(data, dict) and "results" in data:
        return data
    return {"results": normalize_results(data), "count": len(normalize_results(data)), "status": "success"}


def get_memory(memory_id: str, *, client: Mem0Client | None = None) -> dict[str, Any]:
    client = client or create_client()
    if client.is_selfhost:
        return _call_selfhost(_selfhost.get_memory, _selfhost_config(client), memory_id)
    return normalize_memory(_cloud_request(client, "GET", f"/v1/memories/{urllib.parse.quote(memory_id)}/"))


def update_memory(memory_id: str, data: str = "", *, metadata: dict[str, Any] | None = None, client: Mem0Client | None = None) -> dict[str, Any]:
    client = client or create_client()
    payload: dict[str, Any] = {}
    if data:
        payload["data"] = data
        payload["memory"] = data
    if metadata is not None:
        payload["metadata"] = metadata
    if client.is_selfhost:
        return _call_selfhost(_selfhost.update_memory, _selfhost_config(client), memory_id, payload)
    return _cloud_request(client, "PUT", f"/v1/memories/{urllib.parse.quote(memory_id)}/", payload)


def delete_memory(memory_id: str, *, client: Mem0Client | None = None) -> dict[str, Any]:
    client = client or create_client()
    if client.is_selfhost:
        return _call_selfhost(_selfhost.delete_memory, _selfhost_config(client), memory_id)
    return _cloud_request(client, "DELETE", f"/v1/memories/{urllib.parse.quote(memory_id)}/")


def delete_all_memories(*, user_id: str = "", app_id: str = "", client: Mem0Client | None = None) -> dict[str, Any]:
    client = client or create_client()
    payload = {k: v for k, v in {"user_id": user_id, "app_id": app_id}.items() if v}
    if client.is_selfhost:
        return _call_selfhost(_selfhost.delete_all_memories, _selfhost_config(client), payload)
    return _cloud_request(client, "DELETE", "/v1/memories/", payload)


def unsupported(name: str, *, partial: bool = False, message: str = "") -> dict[str, Any]:
    return {
        "status": "partial" if partial else "unsupported",
        "capability": name,
        "message": message or f"{name} is not supported by the self-host compatibility bridge.",
    }


def list_entities(**_: Any) -> dict[str, Any]:
    return unsupported("list_entities")


def delete_entities(**_: Any) -> dict[str, Any]:
    return unsupported("delete_entities")


def list_events(**_: Any) -> dict[str, Any]:
    return unsupported("list_events", partial=True, message="Self-host writes are synchronous or server-defined; no Cloud event list is available.")


def get_event_status(event_id: str = "", **_: Any) -> dict[str, Any]:
    if not event_id:
        return unsupported("get_event_status", partial=True, message="No event_id was returned by this backend.")
    return {"status": "partial", "event_id": event_id, "message": "Self-host event status is not available; check the returned memory response directly."}

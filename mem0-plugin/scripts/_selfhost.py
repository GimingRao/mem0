"""Self-host Mem0 REST compatibility layer.

This module is intentionally small: C-line callers depend on _mem0_client,
while B-line can later replace the internals here without changing hooks or
the MCP bridge.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_TIMEOUT = 15
LOCAL_FILTER_KEYS = {"app_id", "project_id", "type", "source"}


@dataclass
class SelfhostConfig:
    api_url: str
    api_key: str = ""
    timeout: int = DEFAULT_TIMEOUT
    transport: str = "http"
    ssh_host: str = ""
    ssh_user: str = ""
    ssh_port: int | None = None
    ssh_key: str = ""
    remote_api_url: str = ""


class SelfhostError(RuntimeError):
    pass


def _headers(config: SelfhostConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Token {config.api_key}"
        headers["X-API-Key"] = config.api_key
    return headers


def _request(config: SelfhostConfig, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    if config.transport == "ssh":
        return _request_ssh(config, method, path, payload)
    base = config.api_url.rstrip("/")
    url = f"{base}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers(config), method=method)
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=config.timeout) as resp:
            raw = resp.read()
            if not raw:
                return {"status": "success"}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SelfhostError(f"self-host request failed: {exc.code} {body[:500]}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SelfhostError(f"self-host request failed: {exc}") from exc


def _ssh_target(config: SelfhostConfig) -> str:
    if not config.ssh_host:
        raise SelfhostError("self-host ssh transport requires MEM0_SELFHOST_SSH_HOST")
    if config.ssh_user:
        return f"{config.ssh_user}@{config.ssh_host}"
    return config.ssh_host


def _request_ssh(config: SelfhostConfig, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    base = (config.remote_api_url or config.api_url).rstrip("/")
    url = f"{base}{path}"
    remote_cmd = ["curl", "-sS", "-w", "\\n%{http_code}", "-X", method, url]
    if config.api_key:
        remote_cmd.extend(["-H", f"X-API-Key: {config.api_key}", "-H", f"Authorization: Token {config.api_key}"])
    if payload is not None:
        remote_cmd.extend(["-H", "Content-Type: application/json", "--data-binary", json.dumps(payload)])

    ssh_cmd = ["ssh", "-o", "BatchMode=yes"]
    if config.ssh_port:
        ssh_cmd.extend(["-p", str(config.ssh_port)])
    if config.ssh_key:
        ssh_cmd.extend(["-i", config.ssh_key])
    ssh_cmd.append(_ssh_target(config))
    ssh_cmd.append(" ".join(shlex.quote(part) for part in remote_cmd))

    try:
        completed = subprocess.run(
            ssh_cmd,
            text=True,
            capture_output=True,
            timeout=config.timeout + 5,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SelfhostError(f"self-host ssh request timed out: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"ssh exited {completed.returncode}"
        raise SelfhostError(f"self-host ssh request failed: {detail}")
    body, _, status_text = completed.stdout.rstrip("\n").rpartition("\n")
    try:
        status = int(status_text)
    except ValueError as exc:
        raise SelfhostError(f"self-host ssh request did not return HTTP status: {completed.stdout[:200]}") from exc
    if status >= 400:
        raise SelfhostError(f"self-host ssh request failed: {status} {body[:500]}")
    if not body:
        return {"status": "success"}
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise SelfhostError(f"self-host ssh request returned invalid JSON: {exc}") from exc


def normalize_memory(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {"memory": str(item), "metadata": {}}
    result = dict(item)
    metadata = result.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    if "type" in result and "type" not in metadata:
        metadata["type"] = result["type"]
    if "app_id" in result and "app_id" not in metadata:
        metadata["app_id"] = result["app_id"]
    if "project_id" in result and "project_id" not in metadata:
        metadata["project_id"] = result["project_id"]
    result["metadata"] = metadata
    return result


def normalize_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [normalize_memory(item) for item in data]
    if isinstance(data, dict):
        for key in ("results", "memories", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return [normalize_memory(item) for item in value]
    return []


def _extract_filter_clauses(filters: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(filters, dict):
        return []
    if isinstance(filters.get("AND"), list):
        return [c for c in filters["AND"] if isinstance(c, dict)]
    return [filters]


def _get_metadata_value(memory: dict[str, Any], key: str) -> Any:
    metadata = memory.get("metadata") or {}
    if key == "type":
        return memory.get("type") or metadata.get("type") or metadata.get("category")
    if key == "app_id":
        return memory.get("app_id") or metadata.get("app_id") or metadata.get("project_id")
    if key == "project_id":
        return memory.get("project_id") or metadata.get("project_id") or memory.get("app_id") or metadata.get("app_id")
    return memory.get(key) if key in memory else metadata.get(key)


def _matches_clause(memory: dict[str, Any], clause: dict[str, Any]) -> bool:
    for key, expected in clause.items():
        if key not in LOCAL_FILTER_KEYS and key != "metadata":
            continue
        if key == "metadata" and isinstance(expected, dict):
            for meta_key, meta_expected in expected.items():
                if meta_key not in LOCAL_FILTER_KEYS:
                    continue
                if _get_metadata_value(memory, meta_key) != meta_expected:
                    return False
            continue
        if expected == "*":
            continue
        if _get_metadata_value(memory, key) != expected:
            return False
    return True


def post_filter(memories: list[dict[str, Any]], filters: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not filters:
        return memories
    if isinstance(filters, dict) and isinstance(filters.get("OR"), list):
        clauses = [c for c in filters["OR"] if isinstance(c, dict)]
        if not clauses:
            return memories
        return [m for m in memories if any(_matches_clause(m, c) for c in clauses)]
    clauses = _extract_filter_clauses(filters)
    if not clauses:
        return memories
    return [m for m in memories if all(_matches_clause(m, c) for c in clauses)]


def coarse_user_filters(filters: dict[str, Any] | None, user_id: str = "") -> dict[str, Any]:
    uid = user_id
    for clause in _extract_filter_clauses(filters):
        if clause.get("user_id") and clause.get("user_id") != "*":
            uid = str(clause["user_id"])
            break
    return {"user_id": uid} if uid else {}


def add_memory(config: SelfhostConfig, payload: dict[str, Any]) -> dict[str, Any]:
    selfhost_payload = dict(payload)
    metadata = dict(selfhost_payload.get("metadata") or {})
    if selfhost_payload.get("app_id") and not metadata.get("app_id"):
        metadata["app_id"] = selfhost_payload["app_id"]
    if selfhost_payload.get("app_id") and not metadata.get("project_id"):
        metadata["project_id"] = selfhost_payload["app_id"]
    selfhost_payload["metadata"] = metadata
    selfhost_payload.pop("app_id", None)
    return _request(config, "POST", "/memories", selfhost_payload)


def search_memories(config: SelfhostConfig, payload: dict[str, Any]) -> dict[str, Any]:
    user_id = payload.get("user_id", "")
    remote_payload = dict(payload)
    if payload.get("filters"):
        remote_payload["filters"] = coarse_user_filters(payload.get("filters"), user_id)
    data = _request(config, "POST", "/search", remote_payload)
    results = post_filter(normalize_list(data), payload.get("filters"))
    top_k = int(payload.get("top_k") or payload.get("limit") or len(results) or 0)
    return {"results": results[:top_k] if top_k else results, "status": "success"}


def get_memories(config: SelfhostConfig, payload: dict[str, Any]) -> dict[str, Any]:
    filters = payload.get("filters")
    page_size = int(payload.get("page_size") or payload.get("limit") or 100)
    user_filter = coarse_user_filters(filters)
    query = urllib.parse.urlencode(user_filter)
    data = _request(config, "GET", f"/memories?{query}" if query else "/memories")
    results = post_filter(normalize_list(data), filters)
    if isinstance(data, dict):
        response = dict(data)
        response["results"] = results[:page_size]
        response["count"] = len(results)
        return response
    return {"results": results[:page_size], "count": len(results), "status": "success"}


def get_memory(config: SelfhostConfig, memory_id: str) -> dict[str, Any]:
    return normalize_memory(_request(config, "GET", f"/memories/{urllib.parse.quote(memory_id)}"))


def update_memory(config: SelfhostConfig, memory_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    selfhost_payload: dict[str, Any] = {}
    if payload.get("data") or payload.get("memory"):
        selfhost_payload["text"] = payload.get("data") or payload.get("memory")
    if payload.get("metadata") is not None:
        selfhost_payload["metadata"] = payload["metadata"]
    return _request(config, "PUT", f"/memories/{urllib.parse.quote(memory_id)}", selfhost_payload)


def delete_memory(config: SelfhostConfig, memory_id: str) -> dict[str, Any]:
    return _request(config, "DELETE", f"/memories/{urllib.parse.quote(memory_id)}")


def delete_all_memories(config: SelfhostConfig, payload: dict[str, Any]) -> dict[str, Any]:
    user_id = payload.get("user_id")
    query = urllib.parse.urlencode({"user_id": user_id}) if user_id else ""
    return _request(config, "DELETE", f"/memories?{query}" if query else "/memories", None)

"""Self-hosted Mem0 health and smoke probe helpers."""

from __future__ import annotations

import json
import importlib
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from _selfhost_config import SelfhostConfig, redact_key


@dataclass
class ProbeResult:
    status: str
    category: str | None = None
    detail: str | None = None
    latency_ms: int | None = None
    data: Any = None

    @property
    def ok(self) -> bool:
        return self.status == "pass"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "category": self.category,
            "detail": self.detail,
            "latency_ms": self.latency_ms,
            "data": self.data,
        }


def classify_http_status(status: int) -> str:
    if status in {401, 403}:
        return "auth"
    if status in {404, 405}:
        return "endpoint"
    if status in {400, 422}:
        return "schema"
    if status >= 500:
        return "runtime"
    return "endpoint"


def classify_exception(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return classify_http_status(exc.code)
    if isinstance(exc, urllib.error.URLError):
        reason = str(getattr(exc, "reason", exc))
        if "timed out" in reason.lower():
            return "endpoint"
        return "endpoint"
    if isinstance(exc, (json.JSONDecodeError, UnicodeDecodeError)):
        return "schema"
    if isinstance(exc, subprocess.TimeoutExpired):
        return "endpoint"
    return "runtime"


def normalize_results(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("results", "memories"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def memory_id_from_add_response(data: Any) -> str | None:
    if isinstance(data, dict):
        for key in ("id", "memory_id"):
            if data.get(key):
                return str(data[key])
        results = data.get("results")
        if isinstance(results, list):
            for item in results:
                found = memory_id_from_add_response(item)
                if found:
                    return found
    if isinstance(data, list):
        for item in data:
            found = memory_id_from_add_response(item)
            if found:
                return found
    return None


def result_matches_probe(result: dict[str, Any], probe_id: str, user_id: str, project_id: str | None) -> bool:
    metadata = result.get("metadata") or {}
    text = str(result.get("memory") or result.get("text") or "")
    if probe_id not in text and metadata.get("probe_id") != probe_id:
        return False
    if result.get("user_id") and result.get("user_id") != user_id:
        return False
    if project_id and metadata.get("app_id") not in {project_id, None}:
        return False
    if metadata.get("type") not in {"health_check", None}:
        return False
    return True


def _headers(config: SelfhostConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["X-API-Key"] = config.api_key
    return headers


def _request_http(
    config: SelfhostConfig,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> tuple[int, Any, int]:
    url = f"{config.api_url}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=_headers(config), method=method)
    start = time.perf_counter()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=config.timeout) as response:
        raw = response.read()
        latency_ms = int((time.perf_counter() - start) * 1000)
        if not raw:
            return response.status, {}, latency_ms
        return response.status, json.loads(raw.decode()), latency_ms


def _ssh_target(config: SelfhostConfig) -> str:
    if not config.ssh_host:
        raise RuntimeError("SSH transport requires ssh_host.")
    target = config.ssh_host
    if config.ssh_user:
        target = f"{config.ssh_user}@{target}"
    return target


def _request_ssh(
    config: SelfhostConfig,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> tuple[int, Any, int]:
    base = config.request_api_url.rstrip("/")
    url = f"{base}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    remote_cmd = ["curl", "-sS", "-w", "\\n%{http_code}", "-X", method, url]
    if config.api_key:
        remote_cmd.extend(["-H", f"X-API-Key: {config.api_key}"])
    if payload is not None:
        remote_cmd.extend(["-H", "Content-Type: application/json", "--data-binary", json.dumps(payload)])

    ssh_cmd = ["ssh", "-o", "BatchMode=yes"]
    if config.ssh_port:
        ssh_cmd.extend(["-p", str(config.ssh_port)])
    if config.ssh_key:
        ssh_cmd.extend(["-i", config.ssh_key])
    ssh_cmd.append(_ssh_target(config))
    ssh_cmd.append(" ".join(shlex.quote(part) for part in remote_cmd))

    start = time.perf_counter()
    completed = subprocess.run(ssh_cmd, text=True, capture_output=True, timeout=config.timeout + 5, check=False)
    latency_ms = int((time.perf_counter() - start) * 1000)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"ssh exited {completed.returncode}")
    body, _, status_text = completed.stdout.rstrip("\n").rpartition("\n")
    try:
        status = int(status_text)
    except ValueError as exc:
        raise RuntimeError(f"SSH curl did not return an HTTP status: {completed.stdout[:200]}") from exc
    data = json.loads(body) if body else {}
    if status >= 400:
        raise urllib.error.HTTPError(url, status, body[:200], {}, None)
    return status, data, latency_ms


def request_json(
    config: SelfhostConfig,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> tuple[int, Any, int]:
    if config.transport == "ssh":
        return _request_ssh(config, method, path, payload, query)
    return _request_http(config, method, path, payload, query)


def _request_result(
    config: SelfhostConfig,
    name: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> ProbeResult:
    try:
        status, data, latency_ms = request_json(config, method, path, payload, query)
    except Exception as exc:
        return ProbeResult("fail", classify_exception(exc), f"{name}: {exc}", data=None)
    if status >= 400:
        return ProbeResult("fail", classify_http_status(status), f"{name}: HTTP {status}", latency_ms, data)
    return ProbeResult("pass", latency_ms=latency_ms, data=data)


def probe_provider(config: SelfhostConfig) -> ProbeResult:
    return _request_result(config, "provider", "GET", "/configure")


def probe_add(config: SelfhostConfig, probe_id: str) -> ProbeResult:
    metadata: dict[str, Any] = {"type": "health_check", "probe": True, "probe_id": probe_id}
    if config.project_id:
        metadata["app_id"] = config.project_id
    payload = {
        "messages": [{"role": "user", "content": f"Mem0 self-host health probe {probe_id}"}],
        "user_id": config.user_id,
        "metadata": metadata,
        "infer": False,
    }
    return _request_result(config, "add", "POST", "/memories", payload)


def probe_search(config: SelfhostConfig, probe_id: str) -> ProbeResult:
    filters: dict[str, Any] = {"user_id": config.user_id}
    if config.project_id:
        filters["app_id"] = config.project_id
    payload = {
        "query": f"Mem0 self-host health probe {probe_id}",
        "filters": filters,
        "top_k": 5,
    }
    result = _request_result(config, "search", "POST", "/search", payload)
    if not result.ok:
        return result
    results = normalize_results(result.data)
    if not any(result_matches_probe(item, probe_id, config.user_id, config.project_id) for item in results):
        return ProbeResult(
            "fail",
            "filter",
            "search succeeded but did not return the metadata-filtered probe",
            result.latency_ms,
            result.data,
        )
    return result


def probe_delete(config: SelfhostConfig, memory_id: str | None) -> ProbeResult:
    if not memory_id:
        return ProbeResult("warn", "schema", "add response did not expose a memory id; cleanup skipped")
    return _request_result(config, "delete", "DELETE", f"/memories/{memory_id}")


def run_health(config: SelfhostConfig) -> dict[str, Any]:
    delegated = _delegate_to_unified_client("selfhost_health", config)
    if delegated is not None:
        return delegated

    probe_id = f"health-{int(time.time() * 1000)}"
    provider = probe_provider(config)
    add = probe_add(config, probe_id)
    search = probe_search(config, probe_id) if add.ok else ProbeResult("fail", add.category, "search skipped because add failed")
    memory_id = memory_id_from_add_response(add.data)
    cleanup = probe_delete(config, memory_id) if add.ok else ProbeResult("warn", "runtime", "cleanup skipped")
    warnings = config.warnings()
    if cleanup.status == "warn" and cleanup.detail:
        warnings.append(cleanup.detail)
    return {
        "provider": {
            "status": "pass" if config.provider == "selfhost" else "warn",
            "value": config.provider,
            "detail": None if config.provider == "selfhost" else "MEM0_PROVIDER is not selfhost",
        },
        "transport": {"status": "pass", "value": config.transport},
        "api_url": {"status": "pass", "value": config.api_url},
        "auth": {
            "status": "pass" if config.auth_configured else "fail",
            "value": redact_key(config.api_key),
            "source": config.api_key_source,
            "category": None if config.auth_configured else "auth",
        },
        "endpoint": provider.as_dict(),
        "add": add.as_dict(),
        "search": search.as_dict(),
        "metadata_filter": {
            "status": "pass" if search.ok else "fail",
            "category": None if search.ok else search.category,
            "detail": "probe found with user/project metadata filters" if search.ok else search.detail,
        },
        "warnings": warnings,
    }


def run_smoke(config: SelfhostConfig) -> dict[str, Any]:
    delegated = _delegate_to_unified_client("selfhost_smoke", config)
    if delegated is not None:
        return delegated

    health = run_health(config)
    failures = []
    for key in ("auth", "endpoint", "add", "search", "metadata_filter"):
        value = health[key]
        if value.get("status") == "fail":
            failures.append({"check": key, "category": value.get("category"), "detail": value.get("detail")})
    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "health": health,
    }


def _delegate_to_unified_client(function_name: str, config: SelfhostConfig) -> dict[str, Any] | None:
    """Use B-line unified client diagnostics when available.

    The module does not exist in the current baseline, so failures to import or
    missing functions intentionally fall back to the local diagnostic transport.
    """
    try:
        module = importlib.import_module("_mem0_client")
    except ImportError:
        return None
    delegate = getattr(module, function_name, None)
    if delegate is None:
        return None
    result = delegate(config)
    return result if isinstance(result, dict) else None

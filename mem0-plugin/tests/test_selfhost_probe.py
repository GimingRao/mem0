from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from _selfhost_config import SelfhostConfig
from _selfhost_probe import (
    classify_exception,
    classify_http_status,
    memory_id_from_add_response,
    normalize_results,
    request_json,
    run_health,
)


def make_config(**kwargs) -> SelfhostConfig:
    defaults = {
        "provider": "selfhost",
        "transport": "https",
        "api_url": "https://mem0.example.com",
        "api_key": "test-key",
        "api_key_source": "test",
        "user_id": "user-1",
        "project_id": "project-1",
        "timeout": 5.0,
    }
    defaults.update(kwargs)
    return SelfhostConfig(**defaults)


def test_classify_status_and_exception_categories():
    assert classify_http_status(401) == "auth"
    assert classify_http_status(422) == "schema"
    assert classify_http_status(404) == "endpoint"
    assert classify_http_status(500) == "runtime"

    error = urllib.error.HTTPError("https://x", 403, "forbidden", {}, None)
    assert classify_exception(error) == "auth"
    assert classify_exception(json.JSONDecodeError("bad", "x", 0)) == "schema"


def test_normalize_results_and_memory_id_extraction():
    assert normalize_results({"results": [{"id": "1"}]}) == [{"id": "1"}]
    assert normalize_results([{"id": "1"}, "bad"]) == [{"id": "1"}]
    assert memory_id_from_add_response({"results": [{"id": "mem-1"}]}) == "mem-1"
    assert memory_id_from_add_response({"memory_id": "mem-2"}) == "mem-2"


def test_run_health_success_with_mocked_transport(monkeypatch):
    calls: list[tuple[str, str, dict | None]] = []

    def fake_request_json(config, method, path, payload=None, query=None):
        calls.append((method, path, payload))
        if path == "/configure":
            return 200, {"llm": {"provider": "openai"}}, 10
        if path == "/memories" and method == "POST":
            probe_id = payload["metadata"]["probe_id"]
            return 200, {"results": [{"id": "mem-1", "memory": f"Mem0 self-host health probe {probe_id}"}]}, 20
        if path == "/search":
            probe_id = payload["query"].split()[-1]
            return (
                200,
                {
                    "results": [
                        {
                            "id": "mem-1",
                            "memory": f"Mem0 self-host health probe {probe_id}",
                            "user_id": "user-1",
                            "metadata": {"type": "health_check", "app_id": "project-1", "probe_id": probe_id},
                        }
                    ]
                },
                30,
            )
        if path == "/memories/mem-1" and method == "DELETE":
            return 200, {"message": "ok"}, 10
        raise AssertionError((method, path, payload))

    monkeypatch.setattr("_selfhost_probe.request_json", fake_request_json)

    report = run_health(make_config())

    assert report["provider"]["status"] == "pass"
    assert report["auth"]["status"] == "pass"
    assert report["add"]["status"] == "pass"
    assert report["search"]["status"] == "pass"
    assert report["metadata_filter"]["status"] == "pass"
    assert ("DELETE", "/memories/mem-1", None) in calls


def test_run_health_classifies_metadata_filter_failure(monkeypatch):
    def fake_request_json(config, method, path, payload=None, query=None):
        if path == "/configure":
            return 200, {}, 10
        if path == "/memories" and method == "POST":
            return 200, {"id": "mem-1"}, 20
        if path == "/search":
            return 200, {"results": []}, 30
        if path == "/memories/mem-1" and method == "DELETE":
            return 200, {}, 10
        raise AssertionError((method, path, payload))

    monkeypatch.setattr("_selfhost_probe.request_json", fake_request_json)

    report = run_health(make_config())

    assert report["search"]["status"] == "fail"
    assert report["search"]["category"] == "filter"
    assert report["metadata_filter"]["category"] == "filter"


def test_ssh_transport_builds_remote_curl_command(monkeypatch):
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, text, capture_output, timeout, check):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout='{"ok": true}\n200', stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = make_config(
        transport="ssh",
        api_url="http://127.0.0.1:8000",
        ssh_host="mem0-box",
        ssh_user="ubuntu",
        ssh_port=2222,
        ssh_key="/tmp/key",
        remote_api_url="http://127.0.0.1:8000",
    )

    status, data, _latency = request_json(config, "POST", "/search", {"query": "x"})

    assert status == 200
    assert data == {"ok": True}
    assert captured["cmd"][:6] == ["ssh", "-o", "BatchMode=yes", "-p", "2222", "-i"]
    assert "ubuntu@mem0-box" in captured["cmd"]
    assert "curl" in captured["cmd"][-1]
    assert "http://127.0.0.1:8000/search" in captured["cmd"][-1]

"""Tests for the self-hosted Mem0 REST compatibility layer."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch


def _mock_response(payload):
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _patch_opener_open(side_effect):
    opener = MagicMock()
    opener.open.side_effect = side_effect
    return patch("urllib.request.build_opener", return_value=opener)


def test_add_writes_app_scope_to_metadata_not_rest_memory_type():
    from _selfhost import SelfhostConfig, add_memory

    captured = {}

    def mock_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _mock_response({"results": [{"id": "m1", "memory": "Stored"}]})

    with _patch_opener_open(mock_urlopen):
        add_memory(
            SelfhostConfig("https://mem0.example.com", "secret"),
            {
                "messages": [{"role": "user", "content": "Remember Postgres"}],
                "user_id": "user-1",
                "app_id": "project-1",
                "metadata": {"source": "manual", "type": "decision"},
            },
        )

    assert captured["url"] == "https://mem0.example.com/memories"
    assert captured["headers"]["X-api-key"] == "secret"
    assert captured["body"]["user_id"] == "user-1"
    assert captured["body"]["metadata"]["type"] == "decision"
    assert captured["body"]["metadata"]["app_id"] == "project-1"
    assert captured["body"]["metadata"]["project_id"] == "project-1"
    assert "memory_type" not in captured["body"]
    assert "app_id" not in captured["body"]


def test_search_sends_only_user_id_remotely_and_post_filters_metadata():
    from _selfhost import SelfhostConfig, search_memories

    captured_body = {}
    remote_results = {
        "results": [
            {
                "id": "keep",
                "memory": "Use pgvector",
                "metadata": {"app_id": "proj", "source": "manual"},
                "type": "decision",
            },
            {
                "id": "wrong-type",
                "memory": "Use sqlite",
                "metadata": {"app_id": "proj", "source": "manual"},
                "type": "anti_pattern",
            },
            {
                "id": "wrong-project",
                "memory": "Use qdrant",
                "metadata": {"app_id": "other", "source": "manual", "type": "decision"},
            },
            {
                "id": "wrong-source",
                "memory": "Use pinecone",
                "metadata": {"app_id": "proj", "source": "import", "type": "decision"},
            },
        ]
    }

    def mock_urlopen(req, timeout=None):
        captured_body.update(json.loads(req.data.decode("utf-8")))
        assert req.full_url == "https://mem0.example.com/search"
        return _mock_response(remote_results)

    filters = {
        "AND": [
            {"user_id": "user-1"},
            {"app_id": "proj"},
            {"metadata": {"type": "decision"}},
            {"metadata": {"source": "manual"}},
        ]
    }
    with _patch_opener_open(mock_urlopen):
        response = search_memories(
            SelfhostConfig("https://mem0.example.com", "secret"),
            {"query": "database", "filters": filters, "top_k": 10},
        )

    assert captured_body["filters"] == {"user_id": "user-1"}
    assert [m["id"] for m in response["results"]] == ["keep"]
    assert response["results"][0]["metadata"]["type"] == "decision"


def test_get_memories_uses_user_id_query_and_local_project_filter():
    from _selfhost import SelfhostConfig, get_memories

    def mock_urlopen(req, timeout=None):
        assert req.full_url == "https://mem0.example.com/memories?user_id=user-1"
        return _mock_response(
            {
                "results": [
                    {"id": "a", "memory": "A", "metadata": {"project_id": "proj"}},
                    {"id": "b", "memory": "B", "metadata": {"project_id": "other"}},
                ]
            }
        )

    with _patch_opener_open(mock_urlopen):
        response = get_memories(
            SelfhostConfig("https://mem0.example.com", "secret"),
            {"filters": {"AND": [{"user_id": "user-1"}, {"project_id": "proj"}]}},
        )

    assert [m["id"] for m in response["results"]] == ["a"]


def test_update_translates_data_to_selfhost_text_field():
    from _selfhost import SelfhostConfig, update_memory

    captured = {}

    def mock_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _mock_response({"message": "updated"})

    with _patch_opener_open(mock_urlopen):
        update_memory(SelfhostConfig("https://mem0.example.com", "secret"), "m1", {"data": "new text"})

    assert captured["url"] == "https://mem0.example.com/memories/m1"
    assert captured["body"] == {"text": "new text"}


def test_event_status_shim():
    from _mem0_client import get_event_status

    assert get_event_status("")["status"] == "partial"
    assert get_event_status("event-1")["event_id"] == "event-1"


def test_metadata_type_normalizes_top_level_type():
    from _selfhost import normalize_memory

    memory = normalize_memory({"id": "m1", "memory": "Remember this", "type": "decision"})

    assert memory["metadata"]["type"] == "decision"


def test_ssh_transport_builds_remote_curl_command():
    from _selfhost import SelfhostConfig, search_memories

    captured = {}

    def fake_run(cmd, text, capture_output, timeout, check):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout='{"results": []}\n200', stderr="")

    filters = {"AND": [{"user_id": "user-1"}]}
    with patch("subprocess.run", side_effect=fake_run):
        response = search_memories(
            SelfhostConfig(
                "https://public.example.com",
                "secret",
                transport="ssh",
                ssh_host="mem0-box",
                ssh_user="ubuntu",
                ssh_port=2222,
                ssh_key="/tmp/key",
                remote_api_url="http://127.0.0.1:8000",
            ),
            {"query": "database", "filters": filters, "top_k": 10},
        )

    assert response["status"] == "success"
    assert captured["cmd"][:6] == ["ssh", "-o", "BatchMode=yes", "-p", "2222", "-i"]
    assert "ubuntu@mem0-box" in captured["cmd"]
    assert "curl" in captured["cmd"][-1]
    assert "http://127.0.0.1:8000/search" in captured["cmd"][-1]
    assert "X-API-Key: secret" in captured["cmd"][-1]

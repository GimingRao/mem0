from __future__ import annotations

import os
import sys

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import _mem0_client
import _selfhost


def test_post_filter_matches_top_level_and_metadata_fields():
    memories = [
        {
            "id": "1",
            "memory": "keep",
            "user_id": "u1",
            "app_id": "app-a",
            "metadata": {"source": "auto-import", "type": "project_profile", "branch": "main"},
        },
        {
            "id": "2",
            "memory": "drop",
            "user_id": "u1",
            "app_id": "app-b",
            "metadata": {"source": "auto-import", "type": "project_profile", "branch": "main"},
        },
    ]

    result = _selfhost.post_filter(
        memories,
        {
            "AND": [
                {"user_id": "u1"},
                {"app_id": "app-a"},
                {"metadata": {"source": "auto-import"}},
                {"metadata": {"type": "project_profile"}},
                {"metadata": {"branch": "main"}},
            ]
        },
    )

    assert [m["id"] for m in result] == ["1"]


def test_build_metadata_injects_selfhost_scope_fields():
    metadata = _mem0_client.build_metadata(
        {"confidence": 0.7},
        memory_type="auto_capture",
        source="auto_capture",
        user_id="u1",
        app_id="app-a",
        project_id="proj-a",
        session_id="s1",
        branch="main",
    )

    assert metadata == {
        "confidence": 0.7,
        "type": "auto_capture",
        "source": "auto_capture",
        "session_id": "s1",
        "branch": "main",
        "app_id": "app-a",
        "project_id": "proj-a",
        "user_id": "u1",
    }


def test_create_client_selects_selfhost_from_api_url(monkeypatch):
    monkeypatch.setenv("MEM0_SELFHOST_API_URL", "http://localhost:8888")
    monkeypatch.setenv("MEM0_SELFHOST_API_KEY", "secret")
    monkeypatch.delenv("MEM0_PROVIDER", raising=False)

    client = _mem0_client.create_client()

    assert client.provider == "selfhost"
    assert client.api_url == "http://localhost:8888"
    assert client.api_key == "secret"

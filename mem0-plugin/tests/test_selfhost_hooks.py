from __future__ import annotations

import os
import sys

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import auto_capture
import capture_compact_summary
import capture_session_summary
import on_pre_compact


def _capture_add(monkeypatch, module):
    calls = []

    class DummyClient:
        api_key = ""

    monkeypatch.setattr(module._mem0_client, "create_client", lambda: DummyClient())

    def fake_add_memory(messages, **kwargs):
        calls.append({"messages": messages, **kwargs})
        return {"status": "success", "id": "m1"}

    monkeypatch.setattr(module._mem0_client, "add_memory", fake_add_memory)
    return calls


def test_auto_capture_store_exchange_uses_unified_client_metadata(monkeypatch):
    calls = _capture_add(monkeypatch, auto_capture)

    ok = auto_capture.store_exchange(
        "key",
        [{"role": "user", "content": "Remember this project decision."}],
        "u1",
        "app-a",
        "main",
        "s1",
    )

    assert ok is True
    assert calls[0]["user_id"] == "u1"
    assert calls[0]["app_id"] == "app-a"
    assert calls[0]["infer"] is True
    assert calls[0]["metadata"]["type"] == "auto_capture"
    assert calls[0]["metadata"]["source"] == "auto_capture"
    assert calls[0]["metadata"]["session_id"] == "s1"
    assert calls[0]["metadata"]["branch"] == "main"
    assert calls[0]["metadata"]["project_id"] == "app-a"


def test_session_summary_uses_unified_client_metadata(monkeypatch):
    calls = _capture_add(monkeypatch, capture_session_summary)

    ok = capture_session_summary.store_summary("key", "summary", "u1", "s1", "app-a", "main", ["a.py"])

    assert ok is True
    assert calls[0]["run_id"] == "s1"
    assert calls[0]["metadata"]["type"] == "session_summary"
    assert calls[0]["metadata"]["source"] == "stop-hook"
    assert calls[0]["metadata"]["files_touched"] == '["a.py"]'


def test_compact_summary_uses_unified_client_metadata(monkeypatch):
    calls = _capture_add(monkeypatch, capture_compact_summary)

    ok = capture_compact_summary.store_summary("key", "compact", "u1", "s1", "app-a", "main")

    assert ok is True
    assert calls[0]["metadata"]["type"] == "compact_summary"
    assert calls[0]["metadata"]["source"] == "session-start-compact"


def test_precompact_store_memory_uses_unified_client_metadata(monkeypatch):
    calls = _capture_add(monkeypatch, on_pre_compact)

    ok = on_pre_compact.store_memory("key", "Files touched: a.py", "u1", "pre-compaction", "s1", "app-a", "main")

    assert ok is True
    assert calls[0]["metadata"]["type"] == "session_state"
    assert calls[0]["metadata"]["source"] == "pre-compaction"

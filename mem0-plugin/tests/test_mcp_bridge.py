from __future__ import annotations

import json
import os
import sys

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import mcp_bridge


def test_tools_list_includes_codex_selfhost_required_tools():
    names = {tool["name"] for tool in mcp_bridge.TOOLS}

    assert {
        "add_memory",
        "search_memories",
        "get_memories",
        "get_memory",
        "update_memory",
        "delete_memory",
        "delete_all_memories",
        "list_entities",
        "delete_entities",
        "list_events",
        "get_event_status",
    } <= names


def test_unsupported_entity_tool_returns_clear_payload():
    result = mcp_bridge.call_tool("list_entities", {"user_id": "u1"})

    assert result["status"] == "unsupported"
    assert result["capability"] == "list_entities"
    assert "not supported" in result["message"]


def test_tools_call_wraps_result_as_mcp_text(monkeypatch):
    monkeypatch.setattr(mcp_bridge, "call_tool", lambda name, args: {"status": "partial", "name": name})

    response = mcp_bridge.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "get_event_status", "arguments": {"event_id": "evt_1"}},
        }
    )

    assert response["id"] == 1
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload == {"status": "partial", "name": "get_event_status"}

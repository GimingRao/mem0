#!/usr/bin/env python3
"""Local stdio MCP bridge for Codex self-host Mem0."""

from __future__ import annotations

import json
import sys
from typing import Any

import _mem0_client as mem0


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


TOOLS: list[dict[str, Any]] = [
    {
        "name": "add_memory",
        "description": "Save a memory or conversation history for a user and app scope.",
        "inputSchema": _schema(
            {
                "messages": {"type": ["array", "string"]},
                "user_id": {"type": "string"},
                "app_id": {"type": "string"},
                "metadata": {"type": "object"},
                "infer": {"type": "boolean"},
                "run_id": {"type": "string"},
                "expiration_date": {"type": "string"},
            },
            ["messages", "user_id"],
        ),
    },
    {
        "name": "search_memories",
        "description": "Semantic search across memories with filters.",
        "inputSchema": _schema(
            {
                "query": {"type": "string"},
                "user_id": {"type": "string"},
                "app_id": {"type": "string"},
                "filters": {"type": "object"},
                "top_k": {"type": "integer"},
                "threshold": {"type": "number"},
            },
            ["query"],
        ),
    },
    {"name": "get_memories", "description": "List memories with optional filters.", "inputSchema": _schema({"user_id": {"type": "string"}, "app_id": {"type": "string"}, "filters": {"type": "object"}, "page": {"type": "integer"}, "page_size": {"type": "integer"}})},
    {"name": "get_memory", "description": "Retrieve one memory by ID.", "inputSchema": _schema({"memory_id": {"type": "string"}}, ["memory_id"])},
    {"name": "update_memory", "description": "Update one memory by ID.", "inputSchema": _schema({"memory_id": {"type": "string"}, "data": {"type": "string"}, "metadata": {"type": "object"}}, ["memory_id"])},
    {"name": "delete_memory", "description": "Delete one memory by ID.", "inputSchema": _schema({"memory_id": {"type": "string"}}, ["memory_id"])},
    {"name": "delete_all_memories", "description": "Delete memories in a user/app scope.", "inputSchema": _schema({"user_id": {"type": "string"}, "app_id": {"type": "string"}})},
    {"name": "list_entities", "description": "List linked entities when supported.", "inputSchema": _schema({"user_id": {"type": "string"}, "app_id": {"type": "string"}})},
    {"name": "delete_entities", "description": "Delete linked entities when supported.", "inputSchema": _schema({"user_id": {"type": "string"}, "app_id": {"type": "string"}, "entity_ids": {"type": "array"}})},
    {"name": "list_events", "description": "List async memory events when supported.", "inputSchema": _schema({"user_id": {"type": "string"}, "app_id": {"type": "string"}})},
    {"name": "get_event_status", "description": "Get async memory event status when supported.", "inputSchema": _schema({"event_id": {"type": "string"}}, ["event_id"])},
]


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "add_memory":
        return mem0.add_memory(**args)
    if name == "search_memories":
        return mem0.search_memories(**args)
    if name == "get_memories":
        return mem0.get_memories(**args)
    if name == "get_memory":
        return mem0.get_memory(args["memory_id"])
    if name == "update_memory":
        return mem0.update_memory(args["memory_id"], data=args.get("data", ""), metadata=args.get("metadata"))
    if name == "delete_memory":
        return mem0.delete_memory(args["memory_id"])
    if name == "delete_all_memories":
        return mem0.delete_all_memories(user_id=args.get("user_id", ""), app_id=args.get("app_id", ""))
    if name == "list_entities":
        return mem0.list_entities(**args)
    if name == "delete_entities":
        return mem0.delete_entities(**args)
    if name == "list_events":
        return mem0.list_events(**args)
    if name == "get_event_status":
        return mem0.get_event_status(**args)
    return {"status": "error", "message": f"Unknown tool: {name}"}


def _tool_response(result: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    req_id = request.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "mem0-self", "version": "0.1.0"}}}
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = request.get("params") or {}
        result = call_tool(params.get("name", ""), params.get("arguments") or {})
        return {"jsonrpc": "2.0", "id": req_id, "result": _tool_response(result)}
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = handle(request)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}}
        if response is not None:
            print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()

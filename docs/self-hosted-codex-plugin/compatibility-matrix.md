# Self-Hosted Codex Plugin Compatibility Matrix

This matrix defines the expected behavior for the `mem0-self` Codex plugin distribution. It compares the official Mem0 Cloud plugin path with the self-host REST adapter path.

## Version Baseline

| Field | Value |
| --- | --- |
| Official upstream base | `90f2d24e832302c97e0daa55454b29657e742c15` |
| Official Codex plugin version | `0.2.9` |
| Self-host plugin id | `mem0-self` |
| First self-host release tag | `codex-mem0-0.2.9-selfhost.1` |

## Capability Matrix

| Capability | Cloud plugin | Self-host plugin | Self-host behavior |
| --- | --- | --- | --- |
| MCP `add_memory` | Full | Full when REST `add` is reachable | Writes through the self-host adapter with required `user_id` and normalized metadata. |
| MCP `search_memories` | Full | Full with local post-filtering | Remote query must include `user_id`; `app_id`, `project_id`, `type`, and `source` filters are applied locally when the server cannot handle nested filters. |
| MCP `get_memories` | Full | Partial to full, server-version dependent | Lists by `user_id` first, then locally filters metadata fields. |
| MCP `get_memory` | Full | Full when REST `get` exists | Falls back to a clear unsupported response if the self-host server lacks a single-memory endpoint. |
| MCP `update_memory` | Full | Partial | Supported only when the server exposes update semantics compatible with the adapter. |
| MCP `delete_memory` | Full | Partial | Supported only when the server exposes delete by memory id. |
| MCP `delete_all_memories` | Full | Partial or disabled | Must require explicit scope and return a clear unsupported response if bulk delete is unavailable. |
| MCP `list_entities` | Full | Degraded or unsupported | Entity APIs are Cloud-oriented; self-host may return unsupported until graph/entity endpoints are mapped. |
| MCP `delete_entities` | Full | Degraded or unsupported | Same entity limitation as `list_entities`. |
| MCP `list_events` | Full | Shim | Self-host REST is usually synchronous; adapter may return an empty or completed event list with `backend=selfhost`. |
| MCP `get_event_status` | Full | Shim | Returns completed status for synchronous operations when no async event id exists. |
| Skills | Full | Inherited | Official skill behavior should be reused; self-host differences belong in adapter docs or appended notes. |
| SessionStart context search | Full | Full with local post-filtering | Searches by `user_id` and locally filters project/app/source metadata. |
| UserPromptSubmit relevance check | Full | Full after adapter support | Uses same extraction and prompt logic, with backend access routed through the provider adapter. |
| Stop session summary capture | Full | Full after adapter support | Summary construction remains upstream; write path routes through the self-host adapter. |
| PreCompact summary capture | Full | Full after adapter support | Same as Stop capture. |
| Auto-import project files | Full | Full with local dedupe | Import chunking remains upstream; duplicate detection cannot rely on Cloud nested metadata filters. |
| Session timeline | Full | Degraded but usable | Remote coarse filter by `user_id`, local post-filter by session/project/type/source. |
| Global search | Full | Degraded | Self-host may not support Cloud `OR` filters; implementation should document whether it broadens by `user_id` or is disabled. |
| Memory categories | Full | Degraded | Cloud category APIs may not exist on self-host; category/type should be represented in metadata where possible. |
| Memory type | Full Cloud semantics | Metadata-compatible | `fact`, `preference`, `decision`, `task_outcome`, and similar types are stored as metadata `type`, not REST `memory_type`, unless the server explicitly supports the requested type. |
| Transport: direct HTTPS | Full | Recommended | Production self-host mode. |
| Transport: direct HTTP | Not applicable | Demo only | API keys are sent in clear text; use only on trusted local/demo networks. |
| Transport: SSH tunnel | Not applicable | Supported by install/ops line | Private endpoint mode; bridge talks to local forwarded endpoint. |

## Known Differences

- Self-host search must include at least `user_id`; Cloud-style nested metadata filters may be ignored or rejected by the server.
- Self-host event APIs are not guaranteed. Synchronous operations should return an explicit completed shim instead of silently failing.
- Entity tools may require graph support and should be treated as degraded until mapped to a concrete self-host server version.
- Cloud-only category and project-scoped controls should degrade into metadata tags instead of changing official skill schemas.

## Release Update Checklist

Update this file whenever any of these changes:

- Official Codex plugin version changes.
- A self-host REST endpoint is added, removed, or renamed.
- Adapter filter translation changes.
- B/C/D lines add health or smoke-test evidence for a new transport mode.
- A Cloud-only capability becomes fully supported by self-host.


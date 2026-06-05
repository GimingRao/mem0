# D Line Technical Design: Transport / Installer / Health / Smoke

## Goals

- Support self-hosted transport setup for direct HTTP, direct HTTPS, and SSH private access.
- Provide an installer path for Codex that checks local prerequisites, writes user-local config, avoids storing plaintext secrets in the repo, and warns about duplicate MCP registration.
- Provide health and smoke commands that classify failures as endpoint, auth, schema, filter, or runtime issues.
- Keep D-line HTTP behavior concentrated in a diagnostic helper and prefer any future unified client/adapter from B line when present.

## Non-Goals

- Do not change MCP tool schemas or hook orchestration.
- Do not rewrite the self-host adapter that B line owns.
- Do not implement enterprise auth, HTTPS termination, or SSH key management.
- Do not persist API keys in repository files.

## Current State

- `mem0-plugin/README.md` is cloud-first and documents Codex direct MCP against `https://mcp.mem0.ai/mcp`.
- `mem0-plugin/.codex-mcp.json` also points at the cloud MCP endpoint.
- Existing Codex hook installer only merges lifecycle hooks into `~/.codex/hooks.json`.
- The self-host FastAPI server exposes `/configure`, `/memories`, `/search`, and uses `X-API-Key` or bearer auth through `server/auth.py`.
- No local `scripts/install.sh`, self-host health command, or smoke script exists yet.

## Design

### Configuration

Self-host diagnostics read:

- `MEM0_PROVIDER=selfhost`
- `MEM0_SELFHOST_API_URL`
- `MEM0_SELFHOST_API_KEY_FILE` or `MEM0_SELFHOST_API_KEY`
- `MEM0_USER_ID`
- `MEM0_PROJECT_ID`
- `MEM0_SELFHOST_TRANSPORT=http|https|ssh`
- SSH-only: `MEM0_SELFHOST_SSH_HOST`, optional `MEM0_SELFHOST_SSH_PORT`, `MEM0_SELFHOST_SSH_USER`, `MEM0_SELFHOST_SSH_KEY`, `MEM0_SELFHOST_REMOTE_API_URL`

The installer writes non-secret values to `~/.mem0/settings.json`. If an API key is provided interactively, it writes the key to a user-local file such as `~/.mem0/selfhost-api-key` with `0600` permissions and stores only the key file path in settings.

### Transport

- Direct HTTP/HTTPS uses Python stdlib `urllib` and centralized timeout/error classification in `_selfhost_probe.py`.
- SSH mode executes a remote-safe `curl` command over `ssh` to reach the configured remote API URL, typically `http://127.0.0.1:8000`.
- HTTP mode emits a warning because `X-API-Key` is sent over plaintext unless the network is trusted.
- HTTPS mode is the recommended production path.
- SSH mode is the private mode when the API only binds to localhost on the server.

### Health

`selfhost_health.py` prints JSON by default and a compact text table on `--format text`. It reports:

- provider
- transport
- api_url
- auth
- add
- search
- metadata_filter
- warnings

Checks run independently and do not stop at the first failure. Error classification is:

- `endpoint`: URL, DNS, connection, TLS, or timeout problem
- `auth`: `401` or `403`
- `schema`: request/response contract mismatch or invalid JSON
- `filter`: add succeeds but search cannot find a known metadata-filtered probe
- `runtime`: server error or local execution failure

### Smoke

`selfhost_smoke.py` runs a stricter chain:

1. Read configuration.
2. Add a unique probe memory with `metadata.type=health_check`.
3. Search for it with `user_id`, `app_id`, and metadata filters.
4. Optionally delete the probe if the response exposes an id.

This is the executable equivalent of configure/add/search/Codex tool add-search until C line owns the actual MCP bridge smoke path. The script can later call the MCP bridge directly without changing installer UX.

### Installer

`scripts/install.sh` is a thin repo-root entrypoint that delegates to `mem0-plugin/scripts/install/selfhost/install.sh`.

The self-host installer:

- Checks `codex`, `python3`, and plugin script availability.
- Writes `~/.mem0/settings.json` keys for self-host mode.
- Writes `~/.mem0/selfhost-api-key` only when a key is provided and no key file already exists.
- Checks `~/.codex/config.toml` and plugin MCP manifests for duplicate `mem0` registrations and prints warnings.
- Optionally runs health after writing config.

## Module Changes

- `mem0-plugin/scripts/_selfhost_config.py`: config loading, normalization, secret redaction, settings persistence.
- `mem0-plugin/scripts/_selfhost_probe.py`: transport execution, response parsing, error classification, health/smoke primitives.
- `mem0-plugin/scripts/selfhost_health.py`: CLI wrapper for health.
- `mem0-plugin/scripts/selfhost_smoke.py`: CLI wrapper for smoke.
- `mem0-plugin/scripts/install/selfhost/install.sh`: interactive/non-interactive installer.
- `scripts/install.sh`: root wrapper.
- `mem0-plugin/README.md`: self-host Codex install, security modes, health/smoke docs.
- `mem0-plugin/tests/test_selfhost_*.py`: focused config/probe tests.

## Compatibility

- Existing cloud behavior remains untouched.
- The new scripts are opt-in and do not modify `.codex-mcp.json`.
- B line can add `_mem0_client.py`; `_selfhost_probe.py` will prefer it when a compatible health/add/search API is available.

## Migration and Rollback

- Rollback is removing `~/.mem0/settings.json` self-host keys and any manually added Codex MCP registration.
- API key files under `~/.mem0` remain user-owned and are not removed automatically.
- No database migration is required.

## Test Plan

- Unit tests for settings persistence, key-file precedence, transport warnings, HTTP request construction, SSH command construction, and error classification.
- CLI smoke tests with mocked transport by testing helper functions directly.
- Manual validation commands:
  - `python3 mem0-plugin/scripts/selfhost_health.py --format json`
  - `python3 mem0-plugin/scripts/selfhost_smoke.py --format text`

## Risks

- If B/C line changes config variable names, docs and helper aliases may need minor alignment.
- SSH mode depends on `ssh` and remote `curl`; health output must classify missing remote commands as runtime failures.
- Filter compatibility on self-host can be weaker than cloud nested metadata filters; smoke classifies this separately as `filter`.

## Open Questions

- Exact MCP bridge command path from C line is not available yet, so the current smoke uses the same REST chain the bridge should call.
- Final plugin ID/manifest changes are out of D-line scope but may affect duplicate registration messages.

# A Line Technical Design: Fork / Release / Upgrade Maintenance

## Scope

A line owns subfeatures 1 and 9 from the Mem0 Self-Hosted Codex Plugin PRD:

- Fork and branch/release baseline.
- Documentation, compatibility matrix, release notes, upgrade checklist, and fork diff checks.

This line does not change `mem0-plugin/scripts` business logic. Adapter, provider selection, MCP bridge, lifecycle hooks, transport, installer, and smoke implementation are owned by B/C/D lines.

## Sources

| Source | Role | Evidence |
| --- | --- | --- |
| `feature_doc/0605_mem0_selfhost_codex_plugin_prd/prd.md` | Primary PRD | Upstream-first fork, official base traceability, compatibility matrix, upgrade flow. |
| `feature_doc/0605_mem0_selfhost_codex_plugin_prd/subfeatures.md` | Primary decomposition | A line owns subfeatures 1 and 9. |
| `mem0-plugin/.codex-plugin/plugin.json` | Code evidence | Official Codex plugin version is `0.2.9`. |
| `git rev-parse HEAD` | Repo evidence | Current upstream/selfhost base is `90f2d24e832302c97e0daa55454b29657e742c15`. |

CodeGraph was not initialized and was intentionally not initialized per project instruction. Source and git fallback were used.

## Goals

- Record the upstream base and branch/tag rules in a root maintenance document.
- Define the expected long-term self-host overlay and forbidden drift.
- Provide a Cloud vs self-host compatibility matrix.
- Provide an upgrade guide, release checklist, and release note template path.
- Add executable scripts for fork diff checks and release note draft generation.

## Non-Goals

- Do not implement provider config, REST adapter, MCP bridge, hooks, transport, installer, or smoke command logic.
- Do not modify official skills or hook business scripts.
- Do not initialize CodeGraph.
- Do not create release tags in this turn.

## Current State

- Current branch is `selfhost/main`.
- `origin` is `https://github.com/GimingRao/mem0.git`.
- `upstream` is `https://github.com/mem0ai/mem0.git`.
- Current HEAD and upstream merge-base are both `90f2d24e832302c97e0daa55454b29657e742c15`.
- `UPSTREAM.md` did not exist before this line's work.
- `feature_doc/0605_mem0_selfhost_codex_plugin_prd/` is currently untracked, so A-line artifacts are added there without assuming prior git ownership.

## Design

### 1. Upstream Baseline

Add root `UPSTREAM.md` as the release-maintenance source of truth. It records:

- upstream and fork repositories,
- `selfhost/main` and `selfhost/release` branch meanings,
- upstream base commit,
- official Codex plugin version,
- self-host plugin id,
- first tag rule,
- long-term diff policy,
- release gate.

### 2. Compatibility Matrix

Add `docs/self-hosted-codex-plugin/compatibility-matrix.md`. The matrix covers:

- MCP tools,
- skills,
- lifecycle hooks,
- auto-import,
- session timeline,
- metadata and memory type behavior,
- Cloud-only and degraded self-host capabilities,
- transport mode expectations.

The matrix treats add/search as expected full self-host capabilities once B/C lines provide the adapter, and marks entity/event/category/bulk operations as degraded or server-version dependent.

### 3. Upgrade and Release Documents

Add:

- `docs/self-hosted-codex-plugin/upgrade-guide.md`
- `docs/self-hosted-codex-plugin/release-checklist.md`

These documents define the rebase flow, conflict handling order, strict diff gate, validation expectations, release note requirements, and rollback handling.

### 4. Maintenance Scripts

Add:

- `scripts/selfhost-fork-diff.py`
- `scripts/selfhost-release-note.py`

`selfhost-fork-diff.py` compares `base...HEAD`, groups allowed overlay files and unexpected files, and supports `--strict` for CI/release gates.
It includes staged, unstaged, and untracked files by default so parallel-worker drift is visible before release.

`selfhost-release-note.py` reads `UPSTREAM.md`, reads `mem0-plugin/.codex-plugin/plugin.json`, summarizes git diff stats, and emits a Markdown release note draft.

## Compatibility

The maintenance model assumes the self-host fork is an upstream-first overlay:

- Cloud mode remains official behavior.
- Self-host differences are constrained to adapter, bridge, install, docs, and compatibility tests.
- Official skills and hook orchestration should remain inherited.
- Unsupported self-host capabilities must fail explicitly or return documented shims.

## Migration and Rollback

Upgrade migration is a rebase or merge from upstream into `selfhost/main`, followed by diff gate, tests, smoke, docs update, `selfhost/release` promotion, and tag creation.

Rollback moves `selfhost/release` back to the previous known-good tag and publishes a release note addendum. Shared branch history should not be force-reset merely to hide a failed upgrade.

## Test Plan

A-line verification:

- `python3 scripts/selfhost-fork-diff.py --base upstream/main`
- `python3 scripts/selfhost-release-note.py --tag codex-mem0-0.2.9-selfhost.1`
- `python3 scripts/selfhost-fork-diff.py --base upstream/main --strict`

Full release verification after B/C/D lines:

- adapter unit tests,
- MCP bridge/tool schema tests,
- Codex hook validation,
- installer health check,
- real self-host add/search smoke test.

## Risks

- Current A-line docs allow future adapter paths before those files exist; B/C/D lines must keep their implementation inside these paths or update the policy with justification.
- Entity/event/category capabilities depend on concrete self-host server support and remain degraded until implementation evidence exists.
- `README.md` only links the self-host Codex plugin maintenance docs; full user-facing install docs are expected from D line.

## Open Questions

- Should Cloud fallback remain enabled by default when `MEM0_PROVIDER` is unset?
- Will the product support multiple self-host endpoint profiles, or a single active endpoint?
- Will memory migration between Cloud and self-host be included in this fork or left to separate tooling?

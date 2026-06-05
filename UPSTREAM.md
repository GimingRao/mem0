# Mem0 Self-Hosted Codex Plugin Upstream Baseline

This file records the upstream base and maintenance rules for the `mem0-self` self-hosted Codex plugin fork.

## Current Base

| Field | Value |
| --- | --- |
| Upstream repository | `https://github.com/mem0ai/mem0` |
| Fork repository | `https://github.com/GimingRao/mem0` |
| Self-host branch | `selfhost/main` |
| Stable release branch | `selfhost/release` |
| Upstream base ref | `upstream/main` |
| Upstream base commit | `90f2d24e832302c97e0daa55454b29657e742c15` |
| Upstream base short SHA | `90f2d24e8323` |
| Official Codex plugin version | `0.2.9` |
| Self-host plugin id | `mem0-self` |
| First self-host tag | `codex-mem0-0.2.9-selfhost.1` |
| Recorded on | `2026-06-05` |

## Branch Rules

| Branch | Purpose | Write policy |
| --- | --- | --- |
| `upstream/main` | Read-only tracking ref for `mem0ai/mem0`. | Never commit here. Fetch only. |
| `main` | Optional fork default branch that may track upstream. | Avoid self-host product work here. |
| `selfhost/main` | Long-running self-host development branch. | Rebase or merge from upstream, then keep self-host overlay small. |
| `selfhost/release` | Stable branch used by Codex plugin installs. | Fast-forward or cherry-pick from validated `selfhost/main` releases only. |
| `release/*` | Temporary release preparation branches. | Delete after tag and release notes are published. |

## Tag Rules

Self-host tags must include the official Codex plugin version they are based on:

```text
codex-mem0-<official-plugin-version>-selfhost.<patch>
```

Examples:

```text
codex-mem0-0.2.9-selfhost.1
codex-mem0-0.2.10-selfhost.1
codex-mem0-0.2.10-selfhost.2
```

Increment `<patch>` when the upstream plugin version is unchanged and only the self-host overlay changes. Reset `<patch>` to `1` after rebasing to a newer official Codex plugin version.

## Long-Term Diff Policy

Self-host changes should stay in these areas:

- `UPSTREAM.md`
- `README.md` self-host Codex plugin references
- `docs/self-hosted-codex-plugin/`
- `scripts/selfhost-*.py`
- `feature_doc/0605_mem0_selfhost_codex_plugin_prd/`
- `mem0-plugin/scripts/_mem0_client.py`
- `mem0-plugin/scripts/_selfhost.py`
- `mem0-plugin/mcp/selfhost-server.*`
- `codex-selfhost/`
- self-host compatibility tests

Avoid long-term edits to official skills, hook orchestration, and extraction scripts. If they must change, only replace the final backend call with the shared provider adapter.

Never commit local plugin cache patches, personal IPs, personal filesystem paths, API keys, or generated secrets.

## Upgrade Flow

```bash
git fetch upstream --tags
git checkout selfhost/main
git rebase upstream/main
python3 scripts/selfhost-fork-diff.py --base upstream/main --strict
python3 scripts/selfhost-release-note.py --tag codex-mem0-<version>-selfhost.<n> > /tmp/release-note.md
```

`selfhost-fork-diff.py` includes staged, unstaged, and untracked files by default. Use `--committed-only` only for historical comparisons, not for release gates.

After B/C/D-line implementation is present, also run the adapter tests, Codex bridge tests, installer health check, and a real self-host add/search smoke test before tagging.

## Release Gate

A self-host release is publishable only when all of these are true:

- `UPSTREAM.md` lists the exact official base commit or tag.
- The release tag follows `codex-mem0-<official-plugin-version>-selfhost.<patch>`.
- `scripts/selfhost-fork-diff.py --strict` shows no unexplained diff outside the accepted overlay.
- Compatibility matrix is updated for Cloud vs self-host capabilities.
- Release notes include official base, self-host tag, smoke-test result, known differences, and rollback instructions.
- No self-host mode path calls `api.mem0.ai` or `mcp.mem0.ai` except when `MEM0_PROVIDER=cloud`.

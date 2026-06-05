# Self-Hosted Codex Plugin Upgrade Guide

Use this guide when rebasing the `mem0-self` fork onto a newer official `mem0ai/mem0` base.

## Preflight

```bash
git status --short --branch
git remote -v
git fetch upstream --tags
```

Confirm the current base in `UPSTREAM.md` and the official Codex plugin version in `mem0-plugin/.codex-plugin/plugin.json`.

## Rebase

Prefer rebasing to the upstream tag that contains the official Codex plugin release. If no plugin-specific tag exists, rebase to `upstream/main`.

```bash
git checkout selfhost/main
git rebase upstream/main
```

Conflict handling order:

1. Keep official skills, hook orchestration, MCP schemas, extraction, chunking, and identity logic unless the upstream change is incompatible with the provider adapter.
2. Reconnect the backend call through the shared self-host adapter instead of copying older fork logic back into official scripts.
3. If upstream now supports the same self-host feature, delete the fork-specific duplicate and narrow the diff.
4. Keep secrets, personal endpoints, and local machine paths out of the repo.

## Diff Check

Run the fork diff check after resolving conflicts:

```bash
python3 scripts/selfhost-fork-diff.py --base upstream/main --strict
```

Any file reported outside the allowed overlay needs either:

- a documented reason in the release note, or
- a follow-up change that moves the diff into adapter, bridge, docs, tests, or installation support.

## Validation

Minimum A-line validation:

```bash
python3 scripts/selfhost-fork-diff.py --base upstream/main
python3 scripts/selfhost-release-note.py --tag codex-mem0-<official-version>-selfhost.<n>
```

Use `--committed-only` only when drafting release notes from committed changes. Release gates should include the worktree so untracked or staged drift is not missed.

Full product validation after B/C/D lines are present:

```bash
pytest mem0-plugin/tests
python3 scripts/selfhost-fork-diff.py --base upstream/main --strict
# Run the self-host health/smoke command provided by the installer line.
```

Smoke-test output must include provider, transport, API URL host, auth status, add/search results, metadata filter behavior, and warnings.

## Release

1. Update `UPSTREAM.md` with the new upstream base commit/tag and official Codex plugin version.
2. Update `docs/self-hosted-codex-plugin/compatibility-matrix.md`.
3. Generate the release note:

   ```bash
   python3 scripts/selfhost-release-note.py --tag codex-mem0-<official-version>-selfhost.<n> > release-note.md
   ```

4. Run the release checklist in `docs/self-hosted-codex-plugin/release-checklist.md`.
5. Move `selfhost/release` to the validated commit.
6. Tag the release:

   ```bash
   git tag codex-mem0-<official-version>-selfhost.<n>
   ```

## Rollback

If an upgrade breaks self-host behavior after release:

1. Move `selfhost/release` back to the previous known-good tag.
2. Publish a release note addendum with the failing upstream base, impacted capability, and workaround.
3. Keep the failed branch for investigation; do not hide the diff by force-resetting shared history.

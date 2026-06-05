# Self-Hosted Codex Plugin Release Checklist

Use this checklist for every `codex-mem0-<official-version>-selfhost.<patch>` release.

## Baseline

- [ ] `UPSTREAM.md` records the official repository, base commit or tag, and official Codex plugin version.
- [ ] Release tag follows `codex-mem0-<official-version>-selfhost.<patch>`.
- [ ] `selfhost/main` has been rebased or merged from the recorded upstream base.
- [ ] `selfhost/release` points only to a validated release commit.

## Fork Diff

- [ ] `python3 scripts/selfhost-fork-diff.py --base upstream/main --strict` passes.
- [ ] All remaining self-host diffs are in adapter, bridge, install, docs, feature design, compatibility tests, or explicitly documented exceptions.
- [ ] No diff is in `~/.codex/plugins/cache`, personal paths, personal hosts, or secret files.

## Compatibility

- [ ] `docs/self-hosted-codex-plugin/compatibility-matrix.md` lists Cloud vs self-host behavior for each MCP tool.
- [ ] Cloud-only or degraded self-host capabilities return explicit unsupported/degraded responses.
- [ ] `memory_type`, metadata, event status, and local post-filter behavior are documented.

## Validation

- [ ] Adapter tests passed.
- [ ] MCP bridge/tool schema tests passed.
- [ ] Codex hook validation passed.
- [ ] Installer health check passed.
- [ ] Real self-host add/search smoke test passed.
- [ ] Smoke output is attached to the release note.

## Security

- [ ] No API key is committed.
- [ ] Debug output redacts secrets.
- [ ] HTTP mode is documented as demo/trusted-network only.
- [ ] HTTPS is documented as the recommended production mode.
- [ ] SSH tunnel mode is documented for private endpoints.

## Release Note

- [ ] Official base commit/tag is listed.
- [ ] Self-host release tag is listed.
- [ ] Fork diff summary is listed.
- [ ] Compatibility changes are listed.
- [ ] Known differences and unsupported capabilities are listed.
- [ ] Upgrade and rollback steps are listed.


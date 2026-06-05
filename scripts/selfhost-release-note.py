#!/usr/bin/env python3
"""Generate a self-host Codex plugin release note draft."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_MD = ROOT / "UPSTREAM.md"
CODEX_PLUGIN_MANIFEST = ROOT / "mem0-plugin" / ".codex-plugin" / "plugin.json"


def run_git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.strip()


def read_upstream_field(label: str) -> str:
    if not UPSTREAM_MD.exists():
        return "UNKNOWN"
    pattern = re.compile(rf"^\|\s*{re.escape(label)}\s*\|\s*(.*?)\s*\|$")
    for line in UPSTREAM_MD.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip().strip("`")
    return "UNKNOWN"


def plugin_version() -> str:
    data = json.loads(CODEX_PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    return str(data.get("version", "UNKNOWN"))


def diff_summary(base: str) -> list[str]:
    output = run_git(["diff", "--stat", f"{base}...HEAD"])
    return output.splitlines() if output else ["No committed fork diff from base."]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Self-host release tag, e.g. codex-mem0-0.2.9-selfhost.1.")
    parser.add_argument("--base", default="upstream/main", help="Upstream base used for diff summary.")
    args = parser.parse_args()

    head = run_git(["rev-parse", "HEAD"])
    short_head = run_git(["rev-parse", "--short=12", "HEAD"])
    upstream_base = read_upstream_field("Upstream base commit")
    upstream_ref = read_upstream_field("Upstream base ref")
    official_version = read_upstream_field("Official Codex plugin version")
    manifest_version = plugin_version()

    print(f"# Release Notes: {args.tag}")
    print()
    print("## Baseline")
    print()
    print(f"- Official upstream base ref: `{upstream_ref}`")
    print(f"- Official upstream base commit: `{upstream_base}`")
    print(f"- Official Codex plugin version: `{official_version}`")
    print(f"- Current Codex plugin manifest version: `{manifest_version}`")
    print(f"- Self-host release tag: `{args.tag}`")
    print(f"- Release commit: `{head}` (`{short_head}`)")
    print()
    print("## Fork Diff Summary")
    print()
    print("```text")
    for line in diff_summary(args.base):
        print(line)
    print("```")
    print()
    print("## Compatibility")
    print()
    print("- Matrix: `docs/self-hosted-codex-plugin/compatibility-matrix.md`")
    print("- Expected self-host mode: add/search full with required `user_id`; metadata filters may use local post-filtering.")
    print("- Expected degraded modes: entity tools, event APIs, category APIs, and bulk delete until server support is mapped.")
    print()
    print("## Validation")
    print()
    print("- [ ] `python3 scripts/selfhost-fork-diff.py --base upstream/main --strict`")
    print("- [ ] Adapter unit tests")
    print("- [ ] MCP bridge/tool schema tests")
    print("- [ ] Codex hook validation")
    print("- [ ] Real self-host add/search smoke test")
    print()
    print("## Known Differences")
    print()
    print("- Self-host mode must not call `api.mem0.ai` or `mcp.mem0.ai`; Cloud mode may use official endpoints.")
    print("- Self-host search may only support coarse server-side filtering and then local metadata filtering.")
    print("- Synchronous self-host REST operations may return completed event-status shims.")
    print()
    print("## Upgrade")
    print()
    print("See `docs/self-hosted-codex-plugin/upgrade-guide.md` and `docs/self-hosted-codex-plugin/release-checklist.md`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

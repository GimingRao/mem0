#!/usr/bin/env python3
"""Report self-host fork drift from the recorded upstream base."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ALLOWED_PREFIXES = (
    "UPSTREAM.md",
    "README.md",
    "docs/self-hosted-codex-plugin/",
    "scripts/selfhost-",
    "feature_doc/0605_mem0_selfhost_codex_plugin_prd/",
    "mem0-plugin/scripts/_mem0_client.py",
    "mem0-plugin/scripts/_selfhost.py",
    "mem0-plugin/mcp/selfhost-server.",
    "codex-selfhost/",
)

WATCH_PREFIXES = (
    "mem0-plugin/skills/",
    "mem0-plugin/hooks/",
    "mem0-plugin/scripts/auto_capture.py",
    "mem0-plugin/scripts/auto_import.py",
    "mem0-plugin/scripts/capture_session_summary.py",
    "mem0-plugin/scripts/capture_compact_summary.py",
    "mem0-plugin/scripts/session_timeline.py",
)


def run_git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.strip()


def changed_files(base: str, include_worktree: bool) -> list[str]:
    paths: set[str] = set()

    committed = run_git(["diff", "--name-only", f"{base}...HEAD"])
    paths.update(line for line in committed.splitlines() if line)

    if include_worktree:
        staged = run_git(["diff", "--name-only", "--cached"])
        unstaged = run_git(["diff", "--name-only"])
        untracked = run_git(["ls-files", "--others", "--exclude-standard"])
        paths.update(line for line in staged.splitlines() if line)
        paths.update(line for line in unstaged.splitlines() if line)
        paths.update(line for line in untracked.splitlines() if line)

    return sorted(paths)


def is_allowed(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def is_watch_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in WATCH_PREFIXES)


def print_group(title: str, paths: list[str]) -> None:
    print(f"\n{title} ({len(paths)})")
    print("-" * len(title))
    if not paths:
        print("None")
        return
    for path in paths:
        marker = " [watch]" if is_watch_path(path) else ""
        print(f"- {path}{marker}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="upstream/main", help="Upstream base ref to diff against.")
    parser.add_argument(
        "--committed-only",
        action="store_true",
        help="Only inspect committed changes from base...HEAD; ignore staged, unstaged, and untracked files.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when unexpected files changed.")
    args = parser.parse_args()

    repo_root = Path(run_git(["rev-parse", "--show-toplevel"]))
    head = run_git(["rev-parse", "--short=12", "HEAD"])
    base_sha = run_git(["rev-parse", "--short=12", args.base])
    files = changed_files(args.base, include_worktree=not args.committed_only)

    allowed = [path for path in files if is_allowed(path)]
    unexpected = [path for path in files if not is_allowed(path)]

    print("Self-host fork diff")
    print("===================")
    print(f"Repo: {repo_root}")
    print(f"Base: {args.base} ({base_sha})")
    print(f"Head: HEAD ({head})")
    print(f"Includes worktree: {not args.committed_only}")
    print(f"Changed files: {len(files)}")

    print_group("Allowed overlay files", allowed)
    print_group("Unexpected files", unexpected)

    if unexpected:
        print("\nReview required: move these changes into the adapter/bridge/docs overlay or document the exception.")
        return 1 if args.strict else 0

    print("\nDiff policy check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

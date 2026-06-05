#!/usr/bin/env python3
"""Run self-hosted Mem0 plugin health diagnostics."""

from __future__ import annotations

import argparse
import json
import sys

from _selfhost_config import ConfigError, load_selfhost_config
from _selfhost_probe import run_health


def _status_line(name: str, item: dict) -> str:
    status = item.get("status", "unknown").upper()
    category = item.get("category")
    detail = item.get("detail") or item.get("value") or ""
    suffix = f" [{category}]" if category else ""
    return f"{status:<5} {name:<16} {detail}{suffix}"


def print_text(report: dict) -> None:
    print("Mem0 self-host health")
    print(_status_line("provider", report["provider"]))
    print(_status_line("transport", report["transport"]))
    print(_status_line("api_url", report["api_url"]))
    print(_status_line("auth", report["auth"]))
    print(_status_line("endpoint", report["endpoint"]))
    print(_status_line("add", report["add"]))
    print(_status_line("search", report["search"]))
    print(_status_line("metadata_filter", report["metadata_filter"]))
    if report.get("warnings"):
        print()
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"- {warning}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check self-hosted Mem0 plugin connectivity.")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args()

    try:
        config = load_selfhost_config()
        report = run_health(config)
    except ConfigError as exc:
        report = {"status": "fail", "category": "config", "detail": str(exc)}
        print(json.dumps(report, indent=2) if args.format == "json" else f"FAIL  config          {exc}")
        return 2

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)

    failed = any(
        report[key].get("status") == "fail" for key in ("auth", "endpoint", "add", "search", "metadata_filter")
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

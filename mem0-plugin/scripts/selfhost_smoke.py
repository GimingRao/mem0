#!/usr/bin/env python3
"""Run a strict self-hosted Mem0 add/search smoke test."""

from __future__ import annotations

import argparse
import json
import sys

from _selfhost_config import ConfigError, load_selfhost_config
from _selfhost_probe import run_smoke
from selfhost_health import print_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Run self-hosted Mem0 configure/add/search smoke test.")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args()

    try:
        config = load_selfhost_config()
        report = run_smoke(config)
    except ConfigError as exc:
        report = {"status": "fail", "failures": [{"check": "config", "category": "config", "detail": str(exc)}]}
        print(json.dumps(report, indent=2) if args.format == "json" else f"FAIL  config          {exc}")
        return 2

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report["health"])
        print()
        print(f"Smoke: {report['status'].upper()}")
        for failure in report["failures"]:
            print(f"- {failure['check']}: {failure.get('detail')} [{failure.get('category')}]")

    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

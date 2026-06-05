#!/usr/bin/env bash
# Install the Mem0 self-host Codex plugin configuration.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${ROOT_DIR}/mem0-plugin/scripts/install/selfhost/install.sh" "$@"

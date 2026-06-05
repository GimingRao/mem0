#!/usr/bin/env bash
# Configure Mem0 self-host settings for Codex without writing secrets to the repo.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
REPO_ROOT="$(cd "${PLUGIN_ROOT}/.." && pwd)"
SETTINGS_FILE="${HOME}/.mem0/settings.json"
DEFAULT_KEY_FILE="${HOME}/.mem0/selfhost-api-key"

usage() {
  cat <<'EOF'
Usage: scripts/install.sh [options]

Options:
  --api-url URL              Self-hosted Mem0 API URL, for example https://mem0.example.com
  --transport MODE           http, https, or ssh
  --api-key-file PATH        Existing file containing the API key
  --api-key KEY              Write KEY to --api-key-file or ~/.mem0/selfhost-api-key
  --user-id ID               Mem0 user_id
  --project-id ID            Default project/app scope
  --ssh-host HOST            SSH host for ssh transport
  --ssh-user USER            SSH user for ssh transport
  --ssh-port PORT            SSH port for ssh transport
  --ssh-key PATH             SSH private key path for ssh transport
  --remote-api-url URL       Remote localhost API URL for ssh transport
  --no-health                Do not run health after writing config
  -h, --help                 Show this help
EOF
}

API_URL="${MEM0_SELFHOST_API_URL:-}"
TRANSPORT="${MEM0_SELFHOST_TRANSPORT:-}"
API_KEY_FILE="${MEM0_SELFHOST_API_KEY_FILE:-}"
API_KEY="${MEM0_SELFHOST_API_KEY:-}"
USER_ID="${MEM0_USER_ID:-${USER:-}}"
PROJECT_ID="${MEM0_PROJECT_ID:-}"
SSH_HOST="${MEM0_SELFHOST_SSH_HOST:-}"
SSH_USER="${MEM0_SELFHOST_SSH_USER:-}"
SSH_PORT="${MEM0_SELFHOST_SSH_PORT:-}"
SSH_KEY="${MEM0_SELFHOST_SSH_KEY:-}"
REMOTE_API_URL="${MEM0_SELFHOST_REMOTE_API_URL:-}"
RUN_HEALTH=1

while [ "$#" -gt 0 ]; do
  case "$1" in
    --api-url) API_URL="${2:-}"; shift 2 ;;
    --transport) TRANSPORT="${2:-}"; shift 2 ;;
    --api-key-file) API_KEY_FILE="${2:-}"; shift 2 ;;
    --api-key) API_KEY="${2:-}"; shift 2 ;;
    --user-id) USER_ID="${2:-}"; shift 2 ;;
    --project-id) PROJECT_ID="${2:-}"; shift 2 ;;
    --ssh-host) SSH_HOST="${2:-}"; shift 2 ;;
    --ssh-user) SSH_USER="${2:-}"; shift 2 ;;
    --ssh-port) SSH_PORT="${2:-}"; shift 2 ;;
    --ssh-key) SSH_KEY="${2:-}"; shift 2 ;;
    --remote-api-url) REMOTE_API_URL="${2:-}"; shift 2 ;;
    --no-health) RUN_HEALTH=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

prompt_if_empty() {
  local var_name="$1"
  local prompt="$2"
  local default_value="${3:-}"
  local current_value="${!var_name:-}"
  if [ -n "${current_value}" ] || [ ! -t 0 ]; then
    return
  fi
  if [ -n "${default_value}" ]; then
    read -r -p "${prompt} [${default_value}]: " current_value
    current_value="${current_value:-${default_value}}"
  else
    read -r -p "${prompt}: " current_value
  fi
  printf -v "${var_name}" '%s' "${current_value}"
}

prompt_secret_if_empty() {
  if [ -n "${API_KEY}" ] || [ -n "${API_KEY_FILE}" ] || [ ! -t 0 ]; then
    return
  fi
  read -r -s -p "API key (optional, hidden): " API_KEY
  echo
}

prompt_if_empty API_URL "Mem0 endpoint" "https://mem0.example.com"
prompt_if_empty TRANSPORT "Transport mode (http, https, ssh)" ""
prompt_if_empty USER_ID "User ID" "${USER:-default}"
prompt_if_empty PROJECT_ID "Default app/project scope" ""
prompt_secret_if_empty

if [ -z "${API_URL}" ]; then
  echo "error: --api-url or MEM0_SELFHOST_API_URL is required" >&2
  exit 2
fi

if [ -z "${TRANSPORT}" ]; then
  case "${API_URL}" in
    https://*) TRANSPORT="https" ;;
    http://*) TRANSPORT="http" ;;
    *) echo "error: API URL must start with http:// or https://" >&2; exit 2 ;;
  esac
fi

case "${TRANSPORT}" in
  http|https|ssh) ;;
  *) echo "error: transport must be http, https, or ssh" >&2; exit 2 ;;
esac

if [ "${TRANSPORT}" = "ssh" ] && [ -z "${SSH_HOST}" ]; then
  prompt_if_empty SSH_HOST "SSH host" ""
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required" >&2
  exit 2
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "warning: codex CLI not found on PATH; install Codex or configure the desktop app manually" >&2
fi

if [ "${TRANSPORT}" = "ssh" ]; then
  if ! command -v ssh >/dev/null 2>&1; then
    echo "error: ssh is required for ssh transport" >&2
    exit 2
  fi
fi

if ! python3 -c "import mem0" >/dev/null 2>&1; then
  echo "warning: Python package mem0ai is not importable in this shell; lifecycle hooks can install plugin deps via scripts/ensure_deps.sh" >&2
fi

mkdir -p "${HOME}/.mem0"
chmod 700 "${HOME}/.mem0" 2>/dev/null || true

if [ -n "${API_KEY}" ]; then
  if [ -z "${API_KEY_FILE}" ]; then
    API_KEY_FILE="${DEFAULT_KEY_FILE}"
  fi
  mkdir -p "$(dirname "${API_KEY_FILE}")"
  umask 177
  printf '%s\n' "${API_KEY}" > "${API_KEY_FILE}"
  chmod 600 "${API_KEY_FILE}" 2>/dev/null || true
  echo "Wrote API key to ${API_KEY_FILE}"
elif [ -z "${API_KEY_FILE}" ] && [ -f "${DEFAULT_KEY_FILE}" ]; then
  API_KEY_FILE="${DEFAULT_KEY_FILE}"
fi

PYTHONPATH="${PLUGIN_ROOT}/scripts${PYTHONPATH:+:${PYTHONPATH}}" python3 - "$API_URL" "$TRANSPORT" "$USER_ID" "$PROJECT_ID" "$API_KEY_FILE" "$SSH_HOST" "$SSH_USER" "$SSH_PORT" "$SSH_KEY" "$REMOTE_API_URL" <<'PY'
import sys
from _selfhost_config import settings_payload, write_settings

api_url, transport, user_id, project_id, api_key_file, ssh_host, ssh_user, ssh_port, ssh_key, remote_api_url = sys.argv[1:]
payload = settings_payload(
    api_url=api_url,
    transport=transport,
    user_id=user_id or None,
    project_id=project_id or None,
    api_key_file=api_key_file or None,
    ssh_host=ssh_host or None,
    ssh_user=ssh_user or None,
    ssh_port=ssh_port or None,
    ssh_key=ssh_key or None,
    remote_api_url=remote_api_url or None,
)
write_settings(payload)
print("Updated ~/.mem0/settings.json")
PY

check_duplicate_registration() {
  local config="${HOME}/.codex/config.toml"
  if [ -f "${config}" ] && grep -Eq '^\[mcp_servers\.mem0\]' "${config}"; then
    echo "warning: ${config} already has [mcp_servers.mem0]; avoid duplicate Mem0 registrations" >&2
  fi
  if [ -f "${PLUGIN_ROOT}/.codex-mcp.json" ] && grep -q '"mem0"' "${PLUGIN_ROOT}/.codex-mcp.json"; then
    echo "note: bundled Codex plugin manifest also registers mem0 MCP when sideloaded" >&2
  fi
}

check_duplicate_registration

cat <<EOF

Mem0 self-host configuration written.
Settings: ${SETTINGS_FILE}
Plugin root: ${PLUGIN_ROOT}

Security mode:
- http  : demo/trusted networks only
- https : recommended production mode
- ssh   : private mode through remote localhost
EOF

if [ "${RUN_HEALTH}" = "1" ]; then
  echo
  echo "Running self-host health..."
  PYTHONPATH="${PLUGIN_ROOT}/scripts${PYTHONPATH:+:${PYTHONPATH}}" python3 "${PLUGIN_ROOT}/scripts/selfhost_health.py" --format text || true
fi

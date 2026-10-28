#!/usr/bin/env bash
set -euo pipefail
UNDEX_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=lib/common.sh
source "$UNDEX_ROOT/lib/common.sh"
# shellcheck source=lib/tools.sh
source "$UNDEX_ROOT/lib/tools.sh"
# shellcheck source=lib/integrations.sh
source "$UNDEX_ROOT/lib/integrations.sh"
# shellcheck source=lib/plugins.sh
source "$UNDEX_ROOT/lib/plugins.sh"

usage() {
    cat <<'EOF'
Usage: bash install.sh [OPTIONS]
  --update               Explicitly update managed tools and selected plugins
  --non-interactive      Skip new logins and optional selection; report pending steps
  --plugins NAMES        Comma-separated optional plugin names (none by default)
  --reuse-options        Reuse the previous optional plugin selection
  --configure-context7   Retry Context7's interactive MCP setup
  --help                 Show this help

Optional: gmail, google-calendar, google-contacts, google-drive,
          openai-templates, pages, sites, plugin-management
EOF
}

while (( $# )); do
    case "$1" in
        --update) UNDEX_UPDATE=1 ;;
        --non-interactive) UNDEX_NONINTERACTIVE=1 ;;
        --configure-context7) UNDEX_CONFIGURE_CONTEXT7=1 ;;
        --reuse-options) UNDEX_REUSE_OPTIONS=1 ;;
        --plugins)
            (( $# >= 2 )) || { printf '%s requires a value.\n' "$1" >&2; exit 1; }
            UNDEX_PLUGIN_SELECTION="$2"; shift ;;
        --help|-h) usage; exit 0 ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 1 ;;
    esac
    shift
done
[[ -t 0 ]] || UNDEX_NONINTERACTIVE=1

finish() {
    local result=$?
    trap - EXIT
    if (( result != 0 )); then UNDEX_FAILED=1; fi
    undex_summary || true
    if (( result != 0 || UNDEX_FAILED != 0 )); then exit 1; fi
}
trap finish EXIT

run_component 'Linux prerequisites' undex_preflight
run_component uv ensure_uv
undex_lock install
run_component 'Node through nvm' ensure_node
run_component Codex ensure_codex
run_component RTK ensure_rtk
run_component 'Playwright CLI' ensure_playwright
run_component Graphify ensure_graphify
run_component 'Personal configuration' cfg apply --codex-home "$CODEX_HOME" --backup-root "$UNDEX_BACKUP_ROOT"

# Continue independent setup after an integration failure, preserving its failed status.
run_component 'RTK integration' configure_rtk || true
run_component 'Context7 MCP' configure_context7 || true
run_component 'Playwright skills/browser' configure_playwright || true
run_component 'Codex authentication' ensure_codex_login || true
select_optional_plugins
run_component Plugins install_plugins || true
run_component 'Graphify helper' cfg launcher --command "$HOME/.local/bin/undex-graphify" --backup-root "$UNDEX_BACKUP_ROOT"

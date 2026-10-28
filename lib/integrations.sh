#!/usr/bin/env bash

standard_codex_home() {
    if [[ "$CODEX_HOME" != "$HOME/.codex" ]]; then
        printf 'Context7 setup home handling is not guaranteed. Use CODEX_HOME=%s for ctx7 setup, or configure its MCP server manually in your custom home. No alternate home was modified.\n' "$HOME/.codex" >&2
        return 1
    fi
}

configure_rtk() {
    snapshot_config || return
    # Codex init is automatic; RTK rejects --auto-patch together with --codex.
    rtk init -g --codex || return
    [[ -s "$CODEX_HOME/RTK.md" ]] || return 1
    undex_record 'RTK hook trust' pending 'Codex may request trust for the generated hook on next start'
}

configure_context7() {
    standard_codex_home || return
    if [[ "$UNDEX_UPDATE" != 1 && "$UNDEX_CONFIGURE_CONTEXT7" != 1 ]] && cfg context7-check --codex-home "$CODEX_HOME"; then
        undex_record 'Context7 authentication' pending 'existing MCP configuration reused; verify access in a fresh Codex session'
        return 0
    fi
    if [[ "$UNDEX_NONINTERACTIVE" == 1 ]]; then
        undex_record Context7 pending 'run bash install.sh --configure-context7 interactively to authorize setup'
        return 0
    fi
    local version
    version="$(state_get ctx7_version)" || return
    if [[ -z "$version" || "$UNDEX_UPDATE" == 1 ]]; then
        version="$(npm view ctx7 version)" || return
        [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
        state_set ctx7_version "$version" || return
    fi
    [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
    snapshot_config || return
    npx --yes "ctx7@$version" setup --codex --mcp || return
    cfg context7-check --codex-home "$CODEX_HOME" || return
    state_set context7_ready yes
}

configure_playwright() {
    playwright-cli install --skills=agents --global || return
    local version previous
    version="$(playwright-cli --version)" || return
    previous="$(state_get browser_cli_version)" || return
    if [[ "$previous" != "$version" || "$UNDEX_UPDATE" == 1 ]]; then
        playwright-cli install-browser chrome --with-deps || return
        state_set browser_cli_version "$version" || return
    elif ! command -v google-chrome >/dev/null && ! playwright-cli install-browser --list | rg_or_grep_chrome; then
        playwright-cli install-browser chrome --with-deps || return
    fi
}

rg_or_grep_chrome() {
    # grep is part of the Ubuntu base; do not require ripgrep on fresh machines.
    grep -qi chrome
}

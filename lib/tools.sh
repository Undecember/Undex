#!/usr/bin/env bash

node_compatible() {
    local version
    version="$(node --version 2>/dev/null)" || return 1
    [[ "$version" =~ ^v([0-9]+)\. ]] && (( BASH_REMATCH[1] >= 20 ))
}

ensure_uv() {
    if ! uv --version >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh || return
    elif [[ "$UNDEX_UPDATE" == 1 ]]; then
        uv self update || return
    fi
    uv --version
}

ensure_node() {
    export NVM_DIR="${NVM_DIR:-${XDG_CONFIG_HOME:+$XDG_CONFIG_HOME/}nvm}"
    # The standard nvm location is ~/.nvm without XDG_CONFIG_HOME.
    [[ "$NVM_DIR" != nvm ]] || NVM_DIR="$HOME/.nvm"
    if [[ ! -s "$NVM_DIR/nvm.sh" || "$UNDEX_UPDATE" == 1 ]]; then
        local release
        release="$(curl -fsSL https://api.github.com/repos/nvm-sh/nvm/releases/latest | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')" || return
        [[ "$release" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
        curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/$release/install.sh" | bash || return
    fi
    [[ -s "$NVM_DIR/nvm.sh" ]] || { printf 'nvm installer did not create nvm.sh.\n' >&2; return 1; }
    # nvm is not nounset-safe; preserve the current Node environment while loading.
    local nvm_result=0
    set +u
    # shellcheck source=/dev/null
    source "$NVM_DIR/nvm.sh" --no-use || nvm_result=$?
    set -u
    (( nvm_result == 0 )) || return "$nvm_result"
    local saved=''
    # Restore an existing Node before either reuse or update so npm inventory
    # comes from the user's previous environment, even in a fresh shell.
    if ! node_compatible; then
        saved="$(state_get node_version)" || return
        if [[ -n "$saved" ]]; then nvm use "$saved" || return
        else nvm use default >/dev/null 2>&1 || true; fi
    fi
    if [[ "$UNDEX_UPDATE" != 1 ]]; then
        node_compatible || nvm install --lts || return
    else
        # Reinstall exact existing npm package versions after selecting the new LTS.
        local packages=''
        if node_compatible; then packages="$(npm list -g --depth=0 --json)" || return; fi
        nvm install --lts || return
        if [[ -n "$packages" ]]; then
            local spec specs
            specs="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print("\n".join(k+"@"+v["version"] for k,v in d.get("dependencies",{}).items() if k not in ("npm","corepack")))' <<<"$packages")" || return
            while IFS= read -r spec; do
                [[ -z "$spec" ]] || npm install -g "$spec" || return
            done <<<"$specs"
        fi
    fi
    node_compatible || return 1
    local version
    version="$(node --version)" || return
    state_set node_version "$version" || return
    printf 'Node %s\n' "$version"
}

ensure_codex() {
    if ! codex --version >/dev/null 2>&1 || [[ "$UNDEX_UPDATE" == 1 ]]; then
        npm i -g @openai/codex || return
    fi
    codex --version || return
    codex plugin add --help >/dev/null || { printf 'Codex plugin CLI is required; rerun with --update.\n' >&2; return 1; }
}

ensure_rtk() {
    if ! rtk --version >/dev/null 2>&1 || [[ "$UNDEX_UPDATE" == 1 ]]; then
        curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh || return
    fi
    rtk --version
}

ensure_playwright() {
    if ! playwright-cli --version >/dev/null 2>&1 || [[ "$UNDEX_UPDATE" == 1 ]]; then
        npm install -g @playwright/cli@latest || return
    fi
    playwright-cli --version || return
    local help
    help="$(playwright-cli install --help)" || return
    [[ "$help" == *--global* ]] || { printf 'Playwright global skills require --update.\n' >&2; return 1; }
}

ensure_graphify() {
    if ! graphify --version >/dev/null 2>&1; then
        uv tool install 'graphifyy[mcp]' || return
    elif [[ "$UNDEX_UPDATE" == 1 ]]; then
        uv tool upgrade graphifyy || return
    elif ! graphify-mcp --help >/dev/null 2>&1; then
        printf 'Graphify lacks MCP support. Reinstall its current version with the [mcp] extra; see README.\n' >&2
        return 1
    fi
    graphify --version || return
    graphify-mcp --help >/dev/null
}

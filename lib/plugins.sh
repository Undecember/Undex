#!/usr/bin/env bash
UNDEX_OPTIONAL_PLUGINS=(gmail google-calendar google-contacts google-drive openai-templates pages sites plugin-management)
UNDEX_SELECTED_PLUGINS=()

ensure_codex_login() {
    if codex login status >/dev/null 2>&1; then return 0; fi
    if [[ "$UNDEX_NONINTERACTIVE" == 1 || ! -t 0 ]]; then
        undex_record 'Codex login' pending 'run codex login --device-auth, then rerun the installer'
        return 0
    fi
    codex login --device-auth || return
    codex login status >/dev/null 2>&1
}

select_optional_plugins() {
    local selection="${UNDEX_PLUGIN_SELECTION:-}" answer='' item found candidate
    if [[ -z "$selection" && ( "${UNDEX_REUSE_OPTIONS:-0}" == 1 || "$UNDEX_UPDATE" == 1 ) ]]; then
        selection="$(state_get optional_plugins)" || return
    elif [[ -z "$selection" && "$UNDEX_NONINTERACTIVE" != 1 && -t 0 ]]; then
        printf '\nOptional plugins (none selected). Enter names separated by commas, or Enter to skip:\n'
        printf '  %s\n' "${UNDEX_OPTIONAL_PLUGINS[@]}"
        read -r answer || answer=''
        selection="$answer"
    fi
    UNDEX_SELECTED_PLUGINS=()
    local entries=()
    IFS=',' read -r -a entries <<<"$selection"
    for item in "${entries[@]}"; do
        item="${item//[[:space:]]/}"
        [[ -n "$item" ]] || continue
        found=0
        for candidate in "${UNDEX_OPTIONAL_PLUGINS[@]}"; do
            [[ "$candidate" != "$item" ]] || found=1
        done
        (( found )) || { printf 'Unknown optional plugin: %s\n' "$item" >&2; return 1; }
        if [[ " ${UNDEX_SELECTED_PLUGINS[*]} " != *" $item "* ]]; then UNDEX_SELECTED_PLUGINS+=("$item"); fi
    done
    local joined
    joined="$(IFS=,; printf '%s' "${UNDEX_SELECTED_PLUGINS[*]}")"
    state_set optional_plugins "$joined"
}

install_plugins() {
    if ! codex login status >/dev/null 2>&1; then
        undex_record Plugins pending 'Codex login is required; rerun after device login'
        return 0
    fi
    local listing installed plugin id is_default
    listing="$(codex plugin list --json)" || return
    installed="$(cfg plugins <<<"$listing")" || return
    for plugin in superpowers github "${UNDEX_SELECTED_PLUGINS[@]}"; do
        id="$plugin@openai-curated-remote"
        if [[ "$UNDEX_UPDATE" != 1 ]] && grep -Fxq -- "$id" <<<"$installed"; then
            if grep -Fxq -- "disabled:$id" <<<"$installed"; then
                undex_record "$plugin plugin" pending 'installed but disabled; enable through /plugins; version preserved'
            else
                undex_record "$plugin plugin" ok 'already installed; version preserved'
            fi
        else
            is_default=0
            [[ "$plugin" != superpowers && "$plugin" != github ]] || is_default=1
            if codex plugin add "$id"; then
                undex_record "$plugin plugin" ok 'installed'
            elif (( is_default )); then
                undex_record "$plugin plugin" failed "retry: codex plugin add $id"
                return 1
            else
                undex_record "$plugin plugin" pending "optional installation failed; retry: codex plugin add $id"
            fi
        fi
        case "$plugin" in
            superpowers|openai-templates) ;;
            *) undex_record "$plugin connection" pending 'confirm service connection in Codex /plugins; installation alone does not verify account access' ;;
        esac
    done
}

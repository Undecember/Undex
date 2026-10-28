#!/usr/bin/env bash
# Shared paths and status reporting. Sourcing this file does not mutate files.
UNDEX_ROOT="${UNDEX_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}"
UNDEX_STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/undex"
UNDEX_STATE_FILE="$UNDEX_STATE_DIR/state.json"
UNDEX_BACKUP_ROOT="$UNDEX_STATE_DIR/backups"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export CODEX_HOME
export PATH="$HOME/.local/bin:$PATH"
UNDEX_UPDATE="${UNDEX_UPDATE:-0}"
UNDEX_NONINTERACTIVE="${UNDEX_NONINTERACTIVE:-0}"
UNDEX_CONFIGURE_CONTEXT7="${UNDEX_CONFIGURE_CONTEXT7:-0}"
UNDEX_FAILED=0
UNDEX_PENDING=0
UNDEX_COMPONENT_PENDING=0
UNDEX_RESULTS=()

cfg() { uv run --quiet --locked --project "$UNDEX_ROOT" python "$UNDEX_ROOT/lib/configure.py" "$@"; }
state_get() { cfg state-get "$1" --state-file "$UNDEX_STATE_FILE"; }
state_set() { cfg state-set "$1" "$2" --state-file "$UNDEX_STATE_FILE"; }
snapshot_config() { cfg snapshot --codex-home "$CODEX_HOME" --backup-root "$UNDEX_BACKUP_ROOT"; }

undex_lock() {
    local name="$1"
    python3 - "$UNDEX_STATE_DIR" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
if any(a.is_symlink() for a in (p,*p.parents)):
    sys.exit('Refusing a symlinked installer state directory.')
PY
    local result=$?
    (( result == 0 )) || return "$result"
    mkdir -p -- "$UNDEX_STATE_DIR" || return
    chmod 700 "$UNDEX_STATE_DIR" || return
    [[ ! -L "$UNDEX_STATE_DIR/$name.lock" ]] || { printf 'Refusing symlinked lock file.\n' >&2; return 1; }
    exec 9>"$UNDEX_STATE_DIR/$name.lock" || return
    flock 9
}

undex_record() {
    local component="$1" status="$2" detail="$3"
    UNDEX_RESULTS+=("$status: $component — $detail")
    printf '%s: %s — %s\n' "$status" "$component" "$detail"
    case "$status" in
        failed) UNDEX_FAILED=1 ;;
        pending) UNDEX_PENDING=1; UNDEX_COMPONENT_PENDING=1 ;;
    esac
}

run_component() {
    local name="$1"
    shift
    UNDEX_COMPONENT_PENDING=0
    if "$@"; then
        if [[ "$UNDEX_COMPONENT_PENDING" != 1 ]]; then undex_record "$name" ok 'ready'; fi
    else
        undex_record "$name" failed 'see command error above; rerun after correcting it'
        return 1
    fi
}

undex_summary() {
    printf '\nUndex setup results\n'
    printf '  %s\n' "${UNDEX_RESULTS[@]}"
    printf 'Backups: %s\nStart a fresh Codex session to load updated skills and plugins.\n' "$UNDEX_BACKUP_ROOT"
    if (( UNDEX_PENDING )); then printf 'Personal or optional setup steps remain; see pending items above.\n'; fi
    return "$UNDEX_FAILED"
}

privileged() {
    if [[ "$(id -u)" == 0 ]]; then "$@"; else
        command -v sudo >/dev/null || { printf 'sudo is needed for missing Linux packages.\n' >&2; return 1; }
        sudo "$@"
    fi
}

undex_preflight() {
    [[ "$(uname -s)" == Linux ]] || { printf 'Undex supports Ubuntu/Linux only.\n' >&2; return 1; }
    [[ -r /etc/os-release ]] || return 1
    local ID='' ID_LIKE=''
    # shellcheck source=/etc/os-release
    source /etc/os-release
    case " $ID $ID_LIKE " in
        *ubuntu*|*debian*) ;;
        *) printf 'This release requires an Ubuntu/Debian apt-based distribution.\n' >&2; return 1 ;;
    esac
    local missing=() tool package
    for tool in curl git python3 flock; do
        if ! command -v "$tool" >/dev/null; then
            case "$tool" in flock) package=util-linux ;; *) package="$tool" ;; esac
            missing+=("$package")
        fi
    done
    [[ -r /etc/ssl/certs/ca-certificates.crt ]] || missing+=(ca-certificates)
    if (( ${#missing[@]} )); then
        privileged apt-get update || return
        privileged apt-get install -y "${missing[@]}" || return
    fi
}

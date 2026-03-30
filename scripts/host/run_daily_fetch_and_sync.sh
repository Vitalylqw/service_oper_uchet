#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
PROJECT_ROOT="$(cd "$(dirname "${SCRIPT_PATH}")/../.." && pwd)"
SO_UCHET_VENV="${SO_UCHET_VENV:-${PROJECT_ROOT}/.host-venv}"
SO_UCHET_ENV_FILE="${SO_UCHET_ENV_FILE:-${PROJECT_ROOT}/config.host.env}"
SO_UCHET_FETCH_SCRIPT="${SO_UCHET_FETCH_SCRIPT:-${PROJECT_ROOT}/scripts/services/fetch_excel_from_smb.py}"
SO_UCHET_CLI_WRAPPER="${SO_UCHET_CLI_WRAPPER:-${PROJECT_ROOT}/scripts/host/run_host_cli.sh}"
SO_UCHET_SYNC_LOG_LEVEL="${SO_UCHET_SYNC_LOG_LEVEL:-INFO}"

CURRENT_PID=""

log() {
    printf '%s | %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

load_env_file() {
    if [[ ! -f "${SO_UCHET_ENV_FILE}" ]]; then
        log "Env file not found: ${SO_UCHET_ENV_FILE}"
        return 1
    fi

    set -a
    # shellcheck disable=SC1090
    source "${SO_UCHET_ENV_FILE}"
    set +a
}

forward_signal() {
    local signal="$1"
    if [[ -n "${CURRENT_PID}" ]] && kill -0 "${CURRENT_PID}" 2>/dev/null; then
        kill -s "${signal}" "${CURRENT_PID}" 2>/dev/null || true
    fi
}

handle_signal() {
    local signal="$1"
    log "Received ${signal}, forwarding to child process"
    forward_signal "${signal}"
    wait "${CURRENT_PID}" 2>/dev/null || true
    exit 128
}

run_command() {
    local -a command=("$@")
    log "Running: ${command[*]}"
    "${command[@]}" &
    CURRENT_PID=$!
    set +e
    wait "${CURRENT_PID}"
    local rc=$?
    set -e
    CURRENT_PID=""
    return "${rc}"
}

trap 'handle_signal INT' INT
trap 'handle_signal TERM' TERM
trap 'handle_signal HUP' HUP

if [[ ! -x "${SO_UCHET_VENV}/bin/python" ]]; then
    log "Python executable not found in venv: ${SO_UCHET_VENV}/bin/python"
    exit 1
fi

if [[ ! -x "${SO_UCHET_CLI_WRAPPER}" ]]; then
    log "CLI wrapper is not executable: ${SO_UCHET_CLI_WRAPPER}"
    exit 1
fi

load_env_file

if [[ $# -gt 0 ]]; then
    SYNC_COMMAND=("${SO_UCHET_CLI_WRAPPER}" "$@")
else
    SYNC_COMMAND=(
        "${SO_UCHET_CLI_WRAPPER}"
        --log-level "${SO_UCHET_SYNC_LOG_LEVEL}"
        sync
        full
        --log-level "${SO_UCHET_SYNC_LOG_LEVEL}"
    )
fi

log "Daily fetch-and-sync job started"
run_command "${SO_UCHET_VENV}/bin/python" "${SO_UCHET_FETCH_SCRIPT}"
log "Excel copy completed successfully"
run_command "${SYNC_COMMAND[@]}"
log "Synchronization completed successfully"

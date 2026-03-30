#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
PROJECT_ROOT="$(cd "$(dirname "${SCRIPT_PATH}")/../.." && pwd)"
SO_UCHET_VENV="${SO_UCHET_VENV:-${PROJECT_ROOT}/.host-venv}"
SO_UCHET_ENV_FILE="${SO_UCHET_ENV_FILE:-${PROJECT_ROOT}/config.host.env}"
SO_UCHET_CLI_BIN="${SO_UCHET_CLI_BIN:-${SO_UCHET_VENV}/bin/so-uchet}"

if [[ ! -x "${SO_UCHET_CLI_BIN}" ]]; then
    echo "CLI executable not found: ${SO_UCHET_CLI_BIN}" >&2
    echo "Install host runtime first: scripts/host/install_host_runtime.sh" >&2
    exit 1
fi

if [[ ! -f "${SO_UCHET_ENV_FILE}" ]]; then
    echo "Env file not found: ${SO_UCHET_ENV_FILE}" >&2
    echo "Create it from config.host.env.example before running host CLI." >&2
    exit 1
fi

exec "${SO_UCHET_CLI_BIN}" --env-file "${SO_UCHET_ENV_FILE}" "$@"

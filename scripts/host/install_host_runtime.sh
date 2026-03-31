#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
PROJECT_ROOT="$(cd "$(dirname "${SCRIPT_PATH}")/../.." && pwd)"

SERVICE_NAME="so-uchet-daily-sync"
INSTALL_USER="${SUDO_USER:-${USER}}"
INSTALL_GROUP="$(id -gn "${INSTALL_USER}")"
VENV_PATH="${PROJECT_ROOT}/.venv"
ENV_FILE="${PROJECT_ROOT}/config.env"
BIN_NAME="so-uchet-host"
SKIP_PIP_INSTALL=0

usage() {
    cat <<'EOF'
Usage: scripts/host/install_host_runtime.sh [options]

Options:
  --user USER           Run systemd service as this user.
  --group GROUP         Group for service and log files.
  --venv PATH           Host virtualenv path.
  --env-file PATH       Host environment file.
  --bin-name NAME       Wrapper command name in /usr/local/bin.
  --skip-pip-install    Skip python package installation into the venv.
  -h, --help            Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --user)
            INSTALL_USER="$2"
            shift 2
            ;;
        --group)
            INSTALL_GROUP="$2"
            shift 2
            ;;
        --venv)
            VENV_PATH="$2"
            shift 2
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --bin-name)
            BIN_NAME="$2"
            shift 2
            ;;
        --skip-pip-install)
            SKIP_PIP_INSTALL=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

require_root() {
    if [[ "$(id -u)" -ne 0 ]]; then
        echo "Run this installer with sudo or as root." >&2
        exit 1
    fi
}

require_file() {
    local path="$1"
    if [[ ! -f "${path}" ]]; then
        echo "Required file not found: ${path}" >&2
        exit 1
    fi
}

render_template() {
    local template_path="$1"
    local destination_path="$2"

    sed \
        -e "s|__PROJECT_ROOT__|${PROJECT_ROOT}|g" \
        -e "s|__SERVICE_USER__|${INSTALL_USER}|g" \
        -e "s|__SERVICE_GROUP__|${INSTALL_GROUP}|g" \
        -e "s|__VENV_PATH__|${VENV_PATH}|g" \
        -e "s|__ENV_FILE__|${ENV_FILE}|g" \
        "${template_path}" > "${destination_path}"
}

create_venv() {
    if [[ ! -d "${VENV_PATH}" ]]; then
        python3 -m venv "${VENV_PATH}"
    fi

    if [[ "${SKIP_PIP_INSTALL}" -eq 0 ]]; then
        "${VENV_PATH}/bin/pip" install --upgrade pip
        "${VENV_PATH}/bin/pip" install -e "${PROJECT_ROOT}"
    fi
}

install_systemd_units() {
    render_template \
        "${PROJECT_ROOT}/deploy/systemd/${SERVICE_NAME}.service.template" \
        "/etc/systemd/system/${SERVICE_NAME}.service"
    render_template \
        "${PROJECT_ROOT}/deploy/systemd/${SERVICE_NAME}.timer.template" \
        "/etc/systemd/system/${SERVICE_NAME}.timer"

    systemctl daemon-reload
    systemctl enable --now "${SERVICE_NAME}.timer"
}

install_logrotate() {
    render_template \
        "${PROJECT_ROOT}/deploy/logrotate/so-uchet.template" \
        "/etc/logrotate.d/so-uchet"
}

install_wrapper() {
    ln -sfn "${PROJECT_ROOT}/scripts/host/run_host_cli.sh" "/usr/local/bin/${BIN_NAME}"
}

prepare_logs() {
    mkdir -p /var/log/so-uchet
    chown "${INSTALL_USER}:${INSTALL_GROUP}" /var/log/so-uchet
    chmod 0750 /var/log/so-uchet
}

main() {
    require_root
    require_file "${PROJECT_ROOT}/scripts/host/run_host_cli.sh"
    require_file "${PROJECT_ROOT}/scripts/host/run_daily_fetch_and_sync.sh"
    require_file "${PROJECT_ROOT}/deploy/systemd/${SERVICE_NAME}.service.template"
    require_file "${PROJECT_ROOT}/deploy/systemd/${SERVICE_NAME}.timer.template"
    require_file "${PROJECT_ROOT}/deploy/logrotate/so-uchet.template"

    if [[ ! -f "${ENV_FILE}" ]]; then
        echo "Env file not found: ${ENV_FILE}" >&2
        echo "Create or update ${PROJECT_ROOT}/config.env before installation." >&2
        exit 1
    fi

    create_venv
    prepare_logs
    install_wrapper
    install_logrotate
    install_systemd_units

    echo "Host runtime installed."
    echo "CLI wrapper: /usr/local/bin/${BIN_NAME}"
    echo "Timer status:"
    systemctl --no-pager --full status "${SERVICE_NAME}.timer" || true
    echo "Next runs:"
    systemctl list-timers "${SERVICE_NAME}.timer" --no-pager || true
}

main "$@"

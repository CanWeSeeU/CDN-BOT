#!/usr/bin/env bash
# =============================================================================
#  CDN Manager Bot — Uninstaller
# =============================================================================

set -euo pipefail

SERVICE_NAME="cdn-manager-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
INSTALL_DIR="/usr/local/cdn-manager"
CDN_CMD="/usr/bin/cdn"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

separator() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }

require_root() {
    [[ $EUID -eq 0 ]] || { error "This script must be run as root."; exit 1; }
}

main() {
    require_root

    echo ""
    separator
    echo -e "  ${BOLD}${RED}CDN Manager Bot — Uninstaller${RESET}"
    separator
    echo ""
    echo -e "  ${YELLOW}The following will be removed:${RESET}"
    echo -e "  • ${INSTALL_DIR}"
    echo -e "  • ${SERVICE_FILE}"
    echo -e "  • ${CDN_CMD}"
    echo ""

    read -rp "  Are you sure you want to uninstall? [y/N]: " CONFIRM
    CONFIRM="${CONFIRM,,}"
    if [[ "$CONFIRM" != "y" && "$CONFIRM" != "yes" ]]; then
        echo -e "  ${YELLOW}Uninstall cancelled.${RESET}"
        exit 0
    fi

    echo ""

    # Stop and disable service
    if systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        systemctl stop "${SERVICE_NAME}"
        success "Service stopped."
    fi

    if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
        systemctl disable "${SERVICE_NAME}"
        success "Service disabled."
    fi

    # Remove service file
    if [[ -f "${SERVICE_FILE}" ]]; then
        rm -f "${SERVICE_FILE}"
        success "Removed: ${SERVICE_FILE}"
    else
        warn "Service file not found: ${SERVICE_FILE}"
    fi

    # Reload systemd
    systemctl daemon-reload
    success "systemd reloaded."

    # Remove install directory
    if [[ -d "${INSTALL_DIR}" ]]; then
        rm -rf "${INSTALL_DIR}"
        success "Removed: ${INSTALL_DIR}"
    else
        warn "Install directory not found: ${INSTALL_DIR}"
    fi

    # Remove cdn command
    if [[ -f "${CDN_CMD}" ]]; then
        rm -f "${CDN_CMD}"
        success "Removed: ${CDN_CMD}"
    else
        warn "CDN command not found: ${CDN_CMD}"
    fi

    echo ""
    separator
    echo -e "  ${BOLD}${GREEN}✅  CDN Manager Bot has been uninstalled.${RESET}"
    separator
    echo ""
}

main "$@"
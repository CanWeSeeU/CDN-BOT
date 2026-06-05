#!/usr/bin/env bash
# =============================================================================
#  CDN Manager Bot — Installer
#  Installs the bot to /usr/local/cdn-manager and sets up the systemd service
# =============================================================================

set -euo pipefail

VERSION="1.1.0"
INSTALL_DIR="/usr/local/cdn-manager"
BOT_DIR="${INSTALL_DIR}/cdn_manager_bot"
VENV_DIR="${INSTALL_DIR}/venv"
ENV_FILE="${BOT_DIR}/.env"
SERVICE_NAME="cdn-manager-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
CDN_CMD="/usr/bin/cdn"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
die()     { error "$*"; exit 1; }

separator() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

header() {
    echo ""
    separator
    echo -e "  ${BOLD}$*${RESET}"
    separator
    echo ""
}

require_root() {
    [[ $EUID -eq 0 ]] || die "This installer must be run as root."
}

show_bot_token_help() {
    echo ""
    separator
    echo -e "  ${BOLD}${CYAN}How to create a Telegram Bot Token${RESET}"
    separator
    echo ""
    echo -e "  ${BOLD}1.${RESET} Open Telegram"
    echo -e "  ${BOLD}2.${RESET} Search for:  ${YELLOW}@BotFather${RESET}"
    echo -e "  ${BOLD}3.${RESET} Send:         ${YELLOW}/newbot${RESET}"
    echo -e "  ${BOLD}4.${RESET} Enter a display name for your bot"
    echo -e "  ${BOLD}5.${RESET} Enter a unique username ending in ${YELLOW}bot${RESET}"
    echo -e "  ${BOLD}6.${RESET} Copy the generated token"
    echo ""
    echo -e "  ${BOLD}Example:${RESET}"
    echo -e "  ${GREEN}123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx${RESET}"
    echo ""
    separator
    echo ""
}

show_admin_id_help() {
    echo ""
    separator
    echo -e "  ${BOLD}${CYAN}How to get your Telegram Numeric ID${RESET}"
    separator
    echo ""
    echo -e "  ${BOLD}1.${RESET} Open Telegram"
    echo -e "  ${BOLD}2.${RESET} Search for:  ${YELLOW}@userinfobot${RESET}"
    echo -e "  ${BOLD}3.${RESET} Press Start"
    echo -e "  ${BOLD}4.${RESET} Send any message"
    echo -e "  ${BOLD}5.${RESET} Copy the ${YELLOW}Id${RESET} value shown in the reply"
    echo ""
    echo -e "  ${BOLD}Example:${RESET}"
    echo -e "  ${GREEN}987654321${RESET}"
    echo ""
    separator
    echo ""
}

show_cf_token_help() {
    echo ""
    separator
    echo -e "  ${BOLD}${CYAN}How to create a Cloudflare API Token${RESET}"
    separator
    echo ""
    echo -e "  ${BOLD}1.${RESET}  Login to ${YELLOW}https://dash.cloudflare.com${RESET}"
    echo -e "  ${BOLD}2.${RESET}  Go to:  ${YELLOW}My Profile → API Tokens${RESET}"
    echo -e "  ${BOLD}3.${RESET}  Click:  ${YELLOW}Create Token${RESET}"
    echo -e "  ${BOLD}4.${RESET}  Choose: ${YELLOW}Edit zone DNS${RESET}  (Use Template)"
    echo ""
    echo -e "  ${BOLD}5.${RESET}  Permissions:"
    echo -e "       ${YELLOW}Zone → DNS → Edit${RESET}"
    echo -e "       ${YELLOW}Zone → Zone → Read${RESET}"
    echo ""
    echo -e "  ${BOLD}6.${RESET}  Zone Resources:"
    echo -e "       ${YELLOW}All Zones${RESET}  (Recommended)"
    echo ""
    echo -e "  ${BOLD}7.${RESET}  Client IP Address Filtering:"
    echo -e "       ${YELLOW}Leave Empty${RESET}"
    echo ""
    echo -e "  ${BOLD}8.${RESET}  Token TTL:"
    echo -e "       ${YELLOW}No Expiration${RESET}"
    echo ""
    echo -e "  ${BOLD}9.${RESET}  Click ${YELLOW}Create Token${RESET} and copy the result"
    echo ""
    echo -e "  ${BOLD}Example:${RESET}"
    echo -e "  ${GREEN}abc123XYZxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx${RESET}"
    echo ""
    separator
    echo ""
}
collect_credentials() {
    header "📋  Configuration — Please provide your credentials"

    #Bot Token
    show_bot_token_help
    while true; do
        read -rp "  Enter Telegram Bot Token: " BOT_TOKEN
        BOT_TOKEN="${BOT_TOKEN// /}"
        if [[ -n "$BOT_TOKEN" ]]; then
            break
        fi
        warn "Bot token cannot be empty."
    done

    echo ""

    #Admin ID
    show_admin_id_help
    while true; do
        read -rp "  Enter Admin Telegram ID: " ADMIN_ID
        ADMIN_ID="${ADMIN_ID// /}"
        if [[ "$ADMIN_ID" =~ ^[0-9]+$ ]]; then
            break
        fi
        warn "Admin ID must be a numeric value."
    done

    echo ""

    #Cloudflare Token
    show_cf_token_help
    while true; do
        read -rp "  Enter Cloudflare API Token: " CF_API_TOKEN
        CF_API_TOKEN="${CF_API_TOKEN// /}"
        if [[ -n "$CF_API_TOKEN" ]]; then
            break
        fi
        warn "Cloudflare API token cannot be empty."
    done
}

install_packages() {
    header "📦  Installing system packages"

    if command -v apt-get &>/dev/null; then
        apt-get update -qq
        apt-get install -y -qq python3 python3-pip python3-venv git curl
    elif command -v yum &>/dev/null; then
        yum install -y -q python3 python3-pip git curl
    elif command -v dnf &>/dev/null; then
        dnf install -y -q python3 python3-pip git curl
    else
        die "Unsupported package manager. Install python3, python3-pip, python3-venv, git manually."
    fi

    success "System packages installed."
}

copy_files() {
    header "📂  Copying application files"

    mkdir -p "${INSTALL_DIR}"
    cp -r "${REPO_DIR}/cdn_manager_bot" "${INSTALL_DIR}/"
    cp "${REPO_DIR}/install.sh"   "${INSTALL_DIR}/"
    cp "${REPO_DIR}/uninstall.sh" "${INSTALL_DIR}/"

    # Initialise git repo in install dir if not present (needed for version updates)
    if [[ -d "${REPO_DIR}/.git" ]] && [[ ! -d "${INSTALL_DIR}/.git" ]]; then
        cp -r "${REPO_DIR}/.git" "${INSTALL_DIR}/"
    fi

    success "Files copied to ${INSTALL_DIR}"
}

create_venv() {
    header "🐍  Creating Python virtual environment"

    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install --quiet --upgrade pip
    "${VENV_DIR}/bin/pip" install --quiet -r "${BOT_DIR}/requirements.txt"

    success "Virtual environment ready at ${VENV_DIR}"
}

write_env() {
    header "⚙️   Writing environment configuration"

    cp "${BOT_DIR}/.env.example" "${ENV_FILE}"
    sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=${BOT_TOKEN}|"       "${ENV_FILE}"
    sed -i "s|^ADMIN_ID=.*|ADMIN_ID=${ADMIN_ID}|"          "${ENV_FILE}"
    sed -i "s|^CF_API_TOKEN=.*|CF_API_TOKEN=${CF_API_TOKEN}|" "${ENV_FILE}"
    chmod 600 "${ENV_FILE}"

    success "Environment file written: ${ENV_FILE}"
}

install_service() {
    header "🔧  Installing systemd service"

    cp "${BOT_DIR}/systemd/${SERVICE_NAME}.service" "${SERVICE_FILE}"
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"
    systemctl start  "${SERVICE_NAME}"

    success "Service ${SERVICE_NAME} enabled and started."
}

install_cdn_command() {
    header "🔗  Installing global 'cdn' command"

    cp "${REPO_DIR}/cdn" "${CDN_CMD}"
    chmod +x "${CDN_CMD}"

    success "'cdn' command installed at ${CDN_CMD}"
}

post_install_summary() {
    echo ""
    separator
    echo -e "  ${BOLD}${GREEN}✅  Installation Completed Successfully${RESET}"
    separator
    echo ""
    echo -e "  ${BOLD}Application Path:${RESET}"
    echo -e "  ${CYAN}/usr/local/cdn-manager${RESET}"
    echo ""
    echo -e "  ${BOLD}Bot Directory:${RESET}"
    echo -e "  ${CYAN}/usr/local/cdn-manager/cdn_manager_bot${RESET}"
    echo ""
    echo -e "  ${BOLD}Environment:${RESET}"
    echo -e "  ${CYAN}/usr/local/cdn-manager/cdn_manager_bot/.env${RESET}"
    echo ""
    echo -e "  ${BOLD}Systemd Service:${RESET}"
    echo -e "  ${CYAN}/etc/systemd/system/cdn-manager-bot.service${RESET}"
    echo ""
    echo -e "  ${BOLD}Management Command:${RESET}"
    echo -e "  ${CYAN}cdn${RESET}"
    echo ""
    separator
    echo -e "  ${BOLD}Useful Commands:${RESET}"
    separator
    echo ""
    echo -e "  ${YELLOW}cdn${RESET}"
    echo -e "  ${YELLOW}systemctl status cdn-manager-bot${RESET}"
    echo -e "  ${YELLOW}journalctl -u cdn-manager-bot -f${RESET}"
    echo ""
    separator
    echo ""
}

main() {
    require_root

    echo ""
    separator
    echo -e "  ${BOLD}${CYAN}CDN Manager Bot — Installer  v${VERSION}${RESET}"
    separator
    echo ""

    install_packages
    collect_credentials
    copy_files
    create_venv
    write_env
    install_service
    install_cdn_command
    post_install_summary
}

main "$@"
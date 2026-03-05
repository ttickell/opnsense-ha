#!/bin/sh

# Project setup utility (not installed on firewall runtime paths).
# Ensures root SSH key-based login from this node to a peer firewall.
# - Uses existing root keypair if present (id_ed25519 preferred, then id_rsa)
# - Generates id_ed25519 with no passphrase if none exists
# - Installs public key on peer root authorized_keys (interactive password over SSH)
# - Enforces secure permissions on peer .ssh and authorized_keys

set -e

usage() {
    echo "Usage: $0 <alt-gw-host-or-ip> [port]"
    echo
    echo "Examples:"
    echo "  $0 10.220.1.3"
    echo "  $0 10.220.1.3 22"
    exit 1
}

log_info() {
    echo "[INFO] $1"
}

log_ok() {
    echo "[OK] $1"
}

log_err() {
    echo "[ERROR] $1" >&2
}

if [ "$(id -u)" -ne 0 ]; then
    log_err "This script must be run as root"
    exit 1
fi

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    usage
fi

PEER_HOST="$1"
PEER_PORT="${2:-22}"
SSH_DIR="/root/.ssh"
KEY_FILE=""

mkdir -p "${SSH_DIR}"
chmod 700 "${SSH_DIR}"

if [ -f "${SSH_DIR}/id_ed25519" ] && [ -f "${SSH_DIR}/id_ed25519.pub" ]; then
    KEY_FILE="${SSH_DIR}/id_ed25519"
    log_info "Using existing key pair: ${KEY_FILE}"
elif [ -f "${SSH_DIR}/id_rsa" ] && [ -f "${SSH_DIR}/id_rsa.pub" ]; then
    KEY_FILE="${SSH_DIR}/id_rsa"
    log_info "Using existing key pair: ${KEY_FILE}"
else
    KEY_FILE="${SSH_DIR}/id_ed25519"
    log_info "No root SSH key pair found; generating ${KEY_FILE} (no passphrase)"
    ssh-keygen -t ed25519 -f "${KEY_FILE}" -N ""
    chmod 600 "${KEY_FILE}"
    chmod 644 "${KEY_FILE}.pub"
    log_ok "Generated root key pair"
fi

PUB_KEY="$(cat "${KEY_FILE}.pub")"

if [ -z "${PUB_KEY}" ]; then
    log_err "Public key is empty: ${KEY_FILE}.pub"
    exit 1
fi

log_info "Installing public key on peer root@${PEER_HOST}:${PEER_PORT}"
log_info "You may be prompted for the peer root password"

printf '%s\n' "${PUB_KEY}" | ssh -p "${PEER_PORT}" -o BatchMode=no -o StrictHostKeyChecking=accept-new "root@${PEER_HOST}" \
    'mkdir -p /root/.ssh && chmod 700 /root/.ssh && touch /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys && cat >> /root/.ssh/authorized_keys && chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys'
log_ok "Public key piped to peer authorized_keys"

log_info "Verifying key-based SSH login to peer"
if ssh -p "${PEER_PORT}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "root@${PEER_HOST}" 'echo peer_key_auth_ok' >/dev/null 2>&1; then
    log_ok "Key-based SSH authentication verified"
else
    log_err "Key installation completed, but key-based auth verification failed"
    exit 1
fi

log_ok "Peer SSH key setup complete"

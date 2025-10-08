#!/bin/sh
# OPNsense HA IPv6 Integration Script
# Manages IPv6 services and NPTv6 rules based on CARP status

TAG="ha-ipv6-integration"
CARP_STATUS=$1

# Configuration
IPV6_STATE_FILE="/var/db/dhcp6c-pds.json"
IPV6_SCRIPTS_PATH="/usr/local/bin"
BACKUP_NODE_IP="192.168.105.2"

# Function to check if we're CARP master
is_carp_master() {
    case "${CARP_STATUS}" in
        "MASTER")
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Function to sync IPv6 state to backup
sync_ipv6_state() {
    if [ -f "${IPV6_STATE_FILE}" ] && [ -n "${BACKUP_NODE_IP}" ]; then
        logger -p info -t ${TAG} "Syncing IPv6 state to backup node"
        # Use scp or rsync to sync state (requires SSH keys)
        # scp "${IPV6_STATE_FILE}" "root@${BACKUP_NODE_IP}:${IPV6_STATE_FILE}" 2>/dev/null || true
    fi
}

# Function to enable IPv6 services and NPTv6 rules
enable_ipv6_services() {
    logger -p info -t ${TAG} "Enabling IPv6 services (CARP MASTER)"
    
    # Run prefix delegation update
    if [ -x "${IPV6_SCRIPTS_PATH}/dhcp6c-prefix-json" ]; then
        "${IPV6_SCRIPTS_PATH}/dhcp6c-prefix-json"
    fi
    
    # Apply NPTv6 rules
    if [ -x "${IPV6_SCRIPTS_PATH}/dhcp6c-checkset-nptv6" ]; then
        "${IPV6_SCRIPTS_PATH}/dhcp6c-checkset-nptv6"
    fi
    
    # Sync state to backup
    sync_ipv6_state
}

# Function to disable IPv6 NPTv6 rules but keep tracking
disable_ipv6_nptv6() {
    logger -p info -t ${TAG} "Disabling IPv6 NPTv6 rules (CARP BACKUP)"
    
    # Keep prefix tracking but disable NPTv6 application
    if [ -x "${IPV6_SCRIPTS_PATH}/dhcp6c-disable-nptv6" ]; then
        "${IPV6_SCRIPTS_PATH}/dhcp6c-disable-nptv6"
    fi
}

# Main execution
case "${CARP_STATUS}" in
    "MASTER")
        enable_ipv6_services
        ;;
    "BACKUP"|"INIT")
        disable_ipv6_nptv6
        ;;
    *)
        logger -p warning -t ${TAG} "Unknown CARP status: ${CARP_STATUS}"
        ;;
esac
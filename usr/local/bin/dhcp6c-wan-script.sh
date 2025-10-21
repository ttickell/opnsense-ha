#!/bin/sh

# OPNsense HA IPv6 DHCPv6 WAN Script - Standards Compliant Version
# Location: /usr/local/bin/dhcp6c-wan-script.sh
# Purpose: Handle DHCPv6 events for dual-WAN IPv6 configuration with HA support
#
# This script is called by dhcp6c when prefix delegations change
# It integrates with the HA system for IPv6 delegation management
#
# Hard link this script to interface-specific names:
# - /usr/local/bin/dhcp6c-wan-comcast.sh (for Comcast/igc1)
# - /usr/local/bin/dhcp6c-wan-att.sh (for AT&T/igc0)

TAG="dhcp6c-ha-script"
HA_IPV6_STATE_DIR="/var/db/ipv6-ha"
DELEGATION_STATE_FILE="${HA_IPV6_STATE_DIR}/delegations.json"

# Ensure state directory exists
mkdir -p "${HA_IPV6_STATE_DIR}"

# Determine interface from script name if not set
if [ -z "$INTERFACE" ]; then
    case $0 in
        */dhcp6c-wan-comcast.sh|*/igc1_dhcp6c.sh)
            export INTERFACE=igc1
            export PROVIDER="comcast"
        ;;
        */dhcp6c-wan-att.sh|*/igc0_dhcp6c.sh)
            export INTERFACE=igc0  
            export PROVIDER="att"
        ;;
        *)
            export INTERFACE=$(basename $0 | sed 's/_dhcp6c\.sh$//' | sed 's/dhcp6c-wan-\(.*\)\.sh$/\1/')
            export PROVIDER="${INTERFACE}"
        ;;
    esac    
fi

# Logging function
log_event() {
    local level=$1
    local message=$2
    echo "$(date '+%Y-%m-%d %H:%M:%S') [${level}] ${message}" >> /tmp/dhcp6c-ha.log
    logger -p "${level}" -t "${TAG}" "${message}"
}

log_event "info" "DHCPv6 event: ${REASON} on ${INTERFACE} (${PROVIDER})"

# Validate required environment
if [ -z "$INTERFACE" ]; then
    log_event "error" "INTERFACE is null - cannot proceed"
    exit 1
fi

# Log environment for debugging (first 10 lines to avoid log spam)
{
    echo "------------------------------------"
    echo "$(date) dhcp6c-ha-script start: ${REASON} on ${INTERFACE}"
    env | head -20
} >> /tmp/dhcp6c-ha.log

# Update delegation state file
update_delegation_state() {
    local temp_file="${DELEGATION_STATE_FILE}.tmp"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Create basic JSON structure if file doesn't exist
    if [ ! -f "${DELEGATION_STATE_FILE}" ]; then
        echo '{}' > "${DELEGATION_STATE_FILE}"
    fi
    
    # Update with current delegation info (simplified for now)
    # This will be enhanced in Phase 2 with full JSON processing
    {
        echo "{"
        echo "  \"${PROVIDER}\": {"
        echo "    \"interface\": \"${INTERFACE}\","
        echo "    \"last_reason\": \"${REASON}\","
        echo "    \"last_updated\": \"${timestamp}\","
        echo "    \"pdinfo\": \"${PDINFO:-}\","
        echo "    \"domain_servers\": \"${new_domain_name_servers:-}\","
        echo "    \"domain_name\": \"${new_domain_name:-}\""
        echo "  }"
        echo "}"
    } > "${temp_file}"
    
    # Atomic move to prevent corruption
    mv "${temp_file}" "${DELEGATION_STATE_FILE}" || {
        log_event "error" "Failed to update delegation state file"
        rm -f "${temp_file}"
    }
}

# Main DHCPv6 event handling
case $REASON in
SOLICIT|INFOREQ|REBIND|RENEW|REQUEST)
    log_event "info" "${REASON} on ${INTERFACE} - processing delegation"

    # Update delegation state
    update_delegation_state

    # Configure DNS servers
    ARGS=
    for NAMESERVER in ${new_domain_name_servers}; do
        ARGS="${ARGS} -a ${NAMESERVER}"
    done
    if [ -n "${ARGS}" ]; then
        /usr/local/sbin/ifctl -i ${INTERFACE} -6nd ${ARGS}
    fi

    # Configure domain search
    ARGS=
    for DOMAIN in ${new_domain_name}; do
        ARGS="${ARGS} -a ${DOMAIN}"
    done
    if [ -n "${ARGS}" ]; then
        /usr/local/sbin/ifctl -i ${INTERFACE} -6sd ${ARGS}
    fi

    # Configure prefix delegations
    ARGS=
    for PD in ${PDINFO}; do
        ARGS="${ARGS} -a ${PD}"
        log_event "info" "Received prefix delegation: ${PD}"
    done
    
    if [ ${REASON} != "RENEW" -a ${REASON} != "REBIND" ]; then
        # Cannot update since PDINFO may be incomplete in these cases
        # as each PD is being handled separately via the client side
        if [ -n "${ARGS}" ]; then
            /usr/local/sbin/ifctl -i ${INTERFACE} -6pd ${ARGS}
        fi
    fi

    # Trigger interface reconfiguration
    FORCE=
    if [ ${REASON} = "REQUEST" ]; then
        log_event "info" "${REASON} on ${INTERFACE} - forcing renewal"
        FORCE=force
    fi

    /usr/local/sbin/configctl -d interface newipv6 ${INTERFACE} ${FORCE}
    
    # Trigger HA IPv6 delegation processing (Phase 2 enhancement)
    if [ -x "/usr/local/bin/ipv6-ha-manager.py" ]; then
        /usr/local/bin/ipv6-ha-manager.py --process-delegation "${PROVIDER}" "${INTERFACE}" &
    fi
    ;;

EXIT|RELEASE)
    log_event "info" "${REASON} on ${INTERFACE} - clearing configuration"

    # Clear delegation state
    update_delegation_state
    
    # Clear interface configuration
    /usr/local/sbin/ifctl -i ${INTERFACE} -6nd
    /usr/local/sbin/ifctl -i ${INTERFACE} -6sd
    /usr/local/sbin/ifctl -i ${INTERFACE} -6pd

    /usr/local/sbin/configctl -d interface newipv6 ${INTERFACE}
    ;;

*)
    log_event "debug" "${REASON} on ${INTERFACE} - ignored (no action required)"
    ;;
esac

log_event "info" "DHCPv6 script completed for ${REASON} on ${INTERFACE}"
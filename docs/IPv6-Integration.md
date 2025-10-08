# IPv6 Integration Documentation

## Overview

This document describes how the OPNsense HA solution integrates with IPv6 dual-WAN configurations, particularly the [opnsense-ipv6](https://github.com/ttickell/opnsense-ipv6) project.

## Integration Points

### 1. CARP Event Handling

The HA script triggers IPv6-specific actions based on CARP state changes:

```bash
# In 00-ha-singleton script
trigger_ipv6_updates() {
    if [ "${ENABLE_IPV6}" != "yes" ]; then
        return
    fi
    
    # Trigger IPv6 prefix delegation updates
    if [ -x "/usr/local/bin/dhcp6c-ula-mapping.py" ]; then
        /usr/local/bin/dhcp6c-ula-mapping.py 2>/dev/null || true
    fi
    
    # Update CARP service status
    configctl interface update carp service_status 2>/dev/null || true
}
```

### 2. Service Coordination

IPv6 services are managed in coordination with CARP status:

- **MASTER**: Enable DHCPv6 client, apply NPTv6 rules, start router advertisements
- **BACKUP**: Disable NPTv6 rules, maintain prefix tracking, stop active services

### 3. State Synchronization

IPv6 prefix delegation state is synchronized between HA nodes:

```bash
# Sync IPv6 state file between nodes
sync_ipv6_state() {
    if [ -f "/var/db/dhcp6c-pds.json" ]; then
        # Sync to backup node (requires SSH key setup)
        rsync /var/db/dhcp6c-pds.json backup-node:/var/db/
    fi
}
```

## Required Modifications to IPv6 Scripts

### 1. CARP-Aware NPTv6 Management

Modify `dhcp6c-checkset-nptv6` to only apply rules on MASTER:

```python
def is_carp_master():
    """Check if any CARP interfaces are in MASTER state"""
    try:
        result = subprocess.run(['ifconfig', '-a'], 
                              capture_output=True, text=True)
        return 'carp:' in result.stdout and 'MASTER' in result.stdout
    except:
        return False

# In main execution:
if is_carp_master():
    # Apply NPTv6 rules
    apply_nptv6_rules()
else:
    # Only track state, don't apply rules
    track_prefix_state()
```

### 2. DHCPv6 Hook Script Modifications

Update DHCPv6 hook scripts to be HA-aware:

```bash
# In dhcp6c_wan_custom.sh
case $REASON in
SOLICIT|REQUEST)
    # Only process on MASTER node
    if is_carp_master; then
        # Normal processing
        /usr/local/sbin/ifctl -i ${INTERFACE} -6pd ${ARGS}
        # Trigger HA IPv6 integration
        /usr/local/bin/ha-ipv6-integration.sh MASTER
    fi
    ;;
esac
```

### 3. Configuration File Updates

Add HA-specific settings to `checkset-nptv6.yml`:

```yaml
# Existing configuration...

# HA-specific settings
ha:
  enabled: true
  sync_state: true
  backup_node_ip: "192.168.105.2"
  apply_rules_only_on_master: true
  state_sync_method: "rsync"  # or "scp"
```

## Installation Integration

### 1. Combined Setup Script

Create a combined installer that sets up both HA and IPv6:

```bash
#!/bin/sh
# Combined HA + IPv6 installer

# Install HA components
./setup-firewall "vtnet1 vtnet2"

# Install IPv6 components (if repository available)
if git clone https://github.com/ttickell/opnsense-ipv6.git; then
    cd opnsense-ipv6
    # Run IPv6 migration to standards
    ./migrate-to-standards.sh
    cd ..
fi

# Configure integration
configure_ipv6_ha_integration
```

### 2. File Migration Requirements

Files that need to be moved to persistent locations:

| Current Location | Target Location | Purpose |
|-----------------|----------------|---------|
| `/var/etc/dhcp6c.conf.custom` | `/usr/local/etc/dhcp6c.conf.custom` | DHCPv6 configuration |
| `/var/etc/dhcp6c_wan_custom.sh` | `/usr/local/bin/dhcp6c_wan_custom.sh` | DHCPv6 hook script |
| `/var/etc/dhcp6c-prefix-json` | `/usr/local/bin/dhcp6c-prefix-json` | Prefix tracking |
| `/var/etc/dhcp6c-checkset-nptv6` | `/usr/local/bin/dhcp6c-checkset-nptv6` | NPTv6 management |

## Service Integration

### 1. Service Dependencies

Ensure proper startup order:

```bash
# 1. Start DHCPv6 client
configctl dhcp6c start

# 2. Wait for prefix delegation
wait_for_prefixes() {
    local timeout=30
    local count=0
    while [ $count -lt $timeout ]; do
        if [ -f "/var/db/dhcp6c-pds.json" ]; then
            local active=$(jq '.summary.active_prefix_delegations' /var/db/dhcp6c-pds.json)
            if [ "$active" -gt 0 ]; then
                return 0
            fi
        fi
        sleep 1
        count=$((count + 1))
    done
    return 1
}

# 3. Apply NPTv6 rules
if wait_for_prefixes; then
    /usr/local/bin/dhcp6c-checkset-nptv6
fi

# 4. Start router advertisements
configctl radvd start
```

### 2. Health Monitoring

Add IPv6-specific health checks:

```bash
# Check IPv6 prefix delegation status
check_ipv6_health() {
    # Check if prefix file exists and is recent
    if [ -f "/var/db/dhcp6c-pds.json" ]; then
        local age=$(( $(date +%s) - $(stat -c %Y /var/db/dhcp6c-pds.json) ))
        if [ $age -lt 3600 ]; then  # Less than 1 hour old
            return 0
        fi
    fi
    return 1
}
```

## Configuration Examples

### 1. Complete HA Configuration

```bash
# /usr/local/etc/ha-singleton.conf
WAN_INTS="vtnet1 vtnet2"
SERVICES="rtsold dhcp6c radvd"
ALT_DEFROUTE_IPV4="192.168.105.2"
ALT_DEFROUTE_IPV6="fd03:17ac:e938:10::2"
ENABLE_IPV6="yes"
ENABLE_SERVICE_MANAGEMENT="yes"
ENABLE_ROUTE_MANAGEMENT="yes"
IPV6_SCRIPT_PATH="/usr/local/bin"
SYNC_IPV6_STATE="yes"
DEBUG="no"
```

### 2. IPv6 NPTv6 Configuration with HA

```yaml
# /usr/local/etc/checkset-nptv6.yml
api-base: "https://localhost/api"
api-key: "your-api-key"
api-secret: "your-api-secret"
dhcp6c-pds-file: "/var/db/dhcp6c-pds.json"
ipv6-ula: "fd00::/7"

lan-interfaces:
  LAN:
    interface: "igc2"
    pd-id: 2
    sla-id: 0
    prefix-len: 0
  GUEST:
    interface: "igc3" 
    pd-id: 3
    sla-id: 0
    prefix-len: 0

# HA-specific settings
ha:
  enabled: true
  sync_state: true
  backup_node_ip: "192.168.105.2"
  apply_rules_only_on_master: true
```

## Troubleshooting

### 1. IPv6 Services Not Starting

```bash
# Check CARP status
ifconfig | grep carp

# Check IPv6 service logs
tail -f /var/log/system.log | grep -E "(dhcp6c|rtsold|radvd)"

# Check prefix delegation status
cat /var/db/dhcp6c-pds.json | jq .
```

### 2. NPTv6 Rules Not Applied

```bash
# Check if rules are being applied only on master
pfctl -s nat | grep inet6

# Check script execution
tail -f /var/log/system.log | grep dhcp6c-checkset-nptv6

# Verify CARP master status
sysctl net.inet.carp.demotion
```

### 3. State Synchronization Issues

```bash
# Check SSH connectivity to backup node
ssh root@backup-node-ip "echo test"

# Check file sync status
ls -la /var/db/dhcp6c-pds.json

# Manual sync test
rsync /var/db/dhcp6c-pds.json backup-node:/var/db/
```

## Future Enhancements

1. **Automatic IPv6 script integration**: Detect and integrate with IPv6 scripts automatically
2. **Real-time state monitoring**: Monitor IPv6 state changes and sync immediately
3. **Advanced health checking**: Include IPv6 connectivity tests in CARP demotion logic
4. **GUI integration**: Provide web interface for IPv6 HA configuration
5. **Backup validation**: Ensure backup node can take over IPv6 services seamlessly
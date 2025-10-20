# DHCP Lease Clearing Enhancement (v2.8)

## Summary
Added automatic DHCP lease clearing to the HA CARP transition script to prevent stale lease state conflicts during failover operations.

## Problem Solved
- **Geographic Lease Conflicts**: VM firewalls with old lease data from different locations (e.g., GA vs FL)
- **Stale State Issues**: DHCP DISCOVER vs REQUEST message type mismatches  
- **Temporal Conflicts**: Old lease information preventing new lease acquisition
- **Manual Power Cycling**: Eliminates need to power cycle cable modems for VM transitions

## Implementation

### New Function: `clear_dhcp_leases()`
- **Location**: `/usr/local/etc/rc.syshook.d/carp/00-ha-singleton`
- **Purpose**: Clean DHCP state before interface reconfiguration
- **Actions**:
  1. Stop DHCP client process gracefully
  2. Remove lease files (`/var/db/dhclient.leases.*`)
  3. Clear stale IP addresses from interface
  4. Force fresh DHCP negotiation

### Configuration Control
- **Setting**: `ENABLE_DHCP_LEASE_CLEARING="yes"`
- **Default**: Enabled (recommended for cable internet)
- **Disable**: Set to "no" in `ha-singleton.conf` if issues arise

### Trigger Points
1. **MASTER Transition (Interface DOWN)**: Clear leases before `rc.configure_interface`
2. **MASTER Transition (Interface UP)**: Clear leases + trigger `configctl interface newip`

## Expected Behavior

### Before (v2.7):
```
VM Firewall: DHCP Discover for c-24-129-124-235.hsd1.fl.comcast.net (old FL lease)
Comcast:     No response (geographic mismatch)
Result:      Manual cable modem power cycle required
```

### After (v2.8):
```
CARP MASTER: Clear stale lease files
VM Firewall: Fresh DHCP Discover (no requested IP)
Comcast:     DHCP Offer for current geographic area  
Result:      Automatic lease acquisition, no power cycle needed
```

## Configuration Example

```bash
# In /usr/local/etc/ha-singleton.conf
ENABLE_DHCP_LEASE_CLEARING="yes"    # Recommended for cable internet
ENABLE_INTERFACE_RECONFIGURE="yes"  # Required for lease clearing to work
```

## Logging

Look for these log messages in `/var/log/system.log`:
```
syshook-carp-ha-singleton: Clearing DHCP leases for vtnet5 (wan2) to prevent stale state
syshook-carp-ha-singleton: Stopping DHCP client for wan2 (PID: 1234)
syshook-carp-ha-singleton: DHCP lease cleanup completed for vtnet5
```

## Compatibility
- **Safe Default**: Clearing leases is generally safe and prevents conflicts
- **Rollback**: Can be disabled via configuration if issues arise
- **Static IPs**: No effect on static IP configurations
- **Multiple WANs**: Works with multi-WAN setups automatically

## Related Issues Fixed
- Resolves geographic DHCP lease conflicts identified in packet analysis
- Eliminates need for manual cable modem power cycling
- Prevents DHCP message type mismatches (DISCOVER vs REQUEST)
- Ensures consistent behavior across physical/virtual firewall transitions

This enhancement makes HA transitions with cable internet providers (Comcast/Xfinity) fully automatic and reliable.
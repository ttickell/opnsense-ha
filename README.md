# OPNsense High Availability (HA) Project

A comprehensive solution for OPNsense High Availability setup with CARP failover, IPv6 support, and service management.

## Project Overview

This project provides automated failover management for OPNsense firewalls with support for any number of WAN interfaces, IPv4 and IPv6 support. It includes intelligent interface management, service control, and route management based on CARP status.

## Features

### ✅ Core HA Functionality
- **CARP-based failover**: Automatic interface management based on CARP master/backup status
- **CARP stability fixes**: Prevents flapping during primary failures with PFSYNC tuning and conditional IPv6 services
- **Service management**: Intelligent start/stop of IPv6 services (`rtsold`, `dhcp6c`, `radvd`) with state-aware configuration
- **Route management**: Backup routing through alternate gateways with automatic cleanup
- **DHCP lease renewal**: Automatic DHCP state restoration during failover for complete connectivity
- **Health monitoring**: CARP service status integration with connectivity checks

### ✅ Advanced Capabilities
- **Configuration-driven**: Flexible configuration file for easy customization
- **Locking mechanism**: Prevents concurrent script execution
- **Comprehensive logging**: Structured logging with appropriate severity levels
- **Error handling**: Robust error handling with fallback mechanisms
- **IPv6 integration**: Ready for integration with IPv6 prefix delegation and NPTv6

### ✅ Installation & Maintenance
- **Automated installer**: Comprehensive setup script with GitHub integration
- **Backup & restore**: Automatic backup of existing configurations
- **Validation checks**: Post-installation validation and health checks
- **Standards compliance**: Follows OPNsense development guidelines

## WAN Interface Prerequisites

> ⚠️ **These requirements must be satisfied before installation. Skipping them produces silent failures — the scripts run normally but failover will not work correctly in production.**

The HA solution depends on the BACKUP node being able to assume the active WAN identity seamlessly when it transitions to MASTER. This requires the following conditions on every WAN interface on both nodes.

### 1. MAC Address Cloning (Required)

Both firewalls' WAN interfaces **must present the same MAC address** to the upstream network.

**Why**: ISPs and upstream routers typically bind DHCP leases to MAC addresses. If the BACKUP node comes up with a different MAC after failover, the upstream router issues a new lease — or refuses to issue one at all until the old lease expires. This causes a connectivity gap of minutes to hours.

**How to configure in OPNsense GUI**:
1. Go to `Interfaces → [WAN interface name]`
2. Scroll to **MAC address** field
3. Enter the MAC address of the **primary firewall's** WAN interface on **both nodes**
4. Save and apply
5. Repeat for every WAN interface (WAN2, WAN3, etc.)

**Verify**:
```bash
ifconfig <wan_device> | grep ether
# Both nodes must show identical output
```

**For multiple WAN interfaces**: Each WAN interface pair (primary WAN ↔ secondary WAN) must share a MAC independently.

### 2. Matching DHCPv6 DUID (Required for IPv6)

Both firewalls **must use the same DHCP Unique Identifier (DUID)** for IPv6 prefix delegation.

**Why**: DHCPv6 servers bind prefix delegations to the DUID, not the MAC address. If the BACKUP node presents a different DUID on failover, the DHCPv6 server will not hand over the existing prefix delegation — the BACKUP node will either get a different prefix or none at all, breaking all downstream IPv6 addressing that depends on the delegated prefix.

**How to configure**:
1. Note the DUID from the primary firewall:
   ```bash
   # On primary firewall
   cat /var/db/dhcp6c_duid
   # or
   cat /var/db/dhcpv6_duid
   ```
2. Copy the exact DUID value to the secondary firewall:
   ```bash
   # On secondary firewall (as root)
   echo -n '<duid-value-from-primary>' > /var/db/dhcp6c_duid
   ```
3. In OPNsense GUI: `Interfaces → [WAN] → DHCPv6 client → DUID` — set the same value on both nodes.

**Verify**:
```bash
# Both nodes must return identical output
cat /var/db/dhcp6c_duid
```

### 3. DHCP-Based WAN Addressing (Required)

WAN interfaces must use **DHCP** (not static) for IPv4 address assignment.

**Why**: The DHCP renewal workflow (`configctl interface reconfigure` / `configctl interface newip`) that restores routes during a MASTER transition only applies to DHCP interfaces. Static WAN interfaces will not trigger route restoration and will require manual intervention after failover.

**How to configure**: `Interfaces → [WAN] → IPv4 Configuration Type → DHCP`

### 4. No CARP VIPs on WAN Interfaces

Do **not** place CARP Virtual IPs on WAN interfaces. WAN failover is managed entirely by the script (interface up/down + DHCP renewal), not by CARP VIPs.

**CARP VIPs belong only on LAN/internal interfaces** where clients need a stable shared IP.

### 5. WAN Interface Naming Convention

The script auto-discovers WAN interfaces at startup by parsing `/conf/config.xml`. No manual configuration is required. Detection rules:

- The `<wan>` interface element is always treated as a WAN.
- Any `<optN>` element whose `<descr>` is `WAN2`–`WAN9` (case-insensitive) is treated as an additional WAN.

For each discovered WAN the script derives three values:

| Field | Source | Used for |
|---|---|---|
| OPNsense name (`wan`, `opt1`) | XML element name | `configctl`, `rc.configure_interface` |
| Device name (`vtnet0`, `vtnet1`) | `<if>` child | `ifconfig up/down` |
| Human label (`wan`, `wan2`) | `<descr>` or element name | config file paths, log messages |

To use a second WAN, give its OPNsense interface the description `WAN2` in **Interfaces → [optN] → Description**. The script will pick it up automatically on the next CARP event.

### WAN Prerequisites Checklist

Before running `setup-firewall`, confirm all of the following:

- [ ] Both nodes: WAN MAC address(es) cloned to match primary
- [ ] Both nodes: DHCPv6 DUID matches (if using IPv6 prefix delegation)
- [ ] Both nodes: WAN interface(s) set to DHCP for IPv4
- [ ] Both nodes: No CARP VIPs assigned to WAN interfaces
- [ ] Second WAN interface (if present): `<descr>WAN2</descr>` set in OPNsense GUI

## Physical Deployment Topology

### Design Principles

The physical plant is designed for survivability by someone who may not be deeply familiar with the configuration — including remote hardware replacement when you are not on-site:

1. **Direct-cable operation must always work.** Port 1 → ISP modem. Port 2 → LAN switch. A replacement firewall cabled identically and restored from config must be online within minutes, with no switch reconfiguration required.
2. **The primary LAN (VLAN 1 / untagged) must just work.** The internal network runs on untagged Ethernet so it survives switch replacements, generic switches, and any scenario where VLAN trunking is not configured. Any device plugged into the LAN switch must get connectivity without VLAN knowledge.
3. **WAN isolation via VLANs is required.** Each ISP modem connection is isolated to its own dedicated VLAN segment. The only members of each WAN VLAN are the ISP modem and the firewall interface serving that WAN. This prevents cross-ISP traffic and eliminates address conflicts between providers.
4. **Physical ports are clearly labeled.** Ports and cables must be labeled by function (WAN1/ISP-A, WAN2/ISP-B, LAN, PFSYNC) to enable a non-expert to complete hardware replacement by following labels alone.

### Current Production Physical Plant

#### Primary Firewall (Physical Hardware)

The primary node is a physical OPNsense appliance with dedicated interface ports per function:

```
┌─────────────────────────────────────────────────────┐
│  Physical Firewall (Primary)                        │
│                                                     │
│  igc0 ──► [isolated switch VLAN: ISP-A modem only] ├─► Xfinity modem
│  igc1 ──► [isolated switch VLAN: ISP-B modem only] ├─► AT&T modem
│  lagg0 ─► [untagged VLAN 1 / LAN switch]           ├─► Internal switch
│  vlan0.110 ────────────────────────────────────────► PFSYNC to secondary
└─────────────────────────────────────────────────────┘
```

- WAN interfaces connect to **physical switch ports configured in isolated, single-purpose VLANs** (only the modem and the firewall port are members).
- The LAN interface is on **untagged VLAN 1** — no VLAN configuration required on the LAN switch for basic connectivity.
- WAN VLAN membership is enforced at the switch, so the firewall's physical ports behave like direct connections to each modem.

#### Secondary Firewall (Proxmox VM)

The secondary node runs as a virtual machine on a Proxmox host. It cannot have dedicated physical ports to each modem — instead, the Proxmox host carries all WAN VLANs on a single **tagged trunk NIC**, and the VM sees them as VLAN sub-interfaces:

```
┌─────────────────────────────────────────────────────┐
│  Proxmox Host                                       │
│                                                     │
│  em0 (trunk) ─┬─ VLAN tag ISP-A ──────────────────►┐│
│               ├─ VLAN tag ISP-B ──────────────────►││  Virtual
│               └─ VLAN tag PFSYNC ─────────────────►││  Firewall
│                                                     ││  (Secondary)
│  vtnet0 (untagged LAN) ───────────────────────────►┘│
└─────────────────────────────────────────────────────┘
```

- WAN interfaces are **VLAN sub-interfaces on a trunk** (e.g., `vtnet4` and `vtnet5` as presented inside the VM).
- The LAN interface is untagged, same principle as the physical node.
- VLAN tagging for the WAN interfaces is handled by the Proxmox virtual switch / bridge configuration.

### Asymmetry Between Nodes

| | Primary (Physical) | Secondary (Proxmox VM) |
|---|---|---|
| WAN connectivity | Physical ports in isolated switch VLANs | VLAN sub-interfaces on trunk NIC |
| LAN connectivity | Physical port, untagged | Virtual NIC, untagged |
| PFSYNC | VLAN sub-interface | VLAN sub-interface on trunk |
| WAN device names | `igc0`, `igc1` | `vtnet4`, `vtnet5` |

This asymmetry is expected and supported. Each node has its own `ha-singleton.conf` with the correct device names for its physical/virtual environment.

### Hardware Replacement Guidance

If the primary firewall must be replaced while you are remote:

1. Install OPNsense on the replacement hardware.
2. Cable by port label: **WAN1 → Xfinity modem**, **WAN2 → AT&T modem**, **LAN → switch**, **PFSYNC → Proxmox host**.
3. Restore from config backup (or manually apply interface assignments to match labels).
4. Set MAC address cloning on both WAN interfaces to match the original primary (see [WAN Interface Prerequisites](#wan-interface-prerequisites)).
5. The Proxmox secondary is already active as MASTER; it will remain MASTER until the primary returns, at which point CARP non-preemptive behavior keeps the secondary active until an explicit failback.

## Quick Start

### Automated Installation with setup-firewall

The `setup-firewall` script provides comprehensive automated installation of the HA solution with intelligent WAN interface detection and configuration.

#### Safety Behavior (March 2026)

To prevent first-install route poisoning, newly generated `/usr/local/etc/ha-singleton.conf` files now install with:

```bash
ENABLE_ROUTE_MANAGEMENT="no"
```

You must explicitly set node-specific peer routes before enabling route management:

- Primary node: `ALT_DEFROUTE_IPV4` / `ALT_DEFROUTE_IPV6` must point to secondary LAN IPs
- Secondary node: `ALT_DEFROUTE_IPV4` / `ALT_DEFROUTE_IPV6` must point to primary LAN IPs

Then enable:

```bash
ENABLE_ROUTE_MANAGEMENT="yes"
```

This avoids incorrect backup default routes on fresh systems.

#### Basic Installation

```bash
# Download and run with defaults (vtnet1, main branch)
curl -sSL https://raw.githubusercontent.com/ttickell/opnsense-ha/main/setup-firewall | sh

# Or download and run locally
wget https://raw.githubusercontent.com/ttickell/opnsense-ha/main/setup-firewall
chmod +x setup-firewall
./setup-firewall
```

#### Advanced Installation Options

```bash
# Single WAN interface
./setup-firewall vtnet1

# Multiple WAN interfaces
./setup-firewall "vtnet1 vtnet2"

# Specific git branch
./setup-firewall "vtnet1 vtnet2" ghcwork

# Clean existing installation first
./setup-firewall --cleanup "vtnet1 vtnet2"

# Clean and install from development branch
./setup-firewall --cleanup "vtnet1 vtnet2" develop
```

#### Setup Script Usage

```bash
Usage: setup-firewall [OPTIONS] [WAN_INTERFACES] [BRANCH_NAME]

Options:
  --cleanup, -c         Clean existing HA installation before installing
  --help, -h           Show help message

Parameters:
  WAN_INTERFACES    Space-delimited list of WAN interface names (default: vtnet1)
  BRANCH_NAME       Git branch to use for installation (default: main)

Examples:
  ./setup-firewall                          # Use defaults (vtnet1, main)
  ./setup-firewall --cleanup vtnet1         # Clean first, single WAN
  ./setup-firewall "vtnet1 vtnet2"          # Multiple WAN interfaces
  ./setup-firewall vtnet1 ghcwork           # Specific branch
  ./setup-firewall --cleanup "vtnet1 vtnet2" develop  # Full custom install
```

#### What the Setup Script Does

1. **Environment Validation**:
   - Verifies running on OPNsense system
   - Checks for root privileges
   - Validates branch names and interface parameters

2. **Backup Creation**:
   - Creates timestamped backup in `/tmp/ha-setup-backup-YYYYMMDD-HHMMSS/`
   - Backs up existing configuration files
   - Preserves current settings for rollback

3. **Installation Process**:
   - Installs git if not present
   - Clones repository from specified branch
   - Creates necessary directory structure
   - Installs and configures all components

4. **File Installation**:
   - `/usr/local/etc/rc.syshook.d/carp/00-ha-singleton` - Main CARP hook script
   - `/usr/local/etc/ha-singleton.conf` - Configuration file (customized for your WANs)
   - `/usr/local/bin/ha-ipv6-integration.sh` - IPv6 integration utilities
   - `/usr/local/etc/rc.carp_service_status.d/wan_connectivity` - Health monitoring

5. **Configuration**:
   - Automatically substitutes WAN interface names in configuration
   - Sets appropriate file permissions
   - Creates universal configuration template
   - Installs with route management disabled by default until peer backup routes are customized

6. **Validation**:
   - Verifies all required files are installed
   - Checks file permissions and executability
   - Confirms installation integrity

#### Post-Installation Verification

After running the setup script, verify the installation:

**Manual confirmation — LAN DHCP gateway option must be the CARP VIP:**

The LAN DHCP server must advertise the CARP VIP as the default gateway, not the node's own LAN IP. If it advertises the node's real IP (e.g. `10.x.x.2`), LAN clients will not recover after failover until their lease expires — because the old gateway IP ends up on the BACKUP node with WANs down.

Verify from a LAN client after obtaining a DHCP lease:
```bash
ip route show default   # Linux
route print             # Windows
netstat -rn | grep default  # macOS / FreeBSD
```
The default gateway must be the CARP VIP. If it is not, correct the `router` option in the DHCP server (Services → DHCPv4 → [LAN] → Gateway) and renew client leases.

```bash
# Check installed files
ls -la /usr/local/etc/rc.syshook.d/carp/00-ha-singleton
ls -la /usr/local/etc/ha-singleton.conf

# Verify WAN auto-discovery works (run directly on the firewall)
sh /tmp/test-wan-discovery.sh

# Test script syntax
sh -n /usr/local/etc/rc.syshook.d/carp/00-ha-singleton

# Check backup was created
ls -la /tmp/ha-setup-backup-*
```

#### Setup Script Output

The installer provides detailed feedback:

```
================================================
OPNsense HA Singleton Setup Script v2.1
================================================

[INFO] Detected OPNsense version: 25.7
[INFO] WAN Interfaces: vtnet1 vtnet2
[INFO] Git Branch: main
[INFO] Cleanup First: false

[INFO] Creating backup in /tmp/ha-setup-backup-20241016-143022
[INFO] Installing from GitHub repository...
[SUCCESS] Installed CARP hook script
[SUCCESS] Installed universal configuration file
[SUCCESS] Installation validation passed

Next steps:
1. Review and customize /usr/local/etc/ha-singleton.conf
2. Configure CARP VIPs in the OPNsense GUI
3. Set up HA synchronization settings
4. Test failover functionality
```

### Manual Installation (Alternative)

```bash
# Clone the repository
git clone https://github.com/ttickell/opnsense-ha.git
cd opnsense-ha

# Run the installer with your WAN interfaces
./setup-firewall "vtnet1 vtnet2"
```

## Key Features

### DHCP Lease Renewal & Interface Reconfiguration

**New in v2.6**: The HA solution now includes automatic DHCP lease renewal during failover to ensure complete connectivity restoration.

#### How It Works

When a firewall transitions from BACKUP to MASTER state:

1. **Interface State Management**: WAN interfaces are brought UP with proper state verification
2. **DHCP State Restoration**: Uses OPNsense's `configctl` system to trigger DHCP renewal:
   - `configctl interface reconfigure <interface>` - Renews DHCP lease and restores routes
   - `configctl interface newip <interface>` - Triggers IP address reconfiguration
3. **Route Table Cleanup**: Removes stale default routes before establishing new ones
4. **Service Coordination**: Ensures IPv6 services restart with fresh network state

#### Configuration

Enable DHCP lease renewal in your configuration:

```bash
# Enable interface reconfiguration for DHCP renewal
ENABLE_INTERFACE_RECONFIGURE="yes"
```

WAN interface discovery is automatic — no `WAN_INTERFACE_MAP` or `WAN_INTS` needed.

#### Benefits

- **Complete Failover**: Both IPv4 and IPv6 connectivity restored automatically
- **No Manual Intervention**: DHCP leases renewed without user action
- **Route Synchronization**: Default routes properly established from DHCP server
- **State Consistency**: Network state matches what DHCP server expects

## Configuration

### Main Configuration File: `/usr/local/etc/ha-singleton.conf`

```bash
# Services to manage
SERVICES="rtsold dhcp6c radvd"

# Backup routes
ALT_DEFROUTE_IPV4="192.168.105.2"
ALT_DEFROUTE_IPV6="fd03:17ac:e938:10::2"

# Feature toggles
ENABLE_IPV6="yes"
ENABLE_SERVICE_MANAGEMENT="yes"
ENABLE_ROUTE_MANAGEMENT="yes"
ENABLE_INTERFACE_RECONFIGURE="yes"  # Enable DHCP lease renewal
DEBUG="no"
```

### CARP Configuration in OPNsense GUI

1. **Configure Virtual IPs**:
   - Go to `Interfaces → Virtual IPs`
   - Create CARP VIPs for each network segment
   - Set appropriate VHID and passwords

2. **High Availability Settings**:
   - Go to `System → High Availability → Settings`
   - Configure synchronization settings
   - Enable pfSync if desired

3. **Interface Configuration**:
   - Ensure both firewalls have identical interface assignments
   - Configure physical IP addresses on each node

## File Structure

```
/usr/local/etc/
├── rc.syshook.d/carp/
│   └── 00-ha-singleton              # Main CARP hook script
├── rc.carp_service_status.d/
│   └── wan_connectivity             # WAN connectivity monitoring
└── ha-singleton.conf                # Configuration file

/usr/local/bin/
└── ha-ipv6-integration.sh           # IPv6 integration script
```

## Testing & Validation

### Failure Condition Tests

| Test Scenario | Expected Result | Status |
|---------------|----------------|---------|
| Primary power failure | Secondary takes over < 30s | ✅ Tested |
| WAN link failure | Failover to backup WAN < 30s | ✅ Tested |
| Service failure | Backup routes activated | ✅ Tested |
| Switch failure | Minimal network interruption | 🔄 Testing |
| IPv6 prefix changes | NPTv6 rules updated | 🔄 Testing |

### Manual Testing

```bash
# Test CARP status
ifconfig | grep carp

# Test interface management
tail -f /var/log/system.log | grep syshook-carp-ha-singleton

# Simulate failover
ifconfig carp0 down  # On master node

# Check service status
service rtsold status
service dhcp6c status
service radvd status
```

## Integration with IPv6 Project

This HA solution is designed to work with the [opnsense-ipv6](https://github.com/ttickell/opnsense-ipv6) project:

- **Prefix delegation management**: Automatic prefix tracking and NPTv6 rule updates
- **State synchronization**: IPv6 state synchronized between HA nodes
- **Service coordination**: IPv6 services managed based on CARP status

## Troubleshooting

### Setup Script Issues

1. **Installation fails**:
   ```bash
   # Check internet connectivity
   ping -c 3 github.com
   
   # Verify OPNsense detection
   cat /usr/local/opnsense/version/opnsense
   
   # Try with cleanup flag
   ./setup-firewall --cleanup "vtnet1 vtnet2"
   ```

2. **Git clone failures**:
   ```bash
   # Install git manually
   pkg install -y git
   
   # Try specific branch
   ./setup-firewall "vtnet1 vtnet2" main
   
   # Check available branches
   git ls-remote --heads https://github.com/ttickell/opnsense-ha.git
   ```

3. **Permission errors**:
   ```bash
   # Ensure running as root
   whoami
   
   # Fix permissions manually if needed
   chmod 755 /usr/local/etc/rc.syshook.d/carp/00-ha-singleton
   ```

4. **Configuration not applied**:
   ```bash
   # Manually edit if needed
   vi /usr/local/etc/ha-singleton.conf
   ```

5. **Rollback installation**:
   ```bash
   # Find your backup
   ls -la /tmp/ha-setup-backup-*
   
   # Restore from backup
   BACKUP_DIR="/tmp/ha-setup-backup-YYYYMMDD-HHMMSS"
   cp -r ${BACKUP_DIR}/usr/local/etc/* /usr/local/etc/
   ```

### Runtime Issues

1. **Script not executing**:
   ```bash
   # Check permissions
   ls -la /usr/local/etc/rc.syshook.d/carp/00-ha-singleton
   
   # Check logs
   tail -f /var/log/system.log | grep carp
   ```

2. **CARP flapping issues**:
   ```bash
   # Check PFSYNC demotion factor (should be 0)
   sysctl net.pfsync.carp_demotion_factor
   
   # Monitor CARP state transitions
   tail -f /var/log/system.log | grep -E "(carp|CARP)"
   
   # Check for interface reload events
   tail -f /var/log/system.log | grep -E "(rtsold|interface.*up)"
   ```

3. **Services not starting/stopping**:
   ```bash
   # Enable debug mode
   echo 'DEBUG="yes"' >> /usr/local/etc/ha-singleton.conf
   
   # Check service status
   service rtsold status
   
   # Verify conditional rtsold configuration
   ps aux | grep rtsold
   ```

4. **Route management issues**:
   ```bash
   # Check current routes
   netstat -rn | grep default
   
   # Test backup connectivity
   ping -I vtnet1 8.8.8.8
   ```

5. **DHCP lease renewal issues**:
   ```bash
   # Check if interface reconfiguration is enabled
   grep ENABLE_INTERFACE_RECONFIGURE /usr/local/etc/ha-singleton.conf
   
   # Verify WAN auto-discovery resolves interfaces correctly
   sh /tmp/test-wan-discovery.sh
   
   # Test configctl commands manually (use OPNsense interface name from discovery)
   configctl interface reconfigure wan
   configctl interface newip wan
   ```

### Log Locations

- **System logs**: `/var/log/system.log`
- **CARP events**: Filter for `syshook-carp-ha-singleton`
- **Service logs**: Check individual service logs

## Architecture

The solution follows OPNsense development best practices:

- **Syshook integration**: Uses OPNsense's native CARP event system
- **Configuration management**: Integrates with OPNsense's configctl where possible
- **Service management**: Uses standard OPNsense service management APIs
- **Logging**: Follows syslog standards with appropriate severity levels

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test your changes thoroughly
4. Submit a pull request

## Version History

### v2.6 (Current)
- **DHCP Lease Renewal**: Complete failover solution with automatic DHCP state restoration
  - Implements `configctl interface reconfigure/newip` for DHCP lease renewal
  - Adds WAN interface auto-discovery from `/conf/config.xml` (eliminates `WAN_INTS`/`WAN_INTERFACE_MAP` manual config)
  - Ensures both IPv4 and IPv6 connectivity restored during failover
  - Resolves "route already in table" errors with enhanced route management
- **Enhanced Interface Management**: Robust interface UP/DOWN logic with configctl integration
- **Improved Route Handling**: Removes existing default routes before adding backup routes
- **Configuration Validation**: Better error handling and fallback mechanisms

### v2.1 (Previous)
- **CARP flapping fixes**: Resolves CARP instability during primary failures
  - Disables PFSYNC CARP demotion factor to prevent automatic demotion during bulk sync failures
  - Implements conditional rtsold configuration to prevent interface reloads that reset CARP state
  - Maintains IPv6 functionality while ensuring stable failover behavior
- Enhanced logging for troubleshooting CARP state transitions
- Improved routing stability during failover scenarios

### v2.0 (Previous)
- Complete rewrite with improved error handling
- Configuration file support
- IPv6 integration hooks
- Comprehensive installer
- Health monitoring and validation

### v1.0 (Legacy)
- Basic CARP failover functionality
- Simple interface and service management

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: Report bugs via GitHub Issues
- **Documentation**: See project wiki for detailed guides
- **Community**: Join discussions in the project discussions section

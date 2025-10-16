# OPNsense High Availability (HA) Project

A comprehensive solution for OPNsense High Availability setup with CARP failover, IPv6 support, and service management.

## Project Overview

This project provides automated failover management for OPNsense firewalls with support for any number of WAN interfaces, IPv4 and IPv6 support. It includes intelligent interface management, service control, and route management based on CARP status.

## Features

### ✅ Core HA Functionality
- **CARP-based failover**: Automatic interface management based on CARP master/backup status
- **Service management**: Intelligent start/stop of IPv6 services (`rtsold`, `dhcp6c`, `radvd`)
- **Route management**: Backup routing through alternate gateways
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

## Quick Start

### Automated Installation with setup-firewall

The `setup-firewall` script provides comprehensive automated installation of the HA solution with intelligent WAN interface detection and configuration.

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

6. **Validation**:
   - Verifies all required files are installed
   - Checks file permissions and executability
   - Confirms installation integrity

#### Post-Installation Verification

After running the setup script, verify the installation:

```bash
# Check installed files
ls -la /usr/local/etc/rc.syshook.d/carp/00-ha-singleton
ls -la /usr/local/etc/ha-singleton.conf

# Verify WAN interfaces were configured
grep "WAN_INTS" /usr/local/etc/ha-singleton.conf

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

## Configuration

### Main Configuration File: `/usr/local/etc/ha-singleton.conf`

```bash
# WAN Interfaces to manage
WAN_INTS="vtnet1 vtnet2"

# Services to manage
SERVICES="rtsold dhcp6c radvd"

# Backup routes
ALT_DEFROUTE_IPV4="192.168.105.2"
ALT_DEFROUTE_IPV6="fd03:17ac:e938:10::2"

# Feature toggles
ENABLE_IPV6="yes"
ENABLE_SERVICE_MANAGEMENT="yes"
ENABLE_ROUTE_MANAGEMENT="yes"
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
   # Check if interfaces were substituted correctly
   grep "WAN_INTS" /usr/local/etc/ha-singleton.conf
   
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

2. **Services not starting/stopping**:
   ```bash
   # Enable debug mode
   echo 'DEBUG="yes"' >> /usr/local/etc/ha-singleton.conf
   
   # Check service status
   service rtsold status
   ```

3. **Route management issues**:
   ```bash
   # Check current routes
   netstat -rn | grep default
   
   # Test backup connectivity
   ping -I vtnet1 8.8.8.8
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

### v2.0 (Current)
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

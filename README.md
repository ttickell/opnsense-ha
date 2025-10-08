# OPNsense High Availability (HA) Project

A comprehensive solution for OPNsense High Availability setup with CARP failover, IPv6 support, and service management.

## Project Overview

This project provides automated failover management for OPNsense firewalls in a dual-WAN environment with both IPv4 and IPv6 support. It includes intelligent interface management, service control, and route management based on CARP status.

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

### Installation

```bash
# Download and run the installer
curl -sSL https://raw.githubusercontent.com/ttickell/opnsense-ha/main/setup-firewall | sh

# Or with custom WAN interfaces
curl -sSL https://raw.githubusercontent.com/ttickell/opnsense-ha/main/setup-firewall | sh -s "vtnet1 vtnet2"
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/ttickell/opnsense-ha.git
cd opnsense-ha

# Run the installer
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

### Common Issues

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

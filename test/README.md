# Test/Development Configuration Files

This directory contains test and development configuration files for the OPNsense HA system.

## Files

### ha-singleton-primary.conf
- **Purpose**: Test configuration for primary firewall
- **Status**: Development/testing version
- **Network**: Test environment (192.168.51.x network)
- **WAN Interfaces**: vtnet0_vlan110 (single WAN for testing)

### ha-singleton-secondary.conf  
- **Purpose**: Test configuration for secondary firewall
- **Status**: Development/testing version
- **Network**: Test environment (192.168.51.x network)
- **WAN Interfaces**: vtnet0_vlan110 (single WAN for testing)

## Production Files

For production-ready configuration files, see the `real/` directory which contains:
- Clean, current configurations
- Production network settings (192.168.105.x)
- Dual WAN interface support
- Proper interface mappings for physical hardware

## Usage

These test files are used for:
- Development and testing new features
- Lab environment validation
- Configuration template examples
- Troubleshooting and debugging

**Do not deploy these files to production firewalls.** Use the files in `real/` directory instead.
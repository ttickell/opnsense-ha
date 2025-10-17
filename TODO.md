# OPNsense HA Project - TODO List

## Current Status: v2.1 - Universal HA Logic Complete ✅

---

## � Phase 0: OPNsense Standards Compliance (PRIORITY)

### 0.1 System Tunables Integration (CARP Fixes)
- [ ] **Add missing PFSYNC demotion factor to OPNsense system defaults**
  - **Issue**: `net.pfsync.carp_demotion_factor` is not in OPNsense system defaults but is crucial for CARP stability
  - **Source**: [CARP Documentation](https://github.com/opnsense/docs/blob/master/source/development/backend/carp.rst#L26) - "Busy processing pfsync updates (net.pfsync.carp_demotion_factor)"
  - **Current**: Only `net.inet.carp.senderr_demotion_factor` is included in [`system.inc:93`](https://github.com/opnsense/core/blob/master/src/etc/inc/system.inc#L93)
  - **Required**: Add to [`system_sysctl_defaults()`](https://github.com/opnsense/core/blob/master/src/etc/inc/system.inc#L68-L93) function
  - **Solution**: Submit patch to OPNsense core to add this critical tunable

### 0.2 IPv6 Service Management via configctl
- [ ] **Add missing IPv6 service definitions to configctl**
  - **Issue**: No configctl actions exist for `rtsold`, `dhcp6c`, or `radvd` IPv6 services
  - **Evidence**: Search of [`actions_interface.conf`](https://github.com/opnsense/core/blob/master/src/opnsense/service/conf/actions.d/actions_interface.conf) shows no IPv6-specific service actions
  - **Impact**: IPv6 services cannot be managed via standard OPNsense service control (`configctl`)
  - **Required Actions**:
    - [ ] Create `actions_ipv6.conf` with rtsold/dhcp6c/radvd service definitions
    - [ ] Add template support for IPv6 service configuration
    - [ ] Integrate with OPNsense service management framework

### 0.3 DHCPv6 Configuration File Location Standards
- [ ] **Fix improper use of `/var/etc` for persistent configuration**
  - **Issue**: opnsense-ipv6 repository uses volatile `/var/etc/` directory for persistent configuration
  - **Evidence**: 
    - [Migration document](https://github.com/ttickell/opnsense-ha/blob/ghcwork/opnsense-ipv6/Migration_to_Standards.md) details `/var/etc/dhcp6c.conf.custom` usage
    - OPNsense core uses `/var/etc/` for generated/temporary files: [`OpenVPN examples`](https://github.com/opnsense/core/blob/master/src/opnsense/scripts/openvpn/ovpn_service_control.php#L206)
  - **Standards Violation**: `/var/etc/` is for generated configuration, not persistent user configuration
  - **Required**: Move to `/usr/local/etc/` for persistent configuration files

### 0.4 Script Location Standardization
- [ ] **Move scripts from volatile to persistent locations**
  - **Issue**: Scripts in `/var/etc/` get overwritten during OPNsense updates
  - **Current Problems**:
    - `/var/etc/dhcp6c_wan_custom.sh` (volatile)
    - `/var/etc/dhcp6c-prefix-json` (volatile) 
    - `/var/etc/dhcp6c-checkset-nptv6` (volatile)
  - **Standards**: Use `/usr/local/bin/` for user scripts (persistent across updates)
  - **Solution**: Implement file location migration as documented in Migration_to_Standards.md

---

## �🔄 Phase 1: HA Failover Testing & Refinement

**Test Environment Network Topology** (See NETWORK-TOPOLOGY.md for details):
- **WAN**: 192.168.50.0/24 (DHCP), fd03:17ac:e938:16::/64
- **LAN**: 192.168.51.0/24, fd03:17ac:e938:1f00::/64
- **Primary LAN**: 192.168.51.2, fd03:17ac:e938:1f00::2  
- **Secondary LAN**: 192.168.51.3, fd03:17ac:e938:1f00::3
- **CARP VIP**: 192.168.51.1, fd03:17ac:e938:1f00::1
- **PFSYNC**: 192.168.103.0/29

### 1.1 Core HA Testing
- [ ] **Test Primary → Backup failover scenarios**
  - [ ] Graceful primary shutdown (CARP transitions)
  - [ ] Primary power failure simulation
  - [ ] Primary WAN interface failure
  - [ ] Primary LAN interface failure
  - [ ] Network cable disconnection scenarios

### 1.2 Service Management Validation
- [ ] **Verify service start/stop behavior**
  - [ ] `rtsold` service management during transitions
  - [ ] `dhcp6c` service management during transitions  
  - [ ] `radvd` service management during transitions
  - [ ] Service startup timing and dependencies

### 1.3 Route Management Testing
- [ ] **Test backup routing functionality**
  - [ ] BACKUP state: routing via secondary firewall LAN IP (192.168.51.3)
  - [ ] MASTER state: routing via WAN DHCP gateway
  - [ ] Route cleanup during state transitions
  - [ ] Multiple failover cycles (master ↔ backup ↔ master)

### 1.4 Interface Management Validation
- [ ] **WAN interface state management**
  - [ ] Interface UP/DOWN state tracking accuracy
  - [ ] Multiple WAN interface coordination
  - [ ] Interface settle time optimization
  - [ ] Error handling for missing/invalid interfaces

### 1.5 Configuration & Logging
- [ ] **Optimize configuration parameters**
  - [ ] Tune `INTERFACE_SETTLE_TIME` for optimal performance
  - [ ] Adjust `SERVICE_STARTUP_DELAY` if needed
  - [ ] Validate debug logging effectiveness
  - [ ] Test with different CARP timings

---

## 🔗 Phase 2: IPv6 Integration from opnsense-ipv6 Project

### 2.1 Standards Compliance Migration
- [ ] **Implement Migration_to_Standards.md recommendations**
  - [ ] Move DHCPv6 configuration to persistent locations
  - [ ] Update script paths in configuration files
  - [ ] Create interface-specific hook scripts in correct locations
  - [ ] Test configuration persistence across OPNsense updates

### 2.2 Repository Analysis & Planning
- [ ] **Analyze opnsense-ipv6 repository structure**
  - [ ] Review existing IPv6 scripts and functionality
  - [ ] Identify integration points with HA system
  - [ ] Map IPv6 services to HA service management
  - [ ] Document IPv6 dependencies and requirements

### 2.3 Code Integration
- [ ] **Merge IPv6 functionality into HA project**
  - [ ] Import IPv6 prefix delegation scripts (from persistent locations)
  - [ ] Import NPTv6 rule management scripts
  - [ ] Import DHCPv6 client customizations 
  - [ ] Import IPv6 monitoring and validation tools

### 2.4 HA-IPv6 Coordination
- [ ] **Integrate IPv6 with HA state management**
  - [ ] IPv6 prefix delegation during MASTER state
  - [ ] IPv6 service shutdown during BACKUP state
  - [ ] IPv6 route management coordination
  - [ ] NPTv6 rule synchronization between nodes

---

## 🏗️ Phase 3: OPNsense Override Structure Compliance

### 3.1 Override Structure Implementation
- [ ] **Implement proper OPNsense override structure**
  - [ ] Move scripts to appropriate override directories
  - [ ] Update paths in configuration and installation scripts
  - [ ] Ensure scripts survive OPNsense updates
  - [ ] Follow OPNsense development guidelines

### 3.2 File Organization Restructure
- [ ] **Reorganize file structure for OPNsense compliance**
  - [ ] `/usr/local/etc/rc.d/` for service scripts
  - [ ] `/usr/local/etc/rc.syshook.d/` for system hooks
  - [ ] `/usr/local/opnsense/scripts/` for OPNsense-specific scripts
  - [ ] `/usr/local/etc/` for configuration files

### 3.3 Integration with OPNsense APIs
- [ ] **Enhance integration with OPNsense systems**
  - [ ] Use `configctl` consistently for all operations
  - [ ] Integrate with OPNsense logging system
  - [ ] Follow OPNsense service management patterns
  - [ ] Ensure compatibility with OPNsense updates

---

## 🔧 Phase 4: Unified Setup Process

### 4.1 Enhanced Installer Development
- [ ] **Expand setup-firewall for unified installation**
  - [ ] Add IPv6 component installation options
  - [ ] Add dependency checking and installation
  - [ ] Add configuration validation and testing
  - [ ] Add rollback capabilities for failed installations

### 4.2 Configuration Management
- [ ] **Unified configuration system**
  - [ ] Single configuration file for HA + IPv6
  - [ ] Configuration validation and error checking
  - [ ] Configuration templates for common scenarios
  - [ ] Configuration migration from separate projects

### 4.3 Testing Framework Enhancement
- [ ] **Comprehensive testing suite**
  - [ ] Add IPv6 functionality tests
  - [ ] Add integration tests for HA + IPv6
  - [ ] Add performance and reliability tests
  - [ ] Add automated test reporting

### 4.4 Documentation & User Experience
- [ ] **Complete project documentation**
  - [ ] Update README with unified installation process
  - [ ] Create configuration guide for HA + IPv6
  - [ ] Add troubleshooting guide
  - [ ] Create quick-start guides for common scenarios

---

## 🎯 Phase 5: Production Readiness

### 5.1 Security & Hardening
- [ ] **Security review and hardening**
  - [ ] Script permission and access control review
  - [ ] Secure communication between HA nodes
  - [ ] Logging security and log rotation
  - [ ] Configuration file security

### 5.2 Performance Optimization
- [ ] **Performance tuning and optimization**
  - [ ] Failover time optimization
  - [ ] Resource usage optimization
  - [ ] Network performance during transitions
  - [ ] Service startup optimization

### 5.3 Monitoring & Alerting
- [ ] **Monitoring and alerting integration**
  - [ ] SNMP monitoring integration
  - [ ] Syslog integration for remote monitoring
  - [ ] Health check and alerting systems
  - [ ] Performance metrics collection

---

## 📋 Current Priority Order

1. **CRITICAL**: OPNsense Standards Compliance (Phase 0) ⚠️
2. **IMMEDIATE**: Complete HA failover testing (Phase 1) ⚡
3. **SHORT-TERM**: Begin IPv6 integration analysis (Phase 2.1) 📋
4. **MEDIUM-TERM**: Implement unified setup (Phase 4) 🔧
5. **LONG-TERM**: Production hardening (Phase 5) 🎯

---

## 📝 Detailed Source Code Citations

### CARP Demotion Factor Issues
- **Missing tunable**: `net.pfsync.carp_demotion_factor` not in [`system_sysctl_defaults()`](https://github.com/opnsense/core/blob/master/src/etc/inc/system.inc#L68-L140)
- **CARP demotion management**: [`carp_set_status.php:44-54`](https://github.com/opnsense/core/blob/master/src/opnsense/scripts/interfaces/carp_set_status.php#L44-L54)
- **Service status integration**: [`carp_service_status:41,58,62`](https://github.com/opnsense/core/blob/master/src/sbin/carp_service_status#L41)
- **Early CARP hook**: [`90-carp:6-8`](https://github.com/opnsense/core/blob/master/src/etc/rc.syshook.d/early/90-carp#L6-L8)

### IPv6 Service Management Gaps
- **Interface actions**: [`actions_interface.conf`](https://github.com/opnsense/core/blob/master/src/opnsense/service/conf/actions.d/actions_interface.conf) - no IPv6 service actions
- **DHCPv6 server actions**: [`actions_dhcpd6.conf`](https://github.com/opnsense/core/blob/master/src/opnsense/service/conf/actions.d/actions_dhcpd6.conf) - only server, no client
- **IPv6 interfaces code**: [`interfaces.inc:630-665`](https://github.com/opnsense/core/blob/master/src/etc/inc/interfaces.inc#L630-L665) - dhcp6c handling

### Configuration Location Issues
- **Volatile `/var/etc` usage**: [`OpenVPN examples`](https://github.com/opnsense/core/blob/master/src/opnsense/scripts/openvpn/ovpn_service_control.php#L206-L207)
- **Template generation target**: System generates to `/var/etc/` for temporary config
- **rtsold integration**: [`rtsold_resolvconf.sh:43`](https://github.com/opnsense/core/blob/master/src/opnsense/scripts/interfaces/rtsold_resolvconf.sh#L43)

---

## 📝 Notes & Considerations

### Technical Debt Items
- [ ] Remove any remaining hardcoded values from scripts
- [ ] Standardize error handling across all components
- [ ] Implement consistent logging format
- [ ] Add proper input validation throughout
- [ ] **Submit patches to OPNsense core for missing IPv6 service integration**
  - [ ] Create pull requests for missing tunables and configctl actions
  - [ ] Ensure patches follow OPNsense development guidelines
  - [ ] Test patches across OPNsense update cycles

### Future Enhancements
- [ ] Support for more than 2 HA nodes (cluster mode)
- [ ] Integration with external monitoring systems
- [ ] Web interface for HA management
- [ ] Automated backup and restore functionality

### Dependencies to Track
- [ ] OPNsense version compatibility matrix
- [ ] FreeBSD version dependencies
- [ ] Required OPNsense packages and plugins
- [ ] Network topology requirements

### Upstream Contributions Required
- [ ] **OPNsense Core**: Add `net.pfsync.carp_demotion_factor` to system defaults
- [ ] **OPNsense Core**: Add IPv6 service management to configctl
- [ ] **OPNsense Documentation**: Update IPv6 best practices for persistent configuration

---

**Last Updated**: October 17, 2025  
**Current Branch**: ghcwork  
**Version**: 2.1 (Universal HA Logic + Standards Compliance Analysis)
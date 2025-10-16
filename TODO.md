# OPNsense HA Project - TODO List

## Current Status: v2.1 - Universal HA Logic Complete ✅

---

## 🔄 Phase 1: HA Failover Testing & Refinement

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

### 2.1 Repository Analysis & Planning
- [ ] **Analyze opnsense-ipv6 repository structure**
  - [ ] Review existing IPv6 scripts and functionality
  - [ ] Identify integration points with HA system
  - [ ] Map IPv6 services to HA service management
  - [ ] Document IPv6 dependencies and requirements

### 2.2 Code Integration
- [ ] **Merge IPv6 functionality into HA project**
  - [ ] Import IPv6 prefix delegation scripts
  - [ ] Import NPTv6 rule management scripts
  - [ ] Import DHCPv6 client customizations
  - [ ] Import IPv6 monitoring and validation tools

### 2.3 HA-IPv6 Coordination
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

1. **IMMEDIATE**: Complete HA failover testing (Phase 1) ⚡
2. **SHORT-TERM**: Begin IPv6 integration analysis (Phase 2.1) 📋
3. **MEDIUM-TERM**: Implement unified setup (Phase 4) 🔧
4. **LONG-TERM**: Production hardening (Phase 5) 🎯

---

## 📝 Notes & Considerations

### Technical Debt Items
- [ ] Remove any remaining hardcoded values from scripts
- [ ] Standardize error handling across all components
- [ ] Implement consistent logging format
- [ ] Add proper input validation throughout
- [ ] **Patch configctl to support IPv6 services (rtsold, dhcp6c, radvd)**
  - [ ] Create action definition files for IPv6 services
  - [ ] Add configctl templates for proper service integration
  - [ ] Test configctl commands work correctly
  - [ ] Ensure patches survive OPNsense updates or implement as overlay

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

---

**Last Updated**: October 16, 2025  
**Current Branch**: ghcwork  
**Version**: 2.1 (Universal HA Logic)
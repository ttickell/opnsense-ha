# OPNsense HA Project - TODO List

## Current Status: v2.6 - Functional HA Implementation ✅

### Completed bidirectional HA failover with DHCP lease renewal

---

## ✅ Completed Work - Phase 1 Testing

### Phase 1: HA Failover Testing & Refinement - Complete

#### 1.1 Core HA Testing - Validated
- [x] **Primary → Secondary failover** - IPv4 immediate, IPv6 in 11 seconds
- [x] **Secondary → Primary failover** - IPv4 almost immediate, IPv6 in ~11 seconds  
- [x] **Primary power failure simulation** - CARP transition validated
- [x] **Dual-firewall coordination** - CARP coordination functional, no flapping observed
- [x] **Non-preemptive behavior validation** - Controlled failback working as designed

#### 1.2 Service Management Validation - Working
- [x] **`rtsold` service management** - Coordination during CARP transitions functional
- [x] **`dhcp6c` service management** - Restart functionality achieving 11-second IPv6 recovery
- [x] **`radvd` service management** - IPv6 route advertisement coordination working
- [x] **Service startup timing** - Startup sequence provides consistent performance

#### 1.3 Route Management Testing - Functional
- [x] **BACKUP state routing** - Backup routes via secondary firewall working
- [x] **MASTER state routing** - DHCP route restoration via configctl functional
- [x] **Route cleanup during transitions** - Route management prevents "route already in table" errors
- [x] **Multiple failover cycles** - Bidirectional stability across test cycles validated

#### 1.4 Interface Management Validation - Working
- [x] **WAN interface state management** - UP/DOWN coordination with configctl integration
- [x] **Interface settle time optimization** - 2-second settle time provides stable operation
- [x] **DHCP lease renewal integration** - configctl interface reconfigure/newip resolves IPv4 connectivity gaps
- [x] **Error handling for edge cases** - Fallback mechanisms with ifconfig backup implemented

#### 1.5 Configuration & Logging - Functional
- [x] **Configuration parameter optimization** - Timings validated through testing
- [x] **Debug logging effectiveness** - Logging provides troubleshooting capability
- [x] **CARP stability tuning** - PFSYNC demotion factor disabled prevents CARP flapping
- [x] **Performance consistency** - ~11 second IPv6 recovery across test scenarios

### Technical Implementation Completed

#### DHCP Lease Renewal Solution (v2.6)
- [x] **configctl interface reconfigure integration** - DHCP lease renewal during failover
- [x] **WAN_INTERFACE_MAP system** - Mapping between device names and OPNsense interface names  
- [x] **Multi-WAN interface support** - Architecture supports multiple WAN interfaces
- [x] **IPv4 restoration** - Addresses gap where IPv4 required manual intervention

#### CARP Stability Enhancements  
- [x] **PFSYNC tuning** - Disabled net.pfsync.carp_demotion_factor prevents bulk sync failures
- [x] **Conditional rtsold management** - Prevents interface reloads that reset CARP state
- [x] **Enhanced error handling** - configctl integration with ifconfig fallbacks

#### OPNsense Native Integration
- [x] **configctl command usage** - OPNsense API integration for interface management
- [x] **System service integration** - Integration with OPNsense service management
- [x] **Standards-compliant logging** - Follows syslog standards with appropriate severity levels

### Test Results Summary

| Test Scenario | IPv4 Recovery | IPv6 Recovery | CARP Behavior | Status |
|--------------|---------------|---------------|---------------|---------|
| **Primary Power Failure** | Brief pause | **11 seconds** | Clean transition | ✅ **Functional** |
| **Secondary Power Failure** | Almost immediate | **~11 seconds** | Clean transition | ✅ **Functional** |
| **Primary Return (Non-preemptive)** | No interruption | No interruption | BACKUP behavior working | ✅ **Functional** |
| **Secondary Return** | <2s interruption | <2s interruption | BACKUP establishment working | ✅ **Functional** |
| **Complete HA Cycle** | Consistent | Consistent | No flapping observed | ✅ **Functional** |

**Test Environment Network Topology**:
- **WAN**: 192.168.50.0/24 (DHCP), fd03:17ac:e938:16::/64
- **LAN**: 192.168.51.0/24, fd03:17ac:e938:1f00::/64
- **Primary LAN**: 192.168.51.2, fd03:17ac:e938:1f00::2  
- **Secondary LAN**: 192.168.51.3, fd03:17ac:e938:1f00::3
- **CARP VIP**: 192.168.51.1, fd03:17ac:e938:1f00::1
- **PFSYNC**: 192.168.103.0/29

---

## 🧹 Lab: Clean Up Proxima

Changes made to the `proxima` Proxmox host for lab testing that must be undone when teardown occurs.

### Permanent changes (survive reboot)

- [x] **`vmbr0.212` OVS internal port** added to `/etc/network/interfaces`
  - IP: `10.220.1.254/24`, VLAN 212 on `vmbr0`
  - Purpose: gives proxima a management IP on the lab LAN so OPNsense GUI is reachable without SSH tunnels
  - **To undo**: remove the `auto vmbr0.212` stanza from `/etc/network/interfaces` and run `ifdown vmbr0.212 && ovs-vsctl del-port vmbr0 vmbr0.212`

### Temporary changes (lost on reboot — action only needed if proxima is NOT rebooted first)

**⚠️ HOLD: Keep these rules ACTIVE until all HA testing is complete, then remove them.**

- [ ] **iptables NAT masquerade rule** — gives lab firewalls temporary internet access for `setup-firewall` and git pulls
  ```
  iptables -t nat -A POSTROUTING -s 10.220.1.0/24 -j MASQUERADE
  ```
  **To undo** (after testing done): `iptables -t nat -D POSTROUTING -s 10.220.1.0/24 -j MASQUERADE`

- [ ] **iptables FORWARD rules** for lab LAN traffic during testing
  ```
  iptables -A FORWARD -s 10.220.1.0/24 -j ACCEPT
  iptables -A FORWARD -d 10.220.1.0/24 -m state --state RELATED,ESTABLISHED -j ACCEPT
  ```
  **To undo** (after testing done):
  ```
  iptables -D FORWARD -s 10.220.1.0/24 -j ACCEPT
  iptables -D FORWARD -d 10.220.1.0/24 -m state --state RELATED,ESTABLISHED -j ACCEPT
  ```

> Note: `net.ipv4.ip_forward` was already `1` on proxima before these changes — no action needed to restore it.
> 
> **Cleanup script** (when testing is complete):
> ```python
> cd /Users/tickell/workspace/opnsense-ha && source .env && python3 << 'PYEOF'
> import sys; sys.path.insert(0, 'lab/scripts')
> import lib
> for cmd in ['iptables -t nat -D POSTROUTING -s 10.220.1.0/24 -j MASQUERADE',
>             'iptables -D FORWARD -s 10.220.1.0/24 -j ACCEPT',
>             'iptables -D FORWARD -d 10.220.1.0/24 -m state --state RELATED,ESTABLISHED -j ACCEPT']:
>     rc, out = lib.host_exec(cmd)
>     print(f'[{rc}] removed')
> PYEOF
> ```

---

## 🔄 Future Development Work

### Phase 0: OPNsense Standards Compliance (Future Upstream Contributions)

#### 0.1 System Tunables Integration (CARP Fixes)
- [ ] **Add missing PFSYNC demotion factor to OPNsense system defaults**
  - **Source**: [CARP Documentation](https://github.com/opnsense/docs/blob/master/source/development/backend/carp.rst#L26) - "Busy processing pfsync updates (net.pfsync.carp_demotion_factor)"
  - **Current**: Only `net.inet.carp.senderr_demotion_factor` is included in [`system.inc:93`](https://github.com/opnsense/core/blob/master/src/etc/inc/system.inc#L93)
  - **Required**: Add to [`system_sysctl_defaults()`](https://github.com/opnsense/core/blob/master/src/etc/inc/system.inc#L68-L93) function
  - **Solution**: Submit patch to OPNsense core to add this critical tunable

#### 0.2 IPv6 Service Management via configctl
- [ ] **Add missing IPv6 service definitions to configctl**
  - **Issue**: No configctl actions exist for `rtsold`, `dhcp6c`, or `radvd` IPv6 services
  - **Evidence**: Search of [`actions_interface.conf`](https://github.com/opnsense/core/blob/master/src/opnsense/service/conf/actions.d/actions_interface.conf) shows no IPv6-specific service actions
  - **Impact**: IPv6 services cannot be managed via standard OPNsense service control (`configctl`)
  - **Required Actions**:
    - [ ] Create `actions_ipv6.conf` with rtsold/dhcp6c/radvd service definitions
    - [ ] Add template support for IPv6 service configuration
    - [ ] Integrate with OPNsense service management framework

#### 0.3 DHCPv6 Configuration File Location Standards
- [ ] **Fix improper use of `/var/etc` for persistent configuration**
  - **Issue**: opnsense-ipv6 repository uses volatile `/var/etc/` directory for persistent configuration
  - **Evidence**: 
    - [Migration document](https://github.com/ttickell/opnsense-ha/blob/ghcwork/opnsense-ipv6/Migration_to_Standards.md) details `/var/etc/dhcp6c.conf.custom` usage
    - OPNsense core uses `/var/etc/` for generated/temporary files: [`OpenVPN examples`](https://github.com/opnsense/core/blob/master/src/opnsense/scripts/openvpn/ovpn_service_control.php#L206)
  - **Standards Violation**: `/var/etc/` is for generated configuration, not persistent user configuration
  - **Required**: Move to `/usr/local/etc/` for persistent configuration files

#### 0.4 Script Location Standardization
- [ ] **Move scripts from volatile to persistent locations**
  - **Issue**: Scripts in `/var/etc/` get overwritten during OPNsense updates
  - **Current Problems**:
    - `/var/etc/dhcp6c_wan_custom.sh` (volatile)
    - `/var/etc/dhcp6c-prefix-json` (volatile) 
    - `/var/etc/dhcp6c-checkset-nptv6` (volatile)
  - **Standards**: Use `/usr/local/bin/` for user scripts (persistent across updates)
  - **Solution**: Implement file location migration as documented in Migration_to_Standards.md

---

## 🏗️ Future Development Roadmap

### Phase 3: Advanced Testing Infrastructure 
- [ ] **Multi-interface test VM architecture**
  - [ ] Separate WAN/LAN interfaces for realistic cable fault simulation
  - [ ] Individual interface disconnection testing capability
  - [ ] Advanced network failure scenario validation

### Phase 4: Network Infrastructure Failure Testing
- [ ] **WAN link failure scenarios** 
  - [ ] Cable fault simulation with selective interface disconnection
  - [ ] Switch failure testing with bridge-level manipulation
  - [ ] ISP connectivity failure validation
- [ ] **LAN network failure scenarios**
  - [ ] LAN switch failure simulation
  - [ ] VLAN failure testing
  - [ ] Network segmentation failure validation

### Phase 5: Extended IPv6 Integration
- [ ] **opnsense-ipv6 project integration**
  - [ ] IPv6 prefix delegation during HA transitions  
  - [ ] NPTv6 rule management coordination
  - [ ] DHCPv6 client customization integration
  - [ ] IPv6 monitoring and validation tools

### Phase 6: Production Enhancements
- [ ] **Security hardening and optimization**
  - [ ] Script permission and access control review
  - [ ] Performance tuning and optimization  
  - [ ] Monitoring and alerting integration
  - [ ] Web interface for HA management

---

## 📋 Current Status Summary

### ✅ **Functional System**
The v2.6 HA solution provides working HA capabilities:

**Core Features Working**:
- ✅ Complete bidirectional failover (Primary ↔ Secondary)
- ✅ DHCP lease renewal for IPv4 connectivity restoration  
- ✅ IPv6 service management with consistent 11-second recovery
- ✅ CARP stability with no flapping observed
- ✅ Multi-WAN interface support architecture
- ✅ OPNsense native integration via configctl
- ✅ Error handling and fallback mechanisms

**Performance Observed**:
- ✅ IPv4: Immediate to almost immediate recovery
- ✅ IPv6: Consistent ~11 second recovery time
- ✅ CARP: Functional coordination and state management
- ✅ Services: Working start/stop coordination
- ✅ Interfaces: Clean UP/DOWN state transitions

**Testing Complete**:
- ✅ Power failure scenarios (both directions)
- ✅ Complete HA cycle validation  
- ✅ Non-preemptive behavior verification
- ✅ Dual-firewall coordination
- ✅ Service and interface management

---

## 📝 Development Priorities

### **Short-Term** (Next Development Cycle)
1. **Advanced Testing Infrastructure** - Multi-interface VMs for cable fault testing
2. **Documentation Enhancement** - Complete deployment guide
3. **Monitoring Integration** - SNMP and alerting system integration

### **Medium-Term** (Future Releases)  
1. **IPv6 Project Integration** - Merge opnsense-ipv6 functionality
2. **Performance Optimization** - Further tune failover timing
3. **Security Hardening** - Security review

### **Long-Term** (Major Enhancements)
1. **Multi-node Clustering** - Support for >2 HA nodes
2. **Web Management Interface** - GUI for HA configuration
3. **OPNsense Core Contributions** - Submit patches upstream

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

**Last Updated**: March 2, 2026  
**Current Branch**: ghcwork  
**Version**: v2.6 - Functional HA Implementation
**Status**: Complete bidirectional HA failover with DHCP lease renewal - Functional and tested
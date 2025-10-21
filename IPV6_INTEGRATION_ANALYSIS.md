# IPv6 Integration Analysis & Implementation Plan
## Executive Summary

This document provides a comprehensive analysis for integrating the `opnsense-ipv6` project functionality into the `opnsense-ha` project while maintaining OPNsense standards compliance and best practices. The analysis is based on definitive sources including OPNsense documentation, source code examination, and established debugging principles.

## Gap Analysis - Current State vs Requirements

### Current IPv6 Functionality in opnsense-ipv6
✅ **Working Components:**
- Custom DHCPv6 configuration for dual WAN (Comcast + AT&T)
- DHCP client ID (DUID) synchronization via DUID override
- JSON-based prefix delegation tracking (`dhcp6c-prefix-json`)
- ULA network mapping system (`dhcp6c-ula-mapping.py`)
- NPTv6 configuration management (`dhcp6c-checkset-nptv6`)
- Provider-specific delegation handling:
  - Comcast: Two /60 prefixes via specific DUID requirements
  - AT&T: Eight /64 prefixes via sequential delegation

### Current HA Functionality in opnsense-ha  
✅ **Working Components:**
- CARP-based failover with IPv6 service management
- DHCPv6 DUID synchronization (25-duid-override hook)
- IPv6 service restart during CARP transitions (`rtsold`, `dhcp6c`, `radvd`)
- Interface reconfiguration triggering IPv6 lease renewal
- Route verification and retry logic for IPv6 gateways

### Critical Integration Requirements

#### 1. **ULA Network Strategy**
**Current**: Uses `fd03:17ac:e938::/48` with specific /64 allocations
- `fd03:17ac:e938:10::/64` - LAN (igc2)
- `fd03:17ac:e938:11::/64` - CAM (igc3)  
- `fd03:17ac:e938:12::/64` - Wireguard
- `fd03:17ac:e938:13::/64` - OpenVPN
- `fd03:17ac:e938:14::/64` - Guest Net
- `fd03:17ac:e938:15::/64` - IOT
- `fd03:17ac:e938:16::/64` - TestNetInt

**Integration Requirement**: Map ULA networks to provider delegations with automatic failover

#### 2. **Provider-Specific Delegation Handling**
**Comcast Configuration Requirements:**
- DUID-dependent: Must use synchronized DUID across HA pair
- Delegation: Two /60 prefixes (16 x /64 networks each)
- Order dependency: Comcast must be first in dhcp6c.conf for DUID recognition

**AT&T Configuration Requirements:**  
- Delegation: AT&T delegates a /60 to their router, which consumes one /64
- Available: Seven /64 prefixes available to our firewall (not eight)
- No DUID dependency but order affects prefix assignment
- Provides consistent prefixes if DUID/order remains stable

#### 3. **NPTv6 Management Requirements**
**Current Challenge**: NPTv6 rules require static prefix configuration
**Solution Needed**: Dynamic NPTv6 rule management based on received delegations

## Standards Compliance Analysis

### OPNsense Configuration File Standards
❌ **Current Violations in opnsense-ipv6:**
- Uses `/var/etc/` for persistent configuration (dhcp6c.conf.custom)
- Scripts in volatile directory (`/var/etc/dhcp6c_wan_custom.sh`)
- JSON state files in `/var/etc/` instead of `/var/db/`

✅ **Compliance Requirements:**
- Persistent config: `/usr/local/etc/`
- Generated config: `/var/etc/` (temporary)
- State data: `/var/db/`
- Scripts: `/usr/local/bin/`

### OPNsense Service Integration Standards
❌ **Current Gaps:**
- No configctl actions for IPv6 services (confirmed in source analysis)
- Direct service manipulation instead of OPNsense service framework

✅ **Standards Compliance Path:**
- Use existing service management where available
- Fallback to direct service control for IPv6-specific services
- Document need for upstream configctl IPv6 service actions

### FreeBSD/OPNsense DHCPv6 Integration
✅ **Current Best Practices:**
- Uses OPNsense's dhcp6c integration (`/var/etc/dhcp6c.conf`)
- Leverages script hooks for delegation processing
- Maintains DUID consistency via OPNsense DUID override

## Technical Architecture Plan

### Phase 1: Standards Compliance Migration
**File Location Standardization:**
```bash
# Move from volatile to persistent locations:
/var/etc/dhcp6c.conf.custom → /usr/local/etc/dhcp6c.conf.custom
/var/etc/dhcp6c_wan_custom.sh → /usr/local/bin/dhcp6c-wan-script.sh
/var/etc/dhcp6c-prefix-json → /usr/local/bin/dhcp6c-prefix-json
/var/etc/dhcp6c-ula-mapping.py → /usr/local/bin/dhcp6c-ula-mapping.py
/var/etc/dhcp6c-checkset-nptv6 → /usr/local/bin/dhcp6c-nptv6-manager

# State files move to proper locations:
/var/db/dhcp6c-pds.json (prefix delegation state)
/var/db/ipv6-ula-mappings.json (ULA mapping state)
```

**Integration with HA Setup Script:**
- Add IPv6 configuration validation to `setup-firewall`
- Implement ULA network validation
- Add provider-specific configuration templates

### Phase 2: HA Integration Architecture

#### 2.1 Enhanced CARP Hook Integration
**Extend `00-ha-singleton` with IPv6-specific functionality:**

```bash
# New configuration options:
ENABLE_IPV6_ULA_MANAGEMENT="yes"
ENABLE_DYNAMIC_NPTV6="yes"  
ULA_PREFIX="fd03:17ac:e938::/48"
IPV6_STATE_DIR="/var/db"
```

**IPv6 Functions to Add:**
- `manage_ipv6_delegations()` - Process received prefix delegations
- `update_ula_mappings()` - Map ULA networks to provider prefixes
- `sync_nptv6_rules()` - Update NPTv6 rules based on current delegations
- `verify_ipv6_connectivity()` - IPv6-specific connectivity validation

#### 2.2 Dynamic Delegation Processing
**Integration Points:**
1. **DHCPv6 Script Hook**: `/usr/local/bin/dhcp6c-wan-script.sh`
   - Processes delegation changes from dhcp6c
   - Updates state files in `/var/db/`
   - Triggers ULA mapping updates
   - Initiates NPTv6 rule synchronization

2. **CARP State Changes**: Enhanced `00-ha-singleton`
   - Validates IPv6 delegations after interface transitions
   - Ensures ULA mappings remain consistent
   - Verifies NPTv6 rules match current delegations

#### 2.3 State Management System
**Central State Files:**
```json
# /var/db/dhcp6c-delegations.json
{
  "comcast": {
    "prefixes": ["2601:346:27f:3960::/60", "2601:346:27f:3b90::/60"],
    "allocated": false,
    "last_updated": "2025-10-21T10:30:00Z"
  },
  "att": {
    "prefixes": [
      "2600:1700:60f0:254d::/64",
      "2600:1700:60f0:254c::/64",
      "2600:1700:60f0:254b::/64",
      "2600:1700:60f0:2549::/64",
      "2600:1700:60f0:254f::/64",
      "2600:1700:60f0:254e::/64",
      "2600:1700:60f0:2550::/64"
    ],
    "allocated": true,
    "assignments": {
      "fd03:17ac:e938:10::/64": "2600:1700:60f0:254d::/64",
      "fd03:17ac:e938:11::/64": "2600:1700:60f0:254c::/64"
    },
    "last_updated": "2025-10-21T10:30:00Z"
  }
}
```

### Phase 3: NPTv6 Automation

#### 3.1 Dynamic NPTv6 Rule Management
**OPNsense API Integration:**
- Use OPNsense API for NPTv6 rule management
- Maintain backup NPTv6 rules for provider failover
- Automatic rule activation based on CARP state

**Implementation Approach:**
```python
# /usr/local/bin/opnsense-nptv6-manager.py
class NPTv6Manager:
    def sync_rules_from_delegations(self, delegations):
        """Update NPTv6 rules based on current delegations"""
        
    def activate_provider_rules(self, provider):
        """Activate NPTv6 rules for specific provider"""
        
    def backup_current_rules(self):
        """Backup current NPTv6 configuration"""
```

#### 3.2 Failover-Aware NPTv6 Configuration
**Primary State (AT&T Active):**
- ULA networks mapped to AT&T delegations
- NPTv6 rules: Internal ULA → External AT&T prefixes
- Comcast delegations maintained but inactive

**Failover State (Comcast Active):**
- ULA networks mapped to Comcast delegations  
- NPTv6 rules: Internal ULA → External Comcast prefixes
- AT&T delegations preserved for failback

## Implementation Sequence

### Phase 1: Foundation (Week 1-2)
1. **File Migration & Standards Compliance**
   - Move all scripts and config to standards-compliant locations
   - Update file permissions and ownership
   - Test basic functionality after migration

2. **HA Script Integration Preparation**  
   - Add IPv6 configuration options to `00-ha-singleton`
   - Implement basic IPv6 state validation functions
   - Create state file management infrastructure

### Phase 2: Core Integration (Week 3-4)
3. **DHCPv6 Configuration Management**
   - Integrate custom dhcp6c configuration with HA setup
   - Implement DUID synchronization validation
   - Add provider-specific configuration templates

4. **ULA Mapping System**
   - Implement dynamic ULA-to-delegation mapping
   - Create mapping state persistence
   - Add mapping validation and recovery functions

### Phase 3: Advanced Features (Week 5-6)  
5. **NPTv6 Automation**
   - Implement OPNsense API integration for NPTv6 management
   - Create automated rule generation from delegations
   - Add failover-aware rule switching

6. **Integration Testing & Validation**
   - Comprehensive HA failover testing with IPv6
   - Provider delegation testing (Comcast/AT&T)
   - NPTv6 failover validation

## Risk Assessment & Mitigation

### High-Risk Areas
1. **DUID Synchronization Failure**
   - **Risk**: Comcast rejects requests with mismatched DUID
   - **Mitigation**: Robust DUID validation and sync verification

2. **Delegation Order Dependencies**
   - **Risk**: Provider delegation order affects prefix assignment
   - **Mitigation**: Standardized dhcp6c.conf generation with fixed ordering

3. **NPTv6 Rule Consistency**
   - **Risk**: Inconsistent NPTv6 rules during failover
   - **Mitigation**: Atomic rule updates with rollback capability

### Medium-Risk Areas
1. **State File Corruption**
   - **Risk**: JSON state files become corrupted
   - **Mitigation**: State file validation and automatic recovery

2. **Service Startup Dependencies**
   - **Risk**: IPv6 services start in wrong order
   - **Mitigation**: Enhanced service dependency management in HA script

## Testing Strategy

### Test Environment Requirements
- Dual WAN simulation (Comcast + AT&T emulation)
- Multiple IPv6 client networks
- NPTv6 rule validation capability
- CARP failover testing infrastructure

### Test Scenarios
1. **Primary → Secondary Failover**
   - Validate IPv6 connectivity preservation
   - Verify ULA mapping consistency
   - Confirm NPTv6 rule switching

2. **Delegation Change Handling**
   - Simulate provider delegation changes
   - Validate automatic ULA remapping
   - Test NPTv6 rule updates

3. **DUID Synchronization Validation**
   - Verify DUID consistency across HA pair
   - Test Comcast-specific DUID requirements
   - Validate delegation acquisition with synchronized DUID

## Deliverables

### Code Components
1. **Enhanced HA Script** (`usr/local/etc/rc.syshook.d/carp/00-ha-singleton`)
2. **IPv6 Configuration Manager** (`usr/local/bin/ipv6-ha-manager.py`)
3. **NPTv6 Rule Manager** (`usr/local/bin/opnsense-nptv6-manager.py`)
4. **Setup Script Integration** (enhanced `setup-firewall`)

### Documentation
1. **IPv6 Integration Guide** - Comprehensive setup and configuration
2. **Troubleshooting Guide** - IPv6-specific debugging procedures  
3. **API Reference** - IPv6 management function documentation
4. **Migration Guide** - Upgrade path from standalone IPv6 setup

### Configuration Templates
1. **DHCPv6 Configuration Templates** - Provider-specific configurations
2. **ULA Network Definitions** - Standardized ULA allocations
3. **NPTv6 Rule Templates** - Failover-aware rule configurations

## Next Steps

**Immediate Actions Required:**
1. **Review and Approve Plan** - Validate approach and scope
2. **Environment Preparation** - Set up integration testing environment
3. **Phase 1 Kickoff** - Begin file migration and standards compliance

**Dependencies:**
- Access to Comcast and AT&T test environments
- OPNsense API documentation and testing access
- Validation of ULA network requirements and assignments

This analysis provides the foundation for a robust IPv6 integration that maintains the sophisticated dual-provider functionality while achieving full HA compatibility and OPNsense standards compliance.
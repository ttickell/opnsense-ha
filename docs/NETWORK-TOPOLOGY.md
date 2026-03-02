# OPNsense HA Project - Network Topology Documentation

## Test Environment Network Configuration

### Network Segments

#### WAN Network (Upstream)
- **IPv4**: `192.168.50.0/24` (DHCP from upstream router)
- **IPv6**: `fd03:17ac:e938:16::/64` (DHCP/SLAAC from upstream router)
- **Interface**: Single WAN interface (e.g., `vtnet0_vlan110`)

#### LAN Network (Internal)
- **IPv4**: `192.168.51.0/24` (Static configuration)
- **IPv6**: `fd03:17ac:e938:1f00::/64` (Delegated/Static configuration)

#### PFSYNC Network (HA Synchronization)
- **IPv4**: `192.168.103.0/29` (Point-to-point between firewalls)
- **Usage**: CARP state synchronization and configuration sync

### Firewall IP Address Assignments

#### Primary Firewall (Node 1)
- **WAN**: DHCP assigned from `192.168.50.0/24` range
- **LAN IPv4**: `192.168.51.2/24` (Primary address)
- **LAN IPv6**: `fd03:17ac:e938:1f00::2/64` (Primary address)
- **PFSYNC**: `192.168.103.1/29`

#### Secondary Firewall (Node 2)
- **WAN**: DHCP assigned from `192.168.50.0/24` range (same MAC as primary)
- **LAN IPv4**: `192.168.51.3/24` (Primary address)
- **LAN IPv6**: `fd03:17ac:e938:1f00::3/64` (Primary address)
- **PFSYNC**: `192.168.103.2/29`

#### CARP Virtual IPs (Shared)
- **LAN IPv4**: `192.168.51.1/24` (CARP VIP)
- **LAN IPv6**: `fd03:17ac:e938:1f00::1/64` (CARP VIP)

### HA Failover Logic

#### MASTER State (Active Firewall)
- WAN interface UP and active (DHCP client running)
- LAN CARP VIP active on this node
- Default route via WAN DHCP gateway
- IPv6 services running (if enabled)

#### BACKUP State (Standby Firewall)
- WAN interface DOWN (to avoid IP conflicts)
- LAN CARP VIP on standby
- Default IPv4 route via active firewall's LAN IP
- IPv6 route via Router Advertisements from active firewall

### Route Configuration Examples

#### When Primary is MASTER, Secondary is BACKUP:
- **Primary**: Routes via WAN gateway (DHCP assigned)
- **Secondary**: Default route via `192.168.51.2` (Primary's LAN IP)

#### When Secondary is MASTER, Primary is BACKUP:
- **Secondary**: Routes via WAN gateway (DHCP assigned)  
- **Primary**: Default route via `192.168.51.3` (Secondary's LAN IP)

### Key Configuration Points

#### 1. MAC Address Cloning ⚠️ Required
Both firewalls' WAN interfaces must present **identical MAC addresses** to the upstream network. ISPs and upstream routers bind DHCP leases to MAC addresses — if the BACKUP node brings up its WAN with a different MAC after failover, the upstream router will not hand over the existing lease. The result is a connectivity gap lasting minutes to hours until the old lease expires.

Configure in OPNsense GUI: `Interfaces → [WAN] → MAC address` — set the same value on both nodes. Verify with `ifconfig <wan_device> | grep ether` on both nodes.

#### 2. Matching DHCPv6 DUID ⚠️ Required for IPv6
Both firewalls must use the **same DHCPv6 DUID** for prefix delegation. DHCPv6 servers bind prefix delegations to the DUID, not the MAC. A mismatched DUID on the BACKUP node means it will receive a different or no prefix delegation on failover, breaking all downstream IPv6 addressing that depends on the delegated prefix.

Copy the DUID from the primary node (`cat /var/db/dhcp6c_duid`) and write the identical value to the same path on the secondary. Also set it explicitly under `Interfaces → [WAN] → DHCPv6 client → DUID` in the GUI on both nodes.

#### 3. Single Active WAN
Only the MASTER node has an active WAN connection. The `00-ha-singleton` hook script explicitly brings WAN interfaces **down** on BACKUP transitions and **up** on MASTER transitions. This prevents IP conflicts when both nodes are live simultaneously.

#### 4. DHCP-Based WAN Addressing
WAN interfaces must use DHCP (not static) for IPv4. The DHCP renewal path (`configctl interface reconfigure` / `configctl interface newip`) that restores default routes during a MASTER transition does not apply to statically addressed interfaces.

#### 5. LAN Connectivity for BACKUP Node
The BACKUP node maintains internet connectivity by routing through the MASTER node's LAN IP (`ALT_DEFROUTE_IPV4` / `ALT_DEFROUTE_IPV6` in the config). This route is injected on BACKUP transitions and removed when the node becomes MASTER.

#### 6. No CARP VIPs on WAN
CARPVirtual IPs must not be placed on WAN interfaces. WAN ownership is managed by the script's up/down logic. CARP VIPs are used only on LAN/internal interfaces.

#### 7. Private IPv6
Static IPv6 configuration is used in the test environment since it uses private (ULA) addressing rather than provider-delegated public prefixes.

### Test Scenarios

#### Primary Failure Scenarios:
- Primary power loss → Secondary becomes MASTER, brings up WAN
- Primary WAN failure → Secondary becomes MASTER, takes over WAN
- Primary LAN failure → Secondary becomes MASTER via CARP

#### Network Validation:
- CARP VIP responds from active node only
- BACKUP node can reach internet via MASTER node's LAN IP
- IPv6 connectivity maintained through proper delegation/static config
- PFSYNC keeps configurations synchronized

### Interface Mapping (Example)
```
Primary Firewall:
- vtnet0_vlan110 (WAN) → 192.168.50.x/24 (DHCP)
- vtnet1 (LAN) → 192.168.51.2/24 + CARP 192.168.51.1/24
- vtnet2 (PFSYNC) → 192.168.103.1/29

Secondary Firewall:
- vtnet0_vlan110 (WAN) → DOWN when BACKUP, DHCP when MASTER
- vtnet1 (LAN) → 192.168.51.3/24 + CARP 192.168.51.1/24  
- vtnet2 (PFSYNC) → 192.168.103.2/29
```

---

**Documentation Date**: October 16, 2025  
**Network Design**: Single WAN, Dual Node HA with CARP  
**Addressing**: Private IPv4 + IPv6 with static delegation
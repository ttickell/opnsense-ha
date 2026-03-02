# OPNsense HA Lab Environment

A fully virtual lab for testing CARP-based HA failover, including realistic simulation of Xfinity/Comcast and AT&T DHCPv6 prefix delegation behavior. Everything runs on the existing Proxmox host and is isolated to Proxmox-internal VLANs — no physical switch changes required.

---

## Design Goals

1. **Faithful ISP simulation** — The simulated WAN segments mimic how Xfinity and AT&T actually hand out IPv4 and IPv6 addressing (single DHCP IPv4 address; DHCPv6-PD with two /60s for Xfinity; drip-fed /64s for AT&T). See [ISP Delegation Behavior](#isp-delegation-behavior) for detail.
2. **Shared ULA space** — IPv6 uses the `fd03:17ac:e938:4000::/50` block earmarked in [opnsense-ipv6/GeneralNotes.md](../opnsense-ipv6/GeneralNotes.md) for test net delegations. This keeps the lab within the same ULA /48 as production without conflicting with any production subnet.
3. **Self-contained on Proxmox** — All VLANs are scoped to a single VLAN-aware Proxmox bridge. No physical switch reconfiguration is needed, though moving to physical switch VLANs is a straightforward future step.
4. **Console-accessible client** — A client LXC on the lab LAN is reachable via the Proxmox GUI console without needing SSH or a production network route.
5. **Mirror production HA structure** — Two OPNsense VMs with the same `ha-singleton` scripts and configuration structure as the production pair.

---

## Network Overview

```
                      Proxmox Host
          ┌──────────────────────────────────────────┐
          │                                          │
          │  vmbr-lab (VLAN-aware bridge)            │
          │                                          │
          │  VLAN 210: lab-wan-a (simulated Xfinity) │
          │    10.220.10.0/30                        │
          │    fd03:17ac:e938:4000::/64              │
          │                                          │
          │  VLAN 211: lab-wan-b (simulated AT&T)    │
          │    10.220.11.0/30                        │
          │    fd03:17ac:e938:4100::/64              │
          │                                          │
          │  VLAN 212: lab-lan (test internal)       │
          │    10.220.1.0/24                         │
          │    fd03:17ac:e938:4200::/64              │
          │                                          │
          │  VLAN 213: lab-pfsync (HA sync)          │
          │    10.220.3.0/30                         │
          └──────────────────────────────────────────┘
```

---

## IP Address Allocation

### IPv4

| Segment | VLAN | Subnet | Gateway / Notes |
|---|---|---|---|
| lab-wan-a | 210 | `10.220.10.0/30` | ISP-A sim: `.1` ; FW WAN: DHCP (`.2`) |
| lab-wan-b | 211 | `10.220.11.0/30` | ISP-B sim: `.1` ; FW WAN2: DHCP (`.2`) |
| lab-lan | 212 | `10.220.1.0/24` | CARP VIP: `.1` ; Primary FW: `.2` ; Secondary FW: `.3` |
| lab-pfsync | 213 | `10.220.3.0/30` | Primary FW: `.1` ; Secondary FW: `.2` |

### IPv6

All addresses are carved from the `fd03:17ac:e938:4000::/50` test delegation block.

| Block | Purpose |
|---|---|
| `fd03:17ac:e938:4000::/56` | Xfinity simulator — link + delegation pool |
| `fd03:17ac:e938:4000::/64` | VLAN 210 link addresses (ISP-A ↔ firewall WAN segment) |
| `fd03:17ac:e938:4040::/60` | Xfinity PD delegation #1 (handed to test firewall) |
| `fd03:17ac:e938:4050::/60` | Xfinity PD delegation #2 (handed to test firewall) |
| `fd03:17ac:e938:4100::/56` | AT&T simulator — link + delegation pool |
| `fd03:17ac:e938:4100::/64` | VLAN 211 link addresses (ISP-B ↔ firewall WAN2 segment) |
| `fd03:17ac:e938:4140::/60` | AT&T delegation pool — 8 × /64 drip-fed from this block |
| `fd03:17ac:e938:4200::/56` | Lab LAN |
| `fd03:17ac:e938:4200::/64` | VLAN 212 LAN subnet (CARP VIP: `fd03:17ac:e938:4200::1`) |

---

## ISP Delegation Behavior

### Xfinity / Comcast Simulation

Key real-world behaviors being simulated:

- **Single IPv4 address** via DHCP (no public block; one address like a residential modem).
- **Two /60 prefix delegations** handed in a single DHCPv6 exchange. The real Xfinity provides prefixes from the `2601:346::/32` range; the lab uses the equivalent ULA test blocks.
- **DUID-sensitive**: Xfinity binds delegations tightly to the DUID. The lab simulator enforces this by binding pool entries — if the test firewall's DUID changes, it gets new prefixes. This is the correct behavior to test against.
- **First IA-PD wins the DUID**: In `dhcp6c.conf`, Xfinity must be listed as the first `interface` block so the DUID used for its exchange is the primary DUID.

The `lab-isp-xfinity` LXC runs `dnsmasq` configured to issue both /60 delegations in response to a single IA-PD SOLICIT. See [isp-simulators/xfinity/dnsmasq.conf](isp-simulators/xfinity/dnsmasq.conf).

### AT&T Simulation

Key real-world behaviors being simulated:

- **Single IPv4 address** via DHCP.
- **Drip-fed /64 delegations** — AT&T's CPE hands out /64 prefixes from an internal /60, one per IA-PD request. The lab `lab-isp-att` LXC simulates this by managing a pool of 8 × /64 prefixes (`fd03:17ac:e938:4140::/64` through `fd03:17ac:e938:4147::/64`). Each SOLICIT receives one /64 from the pool; subsequent requests get the next available prefix (within the same session, the same prefix is renewed).
- **DUID less sensitive** than Xfinity in practice — the lab does not enforce strict DUID binding on AT&T.

See [isp-simulators/att/dnsmasq.conf](isp-simulators/att/dnsmasq.conf).

---

## Virtual Machines

### Resource Summary

| VM / LXC | Role | vCPUs | RAM | Disk | OS |
|---|---|---|---|---|---|
| `lab-isp-xfinity` | Xfinity ISP simulator | 1 | 256 MB | 2 GB | Alpine Linux LXC |
| `lab-isp-att` | AT&T ISP simulator | 1 | 256 MB | 2 GB | Alpine Linux LXC |
| `lab-fw-primary` | Test primary firewall | 2 | 2 GB | 8 GB | OPNsense VM |
| `lab-fw-secondary` | Test secondary firewall | 2 | 2 GB | 8 GB | OPNsense VM |
| `lab-client` | Test client (console access) | 1 | 512 MB | 4 GB | Debian LXC |

**Total**: ~5 GB RAM, ~24 GB disk.

### Network Interface Assignments

#### `lab-isp-xfinity`
| Interface | VLAN | Address |
|---|---|---|
| eth0 | 210 (untagged) | `10.220.10.1/30`, `fd03:17ac:e938:4000::1/64` |

#### `lab-isp-att`
| Interface | VLAN | Address |
|---|---|---|
| eth0 | 211 (untagged) | `10.220.11.1/30`, `fd03:17ac:e938:4100::1/64` |

#### `lab-fw-primary`
| Interface | VLAN | Role | OPNsense name |
|---|---|---|---|
| vtnet0 | 210 (untagged) | WAN (Xfinity) | `wan` |
| vtnet1 | 211 (untagged) | WAN2 (AT&T) | `wan2` |
| vtnet2 | 212 (untagged) | LAN | `lan` |
| vtnet3 | 213 (untagged) | PFSYNC | *(direct interface)* |

#### `lab-fw-secondary`
| Interface | VLAN | Role | OPNsense name |
|---|---|---|---|
| vtnet0 | 210 (untagged) | WAN (Xfinity) | `wan` |
| vtnet1 | 211 (untagged) | WAN2 (AT&T) | `wan2` |
| vtnet2 | 212 (untagged) | LAN | `lan` |
| vtnet3 | 213 (untagged) | PFSYNC | *(direct interface)* |

#### `lab-client`
| Interface | VLAN | Address |
|---|---|---|
| eth0 | 212 (untagged) | DHCP from lab firewall |

---

## Proxmox Setup

### 1. Create the lab bridge

In the Proxmox GUI under the host's **Network** tab, or via `/etc/network/interfaces`:

```
auto vmbr-lab
iface vmbr-lab inet manual
    bridge_ports none
    bridge_stp off
    bridge_fd 0
    bridge_vlan_aware yes
    bridge_vids 2-4094
```

> **Note**: `bridge_ports none` creates a fully internal bridge with no uplink to a physical NIC. All lab traffic stays inside the Proxmox host. If you later want VMs on physical switch VLANs 210-213, change `bridge_ports none` to the trunk NIC.

Apply with `ifreload -a` or reboot.

### 2. Create ISP simulator LXCs

For each ISP simulator, create an Alpine Linux LXC:
- OS template: `alpine-3.x-default`
- Network: `vmbr-lab`, VLAN tag = 210 (Xfinity) or 211 (AT&T); untagged access
- No firewall on the LXC (it acts as the upstream device)

Install dnsmasq inside each LXC:
```bash
apk add dnsmasq
```

Copy the corresponding config from [isp-simulators/](isp-simulators/) and enable the service:
```bash
rc-update add dnsmasq
rc-service dnsmasq start
```

### 3. Create OPNsense firewall VMs

Create two OPNsense VMs with four virtual NICs each, assigning to `vmbr-lab` with the VLAN tags listed in the interface tables above.

After installation, install the HA scripts using `setup-firewall`:
```bash
./setup-firewall "vtnet0 vtnet1"
```

Then copy the lab configuration files from [firewall-configs/](firewall-configs/) to `/usr/local/etc/ha-singleton.conf` on each node.

> **MAC address cloning**: Both lab firewall VMs must be configured with the same MAC address on vtnet0 and vtnet1. Set this in the Proxmox VM hardware config (Network Device → MAC address). Use the primary VM's auto-assigned MAC as the clone target.

> **DHCPv6 DUID**: After first boot, copy `/var/db/dhcp6c_duid` from the primary lab firewall to the secondary to ensure both present the same DUID to the Xfinity simulator.

### 4. Create client LXC

Create a Debian LXC:
- Network: `vmbr-lab`, VLAN 212, untagged
- Console access via Proxmox GUI

The client will receive an IPv4 address via DHCP and an IPv6 address from the lab firewall's RA. Verify connectivity:
```bash
# From client console
ping -c 3 10.220.1.1          # Lab firewall CARP VIP
curl -6 https://ipv6.google.com  # IPv6 internet (if lab FW has upstream)
```

---

## HA Configuration for Lab Firewalls

The `ha-singleton.conf` for each lab firewall is in [firewall-configs/](firewall-configs/). Key values:

### Primary (`lab-fw-primary`)
```bash
WAN_INTS="vtnet0 vtnet1"
WAN_INTERFACE_MAP="wan:vtnet0 wan2:vtnet1"
ALT_DEFROUTE_IPV4="10.220.1.3"       # Secondary FW LAN IP
ALT_DEFROUTE_IPV6="fd03:17ac:e938:4200::3"
ENABLE_IPV6="yes"
ENABLE_INTERFACE_RECONFIGURE="yes"
DEBUG="yes"   # Recommended during lab testing
```

### Secondary (`lab-fw-secondary`)
```bash
WAN_INTS="vtnet0 vtnet1"
WAN_INTERFACE_MAP="wan:vtnet0 wan2:vtnet1"
ALT_DEFROUTE_IPV4="10.220.1.2"       # Primary FW LAN IP
ALT_DEFROUTE_IPV6="fd03:17ac:e938:4200::2"
ENABLE_IPV6="yes"
ENABLE_INTERFACE_RECONFIGURE="yes"
DEBUG="yes"
```

---

## Testing Failover

### Trigger failover (from primary console)
```bash
# Drop CARP priority on the primary to force secondary to become MASTER
ifconfig carp0 down       # On lab-fw-primary
```

### Watch the logs
```bash
# On the secondary lab firewall
tail -f /var/log/system.log | grep -E "(syshook-carp|CARP|dhcp6c|rtsold)"
```

### Verify from client
```bash
# From lab-client console — ping should continue after brief pause
ping 8.8.8.8 -c 60
# Check IPv6 routing
ip -6 route show
```

### Check prefix delegation state
```bash
# On the active (MASTER) firewall
cat /var/db/ipv6-ha/dhcp6c-delegations.json
```

---

## Future: Physical Switch VLANs

To move the lab to physical switch-backed VLANs (so the lab firewalls are on real switch ports instead of virtual bridges):

1. Configure VLANs 210-213 on the physical switch.
2. Assign a trunk port from the switch to the Proxmox host.
3. Change `bridge_ports none` to `bridge_ports <trunk_nic>` in the `vmbr-lab` config.
4. Move the ISP simulator LXCs to LXCs with passthrough to a physical switch port in the appropriate VLAN (or keep them virtual — the ISP simulators don't need physical connectivity).

The firewall VMs and their network configs require no changes.

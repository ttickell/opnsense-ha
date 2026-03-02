# OPNsense HA Lab Environment

A fully virtual lab for testing CARP-based HA failover, including realistic simulation of Xfinity/Comcast and AT&T DHCPv6 prefix delegation behavior. Everything runs on the existing Proxmox host and is isolated to Proxmox-internal VLANs — no physical switch changes required.

---

## Phases

| Phase | Scope | Status |
|---|---|---|
| **Phase 1** | Isolated lab — CARP/HA + DHCPv6-PD testing with no internet access | Designed; ready to build |
| **Phase 2** | Internet-connected lab — lab-uplink VLAN, real firewall integration, end-to-end NPTv6 | Future |

This document covers Phase 1 in full. See [Phase 2 (Future)](#phase-2-future) for the planned extension.

---

## Design Goals

### Phase 1
1. **Faithful ISP simulation** — The simulated WAN segments mimic how Xfinity and AT&T actually hand out IPv4 and IPv6 addressing (single DHCP IPv4 address; DHCPv6-PD with two /60s for Xfinity; drip-fed /64s for AT&T). See [ISP Delegation Behavior](#isp-delegation-behavior) for detail.
2. **Shared ULA space** — IPv6 uses the `fd03:17ac:e938:4000::/50` block earmarked in [opnsense-ipv6/GeneralNotes.md](../opnsense-ipv6/GeneralNotes.md) for test net delegations. This keeps the lab within the same ULA /48 as production without conflicting with any production subnet.
3. **Self-contained on Proxmox** — All VLANs are scoped to a single VLAN-aware Proxmox bridge. No physical switch reconfiguration is needed, though moving to physical switch VLANs is a straightforward future step.
4. **Console-accessible client** — A client LXC on the lab LAN is reachable via the Proxmox GUI console without needing SSH or a production network route.
5. **Mirror production HA structure** — Two OPNsense VMs with the same `ha-singleton` scripts and configuration structure as the production pair.

### Phase 2
6. **Real internet routing** — Lab firewalls have a path to the internet via a lab-uplink VLAN connected to the production firewall. Enables end-to-end NPTv6 and real DHCP lease renewal testing.
7. **Physical switch migration** — VLANs 210-214 move from internal Proxmox bridge to physical switch ports, mirroring the production topology more closely.

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
| lab-pfsync | 213 | `10.220.3.0/30` | Primary FW: `.2` ; Secondary FW: `.3` |

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

## Phase 1 Task List

A sequenced checklist for building the isolated lab. Tasks are grouped by dependency order — complete each group before the next.

### Group 1 — Proxmox Prerequisites

- [ ] **1.1** Confirm Proxmox node name and API endpoint (needed for automation)
- [ ] **1.2** Download Alpine Linux LXC template (latest `alpine-3.x-default`) via Proxmox storage
- [ ] **1.3** Download Debian LXC template (latest `debian-12-standard`) via Proxmox storage
- [ ] **1.4** Download OPNsense ISO and upload to Proxmox ISO storage
  - Source: https://opnsense.org/download/ — select `dvd`, `amd64`
  - Filename pattern: `OPNsense-<version>-dvd-amd64.iso`
- [ ] **1.5** Confirm VLANs 210-213 are free on `vmbr0` — **already verified, no action needed**
  - Both nodes use OVS (`vmbr0`); lab VMs attach directly to `vmbr0` with VLAN tags 210-213
  - No new bridge required

> **Do not touch VMID 100 (`router-b`) on `proxima`.**
> This VM is the reference implementation of the production HA failover configuration. It must not be modified, cloned from, or deleted. All lab VMs use VMID 110+.

### Group 2 — ISP Simulator LXCs

- [ ] **2.1** Create `lab-isp-xfinity` LXC (Alpine, 1 vCPU, 256 MB RAM, 2 GB disk)
  - NIC: `vmbr-lab`, VLAN tag 210, untagged inside container
  - Static IP: `10.220.10.1/30`, `fd03:17ac:e938:4000::1/64`
  - No firewall
- [ ] **2.2** Create `lab-isp-att` LXC (Alpine, 1 vCPU, 256 MB RAM, 2 GB disk)
  - NIC: `vmbr-lab`, VLAN tag 211, untagged inside container
  - Static IP: `10.220.11.1/30`, `fd03:17ac:e938:4100::1/64`
  - No firewall
- [ ] **2.3** On `lab-isp-xfinity`: run `lab/isp-simulators/setup.sh` and copy `lab/isp-simulators/xfinity/dnsmasq.conf` to `/etc/dnsmasq.conf`
- [ ] **2.4** On `lab-isp-att`: run `lab/isp-simulators/setup.sh` and copy `lab/isp-simulators/att/dnsmasq.conf` to `/etc/dnsmasq.conf`
- [ ] **2.5** Verify dnsmasq is listening on each simulator: `netstat -ulnp | grep 67`
  - If DHCPv6-PD via dnsmasq fails (version incompatibility), fall back to the `dhcpd6` config blocks in the comments of each `dnsmasq.conf`

### Group 3 — Firewall VMs

- [ ] **3.1** Create `lab-fw-primary` VM (2 vCPU, 2 GB RAM, 8 GB disk, OPNsense ISO)
  - vtnet0: `vmbr-lab`, VLAN 210 — WAN (Xfinity)
  - vtnet1: `vmbr-lab`, VLAN 211 — WAN2 (AT&T)
  - vtnet2: `vmbr-lab`, VLAN 212 — LAN
  - vtnet3: `vmbr-lab`, VLAN 213 — PFSYNC
- [ ] **3.2** Create `lab-fw-secondary` VM (same spec)
  - NIC assignments identical to primary (same VLANs, same roles)
- [ ] **3.3** Record the auto-assigned MAC addresses for vtnet0 and vtnet1 on `lab-fw-primary`
- [ ] **3.4** On `lab-fw-secondary`, set vtnet0 MAC = primary's vtnet0 MAC; set vtnet1 MAC = primary's vtnet1 MAC
  - This is mandatory — ISP simulators bind DHCP leases to MAC
- [ ] **3.5** Install OPNsense on both VMs via console (boot from ISO, follow installer, assign interfaces)
  - vtnet0 → WAN, vtnet1 → WAN2, vtnet2 → LAN, vtnet3 → no assignment (used directly for PFSYNC)
  - LAN: `10.220.1.2/24` (primary), `10.220.1.3/24` (secondary)
  - PFSYNC: `10.220.3.2/30` (primary), `10.220.3.3/30` (secondary)
- [ ] **3.6** Configure CARP in OPNsense GUI on both nodes (VIP `10.220.1.1`, VHID 1)
- [ ] **3.7** Configure PFSYNC in OPNsense GUI; verify `pfctl -s References` shows sync active
- [ ] **3.8** On `lab-fw-primary`: install `ha-singleton` scripts via `setup-firewall`:
  ```bash
  ./setup-firewall "vtnet0 vtnet1"
  ```
- [ ] **3.9** Copy `lab/firewall-configs/ha-singleton-primary.conf` to `/usr/local/etc/ha-singleton.conf` on `lab-fw-primary`
- [ ] **3.10** Repeat steps 3.8–3.9 on `lab-fw-secondary` using `ha-singleton-secondary.conf`
- [ ] **3.11** Copy DHCPv6 DUID from primary to secondary:
  ```bash
  # On lab-fw-primary
  cat /var/db/dhcp6c_duid    # note the value
  # On lab-fw-secondary
  cp /var/db/dhcp6c_duid /var/db/dhcp6c_duid.bak
  # replace with primary's value
  ```
  > Do this only after primary has made at least one successful DHCPv6 exchange with the Xfinity simulator.

### Group 4 — Client LXC

- [ ] **4.1** Create `lab-client` LXC (Debian, 1 vCPU, 512 MB RAM, 4 GB disk)
  - NIC: `vmbr-lab`, VLAN 212, untagged inside container
  - DHCP for both IPv4 and IPv6 (gets address from lab firewall)
  - No firewall

### Group 5 — Smoke Tests

- [ ] **5.1** From `lab-client` console: `ping -c 3 10.220.1.1` — should reach CARP VIP
- [ ] **5.2** From `lab-client` console: `ip -6 addr` — should show a GUA from the delegated prefix
- [ ] **5.3** Trigger primary→secondary failover:
  ```bash
  # On lab-fw-primary console
  ifconfig carp0 down
  ```
- [ ] **5.4** Verify `lab-fw-secondary` logs show MASTER transition:
  ```bash
  tail -f /var/log/system.log | grep "syshook-carp"
  ```
- [ ] **5.5** From `lab-client` console: `ping -c 3 10.220.1.1` — should recover within ~5 seconds
- [ ] **5.6** Restore primary to MASTER:
  ```bash
  # On lab-fw-primary console
  ifconfig carp0 up
  ```
- [ ] **5.7** Verify PFSYNC state table is syncing: `pfctl -s state | wc -l` on both nodes should be comparable

---

## Reference

The sections below are detailed setup reference supporting the task list above.

---

## Proxmox Setup

### 1. Verify bridge — no new bridge required (OVS)

Both Proxmox nodes (`proxima`, `toliman`) use **Open vSwitch (OVSBridge `vmbr0`)**, not standard Linux bridges. OVS isolates VLANs natively, so lab VMs simply connect to the existing `vmbr0` bridge with a VLAN tag — no new bridge creation is needed.

VLANs 210-213 are confirmed unused on both nodes. All lab VMs and LXCs will be attached to `vmbr0` with the appropriate VLAN tag; OVS enforces isolation between VLANs automatically.

> **No action required for this step.** If you were expecting a `vmbr-lab` entry in the Proxmox network config, this is why it won't be there.

**Phase 2 note**: `proxima` has an unassigned physical NIC (`enp5s0`) not currently in any bridge or bond. This is the candidate uplink NIC for the Phase 2 lab-uplink (VLAN 214). No action now.

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

## Phase 2 (Future)

Phase 2 extends the lab with a real internet path and physical switch backing. It has two independent sub-goals that can be done in either order.

### 2A — Internet Access via Lab-Uplink

Adds a VLAN 214 `lab-uplink` segment connecting the lab firewall pair to the production firewall:

- VLAN 214: `10.220.0.0/30` — production FW: `.1`; lab FW CARP VIP: `.2`
- Changes on production FW: static route for `10.220.1.0/24` (lab LAN) via `10.220.0.2`; firewall rule permitting lab LAN → internet (block lab LAN → production LAN)
- Changes on lab FW VMs: add a 5th NIC on `vmbr-lab`, VLAN 214 — this interface must **not** appear in `WAN_INTS`; add default route to `10.220.0.1`
- IPv6: static route on production FW for `fd03:17ac:e938:4200::/56` via lab FW VIP
- Enables: real DHCP lease renewal testing, NPTv6 end-to-end, `ping 8.8.8.8` from `lab-client`

### 2B — Physical Switch VLANs

Moves VLANs 210-213 from the internal OVS bridge to physical switch ports:

1. Configure VLANs 210-213 on the physical switch.
2. `proxima` has `enp5s0` currently unassigned — this is the candidate trunk NIC. Add it to `bond0` or create a new OVS port for it.
3. Tag VLANs 210-213 on the physical switch trunk port connected to `enp5s0`.
4. ISP simulator LXCs can optionally be moved to physical ports in their respective VLANs, or left virtual.

The firewall VMs and their `ha-singleton.conf` configs require no changes for this migration.

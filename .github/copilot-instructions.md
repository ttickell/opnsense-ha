# GitHub Copilot Instructions — opnsense-ha

This file describes the project layout, conventions, and key design decisions so that AI assistants and new contributors can work effectively without re-deriving context from scratch.

---

## AI Assistant Directives

- **Answer direct questions directly.** If the user asks a yes/no or factual question, answer it first. Do not take action in response to a question.
- **Propose before acting.** If a question implies that action may be needed, state what action you think is appropriate and wait for explicit confirmation before doing anything.
- **No implicit actions.** Do not run commands, install, edit, deploy, or validate unless the user explicitly asks for that exact action.
- **Read-only checks also require consent.** Treat inspections, audits, and diagnostics as actions; only run them when explicitly requested.
- **One-step execution only.** Do not chain multiple phases (e.g., install + preflight + debug) unless the user explicitly requests the full sequence.
- **Intent gate before actions.** Before any action, state one-line intent and wait for explicit go-ahead.
- **Facts vs next step.** Clearly separate observed facts from proposed next steps in responses.
- **Label assumptions.** If any assumption is required, label it and obtain confirmation before acting on it.
- **Scope discipline.** Keep responses tightly scoped to the user's request; avoid extra unsolicited steps.
- **Path clarity in VS Code chat.** When answering path questions, state whether the path is absolute or workspace-relative, and provide the full absolute path in plain text (for example: `/usr/local/etc/checkset-nptv6.yml`) to avoid UI path-chip collapsing ambiguity.
- **Debug command-first for system issues.** When debugging system-level commands, first isolate and validate the exact command behavior (with minimal repro steps) before editing project files. Do not iterate through edit/commit/push cycles until command-level root cause is confirmed.
- **Always run the tool after fixing tool bugs.** When developing or modifying an operational tool/script, validate the fix by executing that same tool/script and confirming behavior. Never patch a tool bug "on the side" and assume the fix worked without running it.
- **Check docs before assuming.** Before concluding a tool or dependency cannot do something, verify the relevant official documentation (or in-repo reference docs) and only then choose a workaround.

---

## Project Purpose

`opnsense-ha` provides automated CARP-based high-availability failover for a pair of OPNsense firewall nodes. It handles:

- Bringing WAN interfaces up (MASTER) or down (BACKUP) on every CARP state change
- DHCP lease renewal via `configctl` when a node transitions to MASTER
- IPv6 service management (`rtsold`, `dhcp6c`, `radvd`) conditioned on CARP role
- Backup routing through the peer firewall's LAN IP while in BACKUP state
- PFSYNC stability tuning to prevent CARP flapping
- IPv6 prefix delegation tracking, ULA mapping, and NPTv6 rule coordination
- An IPv6 connectivity monitor daemon as an rc.d service

The solution is installed on both firewalls and reacts to OPNsense's native CARP syshook events.

---

## Repository Layout

```
opnsense-ha/
├── README.md                          # Primary documentation — start here
├── TODO.md                            # Current status and roadmap
├── LICENSE
├── .gitignore
├── .gitmodules                        # Declares three upstream submodules
│
├── setup-firewall                     # Installer script (sh); run on each OPNsense node
├── cleanup-firewall                   # Uninstaller script (sh)
├── test-ha-setup.sh                   # Automated installation validation script
│
├── docs/                              # Secondary / reference documentation
│   ├── NETWORK-TOPOLOGY.md            # IP addressing, segment layout, WAN prereqs
│   ├── Goal.md                        # Original design goals and real-site config inputs
│   ├── HOW_TO_DEBUG.md                # Debugging protocol; configctl syntax reference
│   ├── IMPLEMENTATION.md              # v2.0 implementation summary
│   ├── IMPLEMENTATION_ANALYSIS.md     # Analysis of implementation decisions
│   ├── IPV6_INTEGRATION_ANALYSIS.md   # Analysis of IPv6/HA integration requirements
│   ├── IPV6_Integration.md            # Integration goals for opnsense-ipv6 submodule
│   ├── IPV6_SERVICE_VALIDATION.md     # IPv6 service validation notes
│   ├── DHCP_LEASE_CLEARING_v2.8.md    # DHCP lease clearing design (v2.8)
│   ├── IPv6-Integration.md            # IPv6 dual-WAN integration documentation
│   └── dhcp_requests.txt              # Sample/captured DHCP request data for reference
│
├── usr/local/                         # Files installed to /usr/local/ on each firewall
│   ├── etc/
│   │   ├── ha-singleton.conf.example  # Configuration template — copy to ha-singleton.conf
│   │   ├── rc.d/
│   │   │   └── ipv6_monitor           # rc.d service script for the IPv6 monitor daemon
│   │   ├── rc.syshook.d/
│   │   │   └── carp/
│   │   │       └── 00-ha-singleton    # Main CARP hook — triggered on every CARP event
│   │   └── ipv6/                      # IPv6-specific config fragments
│   └── bin/
│       ├── ha-ipv6-integration.sh     # IPv6 NPTv6/delegation coordination on CARP events
│       ├── dhcp6c-wan-script.sh       # dhcp6c exit hook; triggers prefix-json update
│       ├── dhcp6c-prefix-json         # Writes current delegations to JSON state file
│       ├── dhcp6c-ula-mapping.py      # Maps ULA prefixes to delegated prefixes
│       ├── ipv6-connectivity-monitor.py # Daemon: monitors IPv6 connectivity continuously
│       ├── ipv6-monitor               # Wrapper/launcher for the monitor daemon
│       └── debug_log                  # Debug log helper utility
│
├── real/                              # Production configs (gitignored — sensitive)
│   ├── ha-singleton-primary.conf      # Config for the primary firewall
│   └── ha-singleton-secondary.conf    # Config for the secondary firewall
│
├── test/                              # Test environment ha-singleton configs
│   ├── ha-singleton-primary.conf
│   └── ha-singleton-secondary.conf
│
├── lab/                               # Virtual HA lab environment
│   ├── README.md                      # Lab design, IP allocation, Proxmox setup steps
│   ├── isp-simulators/
│   │   ├── setup.sh                   # Bootstrap script for Alpine ISP simulator LXCs
│   │   ├── xfinity/dnsmasq.conf       # Simulates Xfinity: single IPv4 + two /60 PD delegations
│   │   └── att/dnsmasq.conf           # Simulates AT&T: single IPv4 + drip-fed /64 PD delegations
│   └── firewall-configs/
│       ├── ha-singleton-primary.conf  # ha-singleton.conf for lab-fw-primary
│       └── ha-singleton-secondary.conf # ha-singleton.conf for lab-fw-secondary
│
├── opnsense-core/                     # Submodule: upstream OPNsense core source (reference only)
├── opnsense-docs/                     # Submodule: upstream OPNsense documentation (reference only)
└── opnsense-ipv6/                     # Submodule: self-developed IPv6 scripts (reference only)
```

---

## Git Submodules

This repo contains three submodules. **None of them are modified here.** Do not edit files under any of these directories.

### `opnsense-core/`
The official [OPNsense core](https://github.com/opnsense/core) source tree. Included as a read-only reference so that script conventions, `configctl` action definitions, and OPNsense API patterns can be verified against the actual implementation without leaving the repo.

### `opnsense-docs/`
The official [OPNsense documentation](https://github.com/opnsense/docs) source. Included as a read-only reference for looking up GUI paths, feature descriptions, and API documentation.

### `opnsense-ipv6/`
A self-developed repo of findings and scripts written to make IPv6 work on OPNsense with two specific ISPs (Xfinity / Comcast and AT&T) and to leverage all available Prefix Delegation (PD) assignments to add IPv6 to internal subnets.

**Important caveats about this submodule**:
- It was written experimentally — the author acknowledges it likely does not follow OPNsense best practices.
- It captures real-world discoveries about how AT&T and Comcast expose DHCPv6 PD, which are not well documented elsewhere.
- The integration goals for pulling this work into `opnsense-ha` properly are tracked in [docs/IPV6_Integration.md](../docs/IPV6_Integration.md) and [docs/IPV6_INTEGRATION_ANALYSIS.md](../docs/IPV6_INTEGRATION_ANALYSIS.md).
- When referencing this submodule, treat it as a source of working logic to be understood and re-implemented to OPNsense standards — not code to be copied verbatim.

---

## The Central Script: `usr/local/etc/rc.syshook.d/carp/00-ha-singleton`

This is the only file that runs on every CARP state change. OPNsense calls it with two arguments:

```
00-ha-singleton <interface> <CARP_STATUS>
# CARP_STATUS is one of: MASTER | BACKUP | INIT
```

Execution flow on MASTER transition:
1. Acquire lock (prevents concurrent runs)
2. Set `net.pfsync.carp_demotion_factor=0` (CARP stability)
3. Discover WAN interfaces via `build_wan_map()` (parses `/conf/config.xml`)
4. Bring all discovered WAN device names **up** via `configctl interface linkup start`
5. Wait `INTERFACE_SETTLE_TIME` seconds
6. Clear stale default routes
7. Trigger DHCP renewal: `configctl interface newip <opnsense_name>` + `rc.configure_interface <opnsense_name>` for each WAN
8. Start IPv6 services (`rtsold`, `dhcp6c`, `radvd`)

BACKUP transition:
1. Acquire lock
2. Set PFSYNC demotion factor
3. Bring all discovered WAN device names **down**
4. Stop IPv6 services
5. Inject backup default routes (`ALT_DEFROUTE_IPV4`, `ALT_DEFROUTE_IPV6`)

---

## Configuration File: `/usr/local/etc/ha-singleton.conf`

Sourced by `00-ha-singleton` at runtime. Every variable has a default inside the script; the conf file overrides them. Use [usr/local/etc/ha-singleton.conf.example](../usr/local/etc/ha-singleton.conf.example) as the template.

### Critical variables

| Variable | Purpose |
|---|---|
| `WAN_MAP` | Auto-discovered at startup by `build_wan_map()` from `/conf/config.xml`. Each entry is `opnsense_name:device:label` (e.g. `wan:vtnet0:wan opt1:vtnet1:wan2`). Can be set manually in `ha-singleton.conf` to override discovery. |
| `ALT_DEFROUTE_IPV4` | Peer firewall's LAN IPv4 — injected as default route when BACKUP |
| `ALT_DEFROUTE_IPV6` | Peer firewall's LAN IPv6 — injected as default route when BACKUP |
| `SERVICES` | Services to start (MASTER) / stop (BACKUP) |
| `ENABLE_IPV6` | Toggle all IPv6 management |
| `ENABLE_INTERFACE_RECONFIGURE` | Toggle DHCP lease renewal on MASTER |
| `DEBUG` | Set to `yes` for verbose syslog output |

WAN interfaces are discovered automatically. `WAN_INTS` and `WAN_INTERFACE_MAP` are no longer config file variables. To add a second WAN, set its OPNsense interface `<descr>` to `WAN2`–`WAN9` in the GUI.

---

## WAN Interface Requirements

> See [docs/NETWORK-TOPOLOGY.md](../docs/NETWORK-TOPOLOGY.md) for full detail. Summary:

1. **Identical MAC addresses** on both nodes' WAN interfaces — configure via `Interfaces → [WAN] → MAC address` in OPNsense GUI. ISPs bind DHCP leases to MAC; mismatches cause post-failover connectivity gaps.
2. **Identical DHCPv6 DUID** on both nodes — copy `/var/db/dhcp6c_duid` from primary to secondary. DHCPv6 servers bind prefix delegations to DUID.
3. **DHCP addressing** (not static) — the `configctl interface reconfigure/newip` renewal path only applies to DHCP interfaces.
4. **No CARP VIPs on WAN** — WAN ownership is managed by up/down logic, not CARP VIPs.

---

## Coding & Scripting Conventions

- All scripts are POSIX `sh` (not bash). Use `[ ]` not `[[ ]]`, no arrays, no process substitution.
- Logging goes through `logger -p <priority> -t <TAG>`. Tags follow the pattern `syshook-carp-ha-singleton` or `ha-ipv6-*`.
- OPNsense native commands are preferred over direct system calls:
  - **Correct**: `configctl interface linkup start <iface>` (space-separated)
  - **Wrong**: `configctl interface linkup.start <iface>` (dot-separated — silently fails)
  - See [docs/HOW_TO_DEBUG.md](../docs/HOW_TO_DEBUG.md) for the full `configctl` syntax reference.
- Feature flags (`ENABLE_*`) must wrap every optional behaviour so operators can disable features without editing the script.
- All changes to `00-ha-singleton` must be tested in the test environment before updating `real/` configs.

---

## Production Physical Plant

The production HA pair is **asymmetric** — the two nodes use different hardware and connect to the modems differently:

| | Primary | Secondary |
|---|---|---|
| Hardware | Physical OPNsense appliance | Proxmox VM |
| WAN connectivity | Dedicated physical ports in isolated access switch VLANs (one port per ISP) | VLAN sub-interfaces on a tagged trunk NIC on the Proxmox host |
| LAN | Physical port, untagged (VLAN 1) | Virtual NIC, untagged (VLAN 1) |
| WAN device names | `igc0`, `igc1` | `vtnet4`, `vtnet5` |
| Config file | `real/ha-singleton-primary.conf` | `real/ha-singleton-secondary.conf` |

### Key physical-plant constraints

- **Untagged LAN is non-negotiable.** The primary internal network must run on untagged VLAN 1 so it works with any switch and survives hardware replacement without switch reconfiguration.
- **VLAN isolation per WAN is required.** Each ISP modem is isolated in its own VLAN containing only the modem and the firewall port. This is enforced at the switch/Proxmox bridge layer, not in OPNsense config.
- **Port labeling must be maintained.** Ports must be labeled WAN1, WAN2, LAN, PFSYNC so a hardware replacement by a non-expert is possible by following labels alone. See README.md → *Hardware Replacement Guidance*.
- **Config files differ per node by design.** The HA scripts are hardware-agnostic; only `ha-singleton.conf` contains node-specific device names.

---

## Real vs Test Environments

| Directory | Purpose |
|---|---|
| `test/` | Test firewall pair (vtnet interfaces, private subnets) |
| `real/` | Production firewall pair — **gitignored**, never committed |

The `real/` directory is excluded from version control via `.gitignore`. Production interface names, IP addresses, and credentials must never appear in committed files.

---

## Proxmox Environment

The Proxmox cluster has two nodes: `proxima` (31 GB RAM, primary lab target) and `toliman` (7 GB RAM). Both use **Open vSwitch (OVSBridge `vmbr0`)** — not standard Linux bridges.

### Protected VMs — do not modify

| VMID | Name | Node | Why protected |
|---|---|---|---|
| 100 | `router-b` | proxima | Reference implementation of the production HA failover pair. Preserved for comparison and rollback reference. |

### Lab VM allocation

Lab VMs use VMID 110+ on `proxima`, VLANs 210-213 on `vmbr0`. See `lab/` for full design.

### Credentials

Proxmox API credentials are stored in `.env` (gitignored). Load with `source .env` before making API calls.

---

## Documentation Conventions

- **README.md** is the user-facing entry point. Keep it current with every feature change.
- **docs/** holds reference, analysis, and design documents. Prefer updating existing docs over creating new ones.
- When adding a new feature, update README.md (Features list + relevant section) and the appropriate `docs/` file.
- All WAN-level prerequisites must be reflected in both README.md (`## WAN Interface Prerequisites`) and docs/NETWORK-TOPOLOGY.md (`### Key Configuration Points`).

---

## Key Documents by Task

| Task | Read first |
|---|---|
| Understanding failover flow | README.md → Key Features; `00-ha-singleton` script |
| Physical plant / deployment topology | README.md → Physical Deployment Topology; [docs/NETWORK-TOPOLOGY.md](../docs/NETWORK-TOPOLOGY.md) → Production Deployment Topology |
| Network addressing / IP layout | [docs/NETWORK-TOPOLOGY.md](../docs/NETWORK-TOPOLOGY.md) |
| WAN setup checklist | README.md → WAN Interface Prerequisites |
| Hardware replacement procedure | README.md → Hardware Replacement Guidance |
| Debugging `configctl` errors | [docs/HOW_TO_DEBUG.md](../docs/HOW_TO_DEBUG.md) |
| IPv6 prefix delegation / NPTv6 | [docs/IPV6_Integration.md](../docs/IPV6_Integration.md); `opnsense-ipv6/` submodule |
| Lab setup and ISP simulation | [lab/README.md](../lab/README.md); `lab/isp-simulators/`; `lab/firewall-configs/` |
| Production site config | [docs/Goal.md](../docs/Goal.md); `real/` (local only) |
| Test validation | `test-ha-setup.sh`; `test/` configs |

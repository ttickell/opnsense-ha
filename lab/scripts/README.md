# lab/scripts

Reusable Python scripts for building, checking, and tearing down the Phase 1 lab environment via the Proxmox API.

## Prerequisites

- Python 3.11+ (stdlib only — no pip installs needed)
- `.env` in the repo root with `PROX_MOX_URL`, `PROX_MOX_USER`, `PROX_MOX_TOKEN`
- Run from the **repo root**: `python3 lab/scripts/<script>.py`

## Scripts

| Script | Purpose |
|---|---|
| `lib.py` | Shared library — API client, constants, helpers. Not run directly. |
| `00_prereqs.py` | Check Proxmox connectivity; download Alpine + Debian LXC templates if missing. |
| `01_create_isp_sims.py` | Create and configure `lab-isp-xfinity` (CTID 110) and `lab-isp-att` (CTID 111). |
| `02_create_firewalls.py` | Create `lab-fw-primary` (VMID 112) and `lab-fw-secondary` (VMID 113) with matched WAN MACs. |
| `03_create_client.py` | Create `lab-client` (CTID 114) on the lab LAN. |
| `status.py` | Show current run state and resource usage for all lab VMs. |
| `destroy.py` | Stop and delete all lab VMs/LXCs (110-114). Prompts for confirmation. |

## Run order

```
python3 lab/scripts/00_prereqs.py          # download templates if needed
python3 lab/scripts/01_create_isp_sims.py  # ISP simulators
python3 lab/scripts/02_create_firewalls.py # OPNsense VMs (then install via console)
python3 lab/scripts/03_create_client.py    # client LXC
python3 lab/scripts/status.py              # verify
```

## Reset / rebuild

```
python3 lab/scripts/destroy.py   # tears down 110-114 (prompts for YES)
# then re-run create scripts above
```

## VMID assignments

| VMID/CTID | Type | Name | Role |
|---|---|---|---|
| 100 | VM | `router-b` | **PROTECTED** — reference impl, never modify |
| 110 | LXC | `lab-isp-xfinity` | Xfinity ISP simulator (dnsmasq, VLAN 210) |
| 111 | LXC | `lab-isp-att` | AT&T ISP simulator (dnsmasq, VLAN 211) |
| 112 | VM | `lab-fw-primary` | OPNsense primary firewall |
| 113 | VM | `lab-fw-secondary` | OPNsense secondary firewall |
| 114 | LXC | `lab-client` | Test client (DHCP, VLAN 212) |

## Notes

- All scripts are **idempotent** — re-running skips resources that already exist.
- `destroy.py --yes` skips the confirmation prompt for scripted resets.
- OPNsense installation on VMIDs 112 and 113 must be done manually via the Proxmox console — the API cannot automate the OPNsense installer.
- IPv4/IPv6 constants and VMID assignments live in `lib.py`. Edit there if the lab plan changes.

#!/usr/bin/env python3
"""
02_create_firewalls.py — Create lab firewall VMs.

Creates:
  VMID 112  lab-fw-primary    OPNsense VM  2 vCPU  2 GB RAM  8 GB disk
  VMID 113  lab-fw-secondary  OPNsense VM  2 vCPU  2 GB RAM  8 GB disk

NICs (both VMs):
  vtnet0 — VLAN 210  WAN  (Xfinity)
  vtnet1 — VLAN 211  WAN2 (AT&T)
  vtnet2 — VLAN 212  LAN
  vtnet3 — VLAN 213  PFSYNC

IMPORTANT: vtnet0 and vtnet1 on the secondary are assigned the same MAC
addresses as the primary. This is required for ISP DHCP binding.

The VMs are created and started but OPNsense installation must be completed
via the Proxmox console (VNC). See lab/README.md for post-install steps.

Usage:
    python3 lab/scripts/02_create_firewalls.py
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lib


def _net(vlan: int, mac: str = "", firewall: bool = False) -> str:
    """Build a Proxmox net parameter string."""
    s = "virtio"
    if mac:
        s += f"={mac}"
    s += f",bridge=vmbr0,tag={vlan}"
    if firewall:
        s += ",firewall=1"
    else:
        s += ",firewall=0"
    return s


def _extract_mac(net_str: str) -> str | None:
    """Extract MAC address from a Proxmox net config string."""
    m = re.search(r"([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})", net_str)
    return m.group(1) if m else None


def create_vm(vmid: int, name: str, net0: str, net1: str,
              net2: str, net3: str) -> bool:
    if lib.vm_exists(vmid):
        lib.print_skip(f"{name} (VMID {vmid})")
        return True

    print(f"\n  Creating {name} (VMID {vmid})...")

    params = {
        "vmid":      vmid,
        "name":      name,
        "memory":    2048,
        "cores":     2,
        "sockets":   1,
        "cpu":       "host",
        "net0":      net0,
        "net1":      net1,
        "net2":      net2,
        "net3":      net3,
        "ide2":      f"{lib.OPNSENSE_ISO},media=cdrom",
        "scsi0":     f"{lib.STORAGE_VM}:8",   # 8 GB system disk
        "scsihw":    "virtio-scsi-pci",
        "boot":      "order=ide2;scsi0",
        "ostype":    "other",
        "onboot":    0,
        "agent":     0,
        "description": f"Lab OPNsense firewall. Managed by lab/scripts.",
    }

    try:
        upid = lib.api_post(f"/api2/json/nodes/{lib.NODE}/qemu", params)
        if not lib.wait_for_task(upid, label=f"create {name}", timeout=120):
            return False
        lib.print_ok(f"Created {name}")
        return True
    except Exception as e:
        lib.print_err(f"Create failed: {e}")
        return False


def get_vm_macs(vmid: int) -> tuple[str | None, str | None]:
    """Return (net0_mac, net1_mac) from a VM config."""
    try:
        cfg = lib.api_get(f"/api2/json/nodes/{lib.NODE}/qemu/{vmid}/config")
        mac0 = _extract_mac(cfg.get("net0", ""))
        mac1 = _extract_mac(cfg.get("net1", ""))
        return mac0, mac1
    except Exception:
        return None, None


def main():
    print("=" * 60)
    print("Step 2: Create Firewall VMs")
    print("=" * 60)

    # --- Primary ---
    print(f"\n--- lab-fw-primary (VMID {lib.VMID_FW_PRIMARY}) ---")
    primary_exists = lib.vm_exists(lib.VMID_FW_PRIMARY)

    ok = create_vm(
        vmid=lib.VMID_FW_PRIMARY,
        name="lab-fw-primary",
        net0=_net(lib.VLAN_WAN_A),
        net1=_net(lib.VLAN_WAN_B),
        net2=_net(lib.VLAN_LAN),
        net3=_net(lib.VLAN_PFSYNC),
    )
    if not ok:
        sys.exit(1)

    # Get primary's WAN MACs for the secondary
    mac0, mac1 = get_vm_macs(lib.VMID_FW_PRIMARY)
    if not mac0 or not mac1:
        lib.print_err("Could not read primary's MAC addresses.")
        sys.exit(1)
    lib.print_ok(f"Primary WAN MACs:  net0={mac0}  net1={mac1}")

    # --- Secondary (inherits WAN MACs from primary) ---
    print(f"\n--- lab-fw-secondary (VMID {lib.VMID_FW_SECONDARY}) ---")
    ok = create_vm(
        vmid=lib.VMID_FW_SECONDARY,
        name="lab-fw-secondary",
        net0=_net(lib.VLAN_WAN_A, mac=mac0),   # same MAC as primary
        net1=_net(lib.VLAN_WAN_B, mac=mac1),   # same MAC as primary
        net2=_net(lib.VLAN_LAN),
        net3=_net(lib.VLAN_PFSYNC),
    )
    if not ok:
        sys.exit(1)

    # Verify secondary MACs match
    s_mac0, s_mac1 = get_vm_macs(lib.VMID_FW_SECONDARY)
    if s_mac0 == mac0 and s_mac1 == mac1:
        lib.print_ok(f"Secondary WAN MACs match primary ✓")
    else:
        lib.print_err(
            f"Secondary MACs do not match!\n"
            f"  Expected: {mac0}, {mac1}\n"
            f"  Got:      {s_mac0}, {s_mac1}"
        )

    print("\n" + "=" * 60)
    print("Firewall VMs created.")
    print("=" * 60)
    print("""
Next steps (manual — via Proxmox console):

  1. Open Proxmox GUI → proxima → lab-fw-primary (112) → Console
  2. Start the VM and install OPNsense from the DVD ISO
  3. Assign interfaces when prompted:
       vtnet0 → WAN      (Xfinity)
       vtnet1 → WAN2     (AT&T)
       vtnet2 → LAN
       vtnet3 → (skip — used for PFSYNC directly from OPNsense GUI)
  4. Set LAN IP: 10.220.1.2/24  gateway: (none)
  5. Repeat for lab-fw-secondary (113):
       LAN IP: 10.220.1.3/24
  6. After both installs, configure CARP and PFSYNC via OPNsense GUI
  7. Install ha-singleton scripts via setup-firewall
  8. Copy lab/firewall-configs/ ha-singleton.conf to each node
  9. Run 03_create_client.py to create the client LXC
""")


if __name__ == "__main__":
    main()

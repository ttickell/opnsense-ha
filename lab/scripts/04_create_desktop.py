#!/usr/bin/env python3
"""
04_create_desktop.py -- Create an Ubuntu 25.04 desktop VM on the lab LAN.

Creates:
  VMID 115  lab-desktop  Ubuntu 25.04 desktop  2 vCPU  4 GB RAM  32 GB disk
  NIC: VLAN 212 (lab LAN) -- gets IP from OPNsense DHCP (10.220.1.100-150)

The Ubuntu 25.04 desktop ISO is already on Synology storage. After creation
the VM boots from the ISO -- install Ubuntu via the Proxmox VNC console, then
use Firefox inside the VM to reach the OPNsense GUI at https://10.220.1.1

Usage:
    python3 lab/scripts/04_create_desktop.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lib

VMID = lib.VMID_DESKTOP
NAME = "lab-desktop"


def create_vm() -> bool:
    if lib.vm_exists(VMID):
        lib.print_skip(f"{NAME} (VMID {VMID})")
        return True

    print(f"\n  Creating {NAME} (VMID {VMID})...")

    params = {
        "vmid":    VMID,
        "name":    NAME,
        "memory":  4096,
        "cores":   2,
        "sockets": 1,
        "cpu":     "host",
        "scsihw":  "virtio-scsi-pci",
        "scsi0":   f"{lib.STORAGE_VM}:32",
        "ide2":    f"{lib.UBUNTU_DESKTOP_ISO},media=cdrom",
        "net0":    f"virtio,bridge=vmbr0,tag={lib.VLAN_LAN},firewall=0",
        "boot":    "order=ide2;scsi0",
        "vga":     "std",
        "ostype":  "l26",
        "onboot":  0,
        "description": (
            "Ubuntu 25.04 desktop VM on lab LAN.\n"
            "Install via Proxmox VNC console, then Firefox -> https://10.220.1.1"
        ),
    }

    try:
        upid = lib.api_post(f"/api2/json/nodes/{lib.NODE}/qemu", params)
        if not lib.wait_for_task(upid, label=f"create {NAME}", timeout=60):
            return False
        lib.print_ok(f"Created {NAME}")
    except Exception as e:
        lib.print_err(f"Create failed: {e}")
        return False
    return True


def main():
    print("=" * 60)
    print("Step 4: Create Ubuntu Desktop VM")
    print("=" * 60)

    if not create_vm():
        sys.exit(1)

    status = lib.vm_status(VMID)
    if status != "running":
        print(f"\n  Starting {NAME}...")
        if not lib.start_vm(VMID, "qemu"):
            lib.print_err("Failed to start VM")
            sys.exit(1)
        lib.print_ok("VM started")
    else:
        lib.print_ok("VM already running")

    print()
    print("=" * 60)
    print("lab-desktop VM is booting from the Ubuntu 25.04 ISO.")
    print()
    print("Next steps:")
    print(f"  1. Open Proxmox GUI -> proxima -> lab-desktop ({VMID}) -> Console")
    print("  2. Install Ubuntu (DHCP for network -- will get 10.220.1.100+)")
    print("  3. After install: eject ISO and reboot")
    print("  4. Open Firefox -> https://10.220.1.1  (OPNsense CARP VIP)")
    print("                 or https://10.220.1.2  (primary direct)")
    print("=" * 60)


if __name__ == "__main__":
    main()

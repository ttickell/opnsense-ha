#!/usr/bin/env python3
"""
03_create_client.py — Create the lab client LXC.

Creates:
  CTID 114  lab-client  Debian LXC  VLAN 212  DHCP

The client gets its IP via DHCP from the lab firewall CARP VIP (10.220.1.1).
Access via Proxmox console (no SSH or production route needed).

Usage:
    python3 lab/scripts/03_create_client.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lib


def create_client() -> bool:
    vmid = lib.VMID_CLIENT
    name = "lab-client"

    if lib.vm_exists(vmid):
        lib.print_skip(f"{name} (CTID {vmid})")
        return True

    print(f"\n  Creating {name} (CTID {vmid})...")

    tpl = lib.find_template(lib.STORAGE_TPL, "debian")
    if not tpl:
        lib.print_err("Debian template not found. Run 00_prereqs.py first.")
        return False
    print(f"  Template: {tpl}")

    net0 = (
        f"name=eth0,bridge=vmbr0,tag={lib.VLAN_LAN},"
        f"ip=dhcp,ip6=dhcp,"
        f"firewall=0"
    )

    params = {
        "vmid":         vmid,
        "hostname":     name,
        "ostemplate":   tpl,
        "storage":      lib.STORAGE_VM,
        "rootfs":       f"{lib.STORAGE_VM}:4",   # 4 GB
        "cores":        1,
        "memory":       512,
        "swap":         256,
        "net0":         net0,
        "onboot":       0,
        "unprivileged": 1,
        "description":  "Lab test client. DHCP from lab firewall. Access via Proxmox console.",
    }

    try:
        upid = lib.api_post(f"/api2/json/nodes/{lib.NODE}/lxc", params)
        if not lib.wait_for_task(upid, label=f"create {name}"):
            return False
        lib.print_ok(f"Created {name}")
    except Exception as e:
        lib.print_err(f"Create failed: {e}")
        return False

    return True


def start_and_verify() -> bool:
    vmid = lib.VMID_CLIENT
    status = lib.vm_status(vmid)
    if status == "running":
        lib.print_ok("lab-client already running")
        return True

    print("  Starting lab-client...")
    if not lib.start_vm(vmid, "lxc"):
        lib.print_err("Failed to start lab-client")
        return False
    time.sleep(5)

    if not lib.ensure_ssh_key():
        print("  ⚠  SSH not set up — skipping IP check. Verify via Proxmox console.")
        return True

    rc, log = lib.pct_exec(vmid,
        "ip addr show eth0 | grep 'inet ' || echo 'no-ip-yet'")
    if "no-ip-yet" in log or rc != 0:
        print("  ⚠  No IP yet — DHCP may still be in progress")
        print("     Wait for lab firewalls to be up, then check: ip addr show eth0")
    else:
        lib.print_ok(f"Client IP: {log.strip()}")

    return True


def main():
    print("=" * 60)
    print("Step 3: Create Lab Client LXC")
    print("=" * 60)

    if not create_client():
        sys.exit(1)

    if not start_and_verify():
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Lab client ready.")
    print("=" * 60)
    print("""
Access via Proxmox GUI → proxima → lab-client (114) → Console

Verify connectivity once the lab firewalls are up:
  ping -c 3 10.220.1.1              # CARP VIP
  ip -6 addr                         # should show delegated prefix addr
  ping6 -c 3 fd03:17ac:e938:4200::1  # CARP VIP IPv6

Run status.py at any time to check the state of all lab VMs.
""")


if __name__ == "__main__":
    main()

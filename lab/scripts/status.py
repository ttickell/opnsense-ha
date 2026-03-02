#!/usr/bin/env python3
"""
status.py — Show current state of all lab VMs and LXCs.

Usage:
    python3 lab/scripts/status.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lib

LAB_NAMES = {
    lib.VMID_ISP_XFINITY:  ("lxc",  "lab-isp-xfinity"),
    lib.VMID_ISP_ATT:      ("lxc",  "lab-isp-att"),
    lib.VMID_FW_PRIMARY:   ("qemu", "lab-fw-primary"),
    lib.VMID_FW_SECONDARY: ("qemu", "lab-fw-secondary"),
    lib.VMID_CLIENT:       ("lxc",  "lab-client"),
}

STATUS_ICON = {
    "running": "▶",
    "stopped": "■",
    "paused":  "⏸",
}


def main():
    print("=" * 60)
    print("Lab VM Status")
    print("=" * 60)
    print(f"\n  {'VMID':<6} {'Type':<5} {'Name':<24} {'Status'}")
    print(f"  {'-'*4}  {'-'*4}  {'-'*22}  {'-'*10}")

    all_running = True
    any_missing = False

    for vmid, (kind, name) in LAB_NAMES.items():
        try:
            s = lib.api_get(f"/api2/json/nodes/{lib.NODE}/{kind}/{vmid}/status/current")
            status = s.get("status", "unknown")
            icon = STATUS_ICON.get(status, "?")
            cpu = s.get("cpu", 0)
            mem = s.get("mem", 0)
            maxmem = s.get("maxmem", 1)
            mem_pct = int(mem / maxmem * 100) if maxmem else 0
            extra = ""
            if status == "running":
                extra = f"  cpu={cpu*100:.0f}%  mem={mem_pct}%"
            else:
                all_running = False
            print(f"  {vmid:<6} {kind:<5} {name:<24} {icon} {status}{extra}")
        except Exception:
            print(f"  {vmid:<6} {kind:<5} {name:<24} ✗ not found")
            any_missing = True
            all_running = False

    print()
    if any_missing:
        print("  Some VMs not found — run the create scripts to build the lab.")
    elif all_running:
        print("  All lab VMs running. ✓")
    else:
        print("  Some VMs are stopped. Start them via Proxmox GUI or:")
        for vmid, (kind, name) in LAB_NAMES.items():
            s = lib.vm_status(vmid)
            if s and s != "running":
                print(f"    {name}: currently {s}")

    # Show ISP sim DHCP health if running
    for vmid, (kind, name) in LAB_NAMES.items():
        if kind != "lxc" or "isp" not in name:
            continue
        if lib.vm_status(vmid) != "running":
            continue
        if lib._ssh_key_exists():
            rc, log = lib.pct_exec(vmid,
                "rc-service dnsmasq status 2>&1 | head -1")
            if rc == 0:
                print(f"  {name} dnsmasq: {log.strip()}")

    print()


if __name__ == "__main__":
    main()

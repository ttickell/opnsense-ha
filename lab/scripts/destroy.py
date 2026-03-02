#!/usr/bin/env python3
"""
destroy.py — Stop and delete all lab VMs and LXCs.

Destroys CTIDs/VMIDs: 110, 111, 112, 113, 114

VMID 100 (router-b) is NEVER touched regardless of arguments.

Usage:
    python3 lab/scripts/destroy.py [--yes]

    --yes   Skip confirmation prompt (for scripted resets)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lib

LAB_ENTRIES = [
    (lib.VMID_CLIENT,       "lxc",  "lab-client"),
    (lib.VMID_FW_SECONDARY, "qemu", "lab-fw-secondary"),
    (lib.VMID_FW_PRIMARY,   "qemu", "lab-fw-primary"),
    (lib.VMID_ISP_ATT,      "lxc",  "lab-isp-att"),
    (lib.VMID_ISP_XFINITY,  "lxc",  "lab-isp-xfinity"),
]


def confirm() -> bool:
    if "--yes" in sys.argv:
        return True
    print("\nThis will STOP and DELETE the following VMs/LXCs:")
    for vmid, kind, name in LAB_ENTRIES:
        exists = lib.vm_exists(vmid)
        state = lib.vm_status(vmid) if exists else "not found"
        print(f"  {vmid}  {name:<24}  {state}")
    print("\nVMID 100 (router-b) will NOT be touched.")
    ans = input("\nType YES to continue: ").strip()
    return ans == "YES"


def destroy_vm(vmid: int, kind: str, name: str) -> bool:
    if not lib.vm_exists(vmid):
        print(f"  — {name} (VMID {vmid}) not found, skipping")
        return True

    # Safety check — never touch protected VMIDs
    if vmid in lib.PROTECTED_VMIDS:
        lib.print_err(f"VMID {vmid} is protected — skipping")
        return False

    status = lib.vm_status(vmid)
    if status == "running":
        print(f"  Stopping {name}...")
        if not lib.stop_vm(vmid, kind):
            lib.print_err(f"Failed to stop {name}, trying force stop...")
            try:
                upid = lib.api_post(
                    f"/api2/json/nodes/{lib.NODE}/{kind}/{vmid}/status/stop",
                    {"forceStop": 1}
                )
                lib.wait_for_task(upid or "", timeout=30)
            except Exception:
                pass
        time.sleep(2)

    print(f"  Deleting {name} (VMID {vmid})...")
    try:
        if kind == "lxc":
            upid = lib.api_delete(
                f"/api2/json/nodes/{lib.NODE}/lxc/{vmid}?purge=1&destroy-unreferenced-disks=1"
            )
        else:
            upid = lib.api_delete(
                f"/api2/json/nodes/{lib.NODE}/qemu/{vmid}?purge=1&destroy-unreferenced-disks=1"
            )
        if upid:
            lib.wait_for_task(upid, label=f"delete {name}", timeout=120)
        lib.print_ok(f"Deleted {name}")
        return True
    except Exception as e:
        lib.print_err(f"Delete failed: {e}")
        return False


def main():
    print("=" * 60)
    print("Lab Environment Teardown")
    print("=" * 60)

    if not confirm():
        print("Aborted.")
        sys.exit(0)

    print()
    ok = True
    for vmid, kind, name in LAB_ENTRIES:
        if not destroy_vm(vmid, kind, name):
            ok = False

    print("\n" + "=" * 60)
    if ok:
        print("Lab environment destroyed. Run 01_create_isp_sims.py to rebuild.")
    else:
        print("Some deletions failed. Check Proxmox task log.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

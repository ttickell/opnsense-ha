#!/usr/bin/env python3
"""
00_prereqs.py — Check and download required LXC templates.

Run this first. It verifies:
  - Proxmox API connectivity
  - OPNsense ISO is present
  - Alpine LXC template is present (downloads if missing)
  - Debian LXC template is present (downloads if missing)

Usage:
    python3 lab/scripts/00_prereqs.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lib


def check_opnsense_iso() -> bool:
    print("\n[OPNsense ISO]")
    try:
        items = lib.api_get(f"/api2/json/nodes/{lib.NODE}/storage/{lib.STORAGE_ISO}/content?content=iso")
        for item in items:
            if "OPNsense-25.1" in item.get("volid", ""):
                lib.print_ok(f"Found: {item['volid']}  ({item.get('size',0)//1048576} MB)")
                return True
        lib.print_err(f"OPNsense-25.1 ISO not found in {lib.STORAGE_ISO}. Upload manually.")
        print(f"    Download from: https://opnsense.org/download/ (dvd, amd64)")
        return False
    except Exception as e:
        lib.print_err(f"Error checking ISO storage: {e}")
        return False


def ensure_template(name_prefix: str, pveam_name: str) -> bool:
    """Check for template; download from pveam if missing."""
    print(f"\n[LXC Template: {name_prefix}]")
    volid = lib.find_template(lib.STORAGE_TPL, name_prefix)
    if volid:
        lib.print_ok(f"Found: {volid}")
        return True

    # Not present — download via pveam
    print(f"  Not found. Fetching available templates from pveam...")
    try:
        available = lib.api_get(f"/api2/json/nodes/{lib.NODE}/aplinfo")
    except Exception as e:
        lib.print_err(f"Failed to fetch aplinfo: {e}")
        return False

    match = None
    for tpl in sorted(available, key=lambda x: x.get("package",""), reverse=True):
        if name_prefix in tpl.get("package","") or name_prefix in tpl.get("source",""):
            match = tpl
            break

    if not match:
        # Try matching on the template filename directly
        for tpl in available:
            if name_prefix in tpl.get("template",""):
                match = tpl
                break

    if not match:
        lib.print_err(f"'{name_prefix}' not found in pveam index. Try: pveam update && pveam available --section system | grep {name_prefix}")
        return False

    template_file = match.get("template", match.get("source", ""))
    print(f"  Downloading: {template_file}")
    try:
        upid = lib.api_post(f"/api2/json/nodes/{lib.NODE}/aplinfo", {
            "storage": lib.STORAGE_TPL,
            "template": template_file,
        })
        if upid:
            ok = lib.wait_for_task(upid, label=f"download {template_file}", timeout=300)
        else:
            ok = False
    except Exception as e:
        lib.print_err(f"Download failed: {e}")
        return False

    if ok:
        volid = lib.find_template(lib.STORAGE_TPL, name_prefix)
        lib.print_ok(f"Downloaded: {volid}")
        return True
    else:
        lib.print_err("Download task failed. Check Proxmox task log.")
        return False


def main():
    print("=" * 60)
    print("Phase 1 Prereqs Check")
    print("=" * 60)

    # Connectivity check
    print("\n[Proxmox Connectivity]")
    try:
        nodes = lib.api_get("/api2/json/nodes")
        node_names = [n["node"] for n in nodes]
        lib.print_ok(f"Connected — nodes: {', '.join(node_names)}")
    except Exception as e:
        lib.print_err(f"Cannot connect to Proxmox: {e}")
        sys.exit(1)

    # Proxmox version
    try:
        ver = lib.api_get("/api2/json/version")
        lib.print_ok(f"Proxmox VE {ver.get('version')} (release {ver.get('release')})")
    except Exception:
        pass

    results = []
    results.append(("OPNsense ISO",     check_opnsense_iso()))
    results.append(("Alpine template",  ensure_template("alpine", "alpine")))
    results.append(("Debian template",  ensure_template("debian", "debian")))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    all_ok = True
    for label, ok in results:
        status = "✓" if ok else "✗"
        print(f"  {status}  {label}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\nAll prerequisites met. Run 01_create_isp_sims.py next.")
        sys.exit(0)
    else:
        print("\nFix the items above before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()

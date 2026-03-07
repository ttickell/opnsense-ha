#!/usr/bin/env python3
"""
01_create_isp_sims.py — Create ISP simulator LXCs.

Creates:
  CTID 110  lab-isp-xfinity  Alpine LXC  VLAN 210  10.220.10.1/30
  CTID 111  lab-isp-att      Alpine LXC  VLAN 211  10.220.11.1/30

Idempotent: skips containers that already exist.
After creation, installs ISC Kea DHCP (kea-dhcp4 + kea-dhcp6) and deploys simulator configs.

Usage:
    python3 lab/scripts/01_create_isp_sims.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lib

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SIMS = [
    {
        "vmid":     lib.VMID_ISP_XFINITY,
        "name":     "lab-isp-xfinity",
        "vlan":     lib.VLAN_WAN_A,
        "ipv4":     lib.IPV4_ISP_XFINITY,
        "ipv6":     lib.IPV6_ISP_XFINITY,
        "conf4":    REPO_ROOT / "lab/isp-simulators/xfinity/kea-dhcp4.conf",
        "conf6":    REPO_ROOT / "lab/isp-simulators/xfinity/kea-dhcp6.conf",
        "isp_key":  "xfinity",
    },
    {
        "vmid":     lib.VMID_ISP_ATT,
        "name":     "lab-isp-att",
        "vlan":     lib.VLAN_WAN_B,
        "ipv4":     lib.IPV4_ISP_ATT,
        "ipv6":     lib.IPV6_ISP_ATT,
        "conf4":    REPO_ROOT / "lab/isp-simulators/att/kea-dhcp4.conf",
        "conf6":    REPO_ROOT / "lab/isp-simulators/att/kea-dhcp6.conf",
        "isp_key":  "att",
    },
]


def create_sim(sim: dict) -> bool:
    vmid = sim["vmid"]
    name = sim["name"]

    if lib.vm_exists(vmid):
        lib.print_skip(f"{name} (CTID {vmid})")
        return True

    print(f"\n  Creating {name} (CTID {vmid})...")

    # Find Alpine template
    tpl = lib.find_template(lib.STORAGE_TPL, "alpine")
    if not tpl:
        lib.print_err("Alpine template not found. Run 00_prereqs.py first.")
        return False
    print(f"  Template: {tpl}")

    net0 = (
        f"name=eth0,bridge=vmbr0,tag={sim['vlan']},"
        f"ip={sim['ipv4']},ip6={sim['ipv6']},"
        f"firewall=0"
    )

    params = {
        "vmid":         vmid,
        "hostname":     name,
        "ostemplate":   tpl,
        "storage":      lib.STORAGE_VM,
        "rootfs":       f"{lib.STORAGE_VM}:2",   # 2 GB
        "cores":        1,
        "memory":       256,
        "swap":         0,
        "net0":         net0,
        "onboot":       0,
        "unprivileged": 0,   # privileged — DHCP servers bind ports 67/547
        "description":  f"Lab ISP simulator ({sim['isp_key']}). Managed by lab/scripts.",
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


def setup_sim(sim: dict) -> bool:
    vmid = sim["vmid"]
    name = sim["name"]

    # Ensure SSH key auth to the Proxmox host is ready
    if not lib.ensure_ssh_key():
        return False

    # Start if not running
    status = lib.vm_status(vmid)
    if status != "running":
        print(f"  Starting {name}...")
        if not lib.start_vm(vmid, "lxc"):
            lib.print_err(f"Failed to start {name}")
            return False
        time.sleep(3)

    # Check if Kea DHCP is already installed
    rc, _ = lib.pct_exec(vmid, "which kea-dhcp4")
    kea_installed = (rc == 0)

    if not kea_installed:
        cfg = lib.api_get(f"/api2/json/nodes/{lib.NODE}/lxc/{vmid}/config")
        has_net1 = bool(cfg.get("net1"))

        # Add a temporary management NIC so apk can reach the internet
        if not has_net1:
            print(f"  Adding temporary management NIC for package install...")
            try:
                lib.api_post(f"/api2/json/nodes/{lib.NODE}/lxc/{vmid}/status/stop")
                time.sleep(4)
                lib.api_put(f"/api2/json/nodes/{lib.NODE}/lxc/{vmid}/config", {
                    "net1": "name=eth1,bridge=vmbr0,firewall=0,ip=dhcp",
                })
                lib.start_vm(vmid, "lxc")
                time.sleep(6)  # wait for DHCP on mgmt NIC
            except Exception as e:
                lib.print_err(f"Could not add mgmt NIC: {e}")
                return False
        else:
            print("  Reusing existing temporary management NIC (net1)...")

        print(f"  Installing ISC Kea in {name}...")
        rc, log = lib.pct_exec(vmid,
            "echo 'nameserver 8.8.8.8' >> /etc/resolv.conf && "
            "apk update -q && apk add -q kea-dhcp4 kea-dhcp6")
        if rc != 0:
            try:
                lib.api_post(f"/api2/json/nodes/{lib.NODE}/lxc/{vmid}/status/stop")
                time.sleep(4)
                lib.api_put(f"/api2/json/nodes/{lib.NODE}/lxc/{vmid}/config", {
                    "delete": "net1",
                })
                lib.start_vm(vmid, "lxc")
                time.sleep(3)
            except Exception:
                pass
            lib.print_err(f"apk install failed (exit {rc}): {log[-400:]}")
            return False
        lib.print_ok("ISC Kea installed")

        # Remove temporary management NIC
        print(f"  Removing temporary management NIC...")
        try:
            lib.api_post(f"/api2/json/nodes/{lib.NODE}/lxc/{vmid}/status/stop")
            time.sleep(4)
            lib.api_put(f"/api2/json/nodes/{lib.NODE}/lxc/{vmid}/config", {
                "delete": "net1",
            })
            lib.start_vm(vmid, "lxc")
            time.sleep(3)
            lib.print_ok("Temporary NIC removed")
        except Exception as e:
            lib.print_err(f"Could not remove mgmt NIC: {e}")
            return False
    else:
        lib.print_ok("ISC Kea already installed")

    # Enable IP forwarding (idempotent — duplicate entries are harmless)
    rc, _ = lib.pct_exec(vmid,
        "grep -q 'ip_forward' /etc/sysctl.conf || ("
        "echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf && "
        "echo 'net.ipv6.conf.all.forwarding=1' >> /etc/sysctl.conf); "
        "sysctl -p /etc/sysctl.conf 2>/dev/null; true")
    lib.print_ok("IP forwarding enabled")

    # Deploy ISC Kea configs
    conf4_path = sim["conf4"]
    conf6_path = sim["conf6"]
    if not conf4_path.exists() or not conf6_path.exists():
        lib.print_err(f"Config not found: {conf4_path} and/or {conf6_path}")
        return False

    rc, _ = lib.pct_exec(vmid, "mkdir -p /etc/kea")
    if rc != 0:
        lib.print_err("Could not create /etc/kea in simulator container")
        return False

    conf4_content = conf4_path.read_text()
    conf6_content = conf6_path.read_text()
    print(f"  Deploying kea-dhcp4.conf ({len(conf4_content)} bytes)...")
    if not lib.pct_push(vmid, conf4_content, "/etc/kea/kea-dhcp4.conf"):
        return False
    print(f"  Deploying kea-dhcp6.conf ({len(conf6_content)} bytes)...")
    if not lib.pct_push(vmid, conf6_content, "/etc/kea/kea-dhcp6.conf"):
        return False
    lib.print_ok("ISC Kea configs deployed")

    # Enable and restart Kea services
    rc, log = lib.pct_exec(vmid,
        "rc-service dnsmasq stop 2>/dev/null || true; "
        "rc-update del dnsmasq default 2>/dev/null || true; "
        "rc-update add kea-dhcp4 default 2>/dev/null; "
        "rc-update add kea-dhcp6 default 2>/dev/null; "
        "rc-service kea-dhcp4 restart; rc-service kea-dhcp6 restart")
    if rc != 0:
        lib.print_err(f"ISC Kea service failed (exit {rc}): {log[-400:]}")
        return False
    lib.print_ok("ISC Kea started")

    # Verify
    rc, log = lib.pct_exec(vmid,
        "ps | grep -E 'kea-dhcp4|kea-dhcp6' | grep -v grep && echo running || echo not-running")
    if "running" in log and "not-running" not in log:
        lib.print_ok("ISC Kea running")
    else:
        print(f"  ⚠  Could not confirm ISC Kea — check container {vmid} manually")

    return True


def main():
    print("=" * 60)
    print("Step 1: Create ISP Simulator LXCs")
    print("=" * 60)

    ok = True
    for sim in SIMS:
        print(f"\n--- {sim['name']} ---")
        if not create_sim(sim):
            ok = False
            continue
        if not setup_sim(sim):
            ok = False

    print("\n" + "=" * 60)
    if ok:
        print("ISP simulators ready. Run 02_create_firewalls.py next.")
    else:
        print("One or more steps failed. Fix errors and re-run (idempotent).")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

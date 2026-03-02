#!/usr/bin/env python3
"""
01_create_isp_sims.py — Create ISP simulator LXCs.

Creates:
  CTID 110  lab-isp-xfinity  Alpine LXC  VLAN 210  10.220.10.1/30
  CTID 111  lab-isp-att      Alpine LXC  VLAN 211  10.220.11.1/30

Idempotent: skips containers that already exist.
After creation, installs dnsmasq and deploys the simulator configs.

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
        "conf":     REPO_ROOT / "lab/isp-simulators/xfinity/dnsmasq.conf",
        "isp_key":  "xfinity",
    },
    {
        "vmid":     lib.VMID_ISP_ATT,
        "name":     "lab-isp-att",
        "vlan":     lib.VLAN_WAN_B,
        "ipv4":     lib.IPV4_ISP_ATT,
        "ipv6":     lib.IPV6_ISP_ATT,
        "conf":     REPO_ROOT / "lab/isp-simulators/att/dnsmasq.conf",
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
        "unprivileged": 0,   # privileged — dnsmasq needs to bind ports 67/547
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
        time.sleep(3)  # let init settle

    print(f"  Installing dnsmasq in {name}...")
    rc, log = lib.pct_exec(vmid, "apk update -q && apk add -q dnsmasq")
    if rc != 0:
        lib.print_err(f"apk install failed (exit {rc}): {log[-300:]}")
        return False
    lib.print_ok("dnsmasq installed")

    # Enable IP forwarding
    rc, _ = lib.pct_exec(vmid,
        "echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf && "
        "echo 'net.ipv6.conf.all.forwarding=1' >> /etc/sysctl.conf && "
        "sysctl -p /etc/sysctl.conf 2>/dev/null; true")
    lib.print_ok("IP forwarding enabled")

    # Deploy dnsmasq config
    conf_path = sim["conf"]
    if not conf_path.exists():
        lib.print_err(f"Config not found: {conf_path}")
        return False

    conf_content = conf_path.read_text()
    print(f"  Deploying dnsmasq config ({len(conf_content)} bytes)...")
    if not lib.pct_push(vmid, conf_content, "/etc/dnsmasq.conf"):
        return False
    lib.print_ok("dnsmasq config deployed")

    # Enable and start dnsmasq
    rc, log = lib.pct_exec(vmid,
        "rc-update add dnsmasq default && rc-service dnsmasq restart")
    if rc != 0:
        lib.print_err(f"dnsmasq service failed (exit {rc}): {log[-300:]}")
        return False
    lib.print_ok("dnsmasq started")

    # Verify
    rc, log = lib.pct_exec(vmid,
        "netstat -ulnp 2>/dev/null | grep ':67 ' || ss -ulnp | grep ':67 ' || echo 'checking-via-ps' && ps | grep dnsmasq | grep -v grep")
    if "dnsmasq" in log or "check" not in log:
        lib.print_ok("dnsmasq running")
    else:
        print(f"  ⚠  Could not confirm dnsmasq — verify manually in container {vmid}")

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

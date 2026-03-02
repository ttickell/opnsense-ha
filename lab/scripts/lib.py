"""
Shared Proxmox API client and lab constants for opnsense-ha lab scripts.

Load credentials from .env two levels up (repo root), falling back to
environment variables already set in the shell.
"""
import json
import os
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path


# ---------------------------------------------------------------------------
# Credentials — load from .env relative to repo root
# ---------------------------------------------------------------------------

def _load_env():
    repo_root = Path(__file__).resolve().parent.parent.parent
    env_file = repo_root / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), val)

_load_env()

PROX_URL   = os.environ["PROX_MOX_URL"].rstrip("/")
PROX_USER  = os.environ["PROX_MOX_USER"]   # root@pam!fw-lab
PROX_TOKEN = os.environ["PROX_MOX_TOKEN"]  # uuid


# ---------------------------------------------------------------------------
# Lab constants
# ---------------------------------------------------------------------------

NODE        = "proxima"
STORAGE_VM  = "local-zfs"    # ZFS pool — VM disks and LXC rootfs
STORAGE_ISO = "Synology"     # NFS — ISOs
STORAGE_TPL = "local"        # dir  — LXC templates (vztmpl)

OPNSENSE_ISO = "Synology:iso/OPNsense-25.1-dvd-amd64.iso"

# VMID / CTID assignments
VMID_ISP_XFINITY  = 110
VMID_ISP_ATT      = 111
VMID_FW_PRIMARY   = 112
VMID_FW_SECONDARY = 113
VMID_CLIENT       = 114

LAB_VMIDS = [
    VMID_ISP_XFINITY,
    VMID_ISP_ATT,
    VMID_FW_PRIMARY,
    VMID_FW_SECONDARY,
    VMID_CLIENT,
]

PROTECTED_VMIDS = [100]  # router-b — never touch

# VLAN assignments
VLAN_WAN_A   = 210
VLAN_WAN_B   = 211
VLAN_LAN     = 212
VLAN_PFSYNC  = 213

# IPv4 addressing
IPV4_ISP_XFINITY = "10.220.10.1/30"
IPV4_ISP_ATT     = "10.220.11.1/30"
IPV4_FW_PRIMARY  = "10.220.1.2/24"
IPV4_FW_SECONDARY= "10.220.1.3/24"
IPV4_FW_CARP     = "10.220.1.1"
IPV4_FW_PFSYNC_PRIMARY   = "10.220.3.1/30"
IPV4_FW_PFSYNC_SECONDARY = "10.220.3.2/30"

# IPv6 addressing
IPV6_ISP_XFINITY = "fd03:17ac:e938:4000::1/64"
IPV6_ISP_ATT     = "fd03:17ac:e938:4100::1/64"


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE

_AUTH = f"PVEAPIToken={PROX_USER}={PROX_TOKEN}"


def _request(method: str, path: str, data: dict | None = None) -> dict:
    url = PROX_URL + path
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method=method,
                                  headers={"Authorization": _AUTH})
    with urllib.request.urlopen(req, context=_ctx, timeout=30) as r:
        return json.loads(r.read())


def api_get(path: str) -> dict | list:
    return _request("GET", path)["data"]


def api_post(path: str, data: dict | None = None) -> str | dict:
    resp = _request("POST", path, data or {})
    return resp.get("data")


def api_put(path: str, data: dict) -> None:
    _request("PUT", path, data)


def api_delete(path: str) -> str | None:
    resp = _request("DELETE", path, {})
    return resp.get("data")


# ---------------------------------------------------------------------------
# Task helpers
# ---------------------------------------------------------------------------

def wait_for_task(upid: str, node: str = NODE, timeout: int = 120,
                  poll: float = 2.0, label: str = "") -> bool:
    """Poll a UPID until it finishes. Returns True on success."""
    deadline = time.time() + timeout
    if label:
        print(f"  Waiting for task: {label}")
    while time.time() < deadline:
        status = api_get(f"/api2/json/nodes/{node}/tasks/{upid}/status")
        if status.get("status") == "stopped":
            ok = status.get("exitstatus") == "OK"
            if not ok:
                print(f"  ✗ Task failed: {status.get('exitstatus')}")
            return ok
        time.sleep(poll)
    print(f"  ✗ Task timed out after {timeout}s")
    return False


def task_log(upid: str, node: str = NODE) -> str:
    lines = api_get(f"/api2/json/nodes/{node}/tasks/{upid}/log?limit=200")
    return "\n".join(e.get("t", "") for e in (lines or []))


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def vm_exists(vmid: int, node: str = NODE) -> bool:
    try:
        api_get(f"/api2/json/nodes/{node}/qemu/{vmid}/status/current")
        return True
    except Exception:
        pass
    try:
        api_get(f"/api2/json/nodes/{node}/lxc/{vmid}/status/current")
        return True
    except Exception:
        pass
    return False


def vm_status(vmid: int, node: str = NODE) -> str | None:
    for kind in ("qemu", "lxc"):
        try:
            s = api_get(f"/api2/json/nodes/{node}/{kind}/{vmid}/status/current")
            return s.get("status")
        except Exception:
            pass
    return None


def start_vm(vmid: int, kind: str, node: str = NODE) -> bool:
    upid = api_post(f"/api2/json/nodes/{node}/{kind}/{vmid}/status/start")
    if upid:
        return wait_for_task(upid, node=node, label=f"start {vmid}")
    return False


def stop_vm(vmid: int, kind: str, node: str = NODE) -> bool:
    upid = api_post(f"/api2/json/nodes/{node}/{kind}/{vmid}/status/stop")
    if upid:
        return wait_for_task(upid, node=node, label=f"stop {vmid}", timeout=60)
    return False


def lxc_exec(vmid: int, command: list[str], stdin: str = "",
             node: str = NODE) -> tuple[int, str]:
    """
    Run a command inside a running LXC container.
    Returns (exit_code, combined output).
    """
    data: dict = {"command": json.dumps(command)}
    if stdin:
        data["input-data"] = stdin
    result = api_post(f"/api2/json/nodes/{node}/lxc/{vmid}/exec", data)
    if not result:
        return 1, "exec returned no result"
    upid = result if isinstance(result, str) else result.get("upid", "")
    if not upid:
        return 1, f"no upid in exec response: {result}"
    wait_for_task(upid, node=node, timeout=60)
    log = task_log(upid, node=node)
    # Proxmox encodes exit code in last log line as "SHELL: exit code X"
    exit_code = 0
    for line in reversed(log.splitlines()):
        if "exit code" in line.lower():
            try:
                exit_code = int(line.strip().split()[-1])
            except ValueError:
                pass
            break
    return exit_code, log


def find_template(storage: str = STORAGE_TPL, prefix: str = "",
                  node: str = NODE) -> str | None:
    """Return the volid of the first matching template in storage."""
    try:
        items = api_get(f"/api2/json/nodes/{node}/storage/{storage}/content?content=vztmpl")
        for item in sorted(items, key=lambda x: x.get("volid", ""), reverse=True):
            volid = item.get("volid", "")
            if prefix in volid:
                return volid
    except Exception:
        pass
    return None


def print_ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def print_skip(msg: str) -> None:
    print(f"  — {msg} (already exists, skipping)")


def print_err(msg: str) -> None:
    print(f"  ✗ {msg}")

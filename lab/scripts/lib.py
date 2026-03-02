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
            # Always write from file so updates take effect without a new shell
            os.environ[key.strip()] = val

_load_env()

PROX_URL   = os.environ["PROX_MOX_URL"].rstrip("/")
PROX_USER  = os.environ["PROX_MOX_USER"]   # root@pam!fw-lab
PROX_TOKEN = os.environ["PROX_MOX_TOKEN"]  # uuid

# SSH access to the Proxmox host (for pct exec / pct push)
# PROX_MOX_SSH_PASS  — root password; only needed for one-time key bootstrap
# PROX_MOX_SSH_KEY   — path to private key; auto-set after bootstrap
PROX_SSH_HOST = os.environ.get("PROX_MOX_SSH_HOST", "").strip()
if not PROX_SSH_HOST:
    # derive from PROX_URL
    import urllib.parse as _up
    PROX_SSH_HOST = _up.urlparse(PROX_URL).hostname or ""
PROX_SSH_PASS = os.environ.get("PROX_MOX_SSH_PASS", "").strip().strip('"').strip("'")
PROX_SSH_KEY  = os.environ.get("PROX_MOX_SSH_KEY",
    str(Path.home() / ".ssh" / "proxmox_lab")).strip()


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
IPV4_FW_PFSYNC_PRIMARY   = "10.220.3.2/30"
IPV4_FW_PFSYNC_SECONDARY = "10.220.3.3/30"

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


# ---------------------------------------------------------------------------
# SSH helpers — run commands on the Proxmox host via pct exec / pct push
# ---------------------------------------------------------------------------

import subprocess

_SSH_BASE = [
    "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=10",
]


def _ssh_key_exists() -> bool:
    return Path(PROX_SSH_KEY).exists()


def ensure_ssh_key() -> bool:
    """
    Ensure key-based SSH auth to the Proxmox host is set up.
    If the key doesn't exist, generate one.
    If the key isn't authorised yet, bootstrap using PROX_SSH_PASS.
    Returns True if SSH key auth is working.
    """
    key = Path(PROX_SSH_KEY)
    pub = Path(str(PROX_SSH_KEY) + ".pub")

    # Generate key if missing
    if not key.exists():
        print(f"  Generating SSH key: {key}")
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-f", str(key), "-N", "", "-C", "proxmox-lab"],
            check=True, capture_output=True,
        )
        print_ok(f"Generated {key}")

    # Test if key auth already works
    result = subprocess.run(
        _SSH_BASE + ["-i", str(key), f"root@{PROX_SSH_HOST}", "echo ok"],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode == 0:
        return True

    # Need to install key — requires PROX_SSH_PASS
    if not PROX_SSH_PASS:
        print_err(
            "SSH key auth not set up and PROX_MOX_SSH_PASS not set in .env.\n"
            "  Add PROX_MOX_SSH_PASS=<root-password> to .env, then re-run."
        )
        return False

    print(f"  Copying SSH key to {PROX_SSH_HOST} (one-time)...")
    env = os.environ.copy()
    env["SSHPASS"] = PROX_SSH_PASS
    result = subprocess.run(
        ["sshpass", "-e", "ssh-copy-id",
         "-o", "StrictHostKeyChecking=no",
         "-i", str(pub),
         f"root@{PROX_SSH_HOST}"],
        env=env, capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        print_err(f"ssh-copy-id failed: {result.stderr.strip()}")
        return False
    print_ok("SSH key installed on Proxmox host")
    print("  Tip: you can now remove PROX_MOX_SSH_PASS from .env")
    return True


def host_exec(command: str, timeout: int = 60) -> tuple[int, str]:
    """
    Run a shell command on the Proxmox host via SSH.
    Returns (exit_code, combined stdout+stderr).
    """
    result = subprocess.run(
        _SSH_BASE + ["-i", PROX_SSH_KEY, f"root@{PROX_SSH_HOST}", command],
        capture_output=True, text=True, timeout=timeout,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def pct_exec(vmid: int, command: str, timeout: int = 120) -> tuple[int, str]:
    """Run a shell command inside an LXC container via pct exec on the host."""
    return host_exec(f"pct exec {vmid} -- /bin/sh -c {repr(command)}", timeout=timeout)


def pct_push(vmid: int, content: str, remote_path: str) -> bool:
    """
    Write string content to a file inside an LXC container.
    Uses a heredoc piped through pct exec.
    """
    # Write to a temp file on the host, then pct push it
    tmp = f"/tmp/pct_push_{vmid}_{abs(hash(remote_path)) % 100000}"
    # Write content to host temp file via ssh
    result = subprocess.run(
        _SSH_BASE + ["-i", PROX_SSH_KEY, f"root@{PROX_SSH_HOST}",
                     f"cat > {tmp}"],
        input=content, text=True, capture_output=True, timeout=30,
    )
    if result.returncode != 0:
        print_err(f"pct_push: failed to write temp file: {result.stderr}")
        return False
    rc, out = host_exec(f"pct push {vmid} {tmp} {remote_path} && rm -f {tmp}")
    if rc != 0:
        print_err(f"pct push failed: {out}")
    return rc == 0

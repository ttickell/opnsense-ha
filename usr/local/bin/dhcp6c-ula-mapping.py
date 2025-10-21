#!/usr/bin/env python3

# OPNsense HA IPv6 ULA Mapping Manager
# Standards-compliant location: /usr/local/bin/dhcp6c-ula-mapping.py
#
# Purpose: Monitor prefix delegation changes and trigger ULA mapping updates
# Integrates with HA system for seamless IPv6 failover

import os
import sys
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime

# Configuration
PREFIX_FILES = [Path('/tmp/igc0_prefixv6'), Path('/tmp/igc1_prefixv6')]
STATE_FILE = Path('/var/db/ipv6-ha/ula-mapping-state.json')
DELEGATION_FILE = Path('/var/db/ipv6-ha/dhcp6c-delegations.json')

# Scripts and tools
PREFIX_JSON_SCRIPT = '/usr/local/bin/dhcp6c-prefix-json'
NPTV6_MANAGER_SCRIPT = '/usr/local/bin/opnsense-nptv6-manager.py'

# ULA Configuration (from GeneralNotes.md)
ULA_PREFIX = 'fd03:17ac:e938::'
ULA_NETWORKS = {
    'lan': 'fd03:17ac:e938:10::/64',      # LAN (igc2)
    'cam': 'fd03:17ac:e938:11::/64',      # CAM (igc3)  
    'wireguard': 'fd03:17ac:e938:12::/64', # Wireguard
    'openvpn': 'fd03:17ac:e938:13::/64',  # OpenVPN
    'guest': 'fd03:17ac:e938:14::/64',    # Guest Net
    'iot': 'fd03:17ac:e938:15::/64',      # IOT
    'testnet': 'fd03:17ac:e938:16::/64'   # TestNetInt
}

# Logging setup
DEBUG = True

def setup_logging():
    """Setup logging configuration"""
    log_level = logging.DEBUG if DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('/tmp/dhcp6c-ula-mapping.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def ensure_directories():
    """Ensure required directories exist"""
    os.makedirs(STATE_FILE.parent, exist_ok=True)
    os.makedirs(DELEGATION_FILE.parent, exist_ok=True)

def load_state():
    """Load last run state"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not load state file: {e}")
    
    return {
        'last_run': 0,
        'last_prefix_times': {},
        'current_mappings': {}
    }

def save_state(state):
    """Save current state"""
    try:
        temp_file = f"{STATE_FILE}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(state, f, indent=4)
        os.rename(temp_file, STATE_FILE)
        logging.debug(f"Saved state to {STATE_FILE}")
    except Exception as e:
        logging.error(f"Failed to save state: {e}")

def check_prefix_file_changes(state):
    """Check if any prefix files have changed"""
    changes_detected = False
    current_times = {}
    
    for prefix_file in PREFIX_FILES:
        if prefix_file.exists():
            mtime = prefix_file.stat().st_mtime
            current_times[str(prefix_file)] = mtime
            
            last_mtime = state['last_prefix_times'].get(str(prefix_file), 0)
            if mtime > last_mtime:
                logging.info(f"Prefix file changed: {prefix_file}")
                changes_detected = True
        else:
            logging.debug(f"Prefix file does not exist: {prefix_file}")
    
    # Update state with current times
    state['last_prefix_times'] = current_times
    
    return changes_detected

def run_script(script_path, description):
    """Run a script and handle errors"""
    try:
        logging.info(f"Running {description}: {script_path}")
        result = subprocess.run([script_path], capture_output=True, text=True, check=True)
        logging.debug(f"{description} completed successfully")
        if result.stdout:
            logging.debug(f"{description} stdout: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"{description} failed: {e}")
        if e.stdout:
            logging.error(f"{description} stdout: {e.stdout}")
        if e.stderr:
            logging.error(f"{description} stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        logging.warning(f"{description} script not found: {script_path}")
        return False

def load_current_delegations():
    """Load current prefix delegations"""
    if not DELEGATION_FILE.exists():
        logging.warning(f"Delegation file not found: {DELEGATION_FILE}")
        return {}
    
    try:
        with open(DELEGATION_FILE, 'r') as f:
            data = json.load(f)
        
        # Extract active delegations
        delegations = data.get('prefix_delegations', {})
        active_delegations = {
            pdid: pd for pdid, pd in delegations.items() 
            if pd.get('status') == 'active'
        }
        
        logging.info(f"Loaded {len(active_delegations)} active delegations")
        return active_delegations
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Could not load delegations: {e}")
        return {}

def create_ula_mappings(delegations):
    """Create ULA to delegation mappings"""
    mappings = {}
    available_prefixes = []
    
    # Collect available prefixes by provider
    comcast_prefixes = []
    att_prefixes = []
    
    for pdid, pd in delegations.items():
        prefix = pd['prefix']
        interface = pd.get('interface', 'unknown')
        
        if interface == 'igc1':  # Comcast
            comcast_prefixes.append(prefix)
        elif interface == 'igc0':  # AT&T
            att_prefixes.append(prefix)
    
    logging.info(f"Available prefixes - Comcast: {len(comcast_prefixes)}, AT&T: {len(att_prefixes)}")
    
    # Prefer AT&T for active mappings (primary provider)
    if att_prefixes:
        available_prefixes = att_prefixes
        active_provider = 'att'
    elif comcast_prefixes:
        available_prefixes = comcast_prefixes  
        active_provider = 'comcast'
    else:
        logging.warning("No active prefixes available for mapping")
        return {}
    
    # Create mappings for ULA networks
    network_names = list(ULA_NETWORKS.keys())
    for i, (network_name, ula_network) in enumerate(ULA_NETWORKS.items()):
        if i < len(available_prefixes):
            mappings[ula_network] = {
                'external_prefix': available_prefixes[i],
                'network_name': network_name,
                'provider': active_provider,
                'created': datetime.now().isoformat()
            }
        else:
            logging.warning(f"No prefix available for ULA network: {network_name} ({ula_network})")
    
    logging.info(f"Created {len(mappings)} ULA mappings using {active_provider} provider")
    return mappings

def trigger_nptv6_updates():
    """Trigger NPTv6 rule updates if manager exists"""
    if os.path.exists(NPTV6_MANAGER_SCRIPT):
        return run_script(NPTV6_MANAGER_SCRIPT, "NPTv6 Manager")
    else:
        logging.info("NPTv6 manager script not found - skipping NPTv6 updates")
        return True

def main():
    """Main execution function"""
    setup_logging()
    logging.info("Starting ULA mapping check")
    
    try:
        ensure_directories()
        state = load_state()
        
        # Check if prefix files have changed
        if not check_prefix_file_changes(state):
            logging.debug("No prefix file changes detected")
            return 0
        
        # Run prefix JSON update
        if not run_script(PREFIX_JSON_SCRIPT, "Prefix JSON updater"):
            return 1
        
        # Load current delegations and create mappings
        delegations = load_current_delegations()
        if delegations:
            mappings = create_ula_mappings(delegations)
            state['current_mappings'] = mappings
            
            # Trigger NPTv6 updates
            trigger_nptv6_updates()
        
        # Update state
        state['last_run'] = datetime.now().timestamp()
        save_state(state)
        
        logging.info("ULA mapping check completed successfully")
        return 0
        
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
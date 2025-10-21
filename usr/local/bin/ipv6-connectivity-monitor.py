#!/usr/local/bin/python3

"""
IPv6 Connectivity Monitor for OPNsense HA
Monitors IPv6 connectivity, gateway reachability, and prefix delegation status
Integration with OPNsense HA CARP system for failover decision support

Version: 1.0 - Phase 3 IPv6 HA Integration
Compatible with OPNsense 25.7.4+
"""

import json
import subprocess
import sys
import time
import syslog
import socket
import ipaddress
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Configuration
CONFIG = {
    'ipv6_test_targets': [
        '2001:4860:4860::8888',  # Google Public DNS
        '2001:4860:4860::8844',  # Google Public DNS (secondary)
        '2606:4700:4700::1111',  # Cloudflare DNS
        '2001:db8::1'            # Documentation prefix (will fail - for testing)
    ],
    'delegation_state_file': '/var/db/ipv6-ha/dhcp6c-delegations.json',
    'monitoring_state_file': '/var/db/ipv6-ha/connectivity-monitoring.json',
    'gateway_timeout': 5,      # seconds
    'connectivity_timeout': 3,  # seconds
    'max_failures': 3,         # consecutive failures before marking as down
    'check_interval': 30,      # seconds between checks
    'syslog_facility': syslog.LOG_DAEMON,
    'syslog_tag': 'ipv6-monitor'
}

class IPv6Monitor:
    """IPv6 Connectivity Monitor for OPNsense HA"""
    
    def __init__(self):
        self.state = self._load_state()
        self._init_logging()
    
    def _init_logging(self):
        """Initialize syslog logging"""
        syslog.openlog(CONFIG['syslog_tag'], syslog.LOG_PID, CONFIG['syslog_facility'])
    
    def _log(self, level, message):
        """Log message to syslog"""
        syslog.syslog(level, message)
        if '--verbose' in sys.argv:
            print(f"{datetime.now().isoformat()}: {message}")
    
    def _load_state(self) -> Dict:
        """Load monitoring state from file"""
        state_file = Path(CONFIG['monitoring_state_file'])
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self._log(syslog.LOG_WARNING, f"Failed to load monitoring state: {e}")
        
        # Default state
        return {
            'last_check': None,
            'interfaces': {},
            'gateways': {},
            'connectivity': {},
            'delegation_status': {},
            'overall_status': 'unknown'
        }
    
    def _save_state(self):
        """Save monitoring state to file"""
        state_file = Path(CONFIG['monitoring_state_file'])
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except IOError as e:
            self._log(syslog.LOG_WARNING, f"Failed to save monitoring state: {e}")
    
    def get_ipv6_interfaces(self) -> Dict[str, Dict]:
        """Get IPv6-enabled interfaces and their addresses"""
        interfaces = {}
        
        try:
            # Get interface list with IPv6 addresses
            result = subprocess.run(
                ['ifconfig', '-f', 'inet6'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                current_interface = None
                
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    
                    # Interface line (starts with interface name)
                    if line and not line.startswith('\t') and ':' in line:
                        interface_name = line.split(':')[0]
                        if not interface_name.startswith('lo'):  # Skip loopback
                            current_interface = interface_name
                            interfaces[current_interface] = {
                                'addresses': [],
                                'status': 'unknown',
                                'mtu': None
                            }
                    
                    # IPv6 address line
                    elif current_interface and 'inet6' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            addr = parts[1]
                            # Skip link-local addresses for connectivity testing
                            if not addr.startswith('fe80:'):
                                interfaces[current_interface]['addresses'].append(addr)
                    
                    # Interface status
                    elif current_interface and 'status:' in line:
                        status = line.split('status:')[1].strip()
                        interfaces[current_interface]['status'] = status
                    
                    # MTU information
                    elif current_interface and 'mtu' in line:
                        try:
                            mtu = line.split('mtu')[1].split()[0]
                            interfaces[current_interface]['mtu'] = int(mtu)
                        except (IndexError, ValueError):
                            pass
            
        except subprocess.TimeoutExpired:
            self._log(syslog.LOG_WARNING, "Timeout getting interface information")
        except Exception as e:
            self._log(syslog.LOG_ERROR, f"Error getting interfaces: {e}")
        
        return interfaces
    
    def get_ipv6_gateways(self) -> Dict[str, Dict]:
        """Get IPv6 default gateways"""
        gateways = {}
        
        try:
            result = subprocess.run(
                ['netstat', '-rn', '-f', 'inet6'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('default') or line.startswith('::/0'):
                        parts = line.split()
                        if len(parts) >= 3:
                            gateway = parts[1]
                            interface = parts[-1] if len(parts) > 3 else 'unknown'
                            
                            gateways[gateway] = {
                                'interface': interface,
                                'reachable': False,
                                'rtt': None,
                                'last_check': None
                            }
            
        except subprocess.TimeoutExpired:
            self._log(syslog.LOG_WARNING, "Timeout getting gateway information")
        except Exception as e:
            self._log(syslog.LOG_ERROR, f"Error getting gateways: {e}")
        
        return gateways
    
    def test_gateway_reachability(self, gateway: str) -> Tuple[bool, Optional[float]]:
        """Test IPv6 gateway reachability using ping6"""
        try:
            start_time = time.time()
            result = subprocess.run(
                ['ping6', '-c', '1', '-W', str(CONFIG['gateway_timeout'] * 1000), gateway],
                capture_output=True, text=True, timeout=CONFIG['gateway_timeout'] + 2
            )
            end_time = time.time()
            
            if result.returncode == 0:
                rtt = (end_time - start_time) * 1000  # Convert to milliseconds
                return True, rtt
            else:
                return False, None
                
        except subprocess.TimeoutExpired:
            self._log(syslog.LOG_DEBUG, f"Gateway ping timeout: {gateway}")
            return False, None
        except Exception as e:
            self._log(syslog.LOG_DEBUG, f"Gateway ping error for {gateway}: {e}")
            return False, None
    
    def test_connectivity(self, target: str, source_interface: Optional[str] = None) -> bool:
        """Test IPv6 connectivity to external target"""
        try:
            cmd = ['ping6', '-c', '1', '-W', str(CONFIG['connectivity_timeout'] * 1000)]
            
            # Add source interface if specified
            if source_interface:
                cmd.extend(['-S', source_interface])
            
            cmd.append(target)
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, 
                timeout=CONFIG['connectivity_timeout'] + 2
            )
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            self._log(syslog.LOG_DEBUG, f"Connectivity test error for {target}: {e}")
            return False
    
    def check_delegation_status(self) -> Dict[str, Dict]:
        """Check IPv6 prefix delegation status"""
        delegation_status = {}
        delegation_file = Path(CONFIG['delegation_state_file'])
        
        if delegation_file.exists():
            try:
                with open(delegation_file, 'r') as f:
                    delegation_data = json.load(f)
                
                for provider, data in delegation_data.items():
                    delegation_status[provider] = {
                        'has_delegation': bool(data.get('delegated_prefixes')),
                        'prefix_count': len(data.get('delegated_prefixes', [])),
                        'last_updated': data.get('last_updated'),
                        'status': 'active' if data.get('delegated_prefixes') else 'inactive'
                    }
                    
            except (json.JSONDecodeError, IOError) as e:
                self._log(syslog.LOG_WARNING, f"Failed to read delegation status: {e}")
        
        return delegation_status
    
    def perform_comprehensive_check(self) -> Dict:
        """Perform comprehensive IPv6 connectivity check"""
        check_time = datetime.now()
        results = {
            'timestamp': check_time.isoformat(),
            'interfaces': {},
            'gateways': {},
            'connectivity': {},
            'delegation_status': {},
            'overall_status': 'unknown'
        }
        
        self._log(syslog.LOG_INFO, "Starting IPv6 connectivity check")
        
        # 1. Check interfaces
        interfaces = self.get_ipv6_interfaces()
        results['interfaces'] = interfaces
        
        active_interfaces = [name for name, data in interfaces.items() 
                           if data['status'] == 'active' and data['addresses']]
        
        if not active_interfaces:
            self._log(syslog.LOG_WARNING, "No active IPv6 interfaces found")
            results['overall_status'] = 'no_interfaces'
            return results
        
        # 2. Check gateways
        gateways = self.get_ipv6_gateways()
        reachable_gateways = 0
        
        for gateway, gateway_info in gateways.items():
            reachable, rtt = self.test_gateway_reachability(gateway)
            gateway_info['reachable'] = reachable
            gateway_info['rtt'] = rtt
            gateway_info['last_check'] = check_time.isoformat()
            
            if reachable:
                reachable_gateways += 1
                self._log(syslog.LOG_DEBUG, f"Gateway {gateway} reachable (RTT: {rtt:.1f}ms)")
            else:
                self._log(syslog.LOG_WARNING, f"Gateway {gateway} unreachable")
        
        results['gateways'] = gateways
        
        # 3. Test external connectivity
        connectivity_results = {}
        successful_tests = 0
        
        for target in CONFIG['ipv6_test_targets']:
            # Skip documentation addresses in production
            if target.startswith('2001:db8:'):
                continue
                
            success = self.test_connectivity(target)
            connectivity_results[target] = {
                'reachable': success,
                'last_check': check_time.isoformat()
            }
            
            if success:
                successful_tests += 1
                self._log(syslog.LOG_DEBUG, f"Connectivity test to {target}: SUCCESS")
            else:
                self._log(syslog.LOG_WARNING, f"Connectivity test to {target}: FAILED")
        
        results['connectivity'] = connectivity_results
        
        # 4. Check delegation status
        delegation_status = self.check_delegation_status()
        results['delegation_status'] = delegation_status
        
        active_delegations = sum(1 for status in delegation_status.values() 
                               if status['status'] == 'active')
        
        # 5. Determine overall status
        if reachable_gateways > 0 and successful_tests > 0:
            results['overall_status'] = 'healthy'
        elif reachable_gateways > 0:
            results['overall_status'] = 'gateway_only'
        elif successful_tests > 0:
            results['overall_status'] = 'connectivity_only'
        else:
            results['overall_status'] = 'degraded'
        
        # Log summary
        self._log(syslog.LOG_INFO, 
                 f"IPv6 status: {results['overall_status']} "
                 f"(interfaces: {len(active_interfaces)}, "
                 f"gateways: {reachable_gateways}/{len(gateways)}, "
                 f"connectivity: {successful_tests}/{len(connectivity_results)}, "
                 f"delegations: {active_delegations})")
        
        return results
    
    def check_status_changes(self, new_results: Dict) -> List[str]:
        """Check for significant status changes"""
        changes = []
        
        # Compare overall status
        old_status = self.state.get('overall_status', 'unknown')
        new_status = new_results['overall_status']
        
        if old_status != new_status:
            changes.append(f"Overall status changed: {old_status} -> {new_status}")
        
        # Compare gateway reachability
        old_gateways = self.state.get('gateways', {})
        new_gateways = new_results.get('gateways', {})
        
        for gateway, new_info in new_gateways.items():
            old_info = old_gateways.get(gateway, {})
            old_reachable = old_info.get('reachable', False)
            new_reachable = new_info.get('reachable', False)
            
            if old_reachable != new_reachable:
                status = "UP" if new_reachable else "DOWN"
                changes.append(f"Gateway {gateway}: {status}")
        
        # Compare delegation status
        old_delegations = self.state.get('delegation_status', {})
        new_delegations = new_results.get('delegation_status', {})
        
        for provider, new_status in new_delegations.items():
            old_status = old_delegations.get(provider, {})
            old_active = old_status.get('status') == 'active'
            new_active = new_status.get('status') == 'active'
            
            if old_active != new_active:
                status = "ACTIVE" if new_active else "INACTIVE"
                changes.append(f"Delegation {provider}: {status}")
        
        return changes
    
    def run_monitoring_cycle(self):
        """Run a single monitoring cycle"""
        results = self.perform_comprehensive_check()
        changes = self.check_status_changes(results)
        
        # Log significant changes
        for change in changes:
            self._log(syslog.LOG_NOTICE, f"IPv6 status change: {change}")
        
        # Update state
        self.state = results
        self._save_state()
        
        return results
    
    def get_status_summary(self) -> Dict:
        """Get current status summary for external tools"""
        if not self.state.get('timestamp'):
            return {'status': 'no_data', 'message': 'No monitoring data available'}
        
        # Check if data is stale
        last_check = datetime.fromisoformat(self.state['timestamp'])
        if datetime.now() - last_check > timedelta(minutes=5):
            return {'status': 'stale', 'message': 'Monitoring data is stale'}
        
        status = self.state.get('overall_status', 'unknown')
        
        summary = {
            'status': status,
            'last_check': self.state['timestamp'],
            'interfaces': len([i for i in self.state.get('interfaces', {}).values() 
                             if i.get('status') == 'active']),
            'gateways': len([g for g in self.state.get('gateways', {}).values() 
                           if g.get('reachable', False)]),
            'connectivity': len([c for c in self.state.get('connectivity', {}).values() 
                               if c.get('reachable', False)]),
            'delegations': len([d for d in self.state.get('delegation_status', {}).values() 
                              if d.get('status') == 'active'])
        }
        
        return summary

def main():
    """Main function"""
    monitor = IPv6Monitor()
    
    if '--status' in sys.argv:
        # Return current status
        status = monitor.get_status_summary()
        print(json.dumps(status, indent=2))
        sys.exit(0 if status['status'] in ['healthy', 'gateway_only'] else 1)
    
    elif '--check' in sys.argv:
        # Run single check
        results = monitor.run_monitoring_cycle()
        if '--json' in sys.argv:
            print(json.dumps(results, indent=2))
        sys.exit(0 if results['overall_status'] in ['healthy', 'gateway_only'] else 1)
    
    elif '--daemon' in sys.argv:
        # Run continuous monitoring
        monitor._log(syslog.LOG_INFO, "Starting IPv6 connectivity monitoring daemon")
        
        try:
            while True:
                monitor.run_monitoring_cycle()
                time.sleep(CONFIG['check_interval'])
        except KeyboardInterrupt:
            monitor._log(syslog.LOG_INFO, "IPv6 monitoring daemon stopped")
        except Exception as e:
            monitor._log(syslog.LOG_ERROR, f"IPv6 monitoring daemon error: {e}")
            sys.exit(1)
    
    else:
        print("IPv6 Connectivity Monitor for OPNsense HA")
        print("Usage:")
        print("  --check          Run single connectivity check")
        print("  --status         Show current status summary")  
        print("  --daemon         Run continuous monitoring")
        print("  --json           Output in JSON format")
        print("  --verbose        Verbose output")
        sys.exit(1)

if __name__ == '__main__':
    main()
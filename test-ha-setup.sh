#!/bin/sh
# OPNsense HA Testing Script
# Comprehensive testing suite for HA functionality

TEST_SCRIPT_VERSION="1.0"
TAG="ha-test-suite"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Logging functions
log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
}

# Test execution wrapper
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    log_test "Running: ${test_name}"
    
    if ${test_function}; then
        log_pass "${test_name}"
        return 0
    else
        log_fail "${test_name}"
        return 1
    fi
}

# Test functions
test_installation() {
    local required_files="
        /usr/local/etc/rc.syshook.d/carp/00-ha-singleton
        /usr/local/etc/ha-singleton.conf
    "
    
    for file in ${required_files}; do
        if [ ! -f "${file}" ]; then
            echo "Missing file: ${file}"
            return 1
        fi
    done
    
    # Check script permissions
    if [ ! -x "/usr/local/etc/rc.syshook.d/carp/00-ha-singleton" ]; then
        echo "Script not executable"
        return 1
    fi
    
    return 0
}

test_configuration() {
    local config_file="/usr/local/etc/ha-singleton.conf"
    
    if [ ! -f "${config_file}" ]; then
        echo "Configuration file missing"
        return 1
    fi
    
    # Source the config and check basic variables
    . "${config_file}"
    
    if [ -z "${WAN_INTS}" ]; then
        echo "WAN_INTS not configured"
        return 1
    fi
    
    if [ -z "${ALT_DEFROUTE_IPV4}" ]; then
        echo "ALT_DEFROUTE_IPV4 not configured"
        return 1
    fi
    
    return 0
}

test_interfaces() {
    . /usr/local/etc/ha-singleton.conf
    
    for interface in ${WAN_INTS}; do
        if ! ifconfig "${interface}" >/dev/null 2>&1; then
            echo "Interface ${interface} does not exist"
            return 1
        fi
    done
    
    return 0
}

test_carp_interfaces() {
    if ! ifconfig | grep -q "carp:"; then
        echo "No CARP interfaces found"
        return 1
    fi
    
    # Check if at least one CARP interface exists
    local carp_count=$(ifconfig | grep -c "carp:")
    if [ ${carp_count} -eq 0 ]; then
        echo "No CARP interfaces configured"
        return 1
    fi
    
    return 0
}

test_services() {
    . /usr/local/etc/ha-singleton.conf
    
    for service in ${SERVICES}; do
        # Check if service exists (don't require it to be running)
        if ! service "${service}" status >/dev/null 2>&1 && 
           ! which "${service}" >/dev/null 2>&1; then
            echo "Service ${service} not available"
            return 1
        fi
    done
    
    return 0
}

test_script_syntax() {
    local script="/usr/local/etc/rc.syshook.d/carp/00-ha-singleton"
    
    # Basic syntax check
    if ! sh -n "${script}"; then
        echo "Script syntax error"
        return 1
    fi
    
    return 0
}

test_logging() {
    local script="/usr/local/etc/rc.syshook.d/carp/00-ha-singleton"
    
    # Test that the script can log (dry run)
    if ! logger -t "ha-test" "Test log message"; then
        echo "Logging not working"
        return 1
    fi
    
    return 0
}

test_connectivity_check() {
    local check_script="/usr/local/etc/rc.carp_service_status.d/wan_connectivity"
    
    if [ ! -f "${check_script}" ]; then
        echo "WAN connectivity check script missing"
        return 1
    fi
    
    if [ ! -x "${check_script}" ]; then
        echo "WAN connectivity check script not executable"
        return 1
    fi
    
    return 0
}

test_backup_routes() {
    . /usr/local/etc/ha-singleton.conf
    
    # Test that backup route IPs are reachable
    if ! ping -c 1 -W 3 "${ALT_DEFROUTE_IPV4}" >/dev/null 2>&1; then
        echo "Backup IPv4 route ${ALT_DEFROUTE_IPV4} not reachable"
        return 1
    fi
    
    return 0
}

test_ipv6_integration() {
    . /usr/local/etc/ha-singleton.conf
    
    if [ "${ENABLE_IPV6}" = "yes" ]; then
        local ipv6_script="/usr/local/bin/ha-ipv6-integration.sh"
        if [ ! -f "${ipv6_script}" ]; then
            echo "IPv6 integration script missing"
            return 1
        fi
        
        if [ ! -x "${ipv6_script}" ]; then
            echo "IPv6 integration script not executable"
            return 1
        fi
    fi
    
    return 0
}

# Simulation tests (require manual verification)
simulate_carp_failover() {
    log_test "SIMULATION: CARP Failover Test"
    echo "This test requires manual verification:"
    echo "1. Monitor system logs: tail -f /var/log/system.log | grep carp"
    echo "2. Trigger CARP failover (interface down, etc.)"
    echo "3. Verify script execution and proper failover"
    echo "4. Check interface states and service status"
    
    read -p "Press Enter when test is complete..."
    log_skip "Manual verification required"
}

simulate_wan_failure() {
    log_test "SIMULATION: WAN Failure Test"
    echo "This test requires manual verification:"
    echo "1. Disconnect primary WAN interface"
    echo "2. Verify backup routes are added"
    echo "3. Test connectivity through backup routes"
    echo "4. Reconnect primary WAN and verify cleanup"
    
    read -p "Press Enter when test is complete..."
    log_skip "Manual verification required"
}

# Performance tests
test_script_performance() {
    local script="/usr/local/etc/rc.syshook.d/carp/00-ha-singleton"
    
    # Test script execution time
    local start_time=$(date +%s%N)
    
    # Simulate script execution (dry run mode would be ideal)
    # For now, just time the syntax check
    sh -n "${script}"
    local exit_code=$?
    
    local end_time=$(date +%s%N)
    local duration=$(( (end_time - start_time) / 1000000 ))  # Convert to ms
    
    echo "Script execution time: ${duration}ms"
    
    if [ ${exit_code} -ne 0 ]; then
        echo "Script execution failed"
        return 1
    fi
    
    if [ ${duration} -gt 5000 ]; then  # More than 5 seconds
        echo "Script execution too slow: ${duration}ms"
        return 1
    fi
    
    return 0
}

# Main test execution
run_all_tests() {
    echo "============================================"
    echo "OPNsense HA Test Suite v${TEST_SCRIPT_VERSION}"
    echo "============================================"
    echo
    
    # Installation tests
    run_test "Installation Check" test_installation
    run_test "Configuration Check" test_configuration
    run_test "Interface Validation" test_interfaces
    run_test "CARP Interface Check" test_carp_interfaces
    run_test "Service Availability" test_services
    
    # Script tests
    run_test "Script Syntax" test_script_syntax
    run_test "Logging Function" test_logging
    run_test "Script Performance" test_script_performance
    
    # Feature tests
    run_test "Connectivity Check Script" test_connectivity_check
    run_test "Backup Routes" test_backup_routes
    run_test "IPv6 Integration" test_ipv6_integration
    
    echo
    echo "============================================"
    echo "Test Summary"
    echo "============================================"
    echo "Total Tests: ${TESTS_TOTAL}"
    echo "Passed: ${TESTS_PASSED}"
    echo "Failed: ${TESTS_FAILED}"
    
    if [ ${TESTS_FAILED} -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        echo
        echo "Manual tests available:"
        echo "  $0 --simulate-failover"
        echo "  $0 --simulate-wan-failure"
        return 0
    else
        echo -e "${RED}Some tests failed. Please review and fix issues.${NC}"
        return 1
    fi
}

# Command line interface
case "${1:-}" in
    --simulate-failover)
        simulate_carp_failover
        ;;
    --simulate-wan-failure)
        simulate_wan_failure
        ;;
    --help|-h)
        echo "Usage: $0 [options]"
        echo "Options:"
        echo "  (no options)           Run all automated tests"
        echo "  --simulate-failover    Run CARP failover simulation"
        echo "  --simulate-wan-failure Run WAN failure simulation"
        echo "  --help                 Show this help"
        ;;
    "")
        run_all_tests
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
#!/bin/sh
# lab-isp-setup.sh
#
# Bootstrap script for either ISP simulator LXC.
# Run as root inside the Alpine LXC after creation.
#
# Usage:
#   For Xfinity simulator: sh lab-isp-setup.sh xfinity
#   For AT&T simulator:    sh lab-isp-setup.sh att

set -e

ISP="${1:-}"
if [ -z "${ISP}" ]; then
    echo "Usage: $0 xfinity|att"
    exit 1
fi

echo "==> Setting up lab-isp-${ISP} on Alpine Linux"

# Update and install ISC Kea DHCP servers + radvd for Router Advertisements
apk update
apk add kea-dhcp4 kea-dhcp6 radvd

# Enable IP forwarding (ISP simulators act as routers)
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
echo "net.ipv6.conf.all.forwarding=1" >> /etc/sysctl.conf
sysctl -p /etc/sysctl.conf 2>/dev/null || true

# Copy Kea configs from the repo (assumes this script runs from lab/)
CONFIG4_SRC="isp-simulators/${ISP}/kea-dhcp4.conf"
CONFIG6_SRC="isp-simulators/${ISP}/kea-dhcp6.conf"
RADVD_SRC="isp-simulators/${ISP}/radvd.conf"
if [ ! -f "${CONFIG4_SRC}" ] || [ ! -f "${CONFIG6_SRC}" ] || [ ! -f "${RADVD_SRC}" ]; then
    echo "ERROR: Config files not found under isp-simulators/${ISP}/"
    echo "Run this script from the lab/ directory."
    exit 1
fi

mkdir -p /etc/kea
cp "${CONFIG4_SRC}" /etc/kea/kea-dhcp4.conf
cp "${CONFIG6_SRC}" /etc/kea/kea-dhcp6.conf
echo "==> Installed Kea configs from ${CONFIG4_SRC} and ${CONFIG6_SRC}"

cp "${RADVD_SRC}" /etc/radvd.conf
echo "==> Installed radvd config from ${RADVD_SRC}"

# Disable legacy dnsmasq if present (prevents port 67/547 conflicts)
rc-service dnsmasq stop 2>/dev/null || true
rc-update del dnsmasq default 2>/dev/null || true

# Enable and start Kea services
rc-update add kea-dhcp4 default
rc-update add kea-dhcp6 default
rc-service kea-dhcp4 restart
rc-service kea-dhcp6 restart

echo "==> ISC Kea DHCP started (kea-dhcp4 + kea-dhcp6)"

# Enable and start radvd (Router Advertisements for IPv6 default route)
rc-update add radvd default
rc-service radvd restart

echo "==> radvd started (Router Advertisements)"
echo ""
echo "Verify services are running:"
echo "  ps aux | grep -E 'kea-dhcp|radvd'"
echo "  tail -f /var/log/messages | grep -E '(kea|radvd)'"
echo ""
echo "Watch for DHCP/RA exchanges when the lab firewall WAN boots:"
echo "  tail -f /var/log/messages | grep -E '(DHCP|dhcp6|prefix|radvd)'"

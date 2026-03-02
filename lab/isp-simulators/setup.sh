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

# Update and install dnsmasq
apk update
apk add dnsmasq

# Enable IP forwarding (ISP simulators act as routers)
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
echo "net.ipv6.conf.all.forwarding=1" >> /etc/sysctl.conf
sysctl -p /etc/sysctl.conf 2>/dev/null || true

# Copy dnsmasq config from the repo (assumes this script runs from lab/)
CONFIG_SRC="isp-simulators/${ISP}/dnsmasq.conf"
if [ ! -f "${CONFIG_SRC}" ]; then
    echo "ERROR: Config file not found: ${CONFIG_SRC}"
    echo "Run this script from the lab/ directory."
    exit 1
fi

cp "${CONFIG_SRC}" /etc/dnsmasq.conf
echo "==> Installed dnsmasq config from ${CONFIG_SRC}"

# Enable and start dnsmasq
rc-update add dnsmasq default
rc-service dnsmasq start

echo "==> dnsmasq started"
echo ""
echo "Verify DHCP is running:"
echo "  ps aux | grep dnsmasq"
echo "  tail -f /var/log/messages | grep dnsmasq"
echo ""
echo "Watch for DHCP exchanges when the lab firewall WAN boots:"
echo "  tail -f /var/log/messages | grep -E '(DHCP|dhcp6|prefix)'"

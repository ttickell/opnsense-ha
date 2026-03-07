#!/bin/sh

# Compatibility shim:
# Existing dhcp6c wrapper scripts call /usr/local/bin/dhcp6c_wan_custom.sh.
# Delegate all logic to the maintained HA hook implementation.

exec /usr/local/bin/dhcp6c-wan-script.sh "$@"

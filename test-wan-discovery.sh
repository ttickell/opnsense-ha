#!/bin/sh
# test-wan-discovery.sh - Test config.xml WAN interface discovery logic
#
# Usage:
#   ./test-wan-discovery.sh                     # uses /conf/config.xml (on firewall)
#   ./test-wan-discovery.sh /path/to/config.xml # use a specific file

CONFIG="${1:-/conf/config.xml}"

if [ ! -f "$CONFIG" ]; then
    echo "ERROR: config.xml not found at: $CONFIG" >&2
    exit 1
fi

echo "Parsing: $CONFIG"
echo ""

# Discovery rules:
#   - Element named "wan"            -> always a WAN; label="wan"
#   - Element named "optN" (N=1-9)
#     where <descr> matches WAN2-WAN9 (case-insensitive) -> additional WAN;
#     label = lowercased descr value
#   - Everything else (lan, lo0, opt2/PFSYNC, etc.)      -> ignored
#
# Output format per line: opnsense_name:device:label
#   opnsense_name  - XML element name (wan, opt1, ...)      -> configctl, rc.configure_interface
#   device         - <if> value (vtnet0, vtnet1, ...)       -> ifconfig
#   label          - human name (wan, wan2, ...)            -> dhcp6c config paths, log messages
#
# Self-closing <descr/> is intentionally not matched by /<descr>[^<]/
# so lan and wan (which have empty descr) are handled by name alone.

WAN_MAP=$(awk '
    /<interfaces>/ { in_if = 1; next }
    /<\/interfaces>/ { in_if = 0 }
    !in_if { next }

    # Opening tag of a top-level interface block: <wan>, <opt1>, etc.
    # Must be a simple open tag (no slash, no self-close, only [a-z0-9])
    /^[[:space:]]*<[a-z][a-z0-9]*>[[:space:]]*$/ {
        tag = $0
        sub(/^[[:space:]]*</, "", tag)
        sub(/>.*$/, "", tag)
        iface = tag
        dev = ""
        descr = ""
    }

    # <if>device</if>  — device name used by ifconfig
    /<if>[^<]/ {
        line = $0
        sub(/.*<if>/, "", line)
        sub(/<\/if>.*/, "", line)
        dev = line
    }

    # <descr>value</descr>  — self-closing <descr/> intentionally NOT matched
    /<descr>[^<]/ {
        line = $0
        sub(/.*<descr>/, "", line)
        sub(/<\/descr>.*/, "", line)
        descr = line
    }

    # Closing tag matching the current interface block
    /^[[:space:]]*<\/[a-z][a-z0-9]*>[[:space:]]*$/ {
        tag = $0
        sub(/^[[:space:]]*<\//, "", tag)
        sub(/>.*$/, "", tag)
        if (tag == iface && dev != "") {
            is_wan = 0
            label = ""
            if (iface == "wan") { is_wan = 1; label = "wan" }
            if (iface ~ /^opt[1-9]$/ && descr ~ /^[Ww][Aa][Nn][2-9]$/) {
                is_wan = 1
                label = tolower(descr)
            }
            if (is_wan) print iface ":" dev ":" label
        }
        iface = ""
        dev = ""
        descr = ""
    }
' "$CONFIG")

echo "=== Raw discovery output (opnsense_name:device:label) ==="
if [ -z "$WAN_MAP" ]; then
    echo "(none — no WAN interfaces found)"
else
    echo "$WAN_MAP"
fi
echo ""

echo "=== Parsed triples (opnsense_name:device:label) ==="
if [ -z "$WAN_MAP" ]; then
    echo "ERROR: No WAN interfaces discovered — check config.xml" >&2
    exit 1
fi

for triple in $WAN_MAP; do
    opnsense_name="${triple%%:*}"
    rest="${triple#*:}"
    device_name="${rest%%:*}"
    label="${rest##*:}"
    printf "  opnsense=%-8s  device=%-12s  label=%s\n" \
        "$opnsense_name" "$device_name" "$label"
done
echo ""

echo "=== Equivalent derived variables ==="
WAN_INTS=""
for triple in $WAN_MAP; do
    rest="${triple#*:}"
    dev="${rest%%:*}"
    WAN_INTS="${WAN_INTS}${WAN_INTS:+ }${dev}"
done
echo "  WAN_INTS=\"$WAN_INTS\""
echo "  WAN_MAP (raw)=\"$WAN_MAP\""
echo ""

echo "=== Lookup function simulations ==="
for triple in $WAN_MAP; do
    opnsense_name="${triple%%:*}"
    rest="${triple#*:}"
    device_name="${rest%%:*}"
    label="${rest##*:}"

    # get_opnsense_interface_name(device) -> opnsense_name
    printf "  get_opnsense_interface_name(%s) -> %s\n" "$device_name" "$opnsense_name"
    # get_wan_label(device) -> label
    printf "  get_wan_label(%s)              -> %s  (e.g. dhcp6c_%s.conf.custom)\n" \
        "$device_name" "$label" "$label"
done

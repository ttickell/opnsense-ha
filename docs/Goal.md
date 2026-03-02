# Goal
The goal is to generate configurations for the HA failover for our real firewall pair.  The details are as follows:

# Exiting Config
## Primary Firewall:
WAN interface : Real interface igc0 maps to WAN
WAN2 interface : Real Interface igc1 maps to WAN2
LAN interface (primary) lagg0. IPv4 192.168.105.2, CARP address 192.168.105.1; IPv6 fd03:17ac:e938:10::2, CARP address fd03:17ac:e938:10::1
PFSYNC is run on interface vlan0.110, network 192.168.103.2/29

## Secondary Firewall
WAN interface : Real interface vtnet4 maps to WAN
WAN2 interface : Real Interface vtnet5 maps to WAN2
LAN interface (primary) vtnet0. IPv4 192.168.105.3, CARP address 192.168.105.1; IPv6 fd03:17ac:e938:10::3, CARP address fd03:17ac:e938:10::1
PFSYNC is run on interface vtnet6, network 192.168.103.3/29

# Success 
Success is the generation of two function configuration files for my environment in the subdirectory "real" and an addition to our .gitignore so that directory isn't commited with our real configuration.

These configurations will cover everything we have done so far, including the management of IPv6 services.

# Other Things
Use our work on the ha fail scripts thus far to build these files and, if I have omitted any data you need, ask me - do not speculate.
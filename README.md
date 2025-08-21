# opnsense-ha
Project for figuring out OPNsense HA in my home environment.

## Thing to Achieve

* Firewalls must function in a primary /secondary configuration, with the secondary taking over if 
  * the primary is offline or
  * [considering] a scenario causes the primary to not have access to either AT&T or Comcast internet connections while the secondary retains access to at least one.
* The Primary firewall (physical system) must be able to be directly plugged into non-vlan aware devices and have the AT&T, Comcast, and main LAN function as expected
  * It is acceptable for the IOT or Guest VLANs to be unaccessiible in this case

## Things to Note
* Comcast may not like a dynamically generated MAC address from Prox-Mox
* Comcast definetly needs a modem reboot if the MAC changes

## Learned so far
* CARP won't work with Broadband connection expections
  * CARP on internal networks for default routes
  * dev.d for changing WAN / WAN2 interface states on CARP failover events?
* The Sync from primary creates advskew adjusted capr interfaces on the secondary 
* rtsold needs to be stopped when wan int brought down - restart with "onestart"
* INIT state for CARP has to be handled in addition to BACKUP and MASTER
* balance-alb on proxmox bond interface really screws up CARP - use actice/passive or deal with LACP on one switch

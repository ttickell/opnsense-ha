# opnsense-ha
Project for figuring out OPNsense HA in my home environment.

## Failure Condition Tests

| Failure | Test Condition | Expected Result | Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| AT&T Outage | AT&T Modem Power Off | Failover to Comcast < 30 Seconds | :heavy_check_mark ||
| AT&T Recovery | Power On AT&T	 Modem | Failback to AT&T and Primary | : heavy_check_mark ||
| Any Switch Failure  | Reboot switches in succession | Minimal interuption to sustained Network traffic | :x: | 246 Switch failure resulted in network failure (should not have?) |
| Primary Hardware Failure | Hard Power Off (Cable Pull) | Failover to virtual secondary firewall within 60 seconds | To Be Tested | |


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
* DUH ... secondary firewall looses internet access in real setup as the WAN interfaces are down - add default route in failover script pointing to non-CARP address of primary firewall

## New Stuff
* i don't care abotu starting /stopping dhcp6c - rtsold will start / hup it on changes
* Probably means I shoudln't bother changing state on either daemon - if the ints are down, they can't work anyway
* radvd - check this - clients are moving back and forth on failover for IPv6, unless I down the not "backup" firewall and reset client network interface
* radvd config (mostly) controlled from Services -> Router Advertisements [I knew this last year?]
* configure CARP for ipv6 THEN configure RA so CARP address may be selected  - I think?  Seems to say it can be but interface only allows "automatic"
* use configctl - configctl configd actions list to see what can be done
* https://chatgpt.com/share/68b60055-bae0-8013-ac10-bbe78f7311b5
* cp /var/db/dhcp6c_duid  /conf

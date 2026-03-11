# Lab Firewall Setup — Clean State

## PRIMARY (port 8022 / 10.220.1.2)

**1. Copy local DUID to override file**
```sh
cp /var/db/dhcp6c_duid /conf/dhcp6c_duid.override && chmod 600 /conf/dhcp6c_duid.override
```

**2. Key primary → secondary** (interactive — enter secondary root password when prompted)
```sh
cd /root/opnsense-ha && git pull --ff-only && sh setup-peer-root-ssh-key.sh 10.220.1.3
```

**3. GUI: DHCPv6 override — WAN**
> Interfaces → WAN → DHCPv6 Client → enable **Override the configuration for this interface** → set file to `/usr/local/etc/dhcp6c_wan.conf.custom` → Save → Apply

**4. GUI: DHCPv6 override — WAN2**
> Interfaces → WAN2 → DHCPv6 Client → enable **Override the configuration for this interface** → set file to `/usr/local/etc/dhcp6c_wan2.conf.custom` → Save → Apply

**5. Install HA singleton**
```sh
cd /root/opnsense-ha && ./setup-firewall --cleanup --alt-gw-ipv4 10.220.1.3 --alt-gw-ipv6 fd03:17ac:e938:4200::3 "vtnet0 vtnet1" ghcwork
```

**6. Install IPv6 tooling (standards-compliance branch)**
```sh
cd /root/opnsense-ipv6 && git fetch --all --prune && git checkout standards-compliance && git pull --ff-only && sh install.sh
```

**7. GUI: Generate API key**
> System → Access → Users → (your user) → API Keys → click **+** → copy key and secret

**8. Edit checkset-nptv6.yml**
```sh
vi /usr/local/etc/checkset-nptv6.yml
```
Fill in:
- `api-base: https://127.0.0.1/api`
- `api-key` and `api-secret` from step 7
- `ipv6-ula: fd03:17ac:e938::/48`
- `lan-interfaces` — set interface to `vtnet2`

**9. Preflight check**
```sh
cd /root/opnsense-ipv6 && sh preflight-check.sh
```

---

## SECONDARY (port 8023 / 10.220.1.3)

**1. Key secondary → primary** (interactive — enter primary root password when prompted)
```sh
cd /root/opnsense-ha && git pull --ff-only && sh setup-peer-root-ssh-key.sh 10.220.1.2
```

**2. Copy DUID from primary's override file**
```sh
scp root@10.220.1.2:/conf/dhcp6c_duid.override /conf/dhcp6c_duid.override && chmod 600 /conf/dhcp6c_duid.override
```

**3. GUI: DHCPv6 override — WAN**
> Interfaces → WAN → DHCPv6 Client → enable **Override the configuration for this interface** → set file to `/usr/local/etc/dhcp6c_wan.conf.custom` → Save → Apply

**4. GUI: DHCPv6 override — WAN2**
> Interfaces → WAN2 → DHCPv6 Client → enable **Override the configuration for this interface** → set file to `/usr/local/etc/dhcp6c_wan2.conf.custom` → Save → Apply

**5. Install HA singleton**
```sh
cd /root/opnsense-ha && ./setup-firewall --cleanup --alt-gw-ipv4 10.220.1.2 --alt-gw-ipv6 fd03:17ac:e938:4200::2 "vtnet0 vtnet1" ghcwork
```

**6. Install IPv6 tooling (standards-compliance branch)**
```sh
cd /root/opnsense-ipv6 && git fetch --all --prune && git checkout standards-compliance && git pull --ff-only && sh install.sh
```

**7. SCP checkset-nptv6.yml from primary**
```sh
scp root@10.220.1.2:/usr/local/etc/checkset-nptv6.yml /usr/local/etc/checkset-nptv6.yml
```

**8. Preflight check**
```sh
cd /root/opnsense-ipv6 && sh preflight-check.sh
```

---

## Both nodes — verification

```sh
configctl interface gateways status
route -6 get default || echo NO_IPV6_DEFAULT
netstat -rn -f inet6 | head -20
```

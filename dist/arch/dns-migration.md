# Migrating DNS to systemd-resolved

This note is for hosts installed with the earlier version of the
[Arch installation guide](./install.md), which used openresolv with
`rc-manager=resolvconf` in `/etc/NetworkManager/conf.d/rc-manager.conf`. Some
of these hosts also run a dnsmasq relay on `127.0.0.1`, added by hand outside
the guide: its files are listed in `system_dns_relay_files`, and NetworkManager
profiles point their DNS at it. Steps marked "with the relay" apply only to
those hosts.

The Ansible `dns` tag does the migration. The
[`dns` role README](../../ansible/roles/dns/README.md) describes the rules it applies;
this note is the procedure. On a host installed with the current guide there is
nothing to migrate, but the tag still writes the resolved, NetworkManager and
Docker settings.

## 1. Before you start

With Docker selected, the role moves `docker0` to `10.184.1.1/28`
(`system_docker_bridge_ip`). While your VPN is still connected, check that no
LAN or VPN route covers that address, and that the default bridge has no more
than 13 containers:

```sh
ip route show match 10.184.1.1      # only the default route should appear
docker network inspect bridge --format '{{len .Containers}}'
```

Then disconnect any VPN. While a VPN client owns `/etc/resolv.conf`, the role
leaves that file alone and the migration is incomplete.

Write down what you have now. The role backs up the files it removes, but not
the NetworkManager profiles it edits, and it keeps no copy of a `daemon.json`
it leaves unchanged:

```sh
readlink -f /etc/resolv.conf
for uuid in $(nmcli -g UUID connection show); do
  nmcli -e no -t -f connection.uuid,connection.id,ipv4.method,ipv4.dns,ipv4.ignore-auto-dns,ipv6.method,ipv6.dns,ipv6.ignore-auto-dns \
    connection show "$uuid"
done > ~/dns-profiles-before.txt
cp /etc/docker/daemon.json ~/docker-daemon-before.json 2>/dev/null ||
  echo 'no daemon.json'
```

## 2. Preview the changes

```sh
make check TAGS=dns BECOME_PASS=1
```

Check mode changes nothing and creates no backup. Read these messages if they
appear:

| Message                                                                             | What to do                                                                                                                                                          |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DNS policy skipped, nothing was changed`                                           | Install or start what the message names (systemd-resolved, NetworkManager, `nmcli`), then run again.                                                                |
| `Require the Docker bridge address to be free for resolved` fails                   | Another program listens on port 53 on the Docker bridge address or on all addresses. Stop or reconfigure it.                                                        |
| `Require systemd-resolved to listen on the Docker bridge` fails (not in check mode) | resolved did not bind port 53 on the bridge address, and `daemon.json` was not changed. Read `journalctl -u systemd-resolved`, fix the cause, then run again.       |
| `Pin the Docker bridge and its DNS server` fails on `fixed-cidr`                    | The `fixed-cidr` lies outside the new bridge network. Change `fixed-cidr` in `/etc/docker/daemon.json`, or set `system_docker_bridge_ip`.                           |
| `Report legacy NetworkManager settings left in place`                               | These files set more than the DNS mode. Remove their `dns=` and `rc-manager=` lines yourself, or they keep overriding resolved.                                     |
| `Report profiles moved to DHCP DNS`                                                 | With the relay. Nothing to do: these profiles will take their DNS servers from DHCP. Check that each one gets servers from its network.                             |
| `Report static profiles that pointed at the relay`                                  | With the relay. These profiles do not use automatic addressing and would have no DNS left. Set their servers yourself, using the `server=` lines the message lists. |
| `Report profiles that mix loopback and remote DNS servers`                          | With the relay. Remove the loopback server from these profiles yourself.                                                                                            |
| `Report a resolv.conf owned by another program`                                     | A VPN client is probably still connected. Disconnect it and run again.                                                                                              |

## 3. Apply

Keep the output: `Report profiles moved to DHCP DNS` lists the profiles the
role changed, which you need to undo the migration. `pipefail` keeps the exit
status of `make` despite `tee`:

```sh
set -o pipefail
make deploy TAGS=dns BECOME_PASS=1 2>&1 | tee ~/dns-migration.log
```

With the relay, DNS lookups may fail for a few seconds between the dnsmasq stop
and the `resolv.conf` switch. The play then checks that resolved answers, and
fails if it does not.

If the output asks you to reconnect VPN, WireGuard or tun connections, do it.
With Docker selected, restart it when no container needs to stay up:

```sh
sudo systemctl restart docker.service
```

## 4. Check the result

```sh
readlink -f /etc/resolv.conf          # /run/systemd/resolve/stub-resolv.conf
systemctl is-enabled systemd-resolved # enabled
systemctl is-enabled dnsmasq          # disabled or not found, with the relay
resolvectl status                     # each link lists its DNS servers
resolvectl query --cache=no archlinux.org
```

With Docker:

```sh
docker run --rm alpine nslookup archlinux.org
```

A second run of the tag should report `changed=0`.

Then reboot, connect your VPN once, and run the checks again. A VPN client that
writes `/etc/resolv.conf` itself may leave a regular file behind after
disconnecting. If the file carries a systemd-resolved header or lists only
loopback servers, the next run of the tag links it back to the stub.

## 5. Undo the migration

Undo before step 6: going back needs openresolv, and dnsmasq with the relay.

First stop later runs from migrating the host again, full runs included. Add
this to `ansible/host_vars/localhost.yml`:

```yaml
system_dns_manage: false
```

### Restore the files

The backups are root-only copies in mode `0600` (see
[Backups](../../ansible/roles/dns/README.md#backups)). Do not restore them with `cp -a`:
it would also copy the `0700` mode of the backup directories onto `/etc`. The
commands below run in one terminal, since later blocks reuse `$B`. List the
backups, then reinstall each file with its normal mode:

```sh
B=/var/lib/dotfiles/dns-backup
sudo find "$B" -type f | sort
sudo find "$B" -type f ! -name '*~' -printf '%P\n' | while read -r file; do
  mode=0644
  case $file in etc/NetworkManager/dispatcher.d/*) mode=0755 ;; esac
  sudo install -D -m "$mode" "$B/$file" "/$file"
done
```

A later run of the tag may have backed up a stub copy over the original
`resolv.conf`; the original then sits next to it as
`resolv.conf.<pid>.<date>~`. Reinstall the earliest copy written by openresolv,
if there is one. The order comes from the backup date in the name: file
times keep the time of the original file, not of the backup.

```sh
original=$(sudo find "$B/etc" -maxdepth 1 -name 'resolv.conf*' \
  -exec grep -q '^# Generated by resolvconf' {} \; -print |
  awk -F . '{ print (/~$/ ? $NF : "~"), $0 }' | sort | head -n 1 | cut -d ' ' -f 2-)
[ -n "$original" ] && sudo install -m 0644 "$original" /etc/resolv.conf
```

If `/etc/resolv.conf` is still a link, or a copy of the resolved stub, remove
it. openresolv writes it again once the services are switched back:

```sh
if [ -L /etc/resolv.conf ] ||
  sudo grep -q '^# This is /run/systemd/resolve/' /etc/resolv.conf; then
  sudo rm -f /etc/resolv.conf
fi
```

### Switch the services back

Remove the policy files and stop resolved. Its sockets would start it again on
the next lookup, so stop them too. The earlier guide left systemd-resolved
disabled:

```sh
sudo rm -f /etc/NetworkManager/conf.d/60-dotfiles-dns.conf
sudo find /etc/systemd/resolved.conf.d -maxdepth 1 \
  -name '60-dotfiles-dns.conf*' -delete
sudo systemctl disable --now systemd-resolved.service \
  systemd-resolved-varlink.socket systemd-resolved-monitor.socket
sudo systemctl reload NetworkManager.service
[ -e /etc/resolv.conf ] || sudo resolvconf -u
```

With the relay, recreate its runtime files and start it:

```sh
sudo systemd-tmpfiles --create /etc/tmpfiles.d/dnsmasq-upstream.conf
sudo systemctl enable --now dnsmasq.service
```

Then set the DNS of each profile listed in `~/dns-migration.log` back to the
values in `~/dns-profiles-before.txt`, for both families, and reconnect it so
the dispatcher hands the upstream servers to the relay again. For example:

```sh
nmcli connection modify '<uuid>' \
  ipv4.dns 127.0.0.1 ipv4.ignore-auto-dns yes \
  ipv6.dns '' ipv6.ignore-auto-dns no
nmcli connection up '<uuid>'
```

### Docker

With Docker, put back the file you saved in step 1, then restart Docker:

```sh
if [ -f ~/docker-daemon-before.json ]; then
  sudo install -m 0644 ~/docker-daemon-before.json /etc/docker/daemon.json
else
  sudo rm -f /etc/docker/daemon.json   # step 1 printed "no daemon.json"
fi
sudo systemctl restart docker.service
```

## 6. Remove the old packages

Once the migration has worked through a reboot, remove what the earlier setup
left. The role removes no package, and `packages_action=reconcile` does not
know openresolv or dnsmasq because they were installed by hand.

### openresolv

openresolv's `resolvconf` writes `/etc/resolv.conf` itself when a tool such as
`wg-quick` calls it, which bypasses resolved. `systemd-resolvconf` hands those
servers to resolved instead. It provides `openresolv`, so check the name pacman
prints:

```sh
pacman -Q openresolv
```

If it prints `openresolv`, replace it. The two packages conflict, and pacman
offers to remove openresolv:

```sh
sudo pacman -S systemd-resolvconf
```

### dnsmasq

With the relay, dnsmasq is no longer needed for DNS, but libvirt starts its own
copy for NAT networks, and NetworkManager does the same for shared connections
such as a hotspot. Check both:

```sh
pgrep -a dnsmasq
sudo virsh net-list --all
sudo grep -rl 'method=shared' /etc/NetworkManager/system-connections/
```

Keep dnsmasq when one of these applies:

- `pgrep` shows a process with `--conf-file=/var/lib/libvirt/dnsmasq/...`;
- `virsh net-list` shows an active network, or one with autostart;
- `grep` prints a file name.

A libvirt NAT network such as `default` stops working without dnsmasq: its
virtual machines get no address and no DNS.

Otherwise remove it. Without `-n`, pacman keeps a modified `/etc/dnsmasq.conf`
as `/etc/dnsmasq.conf.pacsave`:

```sh
sudo pacman -Rs dnsmasq
```

### Orphaned dependencies

List the packages that nothing needs anymore, read the list, then remove them.
A single `t` leaves out the packages another installed package lists as an
optional dependency; `-tt` would include them. An empty list means there is
nothing to remove:

```sh
pacman -Qdtq
sudo pacman -Rns $(pacman -Qdtq)
```

## 7. Clean up

Once DNS has worked through a reboot and a VPN connection, delete the backups
and your notes:

```sh
sudo rm -r /var/lib/dotfiles/dns-backup
sudo find /etc/docker -name 'daemon.json.*~' -delete
rm -f ~/dns-profiles-before.txt ~/dns-migration.log ~/docker-daemon-before.json
```

# Migrating DNS to systemd-resolved

This note is for hosts installed with the earlier version of the
[Arch installation guide](./install.md): openresolv with
`rc-manager=resolvconf`, a standalone dnsmasq relay on `127.0.0.1`, and
NetworkManager profiles whose DNS points at that relay. The Ansible `dns` tag
does the migration. The [Ansible guide](../../ansible/README.md#dns) describes
every rule it applies; this note is the procedure.

A host installed with the current guide has nothing to migrate. Running the tag
there only checks the configuration.

## 1. Before you start

Disconnect any VPN. While a VPN client owns `/etc/resolv.conf`, the role leaves
that file alone and the migration is incomplete.

Write down what you have now. The role backs up the files it removes, but it
does not back up the NetworkManager profiles it edits:

```sh
readlink -f /etc/resolv.conf
nmcli -f NAME,UUID,TYPE connection show
for uuid in $(nmcli -g UUID connection show); do
  nmcli -e no -t -f connection.id,ipv4.method,ipv4.dns,ipv6.method,ipv6.dns \
    connection show "$uuid"
done > ~/dns-profiles-before.txt
```

## 2. Preview the changes

```sh
make install ANSIBLE_ARGS="--tags dns --ask-become-pass --check --diff"
```

Check mode reports what would change without changing anything or creating
backups. Read these messages if they appear:

| Message | What to do |
| --- | --- |
| `DNS policy skipped, nothing was changed` | Install or start what the message names (systemd-resolved, NetworkManager, `nmcli`), then run again. |
| `Require the Docker bridge address to be free for resolved` fails | Another program listens on port 53 on the Docker bridge address or on all addresses. Stop or reconfigure it. |
| `Pin the Docker bridge and its DNS server` fails on `fixed-cidr` | The `fixed-cidr` lies outside the new bridge network. Change `fixed-cidr` in `/etc/docker/daemon.json`, or set `system_docker_bridge_ip`. |
| `Report static profiles that pointed at the relay` | These profiles have a manual method and would have no DNS left. Set their servers yourself, using the `server=` lines the message lists. |
| `Report profiles that mix loopback and remote DNS servers` | Remove `127.0.0.1` from these profiles yourself. |
| `Report a resolv.conf owned by another program` | A VPN client is probably still connected. Disconnect it and run again. |

## 3. Apply

Keep the output: it lists the profiles the role changed, which you need to undo
the migration.

```sh
make install ANSIBLE_ARGS="--tags dns --ask-become-pass" 2>&1 | tee ~/dns-migration.log
```

DNS lookups may fail for a few seconds between the dnsmasq stop and the
`resolv.conf` switch. The play ends by checking that resolved answers, and it
fails if it does not.

If the output asks you to reconnect VPN, WireGuard or tun connections, do it:
the role does not reapply them in place.

With Docker selected, restart it when no container needs to stay up, so it
reads the new `daemon.json`:

```sh
sudo systemctl restart docker.service
```

## 4. Check the result

```sh
readlink -f /etc/resolv.conf          # /run/systemd/resolve/stub-resolv.conf
systemctl is-enabled systemd-resolved # enabled
systemctl is-enabled dnsmasq          # disabled, or not found
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

## 5. Remove the old packages

The role removes no package, and `packages_action=reconcile` does not know
these two because the earlier guide installed them by hand.

### openresolv

`systemd-resolvconf` provides `openresolv`, so `pacman -Qi openresolv` shows
`systemd-resolvconf` once the switch is done. Check the name pacman prints:

```sh
pacman -Q openresolv
```

If it prints `openresolv`, replace it. The two packages conflict, and pacman
offers to remove openresolv:

```sh
sudo pacman -S systemd-resolvconf
```

### dnsmasq

The relay no longer needs dnsmasq, but libvirt starts its own copy for NAT
networks, and NetworkManager does the same for shared connections such as a
hotspot. Check both:

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

Otherwise remove it. pacman keeps a modified `/etc/dnsmasq.conf` as
`/etc/dnsmasq.conf.pacsave`:

```sh
sudo pacman -Rns dnsmasq
```

### Orphaned dependencies

List the packages that nothing needs anymore, read the list, then remove them.
The double `t` keeps out the packages another package still lists as an
optional dependency, such as dnsmasq for libvirt:

```sh
pacman -Qdttq
sudo pacman -Rns $(pacman -Qdttq)
```

## 6. Undo the migration

The role copied every file it removed or replaced to
`/var/lib/dotfiles/dns-backup`, under its full path. `daemon.json` has a
timestamped copy next to it instead.

```sh
sudo find /var/lib/dotfiles/dns-backup -type f
```

To go back to the relay:

```sh
sudo cp -a --remove-destination /var/lib/dotfiles/dns-backup/etc/. /etc/
sudo rm /etc/NetworkManager/conf.d/60-dotfiles-dns.conf \
  /etc/systemd/resolved.conf.d/60-dotfiles-dns.conf
sudo systemctl disable --now systemd-resolved.service
sudo systemctl enable --now dnsmasq.service
sudo systemctl reload NetworkManager.service
```

The earlier guide left systemd-resolved disabled, hence the `disable`.

`--remove-destination` replaces the `/etc/resolv.conf` link with the saved
file instead of writing through the link into `/run`. Then set the DNS of each
profile listed in `~/dns-migration.log` back to the values in
`~/dns-profiles-before.txt`, for example:

```sh
nmcli connection modify "<profile>" ipv4.dns 127.0.0.1 ipv4.ignore-auto-dns yes
```

Do not run the `dns` tag again afterwards, or it migrates the host again.

## 7. Clean up

Once DNS has worked through a reboot and a VPN connection, delete the backups
and your notes:

```sh
sudo rm -r /var/lib/dotfiles/dns-backup
rm ~/dns-profiles-before.txt ~/dns-migration.log
```

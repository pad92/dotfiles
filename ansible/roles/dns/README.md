# dns

Makes systemd-resolved the only DNS resolver, for the host and for Docker
containers, and migrates hosts from the former openresolv setup and dnsmasq
relay.

## Requirements

- `systemd-resolved.service`, a running `NetworkManager.service` and `nmcli`.
  When one is missing, the role says which and changes nothing.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                        | Default                                                    | Description                                                                  |
| :------------------------------ | :--------------------------------------------------------- | :--------------------------------------------------------------------------- |
| `dns_manage`                    | `true`                                                     | `false` leaves the resolver alone on every run, full runs included.          |
| `dns_llmnr`                     | `'no'`                                                     | resolved `LLMNR=`. Keep it quoted: a bare `no` is a boolean.                 |
| `dns_multicast_dns`             | `resolve`                                                  | resolved `MulticastDNS=`: `.local` names resolve, the host is not announced. |
| `dns_fallback_servers`          | `[]`                                                       | resolved `FallbackDNS=`. Empty disables the compiled-in public resolvers.    |
| `dns_resolved_dropin`           | `/etc/systemd/resolved.conf.d/60-dotfiles-dns.conf`        | resolved drop-in.                                                            |
| `dns_networkmanager_conf`       | `/etc/NetworkManager/conf.d/60-dotfiles-dns.conf`          | NetworkManager drop-in that hands each link's servers to resolved.           |
| `dns_docker_bridge_ip`          | `10.184.1.1/28`                                            | `docker0` address, used as Docker's `bip` and `dns`.                         |
| `dns_docker_daemon_config_path` | `/etc/docker/daemon.json`                                  | Docker daemon configuration.                                                 |
| `dns_relay_files`               | see `defaults/main.yml`                                    | Files that identify the former dnsmasq relay.                                |
| `dns_legacy_files`              | `dns.conf`, `rc-manager.conf` in NetworkManager's `conf.d` | Former NetworkManager settings to remove.                                    |
| `dns_backup_dir`                | `/var/lib/dotfiles/dns-backup`                             | Where removed or replaced files are copied first.                            |
| `dns_resolv_conf`               | `/etc/resolv.conf`                                         | Linked to the resolved stub.                                                 |
| `dns_resolved_stub`             | `/run/systemd/resolve/stub-resolv.conf`                    | Stub file.                                                                   |
| `dns_force_resolv_conf_link`    | `false`                                                    | Replace a `resolv.conf` written by another program, such as a VPN client.    |
| `dns_unit_directory`            | `/usr/lib/systemd/system`                                  | Where the units are looked up.                                               |

The [DNS migration note](../../../dist/arch/dns-migration.md) gives the
migration procedure; this file describes the rules it relies on.

## Policy

- `LLMNR=no`: a single-label name that DNS cannot resolve is never asked on the
  local network, where any host could answer it.
- `MulticastDNS=resolve`: `.local` names still resolve, but the host does not
  announce its name.
- An empty `FallbackDNS=`: when no link has DNS servers, lookups fail instead
  of going in clear text to the compiled-in public resolvers.

## Docker

With `12_containers_docker`, resolved also listens on `dns_docker_bridge_ip`.
The role sets it as `bip` and as the only `dns` entry in `daemon.json`, and
keeps the other keys. Containers then get the host's view, VPN split DNS
included. The listener binds even while `docker0` is absent.

Docker reads the file at startup: restart `docker.service` yourself when no
container needs to stay up. Without an earlier `bip`, Docker used
`172.17.0.1/16`, so containers on the default bridge get new addresses, and the
new network must not overlap a LAN or VPN route.

A `/28` leaves 13 addresses for containers on the default bridge.
User-defined networks take their subnets from `default-address-pools`. A
`fixed-cidr` inside the bridge network is kept; one outside it stops the play,
since Docker would refuse to start. An empty `daemon.json` is read as `{}`.

Before any change, the role lists the port 53 listeners with `ss`. If a program
other than resolved, or the relay dnsmasq it is about to stop, holds port 53 on
the bridge address or on all addresses, the play stops and names it. The relay
is recognised by the main PID of `dnsmasq.service`. libvirt's dnsmasq listens
on its own bridge addresses and does not conflict.

After the `resolv.conf` switch, the play fails if resolved does not hold port
53 on the bridge address over both UDP and TCP: resolved only logs a listener
it cannot bind. Check mode skips this, since it does not restart resolved.

Removing `12_containers_docker` later drops the listener but leaves `bip` and
`dns` in `daemon.json`. Remove the `dns` entry yourself if Docker stays
installed.

## resolv.conf

The role enables and starts resolved, then links `dns_resolv_conf` to the stub.
A link that already resolves to the stub is left alone. A link to another
file, `/run/systemd/resolve/resolv.conf` included, is replaced: that file sends
programs straight to the upstream servers and skips the resolved policy.

A regular file is replaced only when it has an openresolv, NetworkManager or
systemd-resolved header, or when all its name servers are loopback addresses
(the former relay, or a stale copy of the stub). Any other file is left alone,
and the play prints its first comment line: typically a VPN client that
rewrote it while connected. Run the role again after disconnecting, or set
`dns_force_resolv_conf_link: true`.

If the stub is missing once resolved has started, the play fails before the
link. After the switch it runs `resolvectl query localhost`, which needs no
network, and fails if resolved does not answer. The Docker settings are
written last.

## Former dnsmasq relay

The relay is recognised by `dns_relay_files`. Only when one of them exists does
the role touch NetworkManager profiles and `dnsmasq.service`. Without them, a
loopback DNS server is a deliberate local resolver (unbound, dnscrypt-proxy)
and is left alone.

With the relay present:

- A profile family whose DNS servers are all loopback addresses and whose
  method is automatic goes back to DHCP DNS. It is reapplied without
  reconnecting, except VPN, WireGuard and tun connections, which are listed
  for you to reconnect.
- A family with another method (`manual`, `link-local`, `shared`) would have no
  server left: it is reported, unchanged, with the `server=` lines of the relay
  files as candidates.
- Profiles that mix loopback and remote servers are reported and unchanged.
  Profiles without IP settings are skipped.
- The relay files are removed and `dnsmasq.service` is stopped and disabled.

`dns_legacy_files` are removed when they set nothing but `dns=` or
`rc-manager=` in `[main]`. A file with other settings is kept and reported.

The role removes no package: openresolv and the relay's dnsmasq were installed
outside the package lists, and the migration note covers their removal.

### Order

resolved starts first, then the profiles change, dnsmasq stops and the relay
files go. dnsmasq stops before its files, because they are how the role
recognises the relay: an interrupted run can still finish on the next one.
resolved is then restarted (it binds extra listeners and drops the fallbacks
only at startup), NetworkManager reloaded, and `resolv.conf` switches last.
Lookups through the old `resolv.conf` fail in the short window between the
dnsmasq stop and the switch.

Check mode changes nothing and creates no backup, but still reports the
profiles it would move to DHCP DNS.

## Backups

Each removed or replaced file is first copied under its full path to
`dns_backup_dir`, for example `/var/lib/dotfiles/dns-backup/etc/resolv.conf`.
The directory is readable by root only and the copies have mode `0600`, so
restore them with an explicit mode rather than `cp -a`. A later backup of the
same path keeps the earlier copy as `<file>.<pid>.<date>~`; order the copies by
that date, since their file times are those of the originals. `daemon.json`
gets a timestamped copy next to it instead. NetworkManager profiles are not
backed up.

```sh
make deploy TAGS=dns BECOME_PASS=1
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: dns
      tags: [dns]
```

## License

Unlicense

## Author Information

pad

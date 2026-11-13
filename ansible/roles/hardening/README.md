# hardening

Applies the desktop sysctl policy and the SSH client defaults. It never
configures the SSH server.

## Requirements

- Privilege escalation (`become: true`).

## Role Variables

| Variable                 | Default | Description                                                    |
| :----------------------- | :------ | :------------------------------------------------------------- |
| `hardening_ipv6_enabled` | `true`  | `false` disables IPv6 on every interface, existing and future. |

The role also reads `packages_selected_groups`: `12_containers_docker` or
`13_containers_podman` enables IPv4 forwarding, and `21_steam` raises
`vm.max_map_count`.

## SSH client

The `ssh_client_hardening` tag makes the system SSH client hash the host names
it adds to `known_hosts`. Existing entries are not converted.

## Kernel settings

The `kernel_hardening` tag manages `/etc/sysctl.d/60-dotfiles-hardening.conf`
and `/etc/sysctl.d/70-dotfiles-bpf.conf`. Their prefixes place the local policy
after the package defaults in `/usr/lib/sysctl.d/`, as systemd recommends. The
role backs up its former drop-ins before removing them.

The policy keeps the filesystem protections, ASLR, the ptrace and
kernel-address restrictions, and the inotify limits. It uses loose
reverse-path filtering for asymmetric VPN routes and disables shared-media
redirects. IPv4 forwarding is enabled only with a container group, and
disabled otherwise. IPv6 stays enabled so LAN and VPN interfaces can configure
it; `hardening_ipv6_enabled: false` sets the `all` and `default` sysctls.

- `vm.mmap_rnd_bits` stays at `32` only when that value is already active,
  since some kernels reject it.
- The user-namespace setting is written only when the kernel exposes it.
- `net.core.bpf_jit_harden` is `2` when available. Unprivileged BPF is
  persisted as the reversible `2` in `70-dotfiles-bpf.conf`, and applied at
  once when its active value is `0`; a kernel already locked at `1` keeps it
  until reboot.

### Steam

With `21_steam`, `60-dotfiles-hardening.conf` gets
`vm.max_map_count = 2147483642`, the value Proton documents for games that
need more mappings. The old `80-gamecompatibility.conf` and
`99-cachyos-gaming.conf` are backed up as `<filename>.dotfiles-backup` before
removal; an existing backup is kept as a timestamped copy. Swappiness, dirty
page writeback, scheduler behavior, network backlog, file-handle limits and
compatibility-mode mmap randomization stay at the kernel or distribution
defaults.

### Migration

The migration removes `kernel.kexec_load_disabled=1`, which cannot be undone
until reboot, keeps TCP timestamps with their randomized offsets, and drops
the interface-specific IPv6 overrides. Reboot once afterwards to clear these
runtime settings. Ansible never reboots the host.

```sh
make deploy TAGS=kernel_hardening BECOME_PASS=1
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: hardening
      tags: [hardening]
```

## License

Unlicense

## Author Information

pad

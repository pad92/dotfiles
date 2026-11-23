# hardening

Applies the desktop sysctl policy and the SSH client defaults. It never
configures the SSH server.

## Requirements

- Privilege escalation (`become: true`).

## Role Variables

| Variable                 | Default | Description                                                                                                    |
| :----------------------- | :------ | :------------------------------------------------------------------------------------------------------------- |
| `hardening_ipv6_enabled` | `true`  | `false` disables IPv6 on every interface, existing and future. The role refuses a value that is not a boolean. |

The kernel template also reads the selected package groups, from
`packages_group_selection`, then `packages_selected_groups`, then
`packages_host_groups`. `12_containers_docker` or `13_containers_podman`
enables IPv4 forwarding, and `21_steam` adds the Steam settings below.

## SSH client

The `ssh_client_hardening` tag makes the system SSH client hash the host names
it adds to `known_hosts`. Existing entries are not converted.

## Kernel settings

The `kernel_hardening` tag manages `/etc/sysctl.d/60-hardening.conf` and
`/etc/sysctl.d/70-bpf.conf`. Their prefixes place the local policy after the
package defaults in `/usr/lib/sysctl.d/`, as systemd recommends. The role backs
up its former drop-ins as `<filename>.dotfiles-backup` before removing them,
among them `hardening.conf`, `60-dotfiles-hardening.conf`,
`70-dotfiles-bpf.conf` and any `zz-dotfiles-*` file.

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
  persisted as the reversible `2` in `70-bpf.conf`, and applied at once when
  its active value is `0`. A kernel already locked at `1` keeps it until
  reboot.

### Steam

With `21_steam`, `60-hardening.conf` gets `vm.max_map_count = 2147483642`,
the value Proton documents for games that need more mappings. It also sets
`vm.dirty_ratio = 10` and `vm.dirty_background_ratio = 5`, so writeback starts
earlier and a large shader cache or game download stalls the desktop less. A
later file that sets `vm.dirty_bytes` or `vm.dirty_background_bytes` takes
precedence, because the kernel keeps only the last of each pair.

The old `80-gamecompatibility.conf` and `99-cachyos-gaming.conf` are backed up
the same way before removal. An existing backup is kept as a timestamped copy.
Swappiness, scheduler behavior, network backlog, file-handle limits and
compatibility-mode mmap randomization stay at the kernel or distribution
defaults.

### Migration

The migration removes `kernel.kexec_load_disabled=1`, which cannot be undone
until reboot, keeps TCP timestamps with their randomized offsets, and drops
the interface-specific IPv6 overrides. Reboot once afterwards to clear these
runtime settings. Ansible never reboots the host. To run only this part, pass
the `kernel_hardening` tag as shown in [Running](../../README.md#running).

## Tags

- `system` and `hardening` run the whole role.
- `ssh_client_hardening` runs the SSH client tasks.
- `kernel_hardening` runs the sysctl tasks.

## Dependencies

None. In `site.yml` the role runs after `docker` and before `dns`.

## Example Playbook

```yaml
- name: Configure the Linux workstations
  hosts: all
  become: true
  roles:
    - role: hardening
      when: packages_action | default('install') != 'plan'
      tags: [system, hardening]
```

## License

Unlicense

## Author Information

pad

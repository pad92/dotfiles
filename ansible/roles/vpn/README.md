# vpn

Configures an openfortivpn SAML VPN as the `openfortivpn@<name>.service`
instance, and lets the local users start and stop it.

## Requirements

- `openfortivpn`, installed by the `23_vpn` package group. `site.yml` runs the
  role only on hosts that select it.
- `vault_vpn_gateway_host` in the Ansible Vault. Without it the role changes
  nothing and leaves the files of an earlier run in place.
- Privilege escalation (`become: true`).

## Role Variables

| Variable              | Default                                                     | Description                                                                                         |
| :-------------------- | :---------------------------------------------------------- | :-------------------------------------------------------------------------------------------------- |
| `vpn_gateway_host`    | `"{{ vault_vpn_gateway_host \| default('') }}"`             | Gateway DNS name. Empty skips the role.                                                             |
| `vpn_gateway_port`    | `'{{ vault_vpn_gateway_port \| default(443) }}'`            | Gateway port, from 1 to 65535.                                                                      |
| `vpn_name`            | `work`                                                      | Instance name, matching `^[a-z0-9][a-z0-9_-]*$`. The daemon reads `<config dir>/<name>.conf`.       |
| `vpn_saml_port`       | `8020`                                                      | Local port where the browser hands back the SAML session, from 1024 to 65535.                       |
| `vpn_start_timeout`   | `5min`                                                      | Start timeout. The unit is ready only after the browser login.                                      |
| `vpn_config_dir`      | `/etc/openfortivpn`                                         | Daemon configuration directory.                                                                     |
| `vpn_unit_dropin_dir` | `/etc/systemd/system/openfortivpn@{{ vpn_name }}.service.d` | Unit drop-in directory.                                                                             |
| `vpn_polkit_rule`     | `/etc/polkit-1/rules.d/60-dotfiles-vpn.rules`               | polkit rule.                                                                                        |
| `vpn_waybar_config`   | `/etc/openfortivpn/waybar.json`                             | File read by the Waybar `VPN` module.                                                               |
| `vpn_users`           | `["{{ ansible_facts['user_id'] }}"]`                        | Users allowed to start and stop the unit. A non-empty list of names matching `^[a-z_][a-z0-9_-]*$`. |
| `vpn_unit_directory`  | `/usr/lib/systemd/system`                                   | Where the `openfortivpn@.service` unit is looked up. The play fails when it is missing.             |

The gateway comes from `vault_vpn_gateway_host` and `vault_vpn_gateway_port`
in `ansible/group_vars/all/vault_vpn.yml`, a Vault file that Git ignores. See
[Vault](../../README.md#vault) to create it. The host must be DNS labels of at
most 253 characters and the ports numbers, because a newline or a space could
otherwise add settings to the daemon configuration or the polkit rule. The
role also reads the `user_id` fact, which `site.yml` gathers as the SSH user.

## Behavior

The role writes:

- `<config dir>/<name>.conf` (root, `0600`): SAML login on `vpn_saml_port`,
  `set-dns = 1`, `use-resolvconf = 1` and `pppd-use-peerdns = 0`. The DNS
  servers and search domains reach systemd-resolved on the `ppp0` link through
  `systemd-resolvconf`, so `/etc/resolv.conf` stays the stub link and the link
  settings go with the tunnel, even after a crash. The
  [dns role](../dns/README.md#resolvconf) manages that link.
- A unit drop-in with `TimeoutStartSec` and `Restart=no`, since each attempt
  needs a new login. A change reloads systemd.
- The polkit rule (`0644`): the users of `vpn_users`, from an active local
  session, may start and stop that unit without a password. Other units and
  verbs keep the default policy.
- The Waybar file: the unit name and the login URL,
  `https://<host>:<port>/remote/saml/start?redirect=1`. A click on the module
  starts the unit and opens the login page. The module turns yellow while it
  waits for the browser and green once the tunnel is up, and a second click
  disconnects. While connected, the tooltip shows the address of the `ppp`
  interface run by the unit, how long its `pppd` has been up (a reconnection
  restarts it), the rate averaged since the previous refresh (30 seconds) and
  the bytes received and sent since the tunnel came up. The module script,
  `~/.config/waybar/modules/vpn`, is deployed by the `dotfiles` role.

From a terminal:

```sh
systemctl start --no-block openfortivpn@work.service
journalctl -fu openfortivpn@work.service
```

## Tags

`system` and `vpn` run the role.

## Dependencies

None. In `site.yml` the role runs after `dns` and before `gpu`.

## Example Playbook

```yaml
- name: Configure the Linux workstations
  hosts: all
  become: true
  roles:
    - role: vpn
      when:
        - packages_action | default('install') != 'plan'
        - >-
          '23_vpn' in (packages_selected_groups |
          default(packages_host_groups | default(none) or []))
      tags: [system, vpn]
```

## License

Unlicense

## Author Information

pad

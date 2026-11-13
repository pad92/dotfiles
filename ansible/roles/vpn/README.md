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

| Variable              | Default                                             | Description                                                    |
| :-------------------- | :-------------------------------------------------- | :------------------------------------------------------------- |
| `vpn_gateway_host`    | `vault_vpn_gateway_host`                            | Gateway DNS name.                                              |
| `vpn_gateway_port`    | `vault_vpn_gateway_port`, else `443`                | Gateway port.                                                  |
| `vpn_name`            | `work`                                              | Instance name; the daemon reads `<config dir>/<name>.conf`.    |
| `vpn_saml_port`       | `8020`                                              | Local port where the browser hands back the SAML session.      |
| `vpn_start_timeout`   | `5min`                                              | Start timeout: the unit is ready only after the browser login. |
| `vpn_config_dir`      | `/etc/openfortivpn`                                 | Daemon configuration directory.                                |
| `vpn_unit_dropin_dir` | `/etc/systemd/system/openfortivpn@<name>.service.d` | Unit drop-in directory.                                        |
| `vpn_polkit_rule`     | `/etc/polkit-1/rules.d/60-dotfiles-vpn.rules`       | polkit rule.                                                   |
| `vpn_waybar_config`   | `/etc/openfortivpn/waybar.json`                     | File read by the Waybar `VPN` module.                          |
| `vpn_users`           | the SSH user                                        | Users allowed to start and stop the unit.                      |
| `vpn_unit_directory`  | `/usr/lib/systemd/system`                           | Where the unit is looked up.                                   |

The gateway lives in a Vault file that Git ignores:

```sh
ansible-vault create --vault-password-file .vault ansible/group_vars/all/vault_vpn.yml
```

```yaml
vault_vpn_gateway_host: vpn.example.com
vault_vpn_gateway_port: 443
```

The host must be a DNS name and the ports numbers: a newline or a space could
otherwise add settings to the daemon configuration or the polkit rule.

## Behavior

The role writes:

- `<config dir>/<name>.conf` (root, `0600`): SAML login on `vpn_saml_port`,
  `set-dns = 1` and `use-resolvconf = 1`. The DNS servers and search domains
  reach systemd-resolved on the `ppp0` link through `systemd-resolvconf`, so
  `/etc/resolv.conf` stays the stub link and the link settings go with the
  tunnel, even after a crash.
- A unit drop-in with `TimeoutStartSec` and `Restart=no`, since each attempt
  needs a new login.
- The polkit rule: the users of `vpn_users`, from an active local session, may
  start and stop that unit without a password. Other units and verbs keep the
  default policy.
- The Waybar file: the unit name and the login URL. A click on the module
  starts the unit and opens the login page; it turns yellow while it waits for
  the browser and green once the tunnel is up. A second click disconnects.

From a terminal:

```sh
systemctl start --no-block openfortivpn@work.service
journalctl -fu openfortivpn@work.service
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: vpn
      when: "'23_vpn' in packages_selected_groups"
      tags: [vpn]
```

## License

Unlicense

## Author Information

pad

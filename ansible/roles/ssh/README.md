# ssh

Deploys the user's `~/.ssh` from the Ansible Vault: the OpenSSH client
configuration, per-host blocks, key pairs, `authorized_keys` and pinned host
keys. The role and the repository hold no key, address or host name.

It manages the client side of the user account only. The SSH server and the
system-wide client hardening stay in the `hardening` role.

## Requirements

- The `vault_ssh_*` variables in a Vault file that Git ignores. Without them
  the role prints a message, changes nothing and leaves the files of an
  earlier run in place.
- The OpenSSH client, to check the configuration before it is written (the
  check is skipped without it).
- No privilege escalation: the role runs as the user (`become: false`).

## Role Variables

| Variable                         | Default                                 | Description                                                              |
| :------------------------------- | :-------------------------------------- | :----------------------------------------------------------------------- |
| `ssh_config_options`             | `vault_ssh_config_options`, else `{}`   | `Host *` options, as `{Option: value}`. A list repeats the option.       |
| `ssh_config_fragments`           | `vault_ssh_config_fragments`, else `{}` | Per-host blocks, as `{file name: OpenSSH text}`, written to `config.d/`. |
| `ssh_config_fragments_exclusive` | `false`                                 | Delete the files of `config.d/` that the vault does not list (not dirs). |
| `ssh_authorized_keys`            | `vault_ssh_authorized_keys`, else `[]`  | Public keys allowed to log in; set, the list replaces the file.          |
| `ssh_known_hosts`                | `vault_ssh_known_hosts`, else `[]`      | Pinned host keys, as `[{name, key}]`; added, the other entries stay.     |
| `ssh_keys`                       | `vault_ssh_keys`, else `[]`             | Key pairs, as `[{name, private, public}]`; `public` is optional.         |
| `ssh_extra_dirs`                 | `[sockets]`                             | Directories created in `~/.ssh`, for instance for `ControlPath`.         |
| `ssh_binary`                     | `/usr/bin/ssh`                          | Client that checks the configuration (`ssh -G`).                         |
| `ssh_home`                       | the user's home                         | Home directory that holds `.ssh`.                                        |
| `ssh_no_log`                     | `true`                                  | Hide the vault values from the output and `--diff`.                      |

Each part is managed only when its variable is set: a vault with
`authorized_keys` alone leaves `~/.ssh/config` untouched.

## Vault

[`vault_ssh.sample.yml`](vault_ssh.sample.yml) documents every variable
with placeholder values. Copy it, encrypt it with the repository password
(`.vault`) while it holds only placeholders, then replace every `<...>` value
in the editor, so that no plain file ever holds a key:

```sh
cp ansible/roles/ssh/vault_ssh.sample.yml ansible/group_vars/all/vault_ssh.yml
ansible-vault encrypt --vault-password-file .vault ansible/group_vars/all/vault_ssh.yml
ansible-vault edit --vault-password-file .vault ansible/group_vars/all/vault_ssh.yml
```

A copy that still holds a key placeholder fails the run before any change:
private keys must hold an OpenSSH private key, and public keys,
`authorized_keys` lines and `known_hosts` keys a key type followed by its
base64 blob.
Do not keep the sample itself in `group_vars/all`: Ansible loads every `.yml`
file there.

## Behavior

Before writing anything, the role checks the values. Each one lands in a
line-based file, so a newline in an option or a key, an option value that is
not a single scalar, a slash in a file name, or a key name already used in
`~/.ssh` (`config`, `known_hosts`, an `ssh_extra_dirs` entry...) fails the run
with a message that names the rule and never the value.

- `~/.ssh`, `config.d/` and the extra directories are `0700`.
- `~/.ssh/config` (`0600`) includes `config.d/*` first, then the `Host *`
  block: OpenSSH keeps the first value it reads, so a host block overrides the
  defaults. Fragments and the main file are checked with `ssh -G` before they
  replace the old ones.
- Private keys are `0600`, public keys `0644`. `authorized_keys` is `0600`.
- `known_hosts` only gains the pinned keys: the entries ssh learnt stay.

Tags: `ssh_config`, `ssh_keys`. Every task that reads a vault value runs with
`no_log`. Set `ssh_no_log=false` for one run to debug it, never in a shared
log.

## Limits

- Removing a key or a pinned host key from the vault does not delete it on
  disk. Only `config.d/` has an opt-in purge.
- `ssh -G` evaluates `Match exec` lines while it checks a fragment.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  roles:
    - role: ssh
      become: false
      tags: [ssh]
```

## License

Unlicense

## Author Information

pad

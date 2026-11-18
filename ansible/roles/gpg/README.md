# gpg

Deploys the user's `~/.gnupg` from the Ansible Vault: the GnuPG configuration
files, public and secret keys and their owner trust. The role and the
repository hold no key or address.

## Requirements

- The `vault_gpg_*` variables in a Vault file that Git ignores. Without them
  the role prints a message, changes nothing and leaves the files of an
  earlier run in place.
- `gpg` and `gpgconf`.
- No privilege escalation: the role runs as the user (`become: false`).

## Role Variables

| Variable             | Default                       | Description                                                        |
| :------------------- | :---------------------------- | :----------------------------------------------------------------- |
| `gpg_config`         | `vault_gpg_config`, else `{}` | GnuPG files, as `{name.conf: [lines]}`. Listed files are replaced. |
| `gpg_keys`           | `vault_gpg_keys`, else `[]`   | Keys, as `[{fingerprint, armor, trust}]`; `trust` is optional.     |
| `gpg_binary`         | `gpg`                         | GnuPG binary.                                                      |
| `gpg_gpgconf_binary` | `gpgconf`                     | Binary that reloads the GnuPG daemons.                             |
| `gpg_home`           | the user's home               | Home directory that holds `.gnupg`.                                |
| `gpg_homedir`        | `{{ gpg_home }}/.gnupg`       | GnuPG home directory.                                              |
| `gpg_no_log`         | `true`                        | Hide the vault values from the output and `--diff`.                |

## Vault

[`vault_gpg.sample.yml`](vault_gpg.sample.yml) documents every variable
with placeholder values. Copy it, encrypt it with the repository password
(`.vault`) while it holds only placeholders, then replace every `<...>` value
in the editor, so that no plain file ever holds a key:

```sh
cp ansible/roles/gpg/vault_gpg.sample.yml ansible/group_vars/all/vault_gpg.yml
ansible-vault encrypt --vault-password-file .vault ansible/group_vars/all/vault_gpg.yml
ansible-vault edit --vault-password-file .vault ansible/group_vars/all/vault_gpg.yml
```

A copy that still holds a key placeholder fails the run before any change.
Do not keep the sample itself in `group_vars/all`: Ansible loads every `.yml`
file there.

To fill it from an existing machine, export without printing the keys:

```sh
gpg --armor --export-secret-keys FINGERPRINT > /dev/shm/key.asc
ansible-vault edit --vault-password-file .vault ansible/group_vars/all/vault_gpg.yml
shred -u /dev/shm/key.asc
```

The secret key keeps its passphrase: `gpg --batch --import` does not ask for
it, and gpg-agent asks at the first signature.

## Behavior

Before writing anything, the role checks the values: a newline in a GnuPG
line, a file name that is not `name.conf`, a fingerprint that is not the full
40 or 64 uppercase hexadecimal characters, or an unknown trust level fails the
run with a message that names the rule and never the value.

- `~/.gnupg` is `0700` and the configuration files `0600`. A changed file
  reloads the daemons with `gpgconf --reload`.
- A key whose fingerprint is not in the keyring is imported from its armor.
  If the armor holds another key, the run fails instead of importing it again
  on every run.
- The owner trust is set only when it differs.

Tags: `gpg_config`, `gpg_keys`. Every task that reads a vault value runs with
`no_log`. Set `gpg_no_log=false` for one run to debug it, never in a shared
log.

## Limits

- Removing a key or a GnuPG file from the vault does not delete it on disk.
- Git signing (`user.signingkey`) stays in the Git configuration.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  roles:
    - role: gpg
      become: false
      tags: [gpg]
```

## License

Unlicense

## Author Information

pad

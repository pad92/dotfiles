# docker

Adds users to the `docker` group on hosts that select the
`12_containers_docker` package group.

## Requirements

- Docker installed by the `packages` role. `site.yml` runs this role only when
  `12_containers_docker` is selected.
- Privilege escalation (`become: true`).

## Role Variables

| Variable             | Default                              | Description                                                                               |
| :------------------- | :----------------------------------- | :---------------------------------------------------------------------------------------- |
| `docker_group_users` | `["{{ ansible_facts['user_id'] }}"]` | Users added to the `docker` group. Each entry must be a non-empty name other than `root`. |

The role also reads the `user_id` fact, which `site.yml` gathers as the SSH
user.

## Group membership

Membership of `docker` grants root-equivalent access to the Docker daemon.
Users are added with `append: true`, so their other groups are kept. When the
`docker` group does not exist yet, the role skips the step without an error.
A change prints a reminder to log out and back in before using `docker`
without `sudo`.

Two other roles complete the setup: `package_services` enables
`docker.socket`, and `dns` writes the bridge address and the DNS server to
`daemon.json` (see [its Docker section](../dns/README.md#docker)).

## Tags

`system` and `docker` run the role.

## Dependencies

None. In `site.yml` the role runs after `package_services` and before
`hardening`.

## Example Playbook

```yaml
- name: Configure the Linux workstations
  hosts: all
  become: true
  roles:
    - role: docker
      when:
        - packages_action | default('install') != 'plan'
        - "'12_containers_docker' in (packages_selected_groups | default([]))"
      tags: [system, docker]
```

## License

Unlicense

## Author Information

pad

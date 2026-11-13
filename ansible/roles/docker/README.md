# docker

Adds users to the `docker` group when `12_containers_docker` is selected.

## Requirements

- Docker installed by the `packages` role; `site.yml` runs the role only when
  `12_containers_docker` is selected.
- Privilege escalation (`become: true`).

## Role Variables

| Variable             | Default      | Description                        |
| :------------------- | :----------- | :--------------------------------- |
| `docker_group_users` | the SSH user | Users added to the `docker` group. |

Membership of `docker` grants root-equivalent access to the Docker daemon. Log
in again to use it. The `package_services` role enables `docker.socket`, and
the `dns` role sets the bridge address and DNS server in `daemon.json`.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: docker
      when: "'12_containers_docker' in packages_selected_groups"
      tags: [docker]
```

## License

Unlicense

## Author Information

pad

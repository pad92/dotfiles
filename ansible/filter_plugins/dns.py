"""Derive the systemd-resolved migration from NetworkManager and Docker state."""

import base64
import ipaddress
import re
from typing import Any

from ansible.errors import AnsibleFilterError

DNS_FAMILIES = ("ipv4", "ipv6")
# Methods under which a link gets DNS servers from DHCP, RA or PPP once the
# static loopback server is gone (nm-settings-nmcli(5)). With any other method
# an empty dns list leaves the link with no server at all.
AUTO_DNS_METHODS = {"ipv4": frozenset({"auto"}), "ipv6": frozenset({"auto", "dhcp"})}
# `nmcli device reapply` cannot update these connections: a VPN or WireGuard
# profile, or a tun device, only takes new DNS settings when it reconnects.
NO_REAPPLY_TYPES = frozenset({"vpn", "wireguard", "tun"})


def _is_loopback_server(server: str) -> bool | None:
    """Return None for entries that cannot be parsed, so they are never rewritten."""
    address = server.split("#", 1)[0].strip()
    if address.startswith("[") and "]" in address:
        address = address[1 : address.index("]")]
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return None


def _keyed_fields(uuid: str, stdout: str) -> dict[str, str]:
    """Parse `nmcli -t -f ... connection show <uuid>` into a property map.

    nmcli prints one `property:value` line per requested property the profile
    has, and no line for a setting the profile lacks (a bridge port has no
    ipv4 setting, for example).
    """
    fields = {}
    for line in stdout.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            raise AnsibleFilterError(f"Unexpected nmcli output for profile {uuid}")
        fields[key] = value
    return fields


def nm_loopback_dns_profiles(results: list[dict[str, Any]]) -> dict[str, list]:
    """Find profiles whose static DNS only points at a local relay.

    Each result holds `item` (the profile UUID) and the `stdout` of
    `nmcli -e no -t -f ipv4.dns,ipv6.dns,ipv4.method,ipv6.method,connection.id
    connection show <uuid>`. A family whose servers are all loopback addresses
    is reset only when its method gets DNS automatically; with a static method
    it is listed under `static` and left alone. Profiles that mix loopback and
    other servers are listed under `mixed`. A family the profile lacks is
    ignored.
    """
    reset = []
    mixed = []
    static = []
    for result in results:
        uuid = result["item"]
        fields = _keyed_fields(uuid, result["stdout"])
        name = fields.get("connection.id") or uuid
        settings = []
        for family in DNS_FAMILIES:
            entries = [
                entry
                for entry in fields.get(f"{family}.dns", "").split(",")
                if entry.strip()
            ]
            if not entries:
                continue
            verdicts = {_is_loopback_server(entry) for entry in entries}
            method = fields.get(f"{family}.method", "")
            if verdicts == {True} and method in AUTO_DNS_METHODS[family]:
                settings += [f"{family}.dns", "", f"{family}.ignore-auto-dns", "no"]
            elif verdicts == {True}:
                static.append(
                    {"uuid": uuid, "name": name, "family": family, "method": method}
                )
            elif True in verdicts:
                mixed.append({"uuid": uuid, "name": name})
        if settings:
            reset.append({"uuid": uuid, "name": name, "settings": settings})
    return {"reset": reset, "mixed": mixed, "static": static}


def dnsmasq_upstream_servers(contents: list[str]) -> list[str]:
    """Return the `server=` values of dnsmasq configuration texts, in order."""
    servers = []
    for content in contents:
        for line in content.splitlines():
            key, separator, value = line.strip().partition("=")
            if separator and key.strip() == "server" and value.strip():
                servers.append(value.strip())
    return list(dict.fromkeys(servers))


# Keys that only choose how NetworkManager handles DNS and resolv.conf. A file
# that sets nothing else contradicts dns=systemd-resolved and can go.
NM_DNS_MODE_KEYS = frozenset({"dns", "rc-manager"})


def nm_dns_mode_only(content: str) -> bool:
    """Tell whether a NetworkManager conf.d file only sets [main] dns/rc-manager."""
    section = None
    keys = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        key, separator, _ = line.partition("=")
        if not separator or section != "main":
            return False
        keys.add(key.strip())
    return bool(keys) and keys <= NM_DNS_MODE_KEYS


def nm_legacy_dns_files(results: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Split slurped legacy conf.d files into those to remove and those to keep.

    Each result is a `slurp` result whose `item` is the `stat` result of the
    file. Files that set only the DNS mode go under `remove`.
    """
    split: dict[str, list[str]] = {"remove": [], "keep": []}
    for result in results:
        content = base64.b64decode(result["content"]).decode("utf-8", "replace")
        target = "remove" if nm_dns_mode_only(content) else "keep"
        split[target].append(result["item"]["stat"]["path"])
    return split


# Header lines of the writers whose resolv.conf the stub link replaces. The two
# resolved headers also mark a copy restored by a program that saved the file
# while resolved managed it; the uplink one lists real upstream servers.
RESOLVED_HEADER = "# This is {} managed by man:systemd-resolved(8)."
RESOLV_CONF_WRITERS = (
    ("# Generated by resolvconf", "openresolv"),
    ("# Generated by NetworkManager", "NetworkManager"),
    (
        RESOLVED_HEADER.format("/run/systemd/resolve/stub-resolv.conf"),
        "a copy of the systemd-resolved stub file",
    ),
    (
        RESOLVED_HEADER.format("/run/systemd/resolve/resolv.conf"),
        "a copy of the systemd-resolved uplink file",
    ),
)


def resolv_conf_origin(content: str) -> dict[str, Any]:
    """Classify a regular resolv.conf before it is replaced by the stub link.

    `managed` is true for a file with an openresolv, NetworkManager or
    systemd-resolved header, and for a file whose name servers are all
    loopback addresses (the former relay on 127.0.0.1 or ::1, or a stub copy
    on 127.0.0.53). Any other file belongs to another program, such as a VPN
    client; `origin` then quotes its first comment line.
    """
    lines = [line.strip() for line in content.splitlines()]
    for header, writer in RESOLV_CONF_WRITERS:
        if any(line.startswith(header) for line in lines):
            return {"managed": True, "origin": writer}
    servers = [
        line.split()[1]
        for line in lines
        if line.startswith("nameserver") and len(line.split()) > 1
    ]
    if servers and all(_is_loopback_server(server) for server in servers):
        return {"managed": True, "origin": "loopback name servers"}
    comments = [
        line.lstrip("#; ").strip() for line in lines if line.startswith(("#", ";"))
    ]
    origin = next((comment for comment in comments if comment), "unknown writer")
    return {"managed": False, "origin": origin}


# Process name of systemd-resolved as ss reports it (comm is cut at 15 chars).
RESOLVED_PROCESS = "systemd-resolve"
WILDCARD_ADDRESSES = frozenset({"0.0.0.0", "*", "::"})
# DNSStubListenerExtra without a udp: or tcp: prefix listens on both.
STUB_PROTOCOLS = ("udp", "tcp")


def _port_listeners(sockets: str) -> list[dict[str, Any]]:
    """Parse `ss -Hlntup 'sport = :53'` into protocol, address, host and owners.

    `process` is the first command name in the users column and `pids` every
    pid there, both empty when ss shows no process details.
    """
    listeners = []
    for line in sockets.splitlines():
        columns = line.split()
        if len(columns) < 5:
            continue
        users = columns[6] if len(columns) > 6 else ""
        process = None
        if '(("' in users:
            process = users.split('(("', 1)[1].split('"', 1)[0]
        listeners.append(
            {
                "protocol": columns[0],
                "address": columns[4],
                "host": columns[4].rpartition(":")[0].split("%", 1)[0].strip("[]"),
                "process": process,
                "pids": set(re.findall(r"pid=(\d+)", users)),
            }
        )
    return listeners


def dns_port_conflicts(
    sockets: str, bridge_address: str, ignored_pids: list[Any] | None = None
) -> list[str]:
    """List the port 53 listeners that keep resolved off the Docker bridge.

    `sockets` is the output of `ss -Hlntup 'sport = :53'`. A listener conflicts
    when it holds the bridge address or a wildcard address and is neither
    systemd-resolved nor owned by a pid in `ignored_pids` (the relay dnsmasq,
    which the role stops). Pids, not process names, single out the relay: any
    other dnsmasq on a wildcard address still conflicts. A bridge listener
    without process details is taken to be resolved from an earlier run.
    """
    ignored = {str(pid) for pid in ignored_pids or [] if str(pid) not in ("", "0")}
    conflicts = []
    for listener in _port_listeners(sockets):
        process = listener["process"]
        if process == RESOLVED_PROCESS or listener["pids"] & ignored:
            continue
        host = listener["host"]
        if host in WILDCARD_ADDRESSES or (host == bridge_address and process):
            conflicts.append(
                f"{listener['protocol']} {listener['address']} "
                f"({process or 'unknown process'})"
            )
    return conflicts


def dns_bridge_listener_missing(sockets: str, bridge_address: str) -> list[str]:
    """Return the protocols on which resolved does not listen on the bridge.

    `sockets` is the output of `ss -Hlntup 'sport = :53'` taken once resolved
    has restarted. resolved only logs a DNSStubListenerExtra it cannot bind,
    so this is the check that containers will get answers. A bridge listener
    without process details counts as resolved, as in dns_port_conflicts.
    """
    bound = {
        listener["protocol"]
        for listener in _port_listeners(sockets)
        if listener["host"] == bridge_address
        and listener["process"] in (RESOLVED_PROCESS, None)
    }
    return [protocol for protocol in STUB_PROTOCOLS if protocol not in bound]


def _split_terse(line: str) -> list[str]:
    """Split a line of `nmcli -t` output on unescaped ':' and unescape fields."""
    fields = [""]
    escaped = False
    for character in line:
        if escaped:
            fields[-1] += character
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ":":
            fields.append("")
        else:
            fields[-1] += character
    return fields


def nm_reapply_targets(active: str, reset: list[dict[str, Any]]) -> dict[str, list]:
    """Pick the devices whose active profile was reset and can be reapplied.

    `active` is the `stdout` of
    `nmcli -t -f UUID,TYPE,DEVICE connection show --active`. Profiles of a
    type listed in NO_REAPPLY_TYPES are returned by name under `reconnect`.
    """
    names = {profile["uuid"]: profile["name"] for profile in reset}
    devices = []
    reconnect = []
    for line in active.splitlines():
        if not line:
            continue
        fields = _split_terse(line)
        if len(fields) != 3:
            raise AnsibleFilterError(f"Unexpected nmcli active connection: {line}")
        uuid, connection_type, device = fields
        if uuid not in names:
            continue
        if connection_type in NO_REAPPLY_TYPES:
            reconnect.append(names[uuid])
        elif device:
            devices.append(device)
    return {"devices": devices, "reconnect": reconnect}


def docker_bridge_address(bridge_ip: str) -> str:
    """Return the host address of a Docker `bip` value such as 10.184.1.1/28."""
    try:
        interface = ipaddress.IPv4Interface(bridge_ip)
    except ValueError as error:
        raise AnsibleFilterError(
            f"Invalid Docker bridge address: {bridge_ip}"
        ) from error
    network = interface.network
    if network.prefixlen < 31 and interface.ip in (
        network.network_address,
        network.broadcast_address,
    ):
        raise AnsibleFilterError(
            f"Docker bridge address {bridge_ip} must be a host address, not "
            "the network or broadcast address"
        )
    return str(interface.ip)


def _require_fixed_cidr_in_bridge(config: dict[str, Any], bridge_ip: str) -> None:
    """Fail when an existing fixed-cidr falls outside the new bridge network.

    Docker refuses to start when fixed-cidr is not inside the `bip` network,
    and dropping the key would discard a deliberate setting.
    """
    fixed_cidr = config.get("fixed-cidr")
    if fixed_cidr is None:
        return
    bridge_network = ipaddress.IPv4Interface(bridge_ip).network
    try:
        container_range = ipaddress.IPv4Network(fixed_cidr, strict=False)
    except (TypeError, ValueError) as error:
        raise AnsibleFilterError(
            f"Invalid fixed-cidr in the Docker daemon configuration: {fixed_cidr}"
        ) from error
    if not container_range.subnet_of(bridge_network):
        raise AnsibleFilterError(
            f"fixed-cidr {fixed_cidr} in the Docker daemon configuration is "
            f"outside the bridge network {bridge_network} of "
            "system_docker_bridge_ip, and Docker would not start. Change "
            "fixed-cidr or system_docker_bridge_ip."
        )


def docker_daemon_dns(config: Any, bridge_ip: str) -> dict[str, Any]:
    """Pin docker0 and point containers at the resolved listener on it."""
    if not isinstance(config, dict):
        raise AnsibleFilterError(
            "The Docker daemon configuration must be a JSON object"
        )
    listener = docker_bridge_address(bridge_ip)
    _require_fixed_cidr_in_bridge(config, bridge_ip)
    # Only top-level keys change, so a shallow copy is enough. deepcopy would
    # also copy the templar behind Ansible's lazy containers, and rebuilding
    # its plugin loaders raises a PluginLoader aliases deprecation warning.
    merged = dict(config)
    merged["bip"] = bridge_ip
    merged["dns"] = [listener]
    return merged


class FilterModule:
    def filters(self) -> dict[str, Any]:
        return {
            "nm_loopback_dns_profiles": nm_loopback_dns_profiles,
            "nm_reapply_targets": nm_reapply_targets,
            "dnsmasq_upstream_servers": dnsmasq_upstream_servers,
            "nm_legacy_dns_files": nm_legacy_dns_files,
            "resolv_conf_origin": resolv_conf_origin,
            "dns_port_conflicts": dns_port_conflicts,
            "dns_bridge_listener_missing": dns_bridge_listener_missing,
            "docker_bridge_address": docker_bridge_address,
            "docker_daemon_dns": docker_daemon_dns,
        }

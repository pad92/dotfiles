"""Derive the systemd-resolved migration from NetworkManager and Docker state."""

import ipaddress
from copy import deepcopy
from typing import Any

from ansible.errors import AnsibleFilterError

DNS_FAMILIES = ("ipv4", "ipv6")


def _is_loopback_server(server: str) -> bool | None:
    """Return None for entries that cannot be parsed, so they are never rewritten."""
    address = server.split("#", 1)[0].strip()
    if address.startswith("[") and "]" in address:
        address = address[1 : address.index("]")]
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return None


def nm_loopback_dns_profiles(results: list[dict[str, Any]]) -> dict[str, list]:
    """Find profiles whose static DNS only points at a local relay.

    Each result holds `item` (the profile UUID) and the `stdout` of
    `nmcli -g ipv4.dns,ipv6.dns,connection.id connection show <uuid>`.
    A family is reset only when every server in it is a loopback address;
    profiles that mix loopback and other servers are reported, not changed.
    """
    reset = []
    mixed = []
    for result in results:
        lines = result["stdout"].split("\n", 2)
        if len(lines) != 3:
            raise AnsibleFilterError(
                f"Unexpected nmcli output for profile {result['item']}"
            )
        name = lines[2]
        settings = []
        for family, servers in zip(DNS_FAMILIES, lines[:2]):
            entries = [entry for entry in servers.split(",") if entry.strip()]
            if not entries:
                continue
            verdicts = {_is_loopback_server(entry) for entry in entries}
            if verdicts == {True}:
                settings += [f"{family}.dns", "", f"{family}.ignore-auto-dns", "no"]
            elif True in verdicts:
                mixed.append({"uuid": result["item"], "name": name})
        if settings:
            reset.append({"uuid": result["item"], "name": name, "settings": settings})
    return {"reset": reset, "mixed": mixed}


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


def docker_daemon_dns(config: Any, bridge_ip: str) -> dict[str, Any]:
    """Pin docker0 and point containers at the resolved listener on it."""
    if not isinstance(config, dict):
        raise AnsibleFilterError(
            "The Docker daemon configuration must be a JSON object"
        )
    merged = deepcopy(config)
    merged["bip"] = bridge_ip
    merged["dns"] = [docker_bridge_address(bridge_ip)]
    return merged


class FilterModule:
    def filters(self) -> dict[str, Any]:
        return {
            "nm_loopback_dns_profiles": nm_loopback_dns_profiles,
            "docker_bridge_address": docker_bridge_address,
            "docker_daemon_dns": docker_daemon_dns,
        }

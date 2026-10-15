"""Filters shared by the local dotfiles playbook."""

from __future__ import annotations

import fnmatch
import json
import re
from typing import Any


PACKAGE_NAME = re.compile(r"^[a-zA-Z0-9@._+-]+$")
GRAPHICS_GROUPS = {
    "07_intel_legacy",
    "08_amd",
    "08_intel_modern",
    "09_nvidia_legacy",
    "09_nvidia_modern",
}
PROTECTED_PACKAGES = {
    "base",
    "base-devel",
    "bash",
    "filesystem",
    "git",
    "glibc",
    "grub",
    "networkmanager",
    "pacman",
    "python",
    "sudo",
    "systemd",
    "linux",
}


def valid_package_name(value: Any) -> bool:
    return isinstance(value, str) and PACKAGE_NAME.fullmatch(value) is not None


def select_package_groups(
    explicit: Any, hostname: Any, host_groups: Any, defaults: Any
) -> Any:
    """Choose an explicit override, hostname mapping, or automatic defaults."""
    if explicit is not None:
        selected = explicit
    elif isinstance(hostname, str) and isinstance(host_groups, dict):
        selected = host_groups.get(hostname, defaults)
    else:
        selected = defaults
    return selected


def parse_package_state(value: Any) -> dict[str, Any] | None:
    """Return validated v1 state, or None when the saved file is invalid."""
    if not isinstance(value, dict) or value.get("version") != 1:
        return None

    result: dict[str, Any] = {"version": 1}
    for key in ("selected_groups", "owned_packages"):
        entries = value.get(key)
        if not isinstance(entries, list) or not all(
            valid_package_name(entry) for entry in entries
        ):
            return None
        result[key] = sorted(set(entries))
    return result


def parse_package_state_json(value: Any) -> dict[str, Any] | None:
    """Decode and validate serialized package state without raising on bad data."""
    if not isinstance(value, str):
        return None
    try:
        return parse_package_state(json.loads(value))
    except (json.JSONDecodeError, TypeError):
        return None


def detect_graphics_groups(pci_devices: Any) -> list[str]:
    """Classify PCI display controllers; incomplete detection returns no defaults."""
    if not isinstance(pci_devices, str) or not pci_devices.strip():
        return []

    detected: set[str] = set()
    saw_controller = False
    incomplete = False
    for line in pci_devices.splitlines():
        if not re.search(r"\[(0300|0302)\]", line):
            continue
        saw_controller = True
        normalized = line.lower()
        if "[1002:" in normalized:
            detected.add("08_amd")
        elif "[8086:" in normalized:
            if any(
                token in normalized
                for token in (
                    "gma",
                    "ironlake",
                    "sandy bridge",
                    "ivy bridge",
                    "haswell",
                    "2nd gen core",
                    "3rd gen core",
                    "4th gen core",
                    "hd graphics 2000",
                    "hd graphics 2500",
                    "hd graphics 3000",
                    "hd graphics 4000",
                    "hd graphics 4200",
                    "hd graphics 4400",
                    "hd graphics 4600",
                    "hd graphics 5000",
                    "hd graphics 5100",
                )
            ):
                detected.add("07_intel_legacy")
            elif any(
                token in normalized
                for token in (
                    "broadwell",
                    "skylake",
                    "kabylake",
                    "coffeelake",
                    "cometlake",
                    "icelake",
                    "tigerlake",
                    "rocketlake",
                    "alderlake",
                    "raptorlake",
                    "meteorlake",
                    "lunarlake",
                    "arrowlake",
                    "iris xe",
                    "uhd graphics",
                    "arc ",
                )
            ):
                detected.add("08_intel_modern")
            else:
                incomplete = True
        elif "[10de:" in normalized:
            if any(
                token in normalized
                for token in (
                    "maxwell",
                    "pascal",
                    "volta",
                    "geforce gtx 745",
                    "geforce gtx 750",
                    "geforce gtx 8",
                    "geforce gtx 9",
                    "geforce gtx 10",
                    "quadro m",
                    "quadro p",
                    "tesla m",
                    "tesla p",
                    "tesla v",
                    "titan v",
                    "titan x",
                )
            ) or any(
                fnmatch.fnmatch(normalized, pattern)
                for pattern in ("* gm[0-9]*", "* gp[0-9]*", "* gv[0-9]*")
            ):
                detected.add("09_nvidia_legacy")
            elif any(
                token in normalized
                for token in (
                    "turing",
                    "tu1",
                    "tu2",
                    "ampere",
                    "ada",
                    "blackwell",
                    "geforce rtx 20",
                    "geforce rtx 30",
                    "geforce rtx 40",
                    "geforce rtx 50",
                    "quadro rtx",
                    "rtx a",
                    "nvidia a",
                    "nvidia h",
                    "nvidia l",
                    "tesla t4",
                )
            ):
                detected.add("09_nvidia_modern")
            else:
                incomplete = True
        else:
            incomplete = True

    if incomplete or not saw_controller or not detected:
        return []
    return sorted(detected)


def detect_sysfs_graphics_groups(devices: Any) -> list[str]:
    """Use the old no-lspci fallback, which can identify AMD GPUs only."""
    if not isinstance(devices, (list, tuple)) or not devices:
        return []
    controllers = [
        device
        for device in devices
        if isinstance(device, dict)
        and isinstance(device.get("class"), str)
        and device["class"].strip().lower().startswith(("0x0300", "0x0302"))
    ]
    if not controllers:
        return []
    if all(
        isinstance(device.get("vendor"), str)
        and device["vendor"].strip().lower() == "0x1002"
        for device in controllers
    ):
        return ["08_amd"]
    return []


def protected_package(package: str) -> bool:
    return package in PROTECTED_PACKAGES or package.startswith("linux-")


def package_removal_candidates(
    installed: Any, desired: Any, owned: Any, protected: Any = None
) -> list[str]:
    """Return only installed, owned, undesired packages outside the protected set."""
    if not all(isinstance(packages, (list, set, tuple)) for packages in (installed, desired, owned)):
        return []
    installed_set = set(installed)
    desired_set = set(desired)
    owned_set = set(owned)
    protected_set = set(PROTECTED_PACKAGES)
    if isinstance(protected, (list, set, tuple)):
        protected_set.update(protected)
    return sorted(
        package
        for package in installed_set & owned_set - desired_set
        if valid_package_name(package)
        and package not in protected_set
        and not package.startswith("linux-")
    )


def safe_removal_preview(
    preview: Any, desired: Any, protected: Any = None
) -> bool:
    """Accept only a valid pacman transaction that includes every candidate."""
    if not isinstance(preview, (list, tuple, set)) or not preview:
        return False
    if not isinstance(desired, (list, tuple, set)):
        return False
    protected_set = set(PROTECTED_PACKAGES)
    if isinstance(protected, (list, set, tuple)):
        protected_set.update(protected)
    values = set(preview)
    return all(valid_package_name(item) for item in values) and not (
        values & set(desired)
        or values & protected_set
        or any(item.startswith("linux-") for item in values)
    )


def unneeded_graphics_packages(
    package_groups: Any,
    selected_groups: Any,
    installed: Any,
    desired: Any,
) -> list[str]:
    """Find installed packages in deselected graphics groups, excluding shared ones."""
    if not isinstance(package_groups, dict):
        return []
    selected = set(selected_groups) if isinstance(selected_groups, (list, set, tuple)) else set()
    installed_set = set(installed) if isinstance(installed, (list, set, tuple)) else set()
    desired_set = set(desired) if isinstance(desired, (list, set, tuple)) else set()
    packages: set[str] = set()
    for group in GRAPHICS_GROUPS - selected:
        values = package_groups.get(group, [])
        if isinstance(values, (list, set, tuple)):
            packages.update(
                package
                for package in values
                if valid_package_name(package)
                and package in installed_set
                and package not in desired_set
            )
    return sorted(packages)


class FilterModule:
    def filters(self) -> dict[str, Any]:
        return {
            "valid_package_name": valid_package_name,
            "select_package_groups": select_package_groups,
            "parse_package_state": parse_package_state,
            "parse_package_state_json": parse_package_state_json,
            "detect_graphics_groups": detect_graphics_groups,
            "detect_sysfs_graphics_groups": detect_sysfs_graphics_groups,
            "protected_package": protected_package,
            "package_removal_candidates": package_removal_candidates,
            "safe_removal_preview": safe_removal_preview,
            "unneeded_graphics_packages": unneeded_graphics_packages,
        }

"""Filters shared by the local dotfiles playbook."""

from __future__ import annotations

import fnmatch
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

PACKAGE_NAME = re.compile(r"^[a-zA-Z0-9@._+-]+$")
GRAPHICS_GROUPS = {
    "07_intel_legacy",
    "08_amd",
    "08_intel_modern",
    "09_nvidia_legacy",
    "09_nvidia_modern",
}
USB_VENDOR_ID = re.compile(r"^[0-9a-f]{4}$")
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
    explicit: Any,
    host_groups: Any,
    defaults: Any,
    detected_graphics_groups: Any = None,
) -> Any:
    """Choose package groups and prefer complete automatic graphics detection.

    An explicit one-run selection wins unchanged. Otherwise the host's own list
    applies, then the OS defaults. Detected graphics groups replace the
    graphics groups of either list.
    """
    if explicit is not None:
        selected = explicit
    elif host_groups is not None:
        selected = host_groups
    else:
        selected = defaults

    if (
        explicit is None
        and isinstance(selected, (list, tuple, set))
        and isinstance(detected_graphics_groups, (list, tuple, set))
        and detected_graphics_groups
    ):
        selected = [group for group in selected if group not in GRAPHICS_GROUPS]
        selected += list(detected_graphics_groups)
    return selected


def usb_vendor_present(vendor_ids: Any, vendor_id: Any) -> bool | None:
    """Whether a USB device of vendor_id is connected, or None when unknown.

    vendor_ids holds the idVendor values read from /sys/bus/usb/devices, one
    per line. The USB root hubs are always listed, so an empty listing means
    sysfs was not read: like an unreadable value or a malformed vendor_id, it
    gives None rather than False.
    """
    if not isinstance(vendor_ids, str) or not isinstance(vendor_id, str):
        return None
    wanted = vendor_id.strip().lower()
    found = [line.strip().lower() for line in vendor_ids.splitlines() if line.strip()]
    if not USB_VENDOR_ID.fullmatch(wanted) or not found:
        return None
    if any(not USB_VENDOR_ID.fullmatch(value) for value in found):
        return None
    return wanted in found


def add_detected_group(
    selected: Any,
    explicit: Any,
    present: Any,
    required_group: Any,
    group: Any,
    recorded: Any = None,
) -> Any:
    """Add a hardware group to a selection that holds required_group.

    The group is added when its device is present, or when the saved package
    state already records it: a device unplugged during one run, or unknown,
    must not make a later reconcile remove what the host uses. An explicit
    one-run selection stays unchanged.
    """
    if (
        explicit is not None
        or not isinstance(selected, list)
        or not isinstance(required_group, str)
        or not isinstance(group, str)
        or required_group not in selected
        or group in selected
    ):
        return selected
    if present is True or (isinstance(recorded, list) and group in recorded):
        return [*selected, group]
    return selected


def dkms_kernel_headers(desired: Any, kernel_package: Any) -> list[str]:
    """Return the running kernel's headers package when a DKMS package is wanted.

    DKMS builds modules only for kernels whose headers are installed, so a
    selected ``*-dkms`` package needs ``<kernel package>-headers``. An unknown
    or invalid kernel package yields nothing rather than a guessed name.
    """
    if not isinstance(desired, (list, tuple, set)) or not valid_package_name(
        kernel_package
    ):
        return []
    if not any(isinstance(name, str) and name.endswith("-dkms") for name in desired):
        return []
    return [f"{kernel_package}-headers"]


def recorded_package_groups(current: Any, previous_state: Any, merge: Any) -> list[str]:
    """Return the group list to save in the package state.

    A full run records its own selection. A partial profile (``merge`` true,
    such as ansible/obs.yml) adds its groups to the saved ones instead of
    replacing the workstation selection with its narrower list.
    """
    groups = {group for group in current or [] if isinstance(group, str)}
    if merge is True and isinstance(previous_state, dict):
        previous = previous_state.get("selected_groups")
        if isinstance(previous, list):
            groups.update(group for group in previous if isinstance(group, str))
    return sorted(groups)


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


def graphics_controllers_found(pci_devices: Any) -> bool:
    """Report whether PCI data includes a display controller, even if unknown."""
    if isinstance(pci_devices, str):
        return any(
            re.search(r"\[(0300|0302)\]", line) for line in pci_devices.splitlines()
        )
    if isinstance(pci_devices, (list, tuple)):
        return any(
            isinstance(device, dict)
            and isinstance(device.get("class"), str)
            and device["class"].strip().lower().startswith(("0x0300", "0x0302"))
            for device in pci_devices
        )
    return False


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
    if not all(
        isinstance(packages, (list, set, tuple))
        for packages in (installed, desired, owned)
    ):
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


def safe_removal_preview(preview: Any, desired: Any, protected: Any = None) -> bool:
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
    selected = (
        set(selected_groups)
        if isinstance(selected_groups, (list, set, tuple))
        else set()
    )
    installed_set = (
        set(installed) if isinstance(installed, (list, set, tuple)) else set()
    )
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


def changed_packages(before: Any, after: Any) -> list[str]:
    """List packages installed or whose version changed between two package_facts."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return []

    def signature(entries: Any) -> list[tuple[str, str, str]]:
        if not isinstance(entries, list):
            return []
        return sorted(
            (
                str(entry.get("version", "")),
                str(entry.get("release", "")),
                str(entry.get("arch", "")),
            )
            for entry in entries
            if isinstance(entry, dict)
        )

    return sorted(
        name
        for name, entries in after.items()
        if name not in before or signature(before[name]) != signature(entries)
    )


LUA_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
LUA_KEYWORDS = {
    "and",
    "break",
    "do",
    "else",
    "elseif",
    "end",
    "false",
    "for",
    "function",
    "goto",
    "if",
    "in",
    "local",
    "nil",
    "not",
    "or",
    "repeat",
    "return",
    "then",
    "true",
    "until",
    "while",
}


def _lua_string(value: str) -> str:
    escaped = []
    for character in value:
        if character in '"\\':
            escaped.append("\\" + character)
        elif character == "\n":
            escaped.append("\\n")
        elif ord(character) < 32 or ord(character) == 127:
            # Decimal escapes are valid in every Lua version.
            escaped.append(f"\\{ord(character):03d}")
        else:
            escaped.append(character)
    return '"' + "".join(escaped) + '"'


def to_lua(value: Any, indent: int = 2, level: int = 0) -> str:
    """Render YAML data as a Lua literal for a generated configuration module.

    Mappings become tables with named fields, sequences become arrays and
    strings are escaped, so values from inventories and the Vault cannot break
    out of the literal. Keys keep their order; other types are rejected.
    """
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("to_lua cannot render NaN or infinity")
        return repr(value)
    if isinstance(value, str):
        return _lua_string(value)
    padding = " " * (indent * (level + 1))
    closing = " " * (indent * level)
    if isinstance(value, Mapping):
        if not value:
            return "{}"
        fields = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"to_lua needs string keys, got {key!r}")
            if LUA_IDENTIFIER.fullmatch(key) and key not in LUA_KEYWORDS:
                name = key
            else:
                name = f"[{_lua_string(key)}]"
            fields.append(f"{padding}{name} = {to_lua(item, indent, level + 1)},")
        return "{\n" + "\n".join(fields) + f"\n{closing}}}"
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        if not value:
            return "{}"
        items = [f"{padding}{to_lua(item, indent, level + 1)}," for item in value]
        return "{\n" + "\n".join(items) + f"\n{closing}}}"
    raise TypeError(f"to_lua cannot render {type(value).__name__}")


class FilterModule:
    def filters(self) -> dict[str, Any]:
        return {
            "valid_package_name": valid_package_name,
            "select_package_groups": select_package_groups,
            "usb_vendor_present": usb_vendor_present,
            "add_detected_group": add_detected_group,
            "dkms_kernel_headers": dkms_kernel_headers,
            "recorded_package_groups": recorded_package_groups,
            "parse_package_state": parse_package_state,
            "parse_package_state_json": parse_package_state_json,
            "detect_graphics_groups": detect_graphics_groups,
            "graphics_controllers_found": graphics_controllers_found,
            "detect_sysfs_graphics_groups": detect_sysfs_graphics_groups,
            "protected_package": protected_package,
            "package_removal_candidates": package_removal_candidates,
            "safe_removal_preview": safe_removal_preview,
            "unneeded_graphics_packages": unneeded_graphics_packages,
            "changed_packages": changed_packages,
            "dotfiles_to_lua": to_lua,
        }

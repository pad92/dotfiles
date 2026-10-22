"""Build LACT profiles from daemon discovery, retaining existing user settings."""

import re
from copy import deepcopy
from typing import Any

from ansible.errors import AnsibleFilterError


def lact_gpu_ids(output: str) -> list[str]:
    """Read canonical IDs from `lact cli list`, without reconstructing PCI IDs."""
    ids = []
    for line in output.splitlines():
        if not line.strip():
            continue
        match = re.match(r"^\d+: (\S+) \(", line)
        if not match:
            raise AnsibleFilterError(f"Unrecognized LACT GPU listing: {line}")
        ids.append(match.group(1))
    if len({gpu.casefold() for gpu in ids}) != len(ids):
        raise AnsibleFilterError("LACT reported ambiguous GPU identifiers")
    return ids


def lact_config(
    existing: Any,
    gpu_ids: list[str],
    amd_gpu_ids: list[str],
    profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Repair identifier casing; never transfer settings to a different GPU."""
    if not isinstance(existing, dict):
        raise AnsibleFilterError("The existing LACT configuration must be a mapping")
    if not isinstance(profiles, dict):
        raise AnsibleFilterError("Default LACT profiles must be a mapping")
    if not amd_gpu_ids or not set(amd_gpu_ids).issubset(gpu_ids):
        raise AnsibleFilterError("No validated AMD GPU selection for LACT")
    canonical = {gpu.casefold(): gpu for gpu in gpu_ids}
    if len(canonical) != len(gpu_ids):
        raise AnsibleFilterError("LACT reported ambiguous GPU identifiers")

    config = deepcopy(existing)
    config.setdefault("version", 7)
    if config["version"] != 7:
        raise AnsibleFilterError("Unsupported LACT configuration version; expected 7")
    stored_profiles = config.setdefault("profiles", {})
    if not isinstance(stored_profiles, dict):
        raise AnsibleFilterError("LACT profiles must be a mapping")

    def remap(container: dict[str, Any]) -> None:
        settings = container.get("gpus", {})
        if not isinstance(settings, dict):
            raise AnsibleFilterError("LACT GPU settings must be a mapping")
        mapped = {}
        for gpu, values in settings.items():
            if not isinstance(gpu, str) or not isinstance(values, dict):
                raise AnsibleFilterError("Invalid LACT GPU configuration")
            if gpu.casefold() not in canonical:
                raise AnsibleFilterError(
                    f"GPU {gpu} is not detected. Review its settings before migration; "
                    "they will not be assigned to another GPU automatically."
                )
            target = canonical[gpu.casefold()]
            if target in mapped:
                raise AnsibleFilterError(f"Conflicting LACT entries for GPU {target}")
            mapped[target] = values
        if "gpus" in container:
            container["gpus"] = mapped

    remap(config)
    for profile in stored_profiles.values():
        if not isinstance(profile, dict):
            raise AnsibleFilterError("Each LACT profile must be a mapping")
        remap(profile)
    for name, settings in profiles.items():
        if not isinstance(name, str) or not isinstance(settings, dict):
            raise AnsibleFilterError("Invalid default LACT profile")
        # Existing profiles, fan curves, automation and profile selection win.
        stored_profiles.setdefault(
            name, {"gpus": {gpu: deepcopy(settings) for gpu in amd_gpu_ids}}
        )
    if not existing:
        config["current_profile"] = (
            "Balance"
            if "Balance" in stored_profiles
            else next(iter(stored_profiles), None)
        )
        config["auto_switch_profiles"] = False
    selected = config.get("current_profile")
    if selected is not None and selected not in stored_profiles:
        raise AnsibleFilterError("The selected LACT profile does not exist")
    return config


class FilterModule:
    def filters(self) -> dict[str, Any]:
        return {"lact_gpu_ids": lact_gpu_ids, "lact_config": lact_config}

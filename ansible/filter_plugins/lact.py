"""Build LACT profiles from daemon discovery, retaining existing user settings."""

import re
from copy import deepcopy
from typing import Any

from ansible.errors import AnsibleFilterError

LEGACY_PROFILE_NAMES = {
    "Balance": "Auto",
    "Silence": "Adaptive",
    "Performance": "PreferMaximumPerformance",
    "Jeux-perf": "PreferMaximumPerformance",
}


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
    nvidia_gpu_ids: list[str] | None = None,
    nvidia_profiles: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Repair GPU ID casing and add defaults for supported AMD and NVIDIA GPUs."""
    nvidia_gpu_ids = [] if nvidia_gpu_ids is None else nvidia_gpu_ids
    nvidia_profiles = {} if nvidia_profiles is None else nvidia_profiles
    profile_sources = (
        ("AMD", amd_gpu_ids, profiles),
        ("NVIDIA", nvidia_gpu_ids, nvidia_profiles),
    )
    if not isinstance(existing, dict):
        raise AnsibleFilterError("The existing LACT configuration must be a mapping")
    for vendor, device_ids, defaults in profile_sources:
        if not isinstance(device_ids, list):
            raise AnsibleFilterError(f"{vendor} LACT GPU identifiers must be a list")
        if not isinstance(defaults, dict):
            raise AnsibleFilterError(
                f"Default {vendor} LACT profiles must be a mapping"
            )
    supported_gpu_ids = [
        gpu for _, device_ids, _ in profile_sources for gpu in device_ids
    ]
    if not supported_gpu_ids:
        raise AnsibleFilterError("No validated AMD or NVIDIA GPU selection for LACT")
    if not set(supported_gpu_ids).issubset(gpu_ids):
        raise AnsibleFilterError("LACT profile GPU selection contains an unknown GPU")
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
    had_profiles = bool(stored_profiles)

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
    for old_name, new_name in LEGACY_PROFILE_NAMES.items():
        if old_name in stored_profiles:
            old_profile = stored_profiles.pop(old_name)
            stored_profiles.setdefault(new_name, old_profile)
            if config.get("current_profile") == old_name:
                config["current_profile"] = new_name
    profile_names = dict.fromkeys(
        name for _, _, defaults in profile_sources for name in defaults
    )
    for name in profile_names:
        if not isinstance(name, str):
            raise AnsibleFilterError("Invalid default LACT profile name")
        profile_gpus = {}
        for vendor, device_ids, defaults in profile_sources:
            if name not in defaults:
                continue
            settings = defaults[name]
            if not isinstance(settings, dict):
                raise AnsibleFilterError(f"Invalid default {vendor} LACT profile")
            profile_gpus.update({gpu: deepcopy(settings) for gpu in device_ids})
        if not profile_gpus:
            continue
        profile = stored_profiles.setdefault(name, {"gpus": {}})
        existing_gpu_settings = profile.setdefault("gpus", {})
        if not isinstance(existing_gpu_settings, dict):
            raise AnsibleFilterError("LACT GPU settings must be a mapping")
        # Keep saved per-GPU settings and add defaults for newly detected GPUs.
        for gpu, settings in profile_gpus.items():
            existing_gpu_settings.setdefault(gpu, settings)
    if not had_profiles and config.get("current_profile") is None:
        config["current_profile"] = (
            "Auto" if "Auto" in stored_profiles else next(iter(stored_profiles), None)
        )
        config["auto_switch_profiles"] = False
    selected = config.get("current_profile")
    if selected is not None and selected not in stored_profiles:
        raise AnsibleFilterError("The selected LACT profile does not exist")
    return config


class FilterModule:
    def filters(self) -> dict[str, Any]:
        return {"lact_gpu_ids": lact_gpu_ids, "lact_config": lact_config}

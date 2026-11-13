# gpu

Configures the NVIDIA and i915 kernel modules, the runtime power management of
a hybrid laptop's NVIDIA GPU, and regenerates the initramfs when the module
options change.

## Requirements

- Arch Linux. The NVIDIA settings need an NVIDIA package profile, and the
  i915 option the modern Intel profile, both selected by the `packages` role.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                     | Default         | Description                                                                                           |
| :--------------------------- | :-------------- | :---------------------------------------------------------------------------------------------------- |
| `gpu_initramfs_generator`    | `auto`          | `auto`, `mkinitcpio` or `dracut`. Set it when both or neither are installed.                          |
| `gpu_initramfs_report_roots` | `[/boot, /efi]` | Trees listed before and after generation to report the written images. Add custom output directories. |
| `gpu_i915_enable_guc`        | `null`          | i915 `enable_guc`: `-1` automatic, `0` off, `1` GuC submission, `2` HuC authentication, `3` both.     |
| `gpu_i915_guc_supported`     | `false`         | Required for the values `1` to `3`. Set it only once the GPU is known to support them.                |

## Kernel modules

With an NVIDIA profile, the role manages
`/etc/modprobe.d/zz-dotfiles-gpu.conf`. Both profiles enable zero-initialized
system memory and DRM modesetting. Runtime D3 uses the driver default:
supported Ampere and newer notebooks use fine-grained power management. GSP
firmware is enabled by default on supported GPUs, so the role does not set it.
Open kernel modules preserve video memory on their own; the role does not
force it on the legacy proprietary driver, which would need systemd
integration and enough temporary storage. Reboot after deployment to apply
the module options.

The i915 GuC option stays at the kernel default unless `gpu_i915_enable_guc`
is set. Support varies by platform; see the kernel's
[i915 documentation](https://docs.kernel.org/gpu/i915.html).

## Runtime power management

A udev rule is installed only when sysfs reports a host battery, an Intel or
AMD boot VGA GPU, a separate NVIDIA GPU, and the modern NVIDIA profile is
selected. The rule matches the bound driver and sets PCI `power/control` to
`auto`; it holds no device identifier. When it changes, the role reloads the
udev rules and replays a `bind` event for the PCI devices bound to `nvidia`,
so it applies without a reboot. Removing the rule leaves `power/control` at
`auto` until the next reboot.

Peripheral batteries marked `Device` do not count. If the battery or GPU
detection is incomplete, the existing rule is kept and the run asks for a new
attempt once the drivers load, so a first installation may need a second run
of the `gpu_modules` tasks after a reboot.

An active GPU workload or a monitoring client can keep the NVIDIA GPU awake.
After deployment and reboot, check idle runtime suspend, `prime-run`
offload, external displays and suspend/resume. See NVIDIA's
[runtime D3](https://download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/dynamicpowermanagement.html)
and
[power management](https://download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/powermanagement.html)
documentation.

## Initramfs

With an NVIDIA profile, the role detects `mkinitcpio` or `dracut` and
regenerates the initramfs after the module configuration changes. The
`dotfiles_initramfs` module reports the images written under
`gpu_initramfs_report_roots`. An unreadable path fails the task instead of
giving a partial report. Package hooks and other external writers are not
audited.

Tags: `gpu`, `gpu_modules`.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: gpu
      tags: [gpu]
```

## License

Unlicense

## Author Information

pad

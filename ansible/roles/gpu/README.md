# gpu

Configures the NVIDIA and i915 kernel modules and the runtime power management
of a hybrid laptop's NVIDIA GPU, then regenerates the initramfs when the module
options change.

## Requirements

- Arch Linux, with `packages_selected_groups` set by the group selection of the
  `packages` role (see [Pre-tasks](../../PLAYBOOKS.md#pre-tasks)). Every task
  is skipped otherwise.
- Exactly one of `mkinitcpio` and `dracut` installed, or
  `gpu_initramfs_generator` set to the one to use. This check runs on every
  such host, with or without an NVIDIA GPU.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                     | Default         | Description                                                                                       |
| :--------------------------- | :-------------- | :------------------------------------------------------------------------------------------------ |
| `gpu_initramfs_generator`    | `auto`          | `auto`, `mkinitcpio` or `dracut`. Set it when both or neither are installed.                      |
| `gpu_initramfs_report_roots` | `[/boot, /efi]` | Trees compared before and after generation to report the written images. Add custom output paths. |
| `gpu_i915_enable_guc`        | `null`          | i915 `enable_guc`: `-1` automatic, `0` off, `1` GuC submission, `2` HuC authentication, `3` both. |
| `gpu_i915_guc_supported`     | `false`         | Required for the values `1` to `3`. Set it only once the GPU is known to support them.            |

External variable:

- `packages_selected_groups`: `09_nvidia_legacy` or `09_nvidia_modern` enables
  the NVIDIA options, `09_nvidia_modern` the runtime power management, and
  `08_intel_modern` the i915 option.

## Kernel modules

With an NVIDIA group selected, the role writes `/etc/modprobe.d/nvidia.conf`:

```sh
options nvidia NVreg_InitializeSystemMemoryAllocations=1
options nvidia_drm modeset=1
```

Both NVIDIA groups get the same file: zero-initialized system memory and DRM
modesetting. The role leaves the following to the driver defaults:

- Runtime D3. Supported Ampere and newer notebooks use fine-grained power
  management.
- GSP firmware, which is enabled by default on supported GPUs.
- Video memory preservation. The open kernel modules handle it on their own.
  On the legacy proprietary driver it would need the systemd integration and
  enough temporary storage.

When `gpu_i915_enable_guc` is set and `08_intel_modern` is selected, the role
writes `options i915 enable_guc=<value>` to `/etc/modprobe.d/i915.conf`. A value
outside `-1` to `3`, a missing `08_intel_modern`, or a value from `1` to `3`
without `gpu_i915_guc_supported: true` fails the run. Support varies by
platform; see the kernel's [i915 documentation](https://docs.kernel.org/gpu/i915.html).

Each file is removed when its condition no longer holds. The role also removes
`zz-dotfiles-gpu.conf` and `zz-dotfiles-i915.conf`, written by earlier
versions. Reboot to apply the module options.

## Runtime power management

`files/detect-hybrid-laptop.sh` reads sysfs and prints `true`, `false` or
`unknown`:

- `true`: a host battery, a boot VGA GPU bound to `i915`, `xe` or `amdgpu`, and
  a GPU bound to `nvidia`.
- `false`: no host battery. Batteries with the `Device` scope, such as those of
  a mouse or headset, do not count.
- `unknown`: anything else, including a battery whose type or scope cannot be
  read, or a GPU whose driver is not bound yet.

On `true` with `09_nvidia_modern` selected, the role installs
`/etc/udev/rules.d/80-dotfiles-nvidia-runtime-pm.rules`. The rule matches the
bound `nvidia` driver rather than a PCI ID, and sets PCI `power/control` to
`auto`. The handlers then reload the udev rules and replay a `bind` event for
the PCI devices bound to `nvidia`, so the rule applies without a reboot.

On `false`, or when `09_nvidia_modern` is not selected, the rule is removed.
The devices keep `power/control=auto` until the next reboot. On `unknown`, the
rule is kept as it is and the run asks for a new attempt once the drivers
load. A first installation may therefore need a second run with `TAGS=gpu`
after a reboot.

An active GPU workload or a monitoring client can keep the NVIDIA GPU awake.
After deploying and rebooting, check idle runtime suspend, `prime-run` offload,
external displays and suspend and resume. See NVIDIA's
[runtime D3](https://download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/dynamicpowermanagement.html)
and
[power management](https://download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/powermanagement.html)
documentation.

## Initramfs

A change to `nvidia.conf` or `i915.conf`, including their removal, or the
removal of a legacy file, notifies the regeneration handler. The
`dotfiles_initramfs` module runs the selected generator and reports the images
written under `gpu_initramfs_report_roots`. An unreadable path fails the task
rather than give a partial report. Package hooks and other external writers
are not audited.

## Tags

`site.yml` tags the role `system` and `gpu`. See
[Running](../../README.md#running) for how to pass tags.

## Dependencies

None. In `site.yml` it runs after `packages`.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: gpu
      when: packages_action | default('install') != 'plan'
      tags: [system, gpu]
```

## License

Unlicense

## Author Information

pad

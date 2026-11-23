# obs

Configures OBS Studio for application demos from the host it runs on: encoder,
canvas, webcam, recording and streaming profiles, branded scene collections,
and a virtual camera for web meetings.

## Requirements

- Arch Linux or CachyOS with the `22_obs` group installed: OBS Studio, PipeWire
  Pulse, WirePlumber, the Hyprland portal backend, `qt6-wayland`,
  `v4l-utils`, `v4l2loopback-dkms`, `obs-backgroundremoval` (AUR), `simde` and
  `ttf-montserrat`. Every OBS 33 plugin needs `simde` to build, and the AUR
  recipe does not declare it.
- A Hyprland session to size the canvas. Without one the canvas falls back to
  1920x1080.
- Privilege escalation (`become: true`) for the virtual camera and the Firefox
  policy.

## Role Variables

| Variable                      | Default                                                                                                            | Description                                                                                         |
| :---------------------------- | :----------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------- |
| `obs_home`                    | `"{{ ansible_facts['user_dir'] }}"`                                                                                | Home directory of the OBS user.                                                                     |
| `obs_config_dir`              | `'{{ obs_home }}/.config/obs-studio'`                                                                              | OBS configuration.                                                                                  |
| `obs_profiles`                | `Enregistrement` (directory `Enregistrement`, usage `record`), `Streaming` (directory `Streaming`, usage `stream`) | Profiles created next to the existing ones, which stay untouched.                                   |
| `obs_scene_collection_name`   | `Applis`                                                                                                           | Collections are named `<name> - <palette>`.                                                         |
| `obs_scene_collection_file`   | `Applis`                                                                                                           | Collections are stored in `basic/scenes/<file>_<palette>.json`.                                     |
| `obs_config_force`            | `false`                                                                                                            | Regenerate the files from the current host, with backups.                                           |
| `obs_encoder`                 | `auto`                                                                                                             | `auto`, `nvenc`, `vaapi` or `x264`.                                                                 |
| `obs_capture_output`          | `''`                                                                                                               | Connector the canvas is sized from. Empty picks the largest external output.                        |
| `obs_output_height`           | `1080`                                                                                                             | Output height of the streaming profile.                                                             |
| `obs_webcam`                  | `''`                                                                                                               | Part of a `/dev/v4l/by-id` name. Empty prefers an external camera.                                  |
| `obs_webcam_background`       | `cutout`                                                                                                           | `cutout`, `blur` or `none`.                                                                         |
| `obs_webcam_blur`             | `6`                                                                                                                | Background blur, 1 to 20.                                                                           |
| `obs_webcam_model`            | `rvm`                                                                                                              | `rvm` (soft matting) or `mediapipe` (lighter, coarser).                                             |
| `obs_webcam_threshold`        | `0.65`                                                                                                             | MediaPipe only. Mask strictness.                                                                    |
| `obs_webcam_edge_trim`        | `2`                                                                                                                | MediaPipe only. Pixels trimmed off the outline, 0 to 30.                                            |
| `obs_mic_device`              | `default`                                                                                                          | Microphone source.                                                                                  |
| `obs_desktop_audio_device`    | `default`                                                                                                          | Desktop audio source.                                                                               |
| `obs_mic_noise_suppression`   | `true`                                                                                                             | RNNoise filter on the microphone. Disable it with an already filtered source such as `voice.clean`. |
| `obs_demo_title`              | `Démo`                                                                                                             | Title of the intro scene.                                                                           |
| `obs_pause_text`              | `Pause, on revient tout de suite`                                                                                  | Text of the pause card.                                                                             |
| `obs_brand_palettes`          | `Sombre`, `Clair`, `Gruvbox`                                                                                       | Text, background and primary colors per palette. See [Profiles and scenes](#profiles-and-scenes).   |
| `obs_brand_font`              | `Montserrat`                                                                                                       | Title font.                                                                                         |
| `obs_virtualcam_enabled`      | `true`                                                                                                             | Set up the v4l2loopback virtual camera.                                                             |
| `obs_virtualcam_label`        | `OBS Virtual Camera`                                                                                               | Device name shown to browsers.                                                                      |
| `obs_virtualcam_video_nr`     | `10`                                                                                                               | `/dev/video` number.                                                                                |
| `obs_virtualcam_firefox_v4l2` | `true`                                                                                                             | Firefox policy to read V4L2 cameras directly.                                                       |
| `obs_firefox_binary_path`     | `/usr/lib/firefox/firefox`                                                                                         | The policy is written only when this file exists.                                                   |
| `obs_firefox_policies_file`   | `/etc/firefox/policies/policies.json`                                                                              | Firefox policies file.                                                                              |

The role also reads the `user_dir` fact, which `site.yml` gathers as the SSH
user, and `packages_selected_groups` through `site.yml`.

## Host detection

The role reads the host before writing anything:

- Encoder: the GPU that renders the desktop (`boot_vga`) encodes. A hybrid
  laptop uses VAAPI on its iGPU and the NVIDIA GPU stays asleep. A desktop
  whose screens hang off NVIDIA uses NVENC. A five-frame ffmpeg encode proves
  the choice. When it fails the role uses x264, with a preset sized to the CPU
  thread count.
- Video: the canvas is 16:9 at the native height of the largest external
  output from `hyprctl monitors`. The streaming profile scales it with Lanczos
  to `obs_output_height`, and the recording profile keeps the canvas size. The
  frame rate is 60 with a hardware encoder on a 60 Hz screen, 30 otherwise.
- Webcam: the role lists every `/dev/video*` node and keeps only color capture
  nodes (MJPG or YUYV), which skips infrared and metadata nodes. External
  cameras win over integrated ones. The source uses the `/dev/v4l/by-id` link,
  else `by-path`, in MJPEG up to 1280x720 at 30 fps, because YUYV at 1080p
  drops to 5 fps on USB 2. Without a camera the scenes get no Caméra source
  and the run warns. Plug the camera in and run again with
  `-e obs_config_force=true`.
- Recordings: hybrid MP4 in `$(xdg-user-dir VIDEOS)/OBS`.

## Webcam background

With `obs-backgroundremoval` installed, `cutout` makes the background
transparent so the person sits directly on the scene. The camera then has no
accent frame and touches the bottom edge. `rvm` (Robust Video Matting) works at
320x192 and remembers the previous frames. It gives a soft alpha that follows
hair, so the plugin's threshold stays off. It runs on the CPU with four
threads, or two below 8 threads, so the NVIDIA GPU stays asleep.

`mediapipe` segments at 256x144, so on a 720p camera its mask shows
stair-stepped edges. With it the mask is thresholded towards hiding the room
(`obs_webcam_threshold`, plugin default 0.5) and `obs_webcam_edge_trim` trims
the room's halo. The contour filter keeps the upstream 0.05, since a larger
value merges small background areas, such as the gap under an arm, into the
person.

`blur` keeps a blurred background in a framed inset, and `none` the raw
picture. Unchanged frames and a hidden camera skip inference. The plugin is
built against the installed OBS. If OBS reports it as not loaded after an OBS
upgrade, rebuild it with yay.

## Profiles and scenes

"Enregistrement" records the native canvas at constant quality. "Streaming"
scales to `obs_output_height` at a constant bitrate, and its recordings reuse
the stream encoder, so a stream is encoded once.

Each palette gets its own scene collection with Montserrat titles:

| Palette | Text      | Background | Primary   |
| :------ | :-------- | :--------- | :-------- |
| Sombre  | `#FFFFFF` | `#242428`  | `#41A890` |
| Clair   | `#2A3235` | `#FFFFFF`  | `#41A890` |
| Gruvbox | `#EBDBB2` | `#1D2021`  | `#83A598` |

Sombre and Clair follow the brand guide. Gruvbox matches the desktop. The
primary color draws the title underline and the camera frame. The scenes are
an intro (title and camera), the screen with a camera inset, the screen only,
one application window on a backdrop with the camera, the camera only, and a
pause card. Desktop audio and the microphone are global sources.

Screen and window captures go through the XDG portal. Wayland gives no way to
name the output in advance, so OBS asks once and keeps a restore token.

Titles need the static Montserrat weights from `ttf-montserrat`. OBS opens the
first face of a font file, and in the variable font from Google Fonts that is
the Thin instance. The run warns when no static Bold face exists.

OBS rewrites these files when it exits, so the role creates them once and then
leaves them alone. `obs_config_force=true` regenerates them and keeps the
previous files as backups. The run refuses to write the configuration while OBS
is running.

## Virtual camera

The virtual camera serves Teams and other web meetings. The role writes
`/etc/modprobe.d/v4l2loopback.conf` with `exclusive_caps=1`, without which
Chromium does not list the device, and `/etc/modules-load.d/v4l2loopback.conf`
to load the module at boot. It also loads the module now. It removes the
`zz-dotfiles-v4l2loopback.conf` files of earlier versions. A module already
loaded with other options stays loaded, since unloading it would cut a running
camera. The run prints the reload command instead.

Firefox asks PipeWire for cameras, and PipeWire never adds a camera for this
device. It checks the device at boot, before OBS writes to it, when the device
only accepts output. When Firefox is installed, the role writes the policy
`media.webrtc.camera.allow-pipewire = false` as a default value, still
editable in `about:config`. Other policies in the file are kept, and invalid
JSON stops the run.

Start the virtual camera from the OBS Controls dock before the meeting, then
pick "OBS Virtual Camera" in the browser. It carries no sound, so pick the
microphone in the meeting as usual.

## Tags

`obs` runs the whole role. `obs_config` runs the profiles and scenes, and
`obs_virtualcam` the virtual camera. With `obs` as the only tag, `site.yml`
also installs the packages: see [OBS profile](../../PLAYBOOKS.md#obs-profile).

## Dependencies

None. The `packages` role installs `22_obs`. In `site.yml` the role runs after
`agent_cli` and before `print3d`.

## Example Playbook

```yaml
- name: Configure the Linux workstations
  hosts: all
  become: true
  roles:
    - role: obs
      when: "'22_obs' in (packages_selected_groups | default([]))"
      tags: [obs]
```

## License

Unlicense

## Author Information

pad

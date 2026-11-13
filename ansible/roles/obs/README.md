# obs

Configures OBS Studio for application demos from the host it runs on: encoder,
canvas, webcam, recording and streaming profiles, branded scene collections,
and a virtual camera for web meetings.

## Requirements

- Arch Linux or CachyOS with the `22_obs` group installed: OBS Studio, PipeWire
  Pulse, WirePlumber, the Hyprland portal backend, `qt6-wayland`,
  `v4l-utils`, `v4l2loopback-dkms`, `obs-backgroundremoval` (AUR), `simde` and
  `ttf-montserrat`. `simde` is a build requirement of every OBS 33 plugin that
  the AUR recipe does not declare.
- A Hyprland session to size the canvas; without one it falls back to
  1920x1080.
- Privilege escalation (`become: true`) for the virtual camera and the Firefox
  policy.

## Role Variables

| Variable                      | Default                                         | Description                                                                                         |
| :---------------------------- | :---------------------------------------------- | :-------------------------------------------------------------------------------------------------- |
| `obs_config_dir`              | `~/.config/obs-studio`                          | OBS configuration.                                                                                  |
| `obs_profiles`                | `Enregistrement` (record), `Streaming` (stream) | Profiles created next to the existing ones.                                                         |
| `obs_scene_collection_name`   | `Applis`                                        | Collections are named `<name> - <palette>`.                                                         |
| `obs_config_force`            | `false`                                         | Regenerate the files from the current host, with backups.                                           |
| `obs_encoder`                 | `auto`                                          | `auto`, `nvenc`, `vaapi` or `x264`.                                                                 |
| `obs_capture_output`          | `''`                                            | Connector the canvas is sized from; empty picks the largest external output.                        |
| `obs_output_height`           | `1080`                                          | Output height of the streaming profile.                                                             |
| `obs_webcam`                  | `''`                                            | Part of a `/dev/v4l/by-id` name; empty prefers an external camera.                                  |
| `obs_webcam_background`       | `cutout`                                        | `cutout`, `blur` or `none`.                                                                         |
| `obs_webcam_blur`             | `6`                                             | Background blur, 1 to 20.                                                                           |
| `obs_webcam_model`            | `rvm`                                           | `rvm` (soft matting) or `mediapipe` (lighter, coarser).                                             |
| `obs_webcam_threshold`        | `0.65`                                          | MediaPipe only: mask strictness.                                                                    |
| `obs_webcam_edge_trim`        | `2`                                             | MediaPipe only: pixels trimmed off the outline (0 to 30).                                           |
| `obs_mic_device`              | `default`                                       | Microphone source.                                                                                  |
| `obs_desktop_audio_device`    | `default`                                       | Desktop audio source.                                                                               |
| `obs_mic_noise_suppression`   | `true`                                          | RNNoise filter on the microphone. Disable it with an already filtered source such as `voice.clean`. |
| `obs_demo_title`              | `Démo`                                          | Title of the intro scene.                                                                           |
| `obs_pause_text`              | `Pause, on revient tout de suite`               | Text of the pause card.                                                                             |
| `obs_brand_palettes`          | Sombre, Clair, Gruvbox                          | Text, background and primary colours per palette.                                                   |
| `obs_brand_font`              | `Montserrat`                                    | Title font.                                                                                         |
| `obs_virtualcam_enabled`      | `true`                                          | Set up the v4l2loopback virtual camera.                                                             |
| `obs_virtualcam_label`        | `OBS Virtual Camera`                            | Device name shown to browsers.                                                                      |
| `obs_virtualcam_video_nr`     | `10`                                            | `/dev/video` number.                                                                                |
| `obs_virtualcam_firefox_v4l2` | `true`                                          | Firefox policy to read V4L2 cameras directly.                                                       |
| `obs_firefox_policies_file`   | `/etc/firefox/policies/policies.json`           | Firefox policies file.                                                                              |

## Host detection

The role reads the host before writing anything:

- Encoder: the GPU that renders the desktop (`boot_vga`) encodes. A hybrid
  laptop uses VAAPI on its iGPU and the NVIDIA GPU stays asleep; a desktop
  whose screens hang off NVIDIA uses NVENC. A five-frame ffmpeg encode proves
  the choice, and x264 is used when it fails, with a preset sized to the CPU
  thread count.
- Video: the canvas is 16:9 at the native height of the largest external
  output from `hyprctl monitors`, scaled with Lanczos to `obs_output_height` in
  the streaming profile; the recording profile keeps the canvas size. The
  frame rate is 60 with a hardware encoder on a 60 Hz screen, 30 otherwise.
- Webcam: every `/dev/video*` node is listed and only colour capture nodes
  (MJPG or YUYV) are kept, so infrared and metadata nodes are skipped. External
  cameras win over integrated ones. The source uses the `/dev/v4l/by-id` link,
  else `by-path`, in MJPEG up to 1280x720 at 30 fps: YUYV at 1080p drops to
  5 fps on USB 2. Without a camera the scenes get no Caméra source and the run
  warns: plug it in and run again with `-e obs_config_force=true`.
- Recordings: hybrid MP4 in `$(xdg-user-dir VIDEOS)/OBS`.

## Webcam background

With `obs-backgroundremoval` installed, `cutout` makes the background
transparent so the person sits directly on the scene; the camera then has no
accent frame and touches the bottom edge. `rvm` (Robust Video Matting) works at
320x192 and remembers the previous frames. It gives a soft alpha that follows
hair, so the plugin's threshold stays off. It runs on the CPU with four
threads, or two below 8 threads, so the NVIDIA GPU stays asleep.

`mediapipe` segments at 256x144: on a 720p camera its mask shows stair-stepped
edges. With it the mask is thresholded towards hiding the room
(`obs_webcam_threshold`, plugin default 0.5) and `obs_webcam_edge_trim` trims
the room's halo. The contour filter keeps the upstream 0.05, since a larger
value merges small background areas, such as the gap under an arm, into the
person.

`blur` keeps a blurred background in a framed inset, `none` the raw picture.
Unchanged frames and a hidden camera skip inference. The plugin is built
against the installed OBS: rebuild it with yay after an OBS upgrade if OBS
reports it as not loaded.

## Profiles and scenes

"Enregistrement" records the native canvas at constant quality. "Streaming"
scales to `obs_output_height` at a constant bitrate, and its recordings reuse
the stream encoder, so a stream is encoded once.

Each palette gets its own scene collection with Montserrat titles. Sombre
(#FFFFFF on #242428) and Clair (#2A3235 on #FFFFFF) follow the brand guide
with the primary colour #41A890; Gruvbox (#EBDBB2 on #1D2021, accent #83A598)
matches the desktop. The primary colour draws the title underline and the
camera frame. Scenes: intro (title and camera), screen with a camera inset,
screen only, one application window on a backdrop with the camera, camera
only, and a pause card. Desktop audio and the microphone are global sources.

Screen and window captures go through the XDG portal: Wayland gives no way to
name the output in advance, so OBS asks once and keeps a restore token.

Titles need the static Montserrat weights from `ttf-montserrat`: OBS opens the
first face of a font file, which is the Thin instance of the variable font
from Google Fonts. The run warns when no static Bold face exists.

OBS rewrites these files when it exits, so the role creates them once and then
leaves them alone. `obs_config_force=true` regenerates them and keeps the
previous files as backups. The run refuses to regenerate while OBS is open.

## Virtual camera

The virtual camera serves Teams and other web meetings. The role writes
`/etc/modprobe.d/zz-dotfiles-v4l2loopback.conf` with `exclusive_caps=1`
(Chromium lists the device only with it) and loads the module now and at every
boot. A module already loaded with other options is not unloaded, since that
would cut a running camera; the run prints the reload command instead.

Firefox asks PipeWire for cameras, and PipeWire never adds a camera for this
device: it checks the device at boot, before OBS writes to it, when it only
accepts output. When Firefox is installed, the role writes the policy
`media.webrtc.camera.allow-pipewire = false` as a default value, still
editable in `about:config`. Other policies in the file are kept, and invalid
JSON stops the run.

Start the virtual camera from the OBS Controls dock before the meeting, then
pick "OBS Virtual Camera" in the browser. It carries no sound: pick the
microphone in the meeting as usual.

Tags: `obs`, `obs_config`, `obs_virtualcam`.

## Dependencies

None. The `packages` role installs `22_obs`; the `obs.yml` playbook runs both.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: obs
      when: "'22_obs' in packages_selected_groups"
      tags: [obs]
```

## License

Unlicense

## Author Information

pad

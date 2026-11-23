# audio

Writes the user PipeWire and WirePlumber configuration: a clean microphone
source with echo cancellation and noise suppression, optional voice effects,
and the Bluetooth and suspend settings.

## Requirements

- PipeWire, PipeWire Pulse and WirePlumber 0.5 as user services. WirePlumber
  0.4 ignores the smart filter properties, so the stages then only show up as
  sources to pick by hand.
- `noise-suppression-for-voice` (RNNoise, in `01_base`) on Arch Linux.
- `swh-plugins` (`26_voice_effects`) for the voice effects.
- Runs as the user, without privilege escalation.

## Role Variables

| Variable                               | Default                                                                                                                                                               | Description                                                                                                           |
| :------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------- |
| `audio_config_home`                    | `XDG_CONFIG_HOME` from the environment, else `user_dir ~ '/.config'`                                                                                                  | Base directory of the written files.                                                                                  |
| `audio_pipewire_dir`                   | `'{{ audio_config_home }}/pipewire/pipewire.conf.d'`                                                                                                                  | PipeWire drop-ins.                                                                                                    |
| `audio_wireplumber_dir`                | `'{{ audio_config_home }}/wireplumber/wireplumber.conf.d'`                                                                                                            | WirePlumber drop-ins.                                                                                                 |
| `audio_config_directories`             | both drop-in directories and their parents                                                                                                                            | Directories the role writes under. None of them may be a link.                                                        |
| `audio_rate`                           | `48000`                                                                                                                                                               | Sample rate of the filter nodes.                                                                                      |
| `audio_quantum`                        | `1024`                                                                                                                                                                | Quantum the echo canceller asks for. A power of two of at least `audio_rate / 100`; the role refuses any other value. |
| `audio_node_prefix`                    | `voice`                                                                                                                                                               | Prefix of every node name.                                                                                            |
| `audio_clean_source`                   | `'{{ audio_node_prefix }}.clean'`                                                                                                                                     | Clean source given to the applications.                                                                               |
| `audio_clean_source_description`       | `Voix filtrée`                                                                                                                                                        | Name shown by the applications.                                                                                       |
| `audio_echo_cancel_source`             | `'{{ audio_node_prefix }}.echo-cancel'`                                                                                                                               | Echo-cancelled source that RNNoise reads.                                                                             |
| `audio_echo_cancel_source_description` | `Voix sans écho (interne)`                                                                                                                                            | Its displayed name.                                                                                                   |
| `audio_echo_cancel_args`               | `high_pass_filter: true`, `noise_suppression` and `transient_suppression: '{{ not audio_rnnoise_enabled \| bool }}'`, `voice_detection: false`, `gain_control: false` | WebRTC options, written as `webrtc.<key>`. Noise and transient suppression run only without RNNoise.                  |
| `audio_rnnoise_enabled`                | `"{{ ansible_facts['os_family'] == 'Archlinux' }}"`                                                                                                                   | Add the RNNoise stage.                                                                                                |
| `audio_rnnoise_controls`               | `VAD Threshold (%): 50`, `VAD Grace Period (ms): 200`, `Retroactive VAD Grace (ms): 50`                                                                               | RNNoise voice detector.                                                                                               |
| `audio_disable_suspend`                | `true`                                                                                                                                                                | Keep ALSA and Bluetooth devices awake. `false` lets idle devices suspend.                                             |
| `audio_voice_effects_group`            | `26_voice_effects`                                                                                                                                                    | Package group that enables the voice effects.                                                                         |
| `audio_voice_effects_enabled`          | `audio_voice_effects_group in (packages_selected_groups \| default([]))`                                                                                              | Write the voice effects file.                                                                                         |
| `audio_voice_effects`                  | vader, chipmunk, robot, church, radio                                                                                                                                 | One virtual source per entry.                                                                                         |
| `audio_obsolete_files`                 | `pipewire/pipewire.conf.d/10-realtime.conf` with its SHA-1                                                                                                            | Former files deleted while unchanged.                                                                                 |

The role also reads the `env`, `user_dir` and `os_family` facts. `site.yml`
gathers them as the SSH user.

## Clean source

The role names its nodes `voice.<name>`, and the stream that feeds a node
`voice.<name>.capture`, so they sort together in `pw-cli`, qpwgraph and
pavucontrol.

`voice.clean` is the clean source. WebRTC cancels the speakers' echo on the
default microphone, in mono, which gives `voice.echo-cancel`. RNNoise then
removes the non-voice noise and mutes the output between phrases. Without
RNNoise, the echo canceller output is `voice.clean`.

Both stages are WirePlumber smart source filters (`filter.smart`). WirePlumber
never makes a smart filter the default source. It chains them by
`filter.smart.before`/`after` (RNNoise nearest the applications, the echo
canceller nearest the microphone), links the echo canceller to the default
microphone, and gives `voice.clean` to every application that records from the
default source. The wiring does not depend on the order in which the nodes
appear. `filter.smart.targetable` lets a voice effect record from
`voice.clean` by name.

Keep the microphone as the default source, since selecting `voice.clean`
would make the echo canceller read its own chain. An application set to a
specific microphone records it unfiltered. If the echo canceller fails to
load, RNNoise reads the microphone directly.

## Voice effects

With `26_voice_effects`, each entry of `audio_voice_effects` becomes a virtual
source fed by `voice.clean`: `voice.vader`, `voice.chipmunk`, `voice.robot`,
`voice.church` and `voice.radio`. The radio effect compresses and slightly
saturates the voice, keeps 300 to 3200 Hz with a presence bump at 1.8 kHz, and
limits the peaks to -1 dBFS, without static. A host without the group loses
the effect file. Every module has the `nofail` flag, so a missing plugin drops
one source without stopping PipeWire.

## WirePlumber settings

WirePlumber keeps the Bluetooth A2DP profile while an application records,
enables every codec (the HFP codecs of headset microphones included) and
leaves LDAC on its adaptive quality.

## Safety

- The role stops before writing anything if one of
  `audio_config_directories` is a link, so it never writes into a clone that
  an old deployment linked there.
- Text values are written as JSON strings, so a quote in a description is
  escaped.
- A file of `audio_obsolete_files` is deleted only while it is a regular file
  with the shipped SHA-1. An edited copy or a link is kept and reported.
  [Cleaning up](../../README.md#cleaning-up) applies the same rule.

## Handlers

A changed file runs `try-reload-or-restart` on PipeWire, PipeWire Pulse and
WirePlumber. `swayosd-server.service`, deployed by the `dotfiles` role, is
`PartOf=pipewire-pulse.service` and restarts with it, because SwayOSD 0.3 never
reconnects to a restarted Pulse server.

## Tags

`dotfiles` and `audio` run the role. See [Running](../../README.md#running) for
the commands.

## Dependencies

None. The `packages` role installs the plugins. In `site.yml` the role runs
after `dotfiles` and before `agent_cli`.

## Example Playbook

```yaml
- name: Configure the Linux workstations
  hosts: all
  become: true
  roles:
    - role: audio
      when: packages_action | default('install') != 'plan'
      become: false
      tags: [dotfiles, audio]
```

## License

Unlicense

## Author Information

pad

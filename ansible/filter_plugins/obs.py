"""Host-aware OBS Studio settings and the application demo scene collection."""

from __future__ import annotations

import re
import uuid
from typing import Any

from ansible.errors import AnsibleFilterError

# Connector prefixes of built-in laptop panels; external screens are preferred.
INTERNAL_CONNECTORS = ("eDP", "LVDS", "DSI")
VAAPI_DRIVERS = {"amdgpu", "i915", "xe", "radeon"}
NVENC_DRIVERS = {"nvidia"}
HIGH_REFRESH_THRESHOLD = 59.0
ASPECT_WIDTH, ASPECT_HEIGHT = 16, 9
DEFAULT_MONITOR = {"name": None, "width": 1920, "height": 1080, "refresh": 60.0}

# OBS packs V4L2 tuples as (first << 32) | second.
V4L2_FOURCC = {
    "MJPG": 0x47504A4D,
    "YUYV": 0x56595559,
}
WEBCAM_FORMAT_PREFERENCE = ("MJPG", "YUYV")
WEBCAM_TARGET_WIDTH = 1280
WEBCAM_TARGET_FPS = 30

ENCODER_IDS = {
    "nvenc": "obs_nvenc_h264_tex",
    "vaapi": "ffmpeg_vaapi_tex",
    "x264": "obs_x264",
}
H264_HIGH_PROFILE = 100
RECORD_QUALITY = 20
STREAM_BITRATE_KBPS = 6000
KEYFRAME_SECONDS = 2

# Stable UUIDs keep regenerated collections diff-friendly.
UUID_NAMESPACE = uuid.UUID("6c5b4f0e-6f62-4a2f-9a51-2f1d0b1e0b5d")
ALIGN_TOP_LEFT = 5
ALIGN_CENTER = 0
BOUNDS_NONE = 0
BOUNDS_STRETCH = 1
BOUNDS_SCALE_INNER = 2


def _even(value: float) -> int:
    return max(2, round(value / 2.0) * 2)


def _aspect_width(height: int) -> int:
    return _even(height * ASPECT_WIDTH / ASPECT_HEIGHT)


def obs_render_nodes(text: Any) -> list[dict[str, Any]]:
    """Parse ``<renderD node> <driver> <boot_vga>`` lines from the role script."""
    if not isinstance(text, str):
        return []
    nodes = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 3 or not re.fullmatch(r"renderD\d+", fields[0]):
            continue
        nodes.append(
            {
                "device": f"/dev/dri/{fields[0]}",
                "driver": fields[1],
                "boot_vga": fields[2] == "1",
            }
        )
    return sorted(nodes, key=lambda node: node["device"])


def obs_encoder_candidate(nodes: Any, override: Any = "auto") -> dict[str, Any]:
    """Pick the hardware encoder of the GPU that renders the desktop.

    Encoding on the compositor GPU keeps frames on that GPU: a hybrid laptop
    uses VAAPI on its iGPU and leaves the NVIDIA GPU asleep, a desktop that
    drives its screens with NVIDIA uses NVENC.
    """
    if override not in ("auto", "nvenc", "vaapi", "x264"):
        raise AnsibleFilterError(
            f"obs_encoder must be auto, nvenc, vaapi or x264, not {override!r}"
        )
    nodes = [node for node in nodes or [] if isinstance(node, dict)]
    if override == "x264":
        return {"kind": "x264", "device": None}
    if override == "nvenc":
        matches = [node for node in nodes if node.get("driver") in NVENC_DRIVERS]
        return {"kind": "nvenc", "device": matches[0]["device"] if matches else None}
    if override == "vaapi":
        matches = [node for node in nodes if node.get("driver") in VAAPI_DRIVERS]
        if not matches:
            raise AnsibleFilterError("obs_encoder=vaapi but no VAAPI GPU was found")
        boot = [node for node in matches if node.get("boot_vga")]
        return {"kind": "vaapi", "device": (boot or matches)[0]["device"]}

    boot = [node for node in nodes if node.get("boot_vga")]
    render = (boot or nodes or [None])[0]
    if render is None:
        return {"kind": "x264", "device": None}
    if render.get("driver") in NVENC_DRIVERS:
        return {"kind": "nvenc", "device": render["device"]}
    if render.get("driver") in VAAPI_DRIVERS:
        return {"kind": "vaapi", "device": render["device"]}
    return {"kind": "x264", "device": None}


def _x264_preset(cpu_threads: Any) -> str:
    threads = cpu_threads if isinstance(cpu_threads, int) else 0
    if threads >= 12:
        return "faster"
    if threads >= 6:
        return "veryfast"
    return "superfast"


def obs_encoder_settings(
    candidate: Any, probe_succeeded: Any, cpu_threads: Any = 0
) -> dict[str, Any]:
    """Return OBS encoder ids and settings, falling back to x264 if the probe failed."""
    kind = candidate.get("kind") if isinstance(candidate, dict) else "x264"
    if kind != "x264" and probe_succeeded is not True:
        kind = "x264"
    common = {"keyint_sec": KEYFRAME_SECONDS, "profile": "high"}
    if kind == "nvenc":
        record = {
            **common,
            "rate_control": "CQP",
            "cqp": RECORD_QUALITY,
            "preset2": "p5",
            "tune": "hq",
            "multipass": "qres",
            "bf": 2,
        }
        stream = {**record, "rate_control": "CBR", "bitrate": STREAM_BITRATE_KBPS}
        del stream["cqp"]
    elif kind == "vaapi":
        record = {
            "keyint_sec": KEYFRAME_SECONDS,
            "profile": H264_HIGH_PROFILE,
            "vaapi_device": candidate["device"],
            "rate_control": "CQP",
            "qp": RECORD_QUALITY,
        }
        stream = {**record, "rate_control": "CBR", "bitrate": STREAM_BITRATE_KBPS}
        del stream["qp"]
    else:
        kind = "x264"
        record = {
            **common,
            "rate_control": "CRF",
            "crf": RECORD_QUALITY,
            "preset": _x264_preset(cpu_threads),
        }
        stream = {**record, "rate_control": "CBR", "bitrate": STREAM_BITRATE_KBPS}
        del stream["crf"]
    return {
        "kind": kind,
        "hardware": kind != "x264",
        "id": ENCODER_IDS[kind],
        "record": record,
        "stream": stream,
    }


def _monitor(entry: Any) -> dict[str, Any] | None:
    if not isinstance(entry, dict) or entry.get("disabled"):
        return None
    width, height = entry.get("width"), entry.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        return None
    if width <= 0 or height <= 0:
        return None
    refresh = entry.get("refreshRate", DEFAULT_MONITOR["refresh"])
    return {
        "name": entry.get("name"),
        "width": width,
        "height": height,
        "refresh": float(refresh) if isinstance(refresh, (int, float)) else 60.0,
    }


def obs_select_monitor(monitors: Any, preferred: Any = "") -> dict[str, Any]:
    """Choose the screen to demo: the preferred connector, else the largest external one."""
    candidates = [m for m in map(_monitor, monitors or []) if m is not None]
    if preferred:
        for monitor in candidates:
            if monitor["name"] == preferred:
                return monitor
        names = ", ".join(str(m["name"]) for m in candidates) or "none"
        raise AnsibleFilterError(
            f"obs_capture_output {preferred!r} is not an active output ({names})"
        )
    if not candidates:
        return dict(DEFAULT_MONITOR)
    external = [
        m for m in candidates if not str(m["name"]).startswith(INTERNAL_CONNECTORS)
    ]
    pool = external or candidates
    return max(pool, key=lambda m: (m["width"] * m["height"], m["refresh"]))


def obs_video_settings(
    monitor: Any, output_height: Any = 1080, hardware_encoder: Any = False
) -> dict[str, Any]:
    """Derive a 16:9 canvas at the screen's native height and a scaled output."""
    if not isinstance(monitor, dict):
        monitor = dict(DEFAULT_MONITOR)
    if not isinstance(output_height, int) or output_height < 360:
        raise AnsibleFilterError("obs_output_height must be an integer >= 360")
    base_height = _even(monitor["height"])
    output = min(output_height, base_height)
    fps = (
        60
        if hardware_encoder is True and monitor["refresh"] >= HIGH_REFRESH_THRESHOLD
        else 30
    )
    return {
        "monitor": monitor["name"],
        "base_width": _aspect_width(base_height),
        "base_height": base_height,
        "output_width": _aspect_width(_even(output)),
        "output_height": _even(output),
        "fps": fps,
    }


CAMERA_HEADER = re.compile(r"^### (/dev/video\d+)\|([^|]*)\|(.*)$")


def _parse_formats(text: str) -> dict[str, dict[tuple[int, int], set[int]]]:
    """Map fourcc -> size -> frame rates from ``v4l2-ctl --list-formats-ext``."""
    sizes: dict[str, dict[tuple[int, int], set[int]]] = {}
    current_format: str | None = None
    current_size: tuple[int, int] | None = None
    for line in text.splitlines():
        if found := re.search(r"\]:\s+'(\w{4})'", line):
            current_format = found.group(1)
            sizes.setdefault(current_format, {})
            current_size = None
        elif (
            found := re.search(r"Size: Discrete (\d+)x(\d+)", line)
        ) and current_format:
            current_size = (int(found.group(1)), int(found.group(2)))
            sizes[current_format].setdefault(current_size, set())
        elif (
            (found := re.search(r"\(([\d.]+) fps\)", line))
            and current_format
            and current_size
        ):
            sizes[current_format][current_size].add(round(float(found.group(1))))
    return sizes


def obs_cameras(text: Any) -> list[dict[str, Any]]:
    """Parse the role's camera listing and keep colour capture nodes only.

    Each block starts with ``### <node>|<stable path>|<name>`` followed by the
    node's format list. Metadata nodes list no format and infrared sensors only
    list GREY, so neither can feed a webcam source.
    """
    if not isinstance(text, str):
        return []
    cameras: list[dict[str, Any]] = []
    block: list[str] = []
    header: re.Match[str] | None = None

    def flush() -> None:
        if header is None:
            return
        formats = _parse_formats("\n".join(block))
        if any(fourcc in formats for fourcc in WEBCAM_FORMAT_PREFERENCE):
            cameras.append(
                {
                    "node": header.group(1),
                    "path": header.group(2) or header.group(1),
                    "name": header.group(3).strip(),
                    "formats": formats,
                }
            )

    for line in text.splitlines():
        if found := CAMERA_HEADER.match(line):
            flush()
            header, block = found, []
        else:
            block.append(line)
    flush()
    return cameras


def obs_pick_webcam(
    cameras: Any, preferred: Any = "", exclude_names: Any = None
) -> dict[str, Any] | None:
    """Pick a camera, preferring an external one over the built-in webcam.

    ``exclude_names`` drops loopback devices such as the OBS virtual camera,
    which lists capture formats while OBS feeds it.
    """
    excluded = {name for name in exclude_names or [] if isinstance(name, str)}
    cameras = [
        camera
        for camera in cameras or []
        if isinstance(camera, dict) and camera.get("name") not in excluded
    ]
    if preferred:
        for camera in cameras:
            if preferred in camera["path"] or preferred in camera["name"]:
                return camera
        found = ", ".join(camera["name"] for camera in cameras) or "none"
        raise AnsibleFilterError(
            f"obs_webcam {preferred!r} matches no colour camera ({found})"
        )
    external = [
        camera
        for camera in cameras
        if "integrated" not in f"{camera['path']} {camera['name']}".lower()
    ]
    pool = external or cameras
    return pool[0] if pool else None


def _pack(first: int, second: int) -> int:
    return (first << 32) | second


def obs_webcam_settings(camera: Any) -> dict[str, Any] | None:
    """Build v4l2_input settings for a camera from ``obs_pick_webcam``.

    YUYV at 1080p saturates USB 2 and drops to a few fps, so MJPEG is preferred
    at up to 1280 pixels wide and 30 fps when the camera offers it.
    """
    if not isinstance(camera, dict):
        return None
    settings: dict[str, Any] = {
        "device_id": camera["path"],
        "input": 0,
        "pixelformat": -1,
        "resolution": -1,
        "framerate": -1,
        "buffering": False,
    }
    formats = camera.get("formats", {})
    for fourcc in WEBCAM_FORMAT_PREFERENCE:
        available = formats.get(fourcc)
        if not available:
            continue
        settings["pixelformat"] = V4L2_FOURCC[fourcc]
        fitting = [size for size in available if size[0] <= WEBCAM_TARGET_WIDTH]
        if fitting:
            width, height = max(fitting, key=lambda size: (size[0] * size[1], size))
            settings["resolution"] = _pack(width, height)
            if WEBCAM_TARGET_FPS in available[(width, height)]:
                settings["framerate"] = _pack(1, WEBCAM_TARGET_FPS)
        break
    return settings


# Upstream 1.4.1 model paths (consts.h). RVM is a recurrent matting model at
# 320x192 that outputs a soft alpha; MediaPipe segments at 256x144.
WEBCAM_MODELS = {
    "rvm": "models/rvm_mobilenetv3_fp32.with_runtime_opt.ort",
    "mediapipe": "models/mediapipe.with_runtime_opt.ort",
}
BLUR_MAX = 20


WEBCAM_BACKGROUND_MODES = ("cutout", "blur", "none")
EDGE_TRIM_MAX = 30


def obs_webcam_filters(
    mode: Any,
    plugin_installed: Any,
    cpu_threads: Any = 0,
    blur: Any = 6,
    threshold: Any = 0.65,
    edge_trim: Any = 2,
    model: Any = "rvm",
) -> list[dict[str, Any]]:
    """Return the obs-backgroundremoval filter for the webcam background.

    ``cutout`` makes the background transparent (blur 0 selects the plugin's
    alpha shader), so the person sits directly on the scene; ``blur`` keeps a
    soft blurred background; ``none`` adds no filter. The MediaPipe model runs
    on the CPU so a hybrid laptop's NVIDIA GPU stays asleep.

    ``rvm`` keeps the model's soft alpha (no threshold), which follows hair
    and keeps its recurrent memory steady; the threshold, contour and edge
    settings then do not apply. ``mediapipe`` is lighter: its mask is
    thresholded, smoothed, trimmed and feathered. Inference is skipped for
    unchanged frames and while the camera is not shown.
    """
    if model not in WEBCAM_MODELS:
        raise AnsibleFilterError(
            f"obs_webcam_model must be rvm or mediapipe, not {model!r}"
        )
    if mode not in WEBCAM_BACKGROUND_MODES:
        raise AnsibleFilterError(
            f"obs_webcam_background must be cutout, blur or none, not {mode!r}"
        )
    if mode == "none" or plugin_installed is not True:
        return []
    if mode == "blur" and (not isinstance(blur, int) or not 1 <= blur <= BLUR_MAX):
        raise AnsibleFilterError(f"obs_webcam_blur must be between 1 and {BLUR_MAX}")
    # The plugin thresholds a background mask: person confidence below the
    # threshold is background, so a higher value hides more of the room.
    if not isinstance(threshold, (int, float)) or not 0 < threshold < 1:
        raise AnsibleFilterError("obs_webcam_threshold must be between 0 and 1")
    # A negative mask_expansion dilates the background mask by that many pixels,
    # trimming the room's halo around the head (plugin range -30..30).
    if not isinstance(edge_trim, int) or not 0 <= edge_trim <= EDGE_TRIM_MAX:
        raise AnsibleFilterError(
            f"obs_webcam_edge_trim must be between 0 and {EDGE_TRIM_MAX}"
        )
    many_cores = isinstance(cpu_threads, int) and cpu_threads >= 8
    # RVM needs about twice MediaPipe's work per frame to hold 30 fps.
    if model == "rvm":
        threads = 4 if many_cores else 2
    else:
        threads = 2 if many_cores else 1
    return [
        _source(
            "Découpage" if mode == "cutout" else "Flou arrière-plan",
            "background_removal",
            "background_removal",
            {
                "advanced": True,
                "model_select": WEBCAM_MODELS[model],
                "useGPU": "cpu",
                "numThreads": threads,
                "blur_background": blur if mode == "blur" else 0,
                "enable_threshold": model != "rvm",
                "threshold": float(threshold),
                # Upstream default. Higher values merge small background
                # areas (such as the gap under an arm) into the person.
                "contour_filter": 0.05,
                "smooth_contour": 0.5,
                "feather": 0.1,
                "mask_expansion": -edge_trim,
                "temporal_smooth_factor": 0.85,
                "enable_image_similarity": True,
                "image_similarity_threshold": 35.0,
                "mask_every_x_frames": 1,
                "stop_when_source_is_inactive": True,
                "enable_focal_blur": False,
            },
        )
    ]


def _abgr(color: str) -> int:
    """Convert ``#RRGGBB`` to the opaque ABGR integer OBS stores."""
    if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise AnsibleFilterError(f"color must look like #RRGGBB, not {color!r}")
    red, green, blue = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return (0xFF << 24) | (blue << 16) | (green << 8) | red


def _source(
    name: str,
    source_id: str,
    versioned_id: str,
    settings: dict[str, Any],
    filters: list[dict[str, Any]] | None = None,
    mixers: int = 0,
) -> dict[str, Any]:
    source = {
        "name": name,
        "uuid": str(uuid.uuid5(UUID_NAMESPACE, name)),
        "id": source_id,
        "versioned_id": versioned_id,
        "settings": settings,
        "mixers": mixers,
        "sync": 0,
        "flags": 0,
        "volume": 1.0,
        "balance": 0.5,
        "enabled": True,
        "muted": False,
        "push-to-mute": False,
        "push-to-mute-delay": 0,
        "push-to-talk": False,
        "push-to-talk-delay": 0,
        "hotkeys": {},
        "deinterlace_mode": 0,
        "deinterlace_field_order": 0,
        "monitoring_type": 0,
        "private_settings": {},
    }
    if filters:
        source["filters"] = filters
    return source


def _item(
    item_id: int,
    source: dict[str, Any],
    box: tuple[float, float, float, float],
    align: int = ALIGN_TOP_LEFT,
    bounds_type: int = BOUNDS_SCALE_INNER,
) -> dict[str, Any]:
    x, y, width, height = box
    return {
        "name": source["name"],
        "source_uuid": source["uuid"],
        "visible": True,
        "locked": False,
        "rot": 0.0,
        "align": align,
        "bounds_type": bounds_type,
        "bounds_align": ALIGN_CENTER,
        "bounds_crop": False,
        "crop_left": 0,
        "crop_top": 0,
        "crop_right": 0,
        "crop_bottom": 0,
        "id": item_id,
        "group_item_backup": False,
        "pos": {"x": float(x), "y": float(y)},
        "scale": {"x": 1.0, "y": 1.0},
        "bounds": {"x": float(width), "y": float(height)},
        "scale_filter": "disable",
        "blend_method": "default",
        "blend_type": "normal",
        "show_transition": {"duration": 0},
        "hide_transition": {"duration": 0},
        "private_settings": {},
    }


def _scene(name: str, layout: list[tuple[Any, ...]]) -> dict[str, Any]:
    items = [_item(index, *entry) for index, entry in enumerate(layout, start=1)]
    return _source(
        name,
        "scene",
        "scene",
        {"id_counter": len(items), "custom_size": False, "items": items},
    )


def obs_scene_collection(
    video: Any, webcam: Any = None, options: Any = None
) -> dict[str, Any]:
    """Build the application demo scene collection for a canvas.

    Screen and window captures go through the XDG portal: Wayland does not let
    a configuration name the output, so OBS asks once and keeps a restore token.
    """
    if not isinstance(video, dict):
        raise AnsibleFilterError("obs_scene_collection needs obs_video_settings output")
    options = options if isinstance(options, dict) else {}
    width, height = video["base_width"], video["base_height"]
    margin = round(width * 0.02)
    title = str(options.get("title", "Démo"))
    pause_text = str(options.get("pause_text", "Pause, on revient tout de suite"))
    background = _abgr(options.get("background", "#242428"))
    text_color = _abgr(options.get("text_color", "#FFFFFF"))
    primary = _abgr(options.get("primary", "#41A890"))
    font_face = str(options.get("font", "Montserrat"))
    mic_device = str(options.get("mic_device", "default"))
    desktop_device = str(options.get("desktop_audio_device", "default"))
    noise_suppression = options.get("noise_suppression", True) is not False
    name = str(options.get("name", "Démo Applis"))

    full = (0, 0, width, height)
    corner_width = round(width * 0.22)
    corner_height = round(corner_width * ASPECT_HEIGHT / ASPECT_WIDTH)
    corner = (
        width - corner_width - margin,
        height - corner_height - margin,
        corner_width,
        corner_height,
    )
    inset = (margin * 2, margin * 2, width - margin * 4, height - margin * 4)
    # The intro camera box is 16:9 so the accent frame hugs the picture.
    # A cut-out person must reach the bottom edge: a box floating above it
    # would slice the shoulders off in mid-air. Framed cameras keep a margin.
    cutout = options.get("webcam_cutout") is True
    if cutout:
        corner = (corner[0], height - corner_height, corner_width, corner_height)
    intro_width = width * 0.5
    intro_height = intro_width * 9 / 16
    intro = (
        width * 0.25,
        height - intro_height if cutout else height * 0.38,
        intro_width,
        intro_height,
    )
    border = max(4, round(height * 0.004))

    def framed(box: tuple[float, float, float, float]) -> tuple[Any, ...]:
        x, y, box_width, box_height = box
        return (
            accent,
            (x - border, y - border, box_width + 2 * border, box_height + 2 * border),
            ALIGN_TOP_LEFT,
            BOUNDS_STRETCH,
        )

    def underline(y_ratio: float) -> tuple[Any, ...]:
        bar_width = width * 0.12
        return (
            accent,
            ((width - bar_width) / 2, height * y_ratio, bar_width, border * 2),
            ALIGN_TOP_LEFT,
            BOUNDS_STRETCH,
        )

    backdrop = _source(
        "Fond",
        "color_source",
        "color_source_v3",
        {"color": background, "width": width, "height": height},
    )
    # One small primary-colour source, stretched for bars and camera frames.
    accent = _source(
        "Accent",
        "color_source",
        "color_source_v3",
        {"color": primary, "width": 64, "height": 64},
    )
    screen = _source(
        "Écran",
        "pipewire-screen-capture-source",
        "pipewire-screen-capture-source",
        {"ShowCursor": True},
    )
    window = _source(
        "Fenêtre appli",
        "pipewire-window-capture-source",
        "pipewire-window-capture-source",
        {"ShowCursor": True},
    )

    def text(
        source_name: str, value: str, size_ratio: float, style: str
    ) -> dict[str, Any]:
        return _source(
            source_name,
            "text_ft2_source",
            "text_ft2_source_v2",
            {
                "text": value,
                "font": {
                    "face": font_face,
                    "size": max(24, round(height * size_ratio)),
                    "style": style,
                    "flags": 1 if style == "Bold" else 0,
                },
                "color1": text_color,
                "color2": text_color,
            },
        )

    title_source = text("Titre", title, 1 / 12, "Bold")
    pause_source = text("Texte pause", pause_text, 1 / 16, "Medium")
    webcam_filters = options.get("webcam_filters") or []
    camera = (
        _source("Caméra", "v4l2_input", "v4l2_input", webcam, filters=webcam_filters)
        if isinstance(webcam, dict)
        else None
    )

    def centered_text(source: dict[str, Any], y_ratio: float) -> tuple[Any, ...]:
        return (source, (width / 2, height * y_ratio, 0, 0), ALIGN_CENTER, BOUNDS_NONE)

    # The accent frame would show as a coloured box around a cut-out person.
    def camera_items(box: tuple[float, float, float, float]) -> list[Any]:
        if not camera:
            return []
        return [(camera, box)] if cutout else [framed(box), (camera, box)]

    with_camera = camera_items(corner)
    scenes = [
        _scene(
            "1 - Intro",
            [(backdrop, full), centered_text(title_source, 0.2), underline(0.29)]
            + camera_items(intro),
        ),
        _scene("2 - Écran + caméra", [(screen, full)] + with_camera),
        _scene("3 - Écran seul", [(screen, full)]),
        _scene(
            "4 - Fenêtre appli",
            [(backdrop, full), (window, inset)] + with_camera,
        ),
    ]
    if camera:
        scenes.append(_scene("5 - Caméra", [(backdrop, full), (camera, full)]))
    scenes.append(
        _scene(
            "6 - Pause",
            [(backdrop, full), centered_text(pause_source, 0.46), underline(0.54)],
        )
    )

    mic_filters = (
        [
            _source(
                "Suppression du bruit",
                "noise_suppress_filter",
                "noise_suppress_filter_v2",
                {"method": "rnnoise"},
            )
        ]
        if noise_suppression
        else []
    )
    sources = [backdrop, accent, screen, window, title_source, pause_source]
    if camera:
        sources.append(camera)
    first = scenes[0]["name"]
    return {
        "name": name,
        "current_scene": first,
        "current_program_scene": first,
        "scene_order": [{"name": scene["name"]} for scene in scenes],
        "sources": sources + scenes,
        "groups": [],
        "quick_transitions": [],
        "transitions": [],
        "saved_projectors": [],
        "current_transition": "Fade",
        "transition_duration": 300,
        "preview_locked": False,
        "scaling_enabled": False,
        "resolution": {"x": width, "y": height},
        "modules": {},
        "version": 2,
        "DesktopAudioDevice1": _source(
            "Audio du bureau",
            "pulse_output_capture",
            "pulse_output_capture",
            {"device_id": desktop_device},
            mixers=0xFF,
        ),
        "AuxAudioDevice1": _source(
            "Micro",
            "pulse_input_capture",
            "pulse_input_capture",
            {"device_id": mic_device},
            filters=mic_filters,
            mixers=0xFF,
        ),
    }


class FilterModule:
    def filters(self) -> dict[str, Any]:
        return {
            "obs_render_nodes": obs_render_nodes,
            "obs_encoder_candidate": obs_encoder_candidate,
            "obs_encoder_settings": obs_encoder_settings,
            "obs_select_monitor": obs_select_monitor,
            "obs_video_settings": obs_video_settings,
            "obs_cameras": obs_cameras,
            "obs_pick_webcam": obs_pick_webcam,
            "obs_webcam_settings": obs_webcam_settings,
            "obs_webcam_filters": obs_webcam_filters,
            "obs_scene_collection": obs_scene_collection,
        }

"""OBS profile: host-derived settings, demo scenes, detection scripts, ownership."""

import importlib.util
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible.errors import AnsibleFilterError
from ansible_host_profiles import resolve_host_settings
from ansible_test_environment import ansible_test_environment, ansible_tree

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/obs"
# Pinned by ansible/requirements.yml, as ansible.cfg does for real runs: the
# test ansible.cfg replaces the repository one, which sets collections_path.
COLLECTIONS = ROOT / ".ansible/collections"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


obs = load("obs_filters", "ansible/filter_plugins/obs.py")
dotfiles = load("dotfiles_filters_obs", "ansible/filter_plugins/dotfiles.py")

# Captured on PadsP5560: Intel iGPU drives the desktop, the RTX is secondary.
HYBRID_LAPTOP_NODES = "renderD128 i915 1\nrenderD129 nvidia 0\n"
# Captured from `hyprctl monitors -j` on PadsP5560 with its two external screens.
HYBRID_LAPTOP_MONITORS = [
    {"name": "eDP-1", "width": 3840, "height": 2400, "refreshRate": 59.994},
    {"name": "DP-2", "width": 2560, "height": 1440, "refreshRate": 59.951},
    {"name": "DP-3", "width": 2560, "height": 1440, "refreshRate": 59.951},
]
# Trimmed list-cameras.sh output from PadsP5560: video0 is the RGB webcam
# (by-path only), video1 a metadata node, video2 the infrared sensor that owns
# the by-id "-index0" link.
INTEGRATED_LISTING = """\
### /dev/video0|/dev/v4l/by-path/pci-0000:00:14.0-usb-0:11:1.0-video-index0|Integrated_Webcam_HD: Integrate
ioctl: VIDIOC_ENUM_FMT
\tType: Video Capture

\t[0]: 'MJPG' (Motion-JPEG, compressed)
\t\tSize: Discrete 1280x720
\t\t\tInterval: Discrete 0.033s (30.000 fps)
\t\tSize: Discrete 640x480
\t\t\tInterval: Discrete 0.033s (30.000 fps)
\t[1]: 'YUYV' (YUYV 4:2:2)
\t\tSize: Discrete 640x480
\t\t\tInterval: Discrete 0.033s (30.000 fps)
### /dev/video1|/dev/v4l/by-path/pci-0000:00:14.0-usb-0:11:1.0-video-index1|Integrated_Webcam_HD: Integrate
ioctl: VIDIOC_ENUM_FMT
\tType: Video Capture

### /dev/video2|/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._Integrated_Webcam_HD-video-index0|Integrated_Webcam_HD: Integrate
ioctl: VIDIOC_ENUM_FMT
\tType: Video Capture

\t[0]: 'GREY' (8-bit Greyscale)
\t\tSize: Discrete 640x360
\t\t\tInterval: Discrete 0.033s (30.000 fps)
"""
# Same v4l2-ctl layout for a USB webcam offering 1080p in both formats.
EXTERNAL_LISTING = """\
### /dev/video4|/dev/v4l/by-id/usb-046d_Logi_Webcam_C920e_9CCDC27F-video-index0|Logi Webcam C920e
\t[0]: 'YUYV' (YUYV 4:2:2)
\t\tSize: Discrete 1920x1080
\t\t\tInterval: Discrete 0.200s (5.000 fps)
\t\tSize: Discrete 1280x720
\t\t\tInterval: Discrete 0.100s (10.000 fps)
\t[1]: 'MJPG' (Motion-JPEG, compressed)
\t\tSize: Discrete 1920x1080
\t\t\tInterval: Discrete 0.033s (30.000 fps)
\t\tSize: Discrete 1280x720
\t\t\tInterval: Discrete 0.033s (30.000 fps)
\t\tSize: Discrete 960x720
\t\t\tInterval: Discrete 0.033s (30.000 fps)
"""
MJPG = 0x47504A4D
YUYV = 0x56595559


class EncoderSelectionTests(unittest.TestCase):
    def test_hybrid_laptop_encodes_on_the_desktop_igpu(self):
        nodes = obs.obs_render_nodes(HYBRID_LAPTOP_NODES)
        self.assertEqual(
            obs.obs_encoder_candidate(nodes),
            {"kind": "vaapi", "device": "/dev/dri/renderD128"},
        )

    def test_nvidia_driving_the_screens_uses_nvenc(self):
        nodes = obs.obs_render_nodes("renderD128 nvidia 1\n")
        self.assertEqual(obs.obs_encoder_candidate(nodes)["kind"], "nvenc")

    def test_amd_desktop_uses_vaapi(self):
        nodes = obs.obs_render_nodes("renderD128 amdgpu 1\n")
        self.assertEqual(
            obs.obs_encoder_candidate(nodes),
            {"kind": "vaapi", "device": "/dev/dri/renderD128"},
        )

    def test_unknown_or_missing_gpu_falls_back_to_x264(self):
        for listing in ("", "renderD128 simpledrm 1\n", "garbage\ncard0 i915 1\n"):
            with self.subTest(listing=listing):
                nodes = obs.obs_render_nodes(listing)
                self.assertEqual(obs.obs_encoder_candidate(nodes)["kind"], "x264")

    def test_overrides_are_validated(self):
        nodes = obs.obs_render_nodes(HYBRID_LAPTOP_NODES)
        self.assertEqual(obs.obs_encoder_candidate(nodes, "nvenc")["kind"], "nvenc")
        with self.assertRaises(AnsibleFilterError):
            obs.obs_encoder_candidate(
                obs.obs_render_nodes("renderD128 nvidia 1"), "vaapi"
            )
        with self.assertRaises(AnsibleFilterError):
            obs.obs_encoder_candidate(nodes, "qsv")

    def test_forced_encoders_pick_a_matching_gpu(self):
        hybrid = obs.obs_render_nodes(HYBRID_LAPTOP_NODES)
        self.assertEqual(
            obs.obs_encoder_candidate(hybrid, "x264"), {"kind": "x264", "device": None}
        )
        self.assertEqual(
            obs.obs_encoder_candidate(hybrid, "vaapi")["device"], "/dev/dri/renderD128"
        )
        # NVIDIA drives the screens: forcing VAAPI uses the secondary AMD GPU.
        nvidia_boot = obs.obs_render_nodes("renderD128 nvidia 1\nrenderD129 amdgpu 0\n")
        self.assertEqual(
            obs.obs_encoder_candidate(nvidia_boot, "vaapi"),
            {"kind": "vaapi", "device": "/dev/dri/renderD129"},
        )

    def test_failed_probe_falls_back_to_software_encoding(self):
        candidate = {"kind": "vaapi", "device": "/dev/dri/renderD128"}
        for probe in (False, None, "yes"):
            with self.subTest(probe=probe):
                settings = obs.obs_encoder_settings(candidate, probe, 16)
                self.assertEqual(settings["id"], "obs_x264")
                self.assertFalse(settings["hardware"])

    def test_vaapi_settings_target_the_probed_device(self):
        settings = obs.obs_encoder_settings(
            {"kind": "vaapi", "device": "/dev/dri/renderD128"}, True
        )
        self.assertEqual(settings["id"], "ffmpeg_vaapi_tex")
        self.assertEqual(settings["record"]["vaapi_device"], "/dev/dri/renderD128")
        self.assertEqual(settings["record"]["rate_control"], "CQP")
        self.assertEqual(settings["stream"]["rate_control"], "CBR")
        self.assertNotIn("qp", settings["stream"])

    def test_nvenc_records_constant_quality_and_streams_constant_bitrate(self):
        settings = obs.obs_encoder_settings(
            {"kind": "nvenc", "device": "/dev/dri/renderD129"}, True
        )
        self.assertEqual(settings["id"], "obs_nvenc_h264_tex")
        self.assertTrue(settings["hardware"])
        record, stream = settings["record"], settings["stream"]
        self.assertEqual((record["rate_control"], record["cqp"]), ("CQP", 20))
        self.assertEqual(record["keyint_sec"], 2)
        self.assertEqual((stream["rate_control"], stream["bitrate"]), ("CBR", 6000))
        self.assertNotIn("cqp", stream)
        # Only the rate control differs between the two outputs.
        self.assertEqual(
            {k: v for k, v in stream.items() if k not in ("rate_control", "bitrate")},
            {k: v for k, v in record.items() if k not in ("rate_control", "cqp")},
        )

    def test_x264_preset_scales_with_cpu_threads(self):
        presets = {
            threads: obs.obs_encoder_settings({"kind": "x264"}, False, threads)[
                "record"
            ]["preset"]
            for threads in (4, 8, 16)
        }
        self.assertEqual(presets, {4: "superfast", 8: "veryfast", 16: "faster"})


class VideoSettingsTests(unittest.TestCase):
    def test_external_screen_wins_over_a_larger_laptop_panel(self):
        monitor = obs.obs_select_monitor(HYBRID_LAPTOP_MONITORS)
        self.assertEqual(monitor["name"], "DP-2")
        video = obs.obs_video_settings(monitor, 1080, True)
        self.assertEqual(
            video,
            {
                "monitor": "DP-2",
                "base_width": 2560,
                "base_height": 1440,
                "output_width": 1920,
                "output_height": 1080,
                "fps": 60,
            },
        )

    def test_16_10_panel_keeps_native_height_on_a_16_9_canvas(self):
        monitor = obs.obs_select_monitor(HYBRID_LAPTOP_MONITORS, "eDP-1")
        video = obs.obs_video_settings(monitor, 1080, False)
        self.assertEqual((video["base_width"], video["base_height"]), (4266, 2400))
        self.assertEqual(video["fps"], 30)

    def test_small_screen_is_not_upscaled(self):
        video = obs.obs_video_settings(
            obs.obs_select_monitor(
                [{"name": "HDMI-A-1", "width": 1366, "height": 768, "refreshRate": 60}]
            ),
            1080,
            True,
        )
        self.assertEqual((video["output_width"], video["output_height"]), (1366, 768))

    def test_missing_or_disabled_outputs(self):
        self.assertEqual(obs.obs_select_monitor([])["name"], None)
        only_disabled = [{**HYBRID_LAPTOP_MONITORS[1], "disabled": True}]
        self.assertEqual(obs.obs_select_monitor(only_disabled)["width"], 1920)
        with self.assertRaises(AnsibleFilterError):
            obs.obs_select_monitor(HYBRID_LAPTOP_MONITORS, "HDMI-A-1")
        with self.assertRaises(AnsibleFilterError):
            obs.obs_video_settings(obs.obs_select_monitor([]), 100)

    def test_outputs_without_a_usable_size_are_ignored(self):
        monitors = [
            {"name": "DP-1", "width": 7680, "height": 0},
            {"name": "HDMI-A-1", "width": "3840", "height": "2160"},
            HYBRID_LAPTOP_MONITORS[1],
        ]
        self.assertEqual(obs.obs_select_monitor(monitors)["name"], "DP-2")
        # Naming one does not bring it back: it would give an empty canvas.
        for name in ("DP-1", "HDMI-A-1"):
            with self.subTest(name=name), self.assertRaises(AnsibleFilterError):
                obs.obs_select_monitor(monitors, name)

    def test_missing_monitor_falls_back_to_a_1080p_canvas(self):
        video = obs.obs_video_settings(None)
        self.assertEqual((video["base_width"], video["base_height"]), (1920, 1080))


class WebcamTests(unittest.TestCase):
    def test_infrared_and_metadata_nodes_are_not_cameras(self):
        cameras = obs.obs_cameras(INTEGRATED_LISTING)
        self.assertEqual([camera["node"] for camera in cameras], ["/dev/video0"])
        settings = obs.obs_webcam_settings(obs.obs_pick_webcam(cameras))
        self.assertEqual(
            settings["device_id"],
            "/dev/v4l/by-path/pci-0000:00:14.0-usb-0:11:1.0-video-index0",
        )
        self.assertEqual(settings["pixelformat"], MJPG)
        self.assertEqual(settings["resolution"], (1280 << 32) | 720)
        self.assertEqual(settings["framerate"], (1 << 32) | 30)

    def test_external_camera_uses_mjpeg_instead_of_slow_yuyv(self):
        cameras = obs.obs_cameras(INTEGRATED_LISTING + EXTERNAL_LISTING)
        camera = obs.obs_pick_webcam(cameras)
        self.assertEqual(camera["name"], "Logi Webcam C920e")
        settings = obs.obs_webcam_settings(camera)
        self.assertEqual(settings["pixelformat"], MJPG)
        self.assertEqual(settings["resolution"], (1280 << 32) | 720)

    def test_yuyv_only_camera_keeps_a_size_within_the_target(self):
        listing = (
            "### /dev/video0||USB Cam\n\t[0]: 'YUYV' (YUYV 4:2:2)\n"
            "\t\tSize: Discrete 1920x1080\n\t\tSize: Discrete 640x480\n"
            "\t\t\tInterval: Discrete 0.050s (20.000 fps)\n"
        )
        settings = obs.obs_webcam_settings(
            obs.obs_pick_webcam(obs.obs_cameras(listing))
        )
        self.assertEqual(settings["device_id"], "/dev/video0")
        self.assertEqual(settings["pixelformat"], YUYV)
        self.assertEqual(settings["resolution"], (640 << 32) | 480)
        # 30 fps is not offered, so the device default rate is kept.
        self.assertEqual(settings["framerate"], -1)

    def test_virtual_camera_and_absent_cameras(self):
        virtual = (
            "### /dev/video10||OBS Virtual Camera\n"
            + EXTERNAL_LISTING.split("\n", 1)[1]
        )
        cameras = obs.obs_cameras(virtual)
        self.assertEqual(len(cameras), 1)
        self.assertIsNone(obs.obs_pick_webcam(cameras, "", ["OBS Virtual Camera"]))
        self.assertIsNone(obs.obs_webcam_settings(obs.obs_pick_webcam([])))
        with self.assertRaises(AnsibleFilterError):
            obs.obs_pick_webcam(obs.obs_cameras(INTEGRATED_LISTING), "C920")

    def test_preferred_camera_wins_over_the_external_one(self):
        cameras = obs.obs_cameras(INTEGRATED_LISTING + EXTERNAL_LISTING)
        by_name = obs.obs_pick_webcam(cameras, "Integrated_Webcam_HD")
        self.assertEqual(by_name["node"], "/dev/video0")
        by_path = obs.obs_pick_webcam(cameras, "usb-046d_Logi")
        self.assertEqual(by_path["node"], "/dev/video4")

    def test_camera_without_a_size_within_the_target_keeps_its_default(self):
        listing = (
            "### /dev/video0||4K Cam\n\t[0]: 'MJPG' (Motion-JPEG)\n"
            "\t\tSize: Discrete 3840x2160\n"
            "\t\t\tInterval: Discrete 0.033s (30.000 fps)\n"
        )
        settings = obs.obs_webcam_settings(
            obs.obs_pick_webcam(obs.obs_cameras(listing))
        )
        self.assertEqual(settings["pixelformat"], MJPG)
        self.assertEqual((settings["resolution"], settings["framerate"]), (-1, -1))

    def test_role_warns_when_no_webcam_is_found(self):
        facts = yaml.safe_load((ROLE / "tasks/facts.yml").read_text())
        tasks = [
            task
            for task in facts
            if task["name"]
            in (
                "Pick the webcam and build its source settings",
                "Warn when no webcam was found",
            )
        ]
        self.assertEqual(len(tasks), 2)
        # An unplugged camera, a virtual camera only, then the C920e.
        virtual = (
            "### /dev/video10||OBS Virtual Camera\n"
            + EXTERNAL_LISTING.split("\n", 1)[1]
        )
        for listing, warned in (
            ("", True),
            (virtual, True),
            (EXTERNAL_LISTING, False),
        ):
            with self.subTest(warned=warned), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                play = work / "play.yml"
                play.write_text(
                    yaml.safe_dump(
                        [
                            {
                                "hosts": "localhost",
                                "connection": "local",
                                "gather_facts": False,
                                "vars": {
                                    "obs_camera_listing": {"stdout": listing},
                                    "obs_webcam": "",
                                    "obs_virtualcam_label": "OBS Virtual Camera",
                                },
                                "tasks": tasks,
                            }
                        ]
                    )
                )
                result = subprocess.run(
                    ["ansible-playbook", "-i", "localhost,", str(play)],
                    env=ansible_test_environment(work),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(
                    "No colour webcam was found" in result.stdout,
                    warned,
                    result.stdout,
                )

    def test_detection_output_that_is_not_text_yields_no_device(self):
        # A skipped or failed detection task registers no stdout string.
        self.assertEqual(obs.obs_render_nodes(None), [])
        self.assertEqual(obs.obs_cameras(None), [])


class BrandThemeTests(unittest.TestCase):
    def collection(self, options=None):
        return obs.obs_scene_collection(
            {"base_width": 2560, "base_height": 1440},
            {"device_id": "/dev/video0"},
            options,
        )

    def sources(self, collection):
        return {source["name"]: source for source in collection["sources"]}

    def test_dark_brand_palette_and_montserrat_are_the_defaults(self):
        sources = self.sources(self.collection())
        # OBS stores colours as opaque ABGR: #242428 -> 0xFF282424.
        self.assertEqual(sources["Fond"]["settings"]["color"], 0xFF282424)
        self.assertEqual(sources["Accent"]["settings"]["color"], 0xFF90A841)
        title = sources["Titre"]["settings"]
        self.assertEqual(title["font"]["face"], "Montserrat")
        self.assertEqual((title["font"]["style"], title["font"]["flags"]), ("Bold", 1))
        self.assertEqual(title["color1"], 0xFFFFFFFF)
        self.assertEqual(sources["Texte pause"]["settings"]["font"]["style"], "Medium")

    def test_light_palette_is_applied(self):
        sources = self.sources(
            self.collection({"background": "#FFFFFF", "text_color": "#2A3235"})
        )
        self.assertEqual(sources["Fond"]["settings"]["color"], 0xFFFFFFFF)
        self.assertEqual(sources["Titre"]["settings"]["color1"], 0xFF35322A)

    def test_accent_frame_surrounds_the_camera_inset(self):
        scene = next(
            source
            for source in self.collection()["sources"]
            if source["name"] == "2 - Écran + caméra"
        )
        frame, camera = scene["settings"]["items"][1:]
        self.assertEqual(frame["bounds_type"], 1)
        for axis in ("x", "y"):
            self.assertLess(frame["pos"][axis], camera["pos"][axis])
            self.assertGreater(
                frame["pos"][axis] + frame["bounds"][axis],
                camera["pos"][axis] + camera["bounds"][axis],
            )

    def test_role_maps_the_brand_and_desktop_palettes(self):
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        palettes = defaults["obs_brand_palettes"]
        self.assertEqual(
            palettes["Sombre"],
            {"text": "#FFFFFF", "background": "#242428", "primary": "#41A890"},
        )
        self.assertEqual(
            palettes["Clair"],
            {"text": "#2A3235", "background": "#FFFFFF", "primary": "#41A890"},
        )
        self.assertEqual(defaults["obs_brand_font"], "Montserrat")

    def test_gruvbox_palette_follows_the_desktop_theme(self):
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        toolkit = (
            ROOT
            / "ansible/roles/dotfiles/templates/home/.config/hypr/hyprtoolkit.conf.j2"
        ).read_text()
        theme = {
            key: "#" + value[-6:].upper()
            for key, value in re.findall(r"^(\w+) = 0x([0-9A-Fa-f]{8})$", toolkit, re.M)
        }
        self.assertEqual(
            defaults["obs_brand_palettes"]["Gruvbox"],
            {
                "text": theme["text"],
                "background": theme["background"],
                "primary": theme["accent"],
            },
        )

    def test_variable_font_instances_do_not_count_as_static_bold(self):
        facts = yaml.safe_load((ROLE / "tasks/facts.yml").read_text())
        check = next(
            task
            for task in facts
            if task["name"] == "Check for a static bold face of the brand font"
        )
        # Real fc-list output: only the variable font, then with ttf-montserrat.
        for lines, expected in ((["458752"], False), (["0", "458752"], True)):
            with self.subTest(lines=lines), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                play = work / "play.yml"
                play.write_text(
                    yaml.safe_dump(
                        [
                            {
                                "hosts": "localhost",
                                "connection": "local",
                                "gather_facts": False,
                                "vars": {
                                    "obs_brand_font_bold": {"stdout_lines": lines}
                                },
                                "tasks": [
                                    check,
                                    {
                                        "name": "Show",
                                        "ansible.builtin.debug": {
                                            "msg": "RESULT={{ obs_brand_font_static_bold | bool }}"
                                        },
                                    },
                                ],
                            }
                        ]
                    )
                )
                result = subprocess.run(
                    ["ansible-playbook", "-i", "localhost,", str(play)],
                    env=ansible_test_environment(work),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"RESULT={expected}", result.stdout)


PLUGIN_MODELS = Path("/usr/share/obs/obs-plugins/obs-backgroundremoval/models")


class WebcamBackgroundTests(unittest.TestCase):
    def settings(self, mode, threads=16, blur=6, model="rvm"):
        [background] = obs.obs_webcam_filters(mode, True, threads, blur, 0.65, 2, model)
        self.assertEqual(background["id"], "background_removal")
        return background["settings"]

    def test_cutout_makes_the_background_transparent(self):
        settings = self.settings("cutout")
        # blur_background 0 selects the plugin's alpha (transparent) shader.
        self.assertEqual(settings["blur_background"], 0)
        # Upstream 1.4.1 MODEL_RVM and USEGPU_CPU constants.
        self.assertEqual(
            settings["model_select"],
            "models/rvm_mobilenetv3_fp32.with_runtime_opt.ort",
        )
        self.assertEqual(settings["useGPU"], "cpu")
        # Thresholding would turn RVM's soft alpha back into a binary mask.
        self.assertFalse(settings["enable_threshold"])
        self.assertGreater(settings["feather"], 0)
        self.assertGreater(settings["smooth_contour"], 0)
        self.assertTrue(settings["stop_when_source_is_inactive"])
        self.assertTrue(settings["enable_image_similarity"])

    @unittest.skipUnless(
        PLUGIN_MODELS.is_dir(), "obs-backgroundremoval is not installed"
    )
    def test_models_ship_with_the_installed_plugin(self):
        for model in obs.WEBCAM_MODELS.values():
            with self.subTest(model=model):
                self.assertTrue((PLUGIN_MODELS.parent / model).is_file())

    def test_unknown_model_is_refused(self):
        with self.assertRaises(AnsibleFilterError):
            self.settings("cutout", model="sinet")

    def test_mediapipe_mask_leans_towards_hiding_the_room(self):
        # Upstream 1.4.1: background = person confidence < threshold, a
        # negative mask_expansion dilates the background mask, and a larger
        # contour_filter merges small background areas into the person.
        settings = self.settings("cutout", model="mediapipe")
        self.assertEqual(
            settings["model_select"], "models/mediapipe.with_runtime_opt.ort"
        )
        self.assertTrue(settings["enable_threshold"])
        self.assertGreater(settings["threshold"], 0.5)
        self.assertLess(settings["mask_expansion"], 0)
        self.assertLessEqual(settings["contour_filter"], 0.05)
        custom = obs.obs_webcam_filters("cutout", True, 16, 6, 0.8, 5, "mediapipe")[0][
            "settings"
        ]
        self.assertEqual((custom["threshold"], custom["mask_expansion"]), (0.8, -5))

    def test_mask_settings_are_bounded(self):
        for threshold, trim in ((0, 2), (1, 2), (0.6, -1), (0.6, 31), (0.6, 1.5)):
            with (
                self.subTest(threshold=threshold, trim=trim),
                self.assertRaises(AnsibleFilterError),
            ):
                obs.obs_webcam_filters("cutout", True, 16, 6, threshold, trim)

    def test_blur_mode_keeps_a_soft_background(self):
        self.assertEqual(self.settings("blur", blur=6)["blur_background"], 6)
        for value in (0, 21, "6"):
            with self.subTest(value=value), self.assertRaises(AnsibleFilterError):
                obs.obs_webcam_filters("blur", True, 16, value)

    def test_threads_follow_the_cpu(self):
        threads = {
            (model, count): self.settings("cutout", count, model=model)["numThreads"]
            for model in ("rvm", "mediapipe")
            for count in (4, 16)
        }
        self.assertEqual(
            threads,
            {("rvm", 4): 2, ("rvm", 16): 4, ("mediapipe", 4): 1, ("mediapipe", 16): 2},
        )

    def test_no_filter_without_plugin_or_in_none_mode(self):
        self.assertEqual(obs.obs_webcam_filters("cutout", False, 16), [])
        self.assertEqual(obs.obs_webcam_filters("none", True, 16), [])
        with self.assertRaises(AnsibleFilterError):
            obs.obs_webcam_filters(True, True, 16)

    def collection(self, mode):
        filters = obs.obs_webcam_filters(mode, True, 16)
        return (
            obs.obs_scene_collection(
                {"base_width": 2560, "base_height": 1440},
                {"device_id": "/dev/video0"},
                {"webcam_filters": filters, "webcam_cutout": mode == "cutout"},
            ),
            filters,
        )

    def scene_items(self, collection, name):
        scene = next(s for s in collection["sources"] if s["name"] == name)
        return scene["settings"]["items"]

    def test_camera_source_carries_the_filter(self):
        collection, filters = self.collection("cutout")
        camera = next(s for s in collection["sources"] if s["name"] == "Caméra")
        self.assertEqual(camera["filters"], filters)

    def test_cut_out_camera_has_no_frame_and_reaches_the_bottom_edge(self):
        collection, _ = self.collection("cutout")
        for scene in ("1 - Intro", "2 - Écran + caméra", "4 - Fenêtre appli"):
            with self.subTest(scene=scene):
                items = self.scene_items(collection, scene)
                camera = next(item for item in items if item["name"] == "Caméra")
                frames = [
                    item
                    for item in items
                    if item["name"] == "Accent"
                    and item["pos"]["x"] <= camera["pos"]["x"]
                    and item["pos"]["y"] <= camera["pos"]["y"]
                    and item["pos"]["x"] + item["bounds"]["x"]
                    >= camera["pos"]["x"] + camera["bounds"]["x"]
                ]
                self.assertEqual(frames, [])
                self.assertEqual(camera["pos"]["y"] + camera["bounds"]["y"], 1440)

    def test_blurred_camera_keeps_its_frame_and_margin(self):
        collection, _ = self.collection("blur")
        items = self.scene_items(collection, "2 - Écran + caméra")
        self.assertEqual(
            [item["name"] for item in items], ["Écran", "Accent", "Caméra"]
        )
        camera = items[2]
        self.assertLess(camera["pos"]["y"] + camera["bounds"]["y"], 1440)

    def test_plugin_detection_reads_the_package_file_list(self):
        facts = yaml.safe_load((ROLE / "tasks/facts.yml").read_text())
        check = next(
            task
            for task in facts
            if task["name"] == "Check for the background removal plugin"
        )
        cases = {
            "/usr/lib/obs-plugins/obs-backgroundremoval.so": True,
            "/usr/lib/obs-modules/plugins/x/obs-backgroundremoval.so": True,
            "/usr/share/obs/obs-plugins/obs-backgroundremoval/models/a.ort": False,
        }
        for path, expected in cases.items():
            with self.subTest(path=path), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                play = work / "play.yml"
                play.write_text(
                    yaml.safe_dump(
                        [
                            {
                                "hosts": "localhost",
                                "connection": "local",
                                "gather_facts": False,
                                "vars": {
                                    "obs_background_plugin_files": {
                                        "rc": 0,
                                        "stdout_lines": ["/usr/", path],
                                    }
                                },
                                "tasks": [
                                    check,
                                    {
                                        "name": "Show",
                                        "ansible.builtin.debug": {
                                            "msg": "RESULT={{ obs_background_plugin_installed | bool }}"
                                        },
                                    },
                                ],
                            }
                        ]
                    )
                )
                result = subprocess.run(
                    ["ansible-playbook", "-i", "localhost,", str(play)],
                    env=ansible_test_environment(work),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"RESULT={expected}", result.stdout)


class SceneCollectionTests(unittest.TestCase):
    def setUp(self):
        self.video = {"base_width": 2560, "base_height": 1440}
        self.webcam = {"device_id": "/dev/video0", "pixelformat": MJPG}

    def items(self, collection):
        return {
            source["name"]: source["settings"]["items"]
            for source in collection["sources"]
            if source["id"] == "scene"
        }

    def test_every_scene_item_points_to_a_defined_source(self):
        collection = obs.obs_scene_collection(self.video, self.webcam)
        uuids = {source["uuid"] for source in collection["sources"]}
        self.assertEqual(len(uuids), len(collection["sources"]))
        for scene, items in self.items(collection).items():
            with self.subTest(scene=scene):
                self.assertTrue(items)
                for item in items:
                    self.assertIn(item["source_uuid"], uuids)
        self.assertEqual(
            [entry["name"] for entry in collection["scene_order"]],
            list(self.items(collection)),
        )

    def test_layout_stays_inside_the_canvas(self):
        collection = obs.obs_scene_collection(self.video, self.webcam)
        for scene, items in self.items(collection).items():
            for item in items:
                with self.subTest(scene=scene, source=item["name"]):
                    x, y = item["pos"]["x"], item["pos"]["y"]
                    right = x + item["bounds"]["x"] if item["align"] == 5 else x
                    bottom = y + item["bounds"]["y"] if item["align"] == 5 else y
                    self.assertTrue(0 <= x <= right <= 2560)
                    self.assertTrue(0 <= y <= bottom <= 1440)

    def test_demo_scenes_combine_screen_and_camera(self):
        items = self.items(obs.obs_scene_collection(self.video, self.webcam))
        names = {
            scene: [item["name"] for item in entries]
            for scene, entries in items.items()
        }
        self.assertEqual(names["2 - Écran + caméra"], ["Écran", "Accent", "Caméra"])
        self.assertEqual(
            names["4 - Fenêtre appli"], ["Fond", "Fenêtre appli", "Accent", "Caméra"]
        )
        sources = {
            source["name"]: source
            for source in obs.obs_scene_collection(self.video, self.webcam)["sources"]
        }
        self.assertEqual(sources["Écran"]["id"], "pipewire-screen-capture-source")
        self.assertEqual(sources["Caméra"]["settings"], self.webcam)

    def test_without_camera_no_camera_source_or_scene_is_created(self):
        collection = obs.obs_scene_collection(self.video, None)
        self.assertNotIn("5 - Caméra", self.items(collection))
        self.assertNotIn(
            "v4l2_input", {source["id"] for source in collection["sources"]}
        )

    def test_audio_devices_and_noise_suppression_are_configurable(self):
        default = obs.obs_scene_collection(self.video, None)
        self.assertEqual(
            default["AuxAudioDevice1"]["filters"][0]["settings"], {"method": "rnnoise"}
        )
        custom = obs.obs_scene_collection(
            self.video,
            None,
            {"mic_device": "Mic_Clean", "noise_suppression": False},
        )
        self.assertEqual(
            custom["AuxAudioDevice1"]["settings"]["device_id"], "Mic_Clean"
        )
        self.assertNotIn("filters", custom["AuxAudioDevice1"])

    def test_scene_collection_requires_video_settings(self):
        with self.assertRaises(AnsibleFilterError):
            obs.obs_scene_collection(None, self.webcam)

    def test_output_is_deterministic_json(self):
        first = json.dumps(obs.obs_scene_collection(self.video, self.webcam))
        second = json.dumps(obs.obs_scene_collection(self.video, self.webcam))
        self.assertEqual(first, second)
        with self.assertRaises(AnsibleFilterError):
            obs.obs_scene_collection(self.video, None, {"background": "blue"})


class FilterExportTests(unittest.TestCase):
    def test_every_obs_filter_used_by_the_role_is_exported(self):
        role_text = "".join(path.read_text() for path in (ROLE / "tasks").glob("*.yml"))
        exported = obs.FilterModule().filters()
        for name in exported:
            self.assertIs(exported[name], getattr(obs, name))
        used = {name for name in exported if f"| {name}" in role_text}
        self.assertEqual(used, set(exported))


class FirefoxPolicyTests(unittest.TestCase):
    """Firefox must read the loopback camera through V4L2, not PipeWire."""

    PREF = "media.webrtc.camera.allow-pipewire"

    def test_policy_turns_off_pipewire_cameras_as_a_default(self):
        document = obs.obs_firefox_policies("")
        self.assertEqual(
            document["policies"]["Preferences"][self.PREF],
            # "default" keeps the preference editable in about:config.
            {"Value": False, "Status": "default"},
        )

    def test_existing_policies_and_preferences_are_kept(self):
        existing = json.dumps(
            {
                "policies": {
                    "DisableTelemetry": True,
                    "Preferences": {"browser.tabs.warnOnClose": False},
                }
            }
        )
        policies = obs.obs_firefox_policies(existing)["policies"]
        self.assertTrue(policies["DisableTelemetry"])
        self.assertIs(policies["Preferences"]["browser.tabs.warnOnClose"], False)
        self.assertIn(self.PREF, policies["Preferences"])
        # Applying it again changes nothing.
        again = obs.obs_firefox_policies(json.dumps({"policies": policies}))
        self.assertEqual(again["policies"], policies)

    def test_malformed_policies_are_refused_not_replaced(self):
        for text in ("{", "[]", '{"policies": []}', '{"policies": {"Preferences": 1}}'):
            with self.subTest(text=text), self.assertRaises(AnsibleFilterError):
                obs.obs_firefox_policies(text)
        # Parsed data would skip the JSON validation: the role must pass text.
        with self.assertRaises(AnsibleFilterError):
            obs.obs_firefox_policies({"policies": {}})

    def run_play(self, work, firefox_installed=True):
        tasks = yaml.safe_load((ROLE / "tasks/firefox.yml").read_text())
        for task in tasks:
            for module in task.values():
                if isinstance(module, dict):
                    # The test runs unprivileged; root ownership is not testable.
                    module.pop("owner", None)
                    module.pop("group", None)
        binary = work / "firefox"
        if firefox_installed:
            binary.write_text("")
        play = work / "play.yml"
        play.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {
                            "obs_firefox_binary_path": str(binary),
                            "obs_firefox_policies_file": str(
                                work / "etc/firefox/policies/policies.json"
                            ),
                        },
                        "tasks": tasks,
                    }
                ]
            )
        )
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(play)],
            env=ansible_test_environment(work),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def test_role_merges_the_policy_once_and_keeps_other_policies(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            policies = work / "etc/firefox/policies/policies.json"
            policies.parent.mkdir(parents=True)
            policies.write_text('{"policies": {"DisableTelemetry": true}}\n')
            first = self.run_play(work)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            written = json.loads(policies.read_text())["policies"]
            self.assertTrue(written["DisableTelemetry"])
            self.assertIs(written["Preferences"][self.PREF]["Value"], False)
            second = self.run_play(work)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("changed=0", second.stdout)

    def test_role_stops_on_invalid_policies_and_leaves_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            policies = work / "etc/firefox/policies/policies.json"
            policies.parent.mkdir(parents=True)
            policies.write_text("{ not json")
            result = self.run_play(work)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not valid JSON", result.stdout)
            self.assertEqual(policies.read_text(), "{ not json")

    def test_nothing_is_written_without_firefox(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            result = self.run_play(work, firefox_installed=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((work / "etc").exists())


class DkmsHeadersTests(unittest.TestCase):
    def test_headers_follow_the_running_kernel_package(self):
        self.assertEqual(
            dotfiles.dkms_kernel_headers(
                ["obs-studio", "v4l2loopback-dkms"], "linux-zen"
            ),
            ["linux-zen-headers"],
        )

    def test_no_dkms_or_unknown_kernel_adds_nothing(self):
        self.assertEqual(dotfiles.dkms_kernel_headers(["obs-studio"], "linux"), [])
        for kernel in ("", None, "bad name"):
            with self.subTest(kernel=kernel):
                self.assertEqual(
                    dotfiles.dkms_kernel_headers(["nvidia-open-dkms"], kernel), []
                )


class PackageStateSelectionTests(unittest.TestCase):
    """A partial profile must not overwrite the workstation's saved groups."""

    WORKSTATION = ("01_base", "03_gtk", "08_intel_modern", "11_hyprland", "20_apps")

    def write_state(self, merge):
        reconcile = yaml.safe_load(
            (ROOT / "ansible/roles/packages/tasks/reconcile.yml").read_text()
        )
        persist = next(
            task
            for task in reconcile
            if task["name"] == "Persist managed package state"
        )
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            state = work / "state/arch-packages.json"
            previous = {
                "version": 1,
                "selected_groups": self.WORKSTATION,
                "owned_packages": ["yq"],
            }
            play = work / "play.yml"
            play.write_text(
                yaml.safe_dump(
                    [
                        {
                            "hosts": "localhost",
                            "connection": "local",
                            "gather_facts": False,
                            "vars": {
                                "packages_action": "install",
                                "packages_state_directory": str(state.parent),
                                "packages_state_path": str(state),
                                "packages_selected_groups": [
                                    "08_intel_modern",
                                    "22_obs",
                                ],
                                "packages_state_data": previous,
                                "packages_state_merge_selection": merge,
                                "packages_owned_after": ["obs-studio", "yq"],
                                "packages_final_inventory": ["obs-studio", "yq"],
                            },
                            "tasks": [persist],
                        }
                    ]
                )
            )
            result = subprocess.run(
                ["ansible-playbook", "-i", "localhost,", str(play)],
                env=ansible_test_environment(work),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(state.read_text())

    def test_obs_profile_adds_its_groups_to_the_saved_selection(self):
        saved = self.write_state(True)
        self.assertEqual(
            saved["selected_groups"], sorted([*self.WORKSTATION, "22_obs"])
        )
        self.assertEqual(saved["owned_packages"], ["obs-studio", "yq"])

    def test_full_run_still_records_exactly_its_selection(self):
        saved = self.write_state(False)
        self.assertEqual(saved["selected_groups"], ["08_intel_modern", "22_obs"])

    def test_obs_profile_enables_the_merge(self):
        play = yaml.safe_load((ROOT / "ansible/obs.yml").read_text())[0]
        self.assertIs(play["vars"]["packages_state_merge_selection"], True)
        defaults = yaml.safe_load(
            (ROOT / "ansible/roles/packages/defaults/main.yml").read_text()
        )
        self.assertIs(defaults["packages_state_merge_selection"], False)

    def test_merge_ignores_invalid_previous_state(self):
        for previous in (None, {}, {"selected_groups": "01_base"}):
            with self.subTest(previous=previous):
                self.assertEqual(
                    dotfiles.recorded_package_groups(["22_obs"], previous, True),
                    ["22_obs"],
                )


class DetectionScriptTests(unittest.TestCase):
    def test_render_nodes_report_driver_and_boot_gpu(self):
        with tempfile.TemporaryDirectory() as tmp:
            sys_root = Path(tmp)
            for node, driver, boot in (
                ("renderD128", "i915", "1"),
                ("renderD129", "nvidia", None),
            ):
                device = sys_root / "devices" / node
                (device).mkdir(parents=True)
                (sys_root / "bus" / driver).mkdir(parents=True, exist_ok=True)
                (device / "driver").symlink_to(sys_root / "bus" / driver)
                if boot:
                    (device / "boot_vga").write_text(boot + "\n")
                (sys_root / "class/drm").mkdir(parents=True, exist_ok=True)
                (sys_root / "class/drm" / node).mkdir()
                (sys_root / "class/drm" / node / "device").symlink_to(device)
            result = subprocess.run(
                ["sh", str(ROLE / "files/detect-render-nodes.sh"), str(sys_root)],
                capture_output=True,
                text=True,
                check=True,
            )
        self.assertEqual(result.stdout, HYBRID_LAPTOP_NODES)

    def test_camera_listing_prefers_by_id_then_by_path_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            dev, sys_root, bin_dir = work / "dev", work / "sys", work / "bin"
            for directory in (dev / "v4l/by-id", dev / "v4l/by-path", bin_dir):
                directory.mkdir(parents=True)
            for index, name in ((0, "Cam A"), (2, "Cam B")):
                (dev / f"video{index}").write_text("")
                names = sys_root / "class/video4linux" / f"video{index}"
                names.mkdir(parents=True)
                (names / "name").write_text(name + "\n")
            (dev / "v4l/by-path/usb-video-index0").symlink_to(dev / "video0")
            (dev / "v4l/by-id/usb-camb-video-index0").symlink_to(dev / "video2")
            (dev / "v4l/by-path/usb-camb-video-index0").symlink_to(dev / "video2")
            stub = bin_dir / "v4l2-ctl"
            stub.write_text('#!/bin/sh\nprintf "formats of %s\\n" "$3"\n')
            stub.chmod(0o755)
            result = subprocess.run(
                ["sh", str(ROLE / "files/list-cameras.sh"), str(dev), str(sys_root)],
                capture_output=True,
                text=True,
                check=True,
                env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
            )
        self.assertEqual(
            result.stdout,
            f"### {dev}/video0|{dev}/v4l/by-path/usb-video-index0|Cam A\n"
            f"formats of {dev}/video0\n"
            f"### {dev}/video2|{dev}/v4l/by-id/usb-camb-video-index0|Cam B\n"
            f"formats of {dev}/video2\n",
        )


class ConfigOwnershipTests(unittest.TestCase):
    """OBS rewrites its files on exit; the role must not undo the user's edits."""

    def run_config(self, work, force, obs_running=False):
        tasks = yaml.safe_load((ROLE / "tasks/config.yml").read_text())
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        play = work / "play.yml"
        play.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {
                            **defaults,
                            "obs_home": str(work / "home"),
                            "obs_config_force": force,
                            "obs_recording_directory": str(work / "home/Videos/OBS"),
                            "obs_encoder_settings": obs.obs_encoder_settings(
                                {"kind": "vaapi", "device": "/dev/dri/renderD128"}, True
                            ),
                            "obs_video_settings": obs.obs_video_settings(
                                obs.obs_select_monitor(HYBRID_LAPTOP_MONITORS),
                                1080,
                                True,
                            ),
                            "obs_webcam_settings": None,
                            "obs_webcam_filters": [],
                        },
                        "tasks": tasks,
                    }
                ]
            )
        )
        # A fake pgrep keeps the result independent of an OBS on the test host.
        bin_dir = work / "bin"
        bin_dir.mkdir(exist_ok=True)
        pgrep = bin_dir / "pgrep"
        pgrep.write_text(f"#!/bin/sh\nexit {0 if obs_running else 1}\n")
        pgrep.chmod(0o755)
        environment = ansible_test_environment(work)
        environment["PATH"] = f"{bin_dir}:{environment['PATH']}"
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(play)],
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def assert_ran(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_regeneration_is_refused_while_obs_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "templates").symlink_to(ROLE / "templates")
            result = self.run_config(work, True, obs_running=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("OBS is running", result.stdout)
            self.assertFalse((work / "home/.config/obs-studio/basic").exists())
            # Without force nothing is overwritten, so a running OBS is fine.
            self.assert_ran(self.run_config(work, False, obs_running=True))

    def test_former_demo_launcher_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "templates").symlink_to(ROLE / "templates")
            launcher = work / "home/.local/share/applications/obs-demo.desktop"
            launcher.parent.mkdir(parents=True)
            launcher.write_text("[Desktop Entry]\nExec=obs --startvirtualcam\n")
            self.assert_ran(self.run_config(work, False))
            self.assertFalse(launcher.exists())
            self.assertFalse((ROLE / "templates/obs-demo.desktop.j2").exists())

    def test_recording_keeps_the_canvas_and_streaming_encodes_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "templates").symlink_to(ROLE / "templates")
            self.assert_ran(self.run_config(work, False))
            profiles = work / "home/.config/obs-studio/basic/profiles"
            self.assertEqual(
                sorted(path.name for path in profiles.iterdir()),
                ["Enregistrement", "Streaming"],
            )
            record = (profiles / "Enregistrement/basic.ini").read_text()
            self.assertIn("OutputCX=2560\nOutputCY=1440\n", record)
            self.assertIn("RecEncoder=ffmpeg_vaapi_tex\n", record)
            stream = (profiles / "Streaming/basic.ini").read_text()
            self.assertIn("Name=Streaming\n", stream)
            self.assertIn("OutputCX=1920\nOutputCY=1080\n", stream)
            self.assertIn("Encoder=ffmpeg_vaapi_tex\n", stream)
            self.assertIn("RecEncoder=none\n", stream)
            settings = json.loads(
                (profiles / "Streaming/streamEncoder.json").read_text()
            )
            self.assertEqual(settings["rate_control"], "CBR")

    def test_each_palette_gets_its_own_scene_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "templates").symlink_to(ROLE / "templates")
            self.assert_ran(self.run_config(work, False))
            scenes = work / "home/.config/obs-studio/basic/scenes"
            self.assertEqual(
                sorted(path.name for path in scenes.iterdir()),
                ["Applis_Clair.json", "Applis_Gruvbox.json", "Applis_Sombre.json"],
            )
            gruvbox = json.loads((scenes / "Applis_Gruvbox.json").read_text())
            self.assertEqual(gruvbox["name"], "Applis - Gruvbox")
            sources = {source["name"]: source for source in gruvbox["sources"]}
            # OBS stores colours as opaque ABGR: #1D2021 -> 0xFF21201D.
            self.assertEqual(sources["Fond"]["settings"]["color"], 0xFF21201D)
            self.assertEqual(sources["Accent"]["settings"]["color"], 0xFF98A583)
            self.assertEqual(sources["Titre"]["settings"]["color1"], 0xFFB2DBEB)

    def test_files_are_created_once_then_left_to_obs_unless_forced(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            # The templates are resolved relative to the playbook directory.
            (work / "templates").symlink_to(ROLE / "templates")
            profile = work / "home/.config/obs-studio/basic/profiles/Enregistrement"
            scenes = work / "home/.config/obs-studio/basic/scenes/Applis_Sombre.json"

            self.assert_ran(self.run_config(work, False))
            basic = (profile / "basic.ini").read_text()
            self.assertIn("Name=Enregistrement", basic)
            self.assertIn("RecEncoder=ffmpeg_vaapi_tex", basic)
            self.assertIn("BaseCX=2560", basic)
            self.assertIn("FPSCommon=60", basic)
            self.assertIn(f"RecFilePath={work}/home/Videos/OBS", basic)
            record = json.loads((profile / "recordEncoder.json").read_text())
            self.assertEqual(record["vaapi_device"], "/dev/dri/renderD128")
            self.assertEqual(json.loads(scenes.read_text())["name"], "Applis - Sombre")
            self.assertTrue(scenes.read_text().endswith("}\n"))

            (profile / "basic.ini").write_text("edited in OBS\n")
            scenes.write_text('{"name": "edited in OBS"}\n')
            self.assert_ran(self.run_config(work, False))
            self.assertEqual((profile / "basic.ini").read_text(), "edited in OBS\n")
            self.assertEqual(scenes.read_text(), '{"name": "edited in OBS"}\n')

            self.assert_ran(self.run_config(work, True))
            self.assertEqual((profile / "basic.ini").read_text(), basic)
            backups = [
                path for path in profile.iterdir() if path.name.startswith("basic.ini.")
            ]
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), "edited in OBS\n")


class ProfileContractTests(unittest.TestCase):
    # Loading the packages role resolves community.general.pacman even when its
    # tasks are skipped by --tags.
    @unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
    def test_obs_profile_refuses_reconcile_before_any_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            result = subprocess.run(
                [
                    "ansible-playbook",
                    "-i",
                    "localhost,",
                    "-c",
                    "local",
                    str(ansible_tree(work) / "obs.yml"),
                    "-e",
                    "packages_action=reconcile",
                    "-e",
                    "ansible_become=false",
                    "--tags",
                    "always",
                ],
                env={
                    **ansible_test_environment(work),
                    "ANSIBLE_COLLECTIONS_PATH": str(COLLECTIONS),
                },
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "would treat every package outside 22_obs", result.stdout, result.stderr
        )

    def test_full_playbook_runs_the_obs_role_only_for_hosts_selecting_it(self):
        site = yaml.safe_load((ROOT / "ansible/site.yml").read_text())
        role = next(entry for entry in site[0]["roles"] if entry["role"] == "obs")
        self.assertIn("'22_obs' in", role["when"])
        with tempfile.TemporaryDirectory() as work:
            settings, _ = resolve_host_settings("PadsP5560", work)
        self.assertIn("22_obs", settings["packages_host_groups"])


if __name__ == "__main__":
    unittest.main()

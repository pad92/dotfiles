import os
import runpy
import tempfile
import unittest
from pathlib import Path

SCRIPT = runpy.run_path(
    str(
        Path(__file__).parents[1]
        / "ansible/roles/dotfiles/files/home/.bin/appimage-integrate.py"
    )
)
ArchiveEntry = SCRIPT["ArchiveEntry"]
ArchiveReader = SCRIPT["ArchiveReader"]
AppImageError = SCRIPT["AppImageError"]
integrate = SCRIPT["integrate"]
parse_7z_listing = SCRIPT["parse_7z_listing"]
replace_exec_program = SCRIPT["replace_exec_program"]
MAX_ICON_BYTES = SCRIPT["MAX_ICON_BYTES"]

PNG = b"\x89PNG\r\n\x1a\n" + b"pixels"
LISTING = """
Listing archive: App.AppImage

--
Path = App.AppImage
Type = SquashFS
Offset = 944632

----------
Path = .DirIcon
Folder = -
Mode = lrwxrwxrwx

Path = app.desktop
Size = 210
Folder = -
Mode = -rw-r--r--

Path = usr
Folder = +
Mode = drwxr-xr-x

Path = usr/bin/app
Folder = -
Mode = -rwxr-xr-x
"""


class FakeReader(ArchiveReader):
    """In-memory image: a value of type str is a symbolic link target."""

    def __init__(self, files: dict[str, bytes | str]) -> None:
        self.files = files
        self.reads: list[str] = []

    def entries(self):
        return {
            name: ArchiveEntry(
                is_dir=False, is_link=isinstance(value, str), size=len(value)
            )
            for name, value in self.files.items()
        }

    def read(self, name: str) -> bytes:
        self.reads.append(name)
        value = self.files[name]
        return value.encode() if isinstance(value, str) else value


def desktop(name: str, extra: str = "") -> bytes:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={name}\n"
        "Exec=AppRun --flag %U\n"
        "TryExec=AppRun\n"
        "Icon=app\n"
        "Actions=new;\n"
        f"{extra}"
        "\n[Desktop Action new]\n"
        "Name=New window\n"
        "Exec=app --new-window\n"
    ).encode()


class AppImageIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.source = root / "Applications"
        self.data = root / "data"
        self.source.mkdir()
        self.images: dict[Path, FakeReader] = {}

    def add(self, file_name: str, files: dict[str, bytes | str], mtime=1000):
        path = self.source / file_name
        path.write_bytes(b"\x7fELF")
        os.utime(path, (mtime, mtime))
        self.images[path] = FakeReader(files)
        return path

    def open_reader(self, path: Path):
        if path not in self.images:
            raise AppImageError("not an AppImage")
        return self.images[path]

    def run_integration(self) -> bool:
        return integrate(self.source, self.data, self.open_reader)

    def entry(self, entry_id: str) -> Path:
        return self.data / f"applications/appimage-{entry_id}.desktop"

    def test_parses_7z_technical_listing(self):
        entries = parse_7z_listing(LISTING)
        self.assertEqual(
            set(entries), {".DirIcon", "app.desktop", "usr", "usr/bin/app"}
        )
        self.assertTrue(entries[".DirIcon"].is_link)
        self.assertTrue(entries["usr"].is_dir)
        self.assertFalse(entries["app.desktop"].is_link)
        self.assertEqual(entries["app.desktop"].size, 210)
        self.assertIsNone(entries["usr"].size)

    def test_listing_without_files_is_an_error(self):
        with self.assertRaises(AppImageError):
            parse_7z_listing("7-Zip\nERROR: not an archive\n")

    def test_exec_program_is_replaced_and_arguments_kept(self):
        self.assertEqual(
            replace_exec_program('"/opt/my app" --x %F', "/home/u/A $1.AppImage"),
            # Quoted-argument escape, then the string-value escape: \\$.
            '"/home/u/A \\\\$1.AppImage" --x %F',
        )
        self.assertEqual(replace_exec_program("app", "/a.AppImage"), '"/a.AppImage"')

    def test_exec_percent_in_the_path_is_not_a_field_code(self):
        self.assertEqual(
            replace_exec_program("app %U", "/home/u/100%U.AppImage"),
            '"/home/u/100%%U.AppImage" %U',
        )

    def test_exec_env_prefix_is_kept(self):
        self.assertEqual(
            replace_exec_program("env GDK_BACKEND=x11 FOO= app %U", "/a.AppImage"),
            'env GDK_BACKEND=x11 FOO= "/a.AppImage" %U',
        )

    def test_writes_entry_pointing_at_appimage_and_copied_icon(self):
        appimage = self.add(
            "My-App-1.0-x86_64.AppImage",
            {"app.desktop": desktop("My App"), "app.png": PNG, "AppRun": b""},
        )
        self.assertTrue(self.run_integration())
        text = self.entry("app").read_text()
        icon = self.data / "icons/appimage/app.png"
        self.assertEqual(icon.read_bytes(), PNG)
        self.assertIn(f'Exec="{appimage}" --flag %U\n', text)
        self.assertIn(f'Exec="{appimage}" --new-window\n', text)
        self.assertIn(f"Icon={icon}\n", text)
        self.assertEqual(text.count("TryExec="), 1)
        self.assertIn(f"TryExec={appimage}\n", text)
        self.assertIn(f"X-AppImage-Integrate-Source={appimage}\n", text)
        # The extra keys belong to [Desktop Entry], before the action group.
        self.assertLess(text.index("TryExec="), text.index("[Desktop Action new]"))
        self.assertFalse(self.run_integration(), "a second run changes nothing")

    def test_dbus_activatable_is_dropped(self):
        self.add(
            "App.AppImage",
            {"app.desktop": desktop("App", "DBusActivatable=true\n")},
        )
        self.run_integration()
        self.assertNotIn("DBusActivatable", self.entry("app").read_text())

    def test_oversized_icon_is_not_read(self):
        path = self.add(
            "App.AppImage",
            {"app.desktop": desktop("App"), "app.png": PNG + bytes(MAX_ICON_BYTES)},
        )
        self.run_integration()
        self.assertNotIn("app.png", self.images[path].reads)
        self.assertIn("Icon=app\n", self.entry("app").read_text())

    def test_name_with_a_control_character_is_skipped(self):
        self.add("App\nNoDisplay=true.AppImage", {"app.desktop": desktop("App")})
        self.run_integration()
        self.assertFalse(self.entry("app").exists())

    def test_entry_of_an_appimage_outside_the_source_is_kept(self):
        self.add("App.AppImage", {"app.desktop": desktop("App")})
        other = self.source.parent / "Other"
        other.mkdir()
        appimage = other / "Tool.AppImage"
        appimage.write_bytes(b"\x7fELF")
        self.images[appimage] = FakeReader({"tool.desktop": desktop("Tool")})
        integrate(other, self.data, self.open_reader)
        self.run_integration()
        self.assertTrue(self.entry("tool").exists())
        self.assertTrue(self.entry("app").exists())
        appimage.unlink()
        self.run_integration()
        self.assertFalse(self.entry("tool").exists(), "gone AppImage, gone entry")

    def test_dangling_entry_link_does_not_stop_the_run(self):
        applications = self.data / "applications"
        applications.mkdir(parents=True)
        (applications / "appimage-gone.desktop").symlink_to(self.data / "missing")
        (applications / "broken.desktop").symlink_to(self.data / "missing")
        self.add("App.AppImage", {"app.desktop": desktop("App")})
        self.run_integration()
        self.assertTrue(self.entry("app").exists())

    def test_icon_falls_back_to_dir_icon_symlink(self):
        self.add(
            "App.AppImage",
            {
                "app.desktop": desktop("App"),
                ".DirIcon": "usr/share/icon",
                "usr/share/icon": PNG,
            },
        )
        self.run_integration()
        self.assertEqual((self.data / "icons/appimage/app.png").read_bytes(), PNG)

    def test_symlink_leaving_the_image_is_ignored(self):
        self.add(
            "App.AppImage",
            {"app.desktop": desktop("App"), ".DirIcon": "../../etc/passwd"},
        )
        self.run_integration()
        self.assertTrue(self.entry("app").exists())
        self.assertFalse((self.data / "icons/appimage").exists())
        self.assertIn("Icon=app\n", self.entry("app").read_text())

    def test_new_version_replaces_entry_and_removed_appimage_is_cleaned(self):
        old = self.add(
            "App-1.0.AppImage", {"app.desktop": desktop("App"), "app.png": PNG}
        )
        self.run_integration()
        old.unlink()
        del self.images[old]
        new = self.add(
            "App-2.0.AppImage", {"app.desktop": desktop("App"), "app.png": PNG}
        )
        self.run_integration()
        self.assertIn(f'Exec="{new}"', self.entry("app").read_text())
        new.unlink()
        del self.images[new]
        self.assertTrue(self.run_integration())
        self.assertFalse(self.entry("app").exists())
        self.assertEqual(list((self.data / "icons/appimage").iterdir()), [])

    def test_newest_copy_wins_when_two_share_an_id(self):
        self.add("App-1.0.AppImage", {"app.desktop": desktop("App")}, mtime=1000)
        newest = self.add(
            "App-2.0.AppImage", {"app.desktop": desktop("App")}, mtime=2000
        )
        self.run_integration()
        self.assertIn(f'Exec="{newest}"', self.entry("app").read_text())
        self.assertEqual(len(list((self.data / "applications").iterdir())), 1)

    def test_self_integrated_appimage_is_skipped_and_foreign_entries_kept(self):
        appimage = self.add("App.AppImage", {"app.desktop": desktop("App")})
        self.run_integration()
        foreign = self.data / "applications/appimagekit-app.desktop"
        foreign.write_text(
            f'[Desktop Entry]\nName=App\nExec="{appimage}" %U\n', encoding="utf-8"
        )
        unrelated = self.data / "applications/firefox.desktop"
        unrelated.write_text("[Desktop Entry]\nExec=firefox\n", encoding="utf-8")
        self.run_integration()
        self.assertFalse(self.entry("app").exists(), "no duplicate entry")
        self.assertTrue(foreign.exists())
        self.assertTrue(unrelated.exists())

    def test_foreign_entry_for_a_longer_path_does_not_skip(self):
        appimage = self.add("App.AppImage", {"app.desktop": desktop("App")})
        (self.data / "applications").mkdir(parents=True)
        (self.data / "applications/old.desktop").write_text(
            f"[Desktop Entry]\nExec={appimage}.old\n", encoding="utf-8"
        )
        self.run_integration()
        self.assertTrue(self.entry("app").exists())

    def test_unreadable_appimage_keeps_its_entry_and_others_proceed(self):
        appimage = self.add("App.AppImage", {"app.desktop": desktop("App")})
        self.run_integration()
        del self.images[appimage]  # a download in progress, for instance
        self.add("Other.AppImage", {"other.desktop": desktop("Other")})
        self.run_integration()
        self.assertTrue(self.entry("app").exists())
        self.assertTrue(self.entry("other").exists())

    def test_image_without_desktop_entry_is_skipped(self):
        self.add("Tool.AppImage", {"AppRun": b""})
        self.add("Lower.appimage", {"lower.desktop": desktop("Lower")})
        (self.source / "notes.txt").write_text("not an AppImage")
        self.run_integration()
        self.assertEqual(
            [path.name for path in (self.data / "applications").iterdir()],
            ["appimage-lower.desktop"],
        )

    def test_missing_source_directory_removes_generated_entries(self):
        self.add("App.AppImage", {"app.desktop": desktop("App")})
        self.run_integration()
        for path in self.source.iterdir():
            path.unlink()
        self.source.rmdir()
        self.run_integration()
        self.assertFalse(self.entry("app").exists())


if __name__ == "__main__":
    unittest.main()

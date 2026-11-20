#!/usr/bin/env python3
"""Add the AppImages of ~/Applications to the application menu.

For each *.AppImage, the desktop entry and the icon embedded in its SquashFS
image are copied to ~/.local/share/applications/appimage-<id>.desktop and
~/.local/share/icons/appimage/, with Exec and TryExec pointing at the AppImage.
The <id> is the name of the embedded desktop file, not the AppImage file name,
so a new version of an application replaces its entry instead of adding one.

The image is read with 7-Zip: an AppImage is never executed, so dropping a
file into the directory does not run its code.

Generated entries carry X-AppImage-Integrate-Source. An entry is deleted only
when that AppImage no longer exists, or when the same AppImage now produces
another entry. An AppImage that a desktop entry not written here already
launches (one that integrated itself) is skipped, to avoid a duplicate.
"""

from __future__ import annotations

import argparse
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

SOURCE_KEY = "X-AppImage-Integrate-Source"
ENTRY_PREFIX = "appimage-"
ICON_SUBDIRECTORY = "icons/appimage"
ICON_EXTENSIONS = (".png", ".svg", ".svgz", ".xpm")
MAX_DESKTOP_BYTES = 64 * 1024
MAX_ICON_BYTES = 4 * 1024 * 1024
MAX_LINK_HOPS = 8
SEVEN_ZIP_TIMEOUT_SECONDS = 120
SAFE_ID = re.compile(r"[^A-Za-z0-9._-]")
# Characters the desktop entry specification requires to be escaped inside a
# quoted Exec argument.
EXEC_RESERVED = re.compile(r'(["`$\\])')


class AppImageError(Exception):
    """The AppImage cannot be read or holds no usable desktop entry."""


@dataclass(frozen=True)
class ArchiveEntry:
    is_dir: bool
    is_link: bool


class ArchiveReader:
    """Read-only view of the SquashFS image inside an AppImage."""

    def entries(self) -> dict[str, ArchiveEntry]:
        raise NotImplementedError

    def read(self, name: str) -> bytes:
        raise NotImplementedError


def parse_7z_listing(text: str) -> dict[str, ArchiveEntry]:
    """Parse `7z l -slt` output into entries keyed by path inside the image."""
    _, separator, body = text.partition("\n----------\n")
    if not separator:
        raise AppImageError("7-Zip printed no file listing")
    entries: dict[str, ArchiveEntry] = {}
    for block in body.split("\n\n"):
        fields = dict(
            line.split(" = ", 1) for line in block.splitlines() if " = " in line
        )
        path = fields.get("Path")
        if not path:
            continue
        mode = fields.get("Mode", "")
        entries[path] = ArchiveEntry(
            is_dir=fields.get("Folder") == "+",
            is_link=mode.startswith("l"),
        )
    return entries


class SevenZipReader(ArchiveReader):
    def __init__(self, appimage: Path, seven_zip: str) -> None:
        self.appimage = appimage
        self.seven_zip = seven_zip
        self._entries: dict[str, ArchiveEntry] | None = None

    def _run(self, switches: list[str], names: list[str]) -> bytes:
        # -spd: names are literal paths, not wildcards. "--" ends the switches,
        # so a file name starting with "-" is not read as one.
        command = [self.seven_zip, *switches, "-tsquashfs", "-spd", "--"]
        command += [str(self.appimage), *names]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                timeout=SEVEN_ZIP_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as error:
            raise AppImageError("7-Zip timed out") from error
        if result.returncode != 0:
            message = result.stderr.decode(errors="replace").strip()
            raise AppImageError(f"7-Zip failed: {message or result.returncode}")
        return result.stdout

    def entries(self) -> dict[str, ArchiveEntry]:
        if self._entries is None:
            listing = self._run(["l", "-slt"], [])
            self._entries = parse_7z_listing(listing.decode(errors="replace"))
        return self._entries

    def read(self, name: str) -> bytes:
        return self._run(["e", "-so"], [name])


@dataclass(frozen=True)
class Integration:
    entry_id: str
    desktop: str
    icon_extension: str | None
    icon: bytes | None


def resolve_link(reader: ArchiveReader, name: str) -> str | None:
    """Follow symbolic links inside the image; None when it leaves the image."""
    entries = reader.entries()
    for _ in range(MAX_LINK_HOPS):
        entry = entries.get(name)
        if entry is None or entry.is_dir:
            return None
        if not entry.is_link:
            return name
        target = reader.read(name).decode(errors="replace").strip()
        if target.startswith("/"):
            return None
        name = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
        if name == ".." or name.startswith("../"):
            return None
    return None


def sniff_icon_extension(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    head = data[:512].lstrip()
    if head.startswith((b"<svg", b"<?xml")) and b"<svg" in data[:4096]:
        return ".svg"
    if data.startswith(b"\x1f\x8b"):
        return ".svgz"
    if data.startswith(b"/* XPM */"):
        return ".xpm"
    return None


def find_icon(reader: ArchiveReader, icon_name: str) -> tuple[str, bytes] | None:
    """Return (extension, bytes) of the icon the desktop entry names."""
    candidates = [icon_name + extension for extension in ICON_EXTENSIONS]
    if icon_name.endswith(ICON_EXTENSIONS):
        candidates.insert(0, icon_name)
    candidates.append(".DirIcon")
    for candidate in candidates:
        if "/" in candidate:
            continue
        resolved = resolve_link(reader, candidate)
        if resolved is None:
            continue
        data = reader.read(resolved)
        if not data or len(data) > MAX_ICON_BYTES:
            continue
        extension = posixpath.splitext(resolved)[1].lower()
        if extension not in ICON_EXTENSIONS:
            sniffed = sniff_icon_extension(data)
            if sniffed is None:
                continue
            extension = sniffed
        return extension, data
    return None


def quote_exec_argument(value: str) -> str:
    return '"' + EXEC_RESERVED.sub(r"\\\1", value) + '"'


def replace_exec_program(exec_value: str, program: str) -> str:
    """Swap the program of an Exec value, keeping its arguments and field codes."""
    value = exec_value.lstrip()
    if value.startswith('"'):
        index = 1
        while index < len(value):
            if value[index] == "\\":
                index += 2
                continue
            if value[index] == '"':
                break
            index += 1
        rest = value[index + 1 :]
    else:
        parts = value.split(None, 1)
        rest = " " + parts[1] if len(parts) == 2 else ""
    return quote_exec_argument(program) + rest


def rewrite_desktop(text: str, appimage: Path, icon_path: Path | None) -> str:
    """Point the embedded desktop entry at the AppImage and the copied icon."""
    lines: list[str] = []
    group = ""
    original_icon: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if group == "Desktop Entry":
                lines.extend(managed_keys(appimage))
            group = stripped[1:-1]
            lines.append(line)
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        in_launchable_group = group == "Desktop Entry" or group.startswith(
            "Desktop Action "
        )
        if separator and in_launchable_group:
            if key == "Exec":
                line = "Exec=" + replace_exec_program(value, str(appimage))
            elif key in ("TryExec", SOURCE_KEY):
                continue
            elif key == "Icon" and icon_path is not None:
                if group == "Desktop Entry":
                    original_icon = value.strip()
                    line = f"Icon={icon_path}"
                elif value.strip() == original_icon:
                    line = f"Icon={icon_path}"
        lines.append(line)
    if group == "Desktop Entry":
        lines.extend(managed_keys(appimage))
    return "\n".join(lines) + "\n"


def managed_keys(appimage: Path) -> list[str]:
    return [f"TryExec={appimage}", f"{SOURCE_KEY}={appimage}"]


def desktop_icon_name(text: str) -> str | None:
    group = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            group = stripped[1:-1]
            continue
        key, separator, value = line.partition("=")
        if group == "Desktop Entry" and separator and key.strip() == "Icon":
            return value.strip() or None
    return None


def read_integration(reader: ArchiveReader) -> Integration:
    """Extract the desktop entry and the icon embedded in one AppImage."""
    entries = reader.entries()
    desktops = sorted(
        name
        for name, entry in entries.items()
        if "/" not in name and name.endswith(".desktop") and not entry.is_dir
    )
    if not desktops:
        raise AppImageError("no desktop entry at the root of the image")
    resolved = resolve_link(reader, desktops[0])
    if resolved is None:
        raise AppImageError(f"{desktops[0]} does not resolve inside the image")
    data = reader.read(resolved)
    if len(data) > MAX_DESKTOP_BYTES:
        raise AppImageError(f"{desktops[0]} is larger than {MAX_DESKTOP_BYTES} bytes")
    try:
        desktop = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AppImageError(f"{desktops[0]} is not UTF-8") from error
    if "[Desktop Entry]" not in desktop:
        raise AppImageError(f"{desktops[0]} has no [Desktop Entry] group")
    entry_id = SAFE_ID.sub("_", desktops[0].removesuffix(".desktop"))
    icon_name = desktop_icon_name(desktop)
    icon = find_icon(reader, icon_name) if icon_name else None
    return Integration(
        entry_id=entry_id,
        desktop=desktop,
        icon_extension=icon[0] if icon else None,
        icon=icon[1] if icon else None,
    )


def write_if_changed(path: Path, data: bytes) -> bool:
    try:
        if path.read_bytes() == data:
            return False
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return True


def managed_source(path: Path) -> Path | None:
    """Return the AppImage a generated entry launches, None for other entries."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    prefix = SOURCE_KEY + "="
    for line in text.splitlines():
        if line.startswith(prefix):
            return Path(line[len(prefix) :])
    return None


def self_integrated(applications: Path, appimages: Iterable[Path]) -> set[Path]:
    """AppImages already launched by an entry this script did not write."""
    wanted = {str(path): path for path in appimages}
    found: set[Path] = set()
    for entry in applications.glob("*.desktop"):
        if not entry.is_file() or managed_source(entry) is not None:
            continue
        try:
            text = entry.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            key, separator, value = line.partition("=")
            if not separator or key.strip() not in ("Exec", "TryExec"):
                continue
            for name, path in wanted.items():
                # The path must end at a quote, a space or the end of the
                # value, so /a/App.AppImage does not match /a/App.AppImage.old.
                if re.search(re.escape(name) + r"(?=[\"'\s]|$)", value):
                    found.add(path)
    return found


def log(message: str) -> None:
    print(f"appimage-integrate: {message}", file=sys.stderr)


def integrate(
    source_directory: Path,
    data_home: Path,
    open_reader: Callable[[Path], ArchiveReader],
) -> bool:
    """Synchronise the generated entries; return whether anything changed."""
    applications = data_home / "applications"
    icons = data_home / ICON_SUBDIRECTORY
    try:
        appimages = sorted(
            path
            for path in source_directory.iterdir()
            if path.suffix.lower() == ".appimage" and path.is_file()
        )
    except FileNotFoundError:
        appimages = []

    skipped = (
        self_integrated(applications, appimages) if applications.is_dir() else set()
    )
    for path in sorted(skipped):
        log(f"{path.name}: launched by its own desktop entry, skipped")

    integrations: dict[str, tuple[Path, Integration]] = {}
    unreadable: set[Path] = set()
    for path in appimages:
        if path in skipped:
            continue
        try:
            integration = read_integration(open_reader(path))
        except AppImageError as error:
            log(f"{path.name}: {error}")
            unreadable.add(path)
            continue
        previous = integrations.get(integration.entry_id)
        # Two versions of one application: the newest file wins.
        if previous is None or path.stat().st_mtime > previous[0].stat().st_mtime:
            if previous is not None:
                log(
                    f"{previous[0].name}: older copy of {integration.entry_id}, ignored"
                )
            integrations[integration.entry_id] = (path, integration)
        else:
            log(f"{path.name}: older copy of {integration.entry_id}, ignored")

    changed = False
    written: set[Path] = set()
    kept_icons: set[Path] = set()
    for entry_id, (path, integration) in integrations.items():
        icon_path = None
        if integration.icon is not None and integration.icon_extension is not None:
            icon_path = icons / (entry_id + integration.icon_extension)
            changed |= write_if_changed(icon_path, integration.icon)
            kept_icons.add(icon_path)
        desktop = rewrite_desktop(integration.desktop, path, icon_path)
        target = applications / f"{ENTRY_PREFIX}{entry_id}.desktop"
        if write_if_changed(target, desktop.encode("utf-8")):
            log(f"{path.name}: wrote {target.name}")
            changed = True
        written.add(target)

    changed |= remove_stale(applications, icons, written, kept_icons, unreadable)
    return changed


def remove_stale(
    applications: Path,
    icons: Path,
    written: set[Path],
    kept_icons: set[Path],
    unreadable: set[Path],
) -> bool:
    """Delete generated entries that this run did not produce again.

    That covers a removed AppImage, one that now integrates itself, and an
    entry renamed by a new version. An entry whose AppImage is still there but
    unreadable (a download in progress, for instance) is kept.
    """
    changed = False
    kept_ids: set[str] = set()
    if not applications.is_dir():
        return False
    for entry in sorted(applications.glob(f"{ENTRY_PREFIX}*.desktop")):
        source = managed_source(entry)
        if source is None:
            continue
        entry_id = entry.name.removeprefix(ENTRY_PREFIX).removesuffix(".desktop")
        if entry in written or source in unreadable:
            kept_ids.add(entry_id)
            continue
        entry.unlink()
        log(f"removed {entry.name}")
        changed = True
    if icons.is_dir():
        for icon in icons.iterdir():
            if icon in kept_icons or icon.stem in kept_ids:
                continue
            if icon.suffix in ICON_EXTENSIONS and icon.is_file():
                icon.unlink()
                changed = True
    return changed


def refresh_desktop_database(applications: Path) -> None:
    program = shutil.which("update-desktop-database")
    if program is None or not applications.is_dir():
        return
    result = subprocess.run(
        [program, str(applications)], capture_output=True, check=False
    )
    if result.returncode != 0:
        log("update-desktop-database failed: " + result.stderr.decode(errors="replace"))


def default_data_home() -> Path:
    value = os.environ.get("XDG_DATA_HOME", "")
    return Path(value) if os.path.isabs(value) else Path.home() / ".local/share"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home() / "Applications",
        help="directory holding the AppImages (default: ~/Applications)",
    )
    parser.add_argument(
        "--data-home",
        type=Path,
        default=default_data_home(),
        help="XDG data directory receiving entries and icons",
    )
    arguments = parser.parse_args(argv)
    seven_zip = shutil.which("7z")
    if seven_zip is None:
        log("7z not found; install the 7zip package")
        return 1
    source = arguments.source.absolute()
    changed = integrate(
        source,
        arguments.data_home,
        lambda path: SevenZipReader(path, seven_zip),
    )
    if changed:
        refresh_desktop_database(arguments.data_home / "applications")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Prune generated wallpaper files while the caller holds the render lock."""

import argparse
import re
import stat
import sys
import time
from pathlib import Path

RENDER_NAME = re.compile(r"[0-9a-f]{64}\.jpg")
TEMPORARY_NAME = re.compile(r"\.awww-render\.[A-Za-z0-9]{6}\.jpg")


def prune_cache(
    directory: Path,
    carousel_directory: Path,
    max_bytes: int,
    max_age_seconds: int,
    protected_paths: list[Path],
) -> int:
    """Return retained bytes; active references may exceed the configured quota."""
    if directory.is_symlink():
        raise ValueError("render cache must not be a symlink")
    protected = {path.resolve() for path in protected_paths}
    references = list(carousel_directory.glob("current-*"))
    references.extend((directory / "pins").glob("awww-*"))
    for reference in references:
        if reference.is_symlink():
            protected.add(reference.resolve())

    entries = []
    total_bytes = 0
    cutoff = time.time() - max_age_seconds
    for path in directory.iterdir():
        # The caller owns the render lock, so no cooperating render is active.
        if (
            TEMPORARY_NAME.fullmatch(path.name)
            and path.is_file()
            and not path.is_symlink()
        ):
            path.unlink()
            continue
        if not RENDER_NAME.fullmatch(path.name):
            continue
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            continue
        entries.append((metadata.st_mtime, metadata.st_size, path))
        total_bytes += metadata.st_size

    for modified, size, path in sorted(entries):
        if path.resolve() in protected:
            continue
        if modified < cutoff or total_bytes > max_bytes:
            path.unlink()
            total_bytes -= size
    return total_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("carousel_directory", type=Path)
    parser.add_argument("--max-bytes", required=True, type=int)
    parser.add_argument("--max-age-days", required=True, type=int)
    parser.add_argument("--protect", type=Path, action="append", default=[])
    args = parser.parse_args()
    if args.max_bytes <= 0 or args.max_age_days <= 0:
        parser.error("cache limits must be positive")
    try:
        retained = prune_cache(
            args.directory,
            args.carousel_directory,
            args.max_bytes,
            args.max_age_days * 86400,
            args.protect,
        )
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Warning: Unable to prune wallpaper cache: {error}", file=sys.stderr)
        return 1
    if retained > args.max_bytes:
        print(
            "Warning: Active wallpaper images exceed the cache quota; "
            "their files were preserved.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

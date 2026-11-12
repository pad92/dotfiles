"""Inventory managed trees and move paths without replacing anything."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import stat


def snapshot(roots: list[str]) -> dict[str, tuple]:
    result: dict[str, tuple] = {}

    def visit(path: str) -> None:
        info = os.lstat(path)
        metadata = (info.st_mode, info.st_uid, info.st_gid, info.st_mtime_ns)
        if stat.S_ISLNK(info.st_mode):
            result[path] = (*metadata, os.readlink(path))
        elif stat.S_ISREG(info.st_mode):
            with open(path, "rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            result[path] = (*metadata, digest)
        elif stat.S_ISDIR(info.st_mode):
            result[path] = metadata
            with os.scandir(path) as entries:
                for entry in entries:
                    visit(entry.path)
        else:
            raise OSError(f"Cannot inventory special file: {path}")

    for root in roots:
        # Missing optional roots are valid; permission errors must propagate.
        try:
            os.lstat(root)
        except FileNotFoundError:
            continue
        visit(root)
        if os.path.islink(root):
            visit(os.path.realpath(root))
    return result


def changed_paths(before: dict, after: dict) -> list[str]:
    return sorted(
        path
        for path in before.keys() | after.keys()
        if before.get(path) != after.get(path)
    )


def move_without_replace(src: str, dest: str) -> None:
    """Rename src to dest atomically, failing if dest exists (renameat2)."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise OSError(errno.ENOSYS, "renameat2 is required; source left untouched")
    rename.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(src), -100, os.fsencode(dest), 1):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), dest)

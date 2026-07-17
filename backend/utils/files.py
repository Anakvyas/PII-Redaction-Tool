from __future__ import annotations

import hashlib
from pathlib import Path

from core.exceptions import UnsupportedFormatError


def sha256_of_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extension_of(filename: str) -> str:
    return Path(filename).suffix.lower()


def format_from_filename(filename: str, allowed: tuple[str, ...]) -> str:
    ext = extension_of(filename)
    if ext not in allowed:
        raise UnsupportedFormatError(
            f"Unsupported file type '{ext}'. Allowed types: {', '.join(allowed)}."
        )
    return ext.lstrip(".")

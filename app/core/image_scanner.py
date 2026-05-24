from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.utils.image_types import SUPPORTED_IMAGE_EXTENSIONS
from app.utils.long_path import display_path, filesystem_path, path_exists, path_is_dir, path_stat


@dataclass(frozen=True, slots=True)
class ImageFile:
    path: Path
    name: str
    suffix: str
    size: int
    mtime: float


def scan_image_files(folder_path: str | Path) -> list[ImageFile]:
    folder = display_path(folder_path)
    if not path_exists(folder):
        raise FileNotFoundError(f"Folder does not exist: {folder}")
    if not path_is_dir(folder):
        raise NotADirectoryError(f"Path is not a folder: {folder}")

    image_entries: list[tuple[Path, os.stat_result]] = []
    with os.scandir(filesystem_path(folder)) as entries:
        for entry in entries:
            path = folder / entry.name
            if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                continue
            if not entry.is_file():
                continue
            image_entries.append((path, entry.stat()))

    return [_to_image_file(path, stat) for path, stat in sorted(image_entries, key=lambda item: _natural_name_key(item[0]))]


def image_file_from_path(path: str | Path) -> ImageFile:
    return _to_image_file(display_path(path))


def _to_image_file(path: Path, stat: os.stat_result | None = None) -> ImageFile:
    stat = stat or path_stat(path)
    return ImageFile(
        path=path,
        name=path.name,
        suffix=path.suffix.lower(),
        size=stat.st_size,
        mtime=stat.st_mtime,
    )


def _natural_name_key(path: Path) -> tuple[tuple[int, object], ...]:
    parts: list[tuple[int, object]] = []
    current = ""
    for char in path.name.casefold():
        if char.isdigit() == (current[:1].isdigit() if current else char.isdigit()):
            current += char
            continue
        parts.append(_name_part_key(current))
        current = char
    if current:
        parts.append(_name_part_key(current))
    return tuple(parts)


def _name_part_key(value: str) -> tuple[int, object]:
    if value.isdigit():
        return (0, int(value))
    return (1, value)

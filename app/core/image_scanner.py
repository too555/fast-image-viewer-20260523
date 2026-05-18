from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.utils.image_types import is_supported_image_file


@dataclass(frozen=True, slots=True)
class ImageFile:
    path: Path
    name: str
    suffix: str
    size: int
    mtime: float


def scan_image_files(folder_path: str | Path) -> list[ImageFile]:
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {folder}")

    image_paths = [path for path in folder.iterdir() if is_supported_image_file(path)]
    return [_to_image_file(path) for path in sorted(image_paths, key=_natural_name_key)]


def _to_image_file(path: Path) -> ImageFile:
    stat = path.stat()
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

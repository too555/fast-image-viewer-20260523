from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.image_scanner import ImageFile
from app.utils.long_path import display_path, filesystem_path, make_dirs, path_exists

THUMBNAIL_SIZE = 128


@dataclass(frozen=True, slots=True)
class ThumbnailResult:
    index: int
    cache_path: Path | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.cache_path is not None and self.error is None


def default_cache_dir() -> Path:
    base_dir = os.environ.get("LOCALAPPDATA")
    if base_dir:
        return Path(base_dir) / "FastImageViewer" / "thumbnails"
    return Path.home() / ".fast_image_viewer" / "thumbnails"


def thumbnail_cache_path(
    image_file: ImageFile,
    thumbnail_size: int = THUMBNAIL_SIZE,
    cache_dir: Path | None = None,
) -> Path:
    cache_root = cache_dir or default_cache_dir()
    key_source = (
        f"{os.path.abspath(str(display_path(image_file.path)))}|"
        f"{image_file.mtime:.6f}|"
        f"{image_file.size}|"
        f"{thumbnail_size}"
    )
    cache_key = hashlib.sha1(key_source.encode("utf-8")).hexdigest()
    return cache_root / f"{cache_key}.bmp"


def ensure_thumbnail(
    index: int,
    image_file: ImageFile,
    thumbnail_size: int = THUMBNAIL_SIZE,
    cache_dir: Path | None = None,
) -> ThumbnailResult:
    cache_path = thumbnail_cache_path(image_file, thumbnail_size, cache_dir)
    if path_exists(cache_path):
        return ThumbnailResult(index=index, cache_path=cache_path)

    make_dirs(cache_path.parent)
    try:
        _create_thumbnail(image_file.path, cache_path, thumbnail_size)
    except (OSError, UnidentifiedImageError, ValueError) as error:
        return ThumbnailResult(index=index, cache_path=None, error=str(error))

    return ThumbnailResult(index=index, cache_path=cache_path)


def _create_thumbnail(source_path: Path, cache_path: Path, thumbnail_size: int) -> None:
    with Image.open(filesystem_path(source_path)) as image:
        if hasattr(image, "draft"):
            image.draft("RGB", (thumbnail_size, thumbnail_size))
        image = ImageOps.exif_transpose(image)
        image.thumbnail((thumbnail_size, thumbnail_size), Image.Resampling.LANCZOS)

        canvas = Image.new("RGB", (thumbnail_size, thumbnail_size), (246, 246, 246))
        left = (thumbnail_size - image.width) // 2
        top = (thumbnail_size - image.height) // 2

        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            rgba = image.convert("RGBA")
            canvas.paste(rgba, (left, top), rgba)
        else:
            canvas.paste(image.convert("RGB"), (left, top))

        canvas.save(filesystem_path(cache_path), format="BMP")

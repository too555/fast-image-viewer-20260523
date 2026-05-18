from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.image_scanner import ImageFile


@dataclass(frozen=True, slots=True)
class PreviewResult:
    cache_path: Path | None
    width: int = 0
    height: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.cache_path is not None and self.error is None


def default_preview_cache_dir() -> Path:
    base_dir = os.environ.get("LOCALAPPDATA")
    if base_dir:
        return Path(base_dir) / "FastImageViewer" / "previews"
    return Path.home() / ".fast_image_viewer" / "previews"


def fit_size(source_width: int, source_height: int, max_width: int, max_height: int) -> tuple[int, int]:
    if source_width <= 0 or source_height <= 0 or max_width <= 0 or max_height <= 0:
        return (0, 0)

    scale = min(max_width / source_width, max_height / source_height, 1.0)
    return (max(1, int(source_width * scale)), max(1, int(source_height * scale)))


def render_preview(
    image_file: ImageFile,
    max_width: int,
    max_height: int,
    cache_dir: Path | None = None,
) -> PreviewResult:
    if max_width <= 0 or max_height <= 0:
        return PreviewResult(cache_path=None, error="Preview area is too small")

    cache_path = _preview_cache_path(image_file, max_width, max_height, cache_dir)
    if cache_path.exists():
        try:
            with Image.open(cache_path) as cached:
                return PreviewResult(cache_path=cache_path, width=cached.width, height=cached.height)
        except (OSError, UnidentifiedImageError, ValueError):
            pass

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        width, height = _create_preview(image_file.path, cache_path, max_width, max_height)
    except (OSError, UnidentifiedImageError, ValueError) as error:
        return PreviewResult(cache_path=None, error=str(error))

    return PreviewResult(cache_path=cache_path, width=width, height=height)


def _preview_cache_path(
    image_file: ImageFile,
    max_width: int,
    max_height: int,
    cache_dir: Path | None = None,
) -> Path:
    cache_root = cache_dir or default_preview_cache_dir()
    key_source = (
        f"{image_file.path.resolve(strict=False)}|"
        f"{image_file.mtime:.6f}|"
        f"{image_file.size}|"
        f"{max_width}x{max_height}"
    )
    cache_key = hashlib.sha1(key_source.encode("utf-8")).hexdigest()
    return cache_root / f"{cache_key}.bmp"


def _create_preview(source_path: Path, cache_path: Path, max_width: int, max_height: int) -> tuple[int, int]:
    with Image.open(source_path) as image:
        if hasattr(image, "draft"):
            image.draft("RGB", (max_width, max_height))
        image = ImageOps.exif_transpose(image)
        target_size = fit_size(image.width, image.height, max_width, max_height)
        if target_size == (0, 0):
            raise ValueError("Image has invalid dimensions")

        image.thumbnail(target_size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", image.size, (246, 246, 246))
        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            rgba = image.convert("RGBA")
            canvas.paste(rgba, (0, 0), rgba)
        else:
            canvas.paste(image.convert("RGB"), (0, 0))

        canvas.save(cache_path, format="BMP")
        return canvas.size

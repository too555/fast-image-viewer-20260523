from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.image_scanner import ImageFile
from app.utils.long_path import display_path, filesystem_path, make_dirs, path_exists

PREVIEW_MODE_FIT_AREA = "fit_area"
PREVIEW_MODE_SCALE_50 = "scale_50"
PREVIEW_MODE_ORIGINAL = "original"
PREVIEW_MODE_SCALE_200 = "scale_200"
PREVIEW_MODE_FIT_HEIGHT = "fit_height"
FIXED_SCALE_FACTORS = {
    PREVIEW_MODE_SCALE_50: 0.5,
    PREVIEW_MODE_ORIGINAL: 1.0,
    PREVIEW_MODE_SCALE_200: 2.0,
}


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


def preview_size_for_mode(
    source_width: int,
    source_height: int,
    max_width: int,
    max_height: int,
    display_mode: str = PREVIEW_MODE_FIT_AREA,
) -> tuple[int, int]:
    if source_width <= 0 or source_height <= 0 or max_width <= 0 or max_height <= 0:
        return (0, 0)
    if display_mode in FIXED_SCALE_FACTORS:
        scale = FIXED_SCALE_FACTORS[display_mode]
        return (max(1, round(source_width * scale)), max(1, round(source_height * scale)))
    if display_mode == PREVIEW_MODE_FIT_HEIGHT:
        scale = max_height / source_height
        return (max(1, round(source_width * scale)), max(1, round(source_height * scale)))
    return fit_size(source_width, source_height, max_width, max_height)


def render_preview(
    image_file: ImageFile,
    max_width: int,
    max_height: int,
    cache_dir: Path | None = None,
    display_mode: str = PREVIEW_MODE_FIT_AREA,
) -> PreviewResult:
    if max_width <= 0 or max_height <= 0:
        return PreviewResult(cache_path=None, error="Preview area is too small")

    cache_path = _preview_cache_path(image_file, max_width, max_height, cache_dir, display_mode)
    if path_exists(cache_path):
        try:
            with Image.open(filesystem_path(cache_path)) as cached:
                return PreviewResult(cache_path=cache_path, width=cached.width, height=cached.height)
        except (OSError, UnidentifiedImageError, ValueError):
            pass

    make_dirs(cache_path.parent)
    try:
        width, height = _create_preview(image_file.path, cache_path, max_width, max_height, display_mode)
    except (OSError, UnidentifiedImageError, ValueError) as error:
        return PreviewResult(cache_path=None, error=str(error))

    return PreviewResult(cache_path=cache_path, width=width, height=height)


def _preview_cache_path(
    image_file: ImageFile,
    max_width: int,
    max_height: int,
    cache_dir: Path | None = None,
    display_mode: str = PREVIEW_MODE_FIT_AREA,
) -> Path:
    cache_root = cache_dir or default_preview_cache_dir()
    key_source = (
        f"{os.path.abspath(str(display_path(image_file.path)))}|"
        f"{image_file.mtime:.6f}|"
        f"{image_file.size}|"
        f"{max_width}x{max_height}|"
        f"{display_mode}"
    )
    cache_key = hashlib.sha1(key_source.encode("utf-8")).hexdigest()
    return cache_root / f"{cache_key}.bmp"


def _create_preview(
    source_path: Path,
    cache_path: Path,
    max_width: int,
    max_height: int,
    display_mode: str,
) -> tuple[int, int]:
    with Image.open(filesystem_path(source_path)) as image:
        if display_mode == PREVIEW_MODE_FIT_AREA and hasattr(image, "draft"):
            image.draft("RGB", (max_width, max_height))
        image = ImageOps.exif_transpose(image)
        target_size = preview_size_for_mode(image.width, image.height, max_width, max_height, display_mode)
        if target_size == (0, 0):
            raise ValueError("Image has invalid dimensions")

        if image.size != target_size:
            image = image.resize(target_size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", target_size, (246, 246, 246))
        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            rgba = image.convert("RGBA")
            canvas.paste(rgba, (0, 0), rgba)
        else:
            canvas.paste(image.convert("RGB"), (0, 0))

        canvas.save(filesystem_path(cache_path), format="BMP")
        return canvas.size

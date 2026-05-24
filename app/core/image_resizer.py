from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.image_scanner import ImageFile
from app.utils.long_path import display_path, filesystem_path, path_exists, path_is_dir

RESIZE_BASIS_WIDTH = "width"
RESIZE_BASIS_HEIGHT = "height"
RESIZE_SIZE_OPTIONS = (800, 1200, 1920)


@dataclass(frozen=True, slots=True)
class ResizeResult:
    output_path: Path
    width: int
    height: int


def resize_image_file(
    image_file: ImageFile,
    target_size: int,
    basis: str,
    output_folder: str | Path | None = None,
) -> ResizeResult:
    if target_size <= 0:
        raise ValueError("リサイズサイズが不正です")
    if basis not in {RESIZE_BASIS_WIDTH, RESIZE_BASIS_HEIGHT}:
        raise ValueError("リサイズ基準が不正です")

    source_path = display_path(image_file.path)
    if output_folder is not None and not path_is_dir(output_folder):
        raise ValueError("保存先フォルダが存在しません")
    output_path = next_resized_path(source_path, output_folder=output_folder)
    if output_path == source_path:
        raise ValueError("元画像と同じファイル名には保存できません")

    try:
        with Image.open(filesystem_path(source_path)) as image:
            image = ImageOps.exif_transpose(image)
            output_width, output_height = resized_dimensions(image.width, image.height, target_size, basis)
            resized = image.resize((output_width, output_height), Image.Resampling.LANCZOS)
            save_image = _prepare_image_for_extension(resized, output_path.suffix.lower())
            save_image.save(filesystem_path(output_path))
    except (OSError, UnidentifiedImageError, ValueError):
        raise

    return ResizeResult(output_path=output_path, width=output_width, height=output_height)


def resized_dimensions(source_width: int, source_height: int, target_size: int, basis: str) -> tuple[int, int]:
    if source_width <= 0 or source_height <= 0:
        raise ValueError("画像サイズが不正です")
    if target_size <= 0:
        raise ValueError("リサイズサイズが不正です")

    if basis == RESIZE_BASIS_WIDTH:
        return (target_size, max(1, round(source_height * target_size / source_width)))
    if basis == RESIZE_BASIS_HEIGHT:
        return (max(1, round(source_width * target_size / source_height)), target_size)
    raise ValueError("リサイズ基準が不正です")


def next_resized_path(source_path: str | Path, output_folder: str | Path | None = None) -> Path:
    source = display_path(source_path)
    destination_folder = display_path(output_folder) if output_folder is not None else source.parent
    stem = source.stem
    suffix = source.suffix
    first_candidate = destination_folder / f"{stem}_resized{suffix}"
    if not path_exists(first_candidate):
        return first_candidate

    index = 1
    while True:
        candidate = destination_folder / f"{stem}_resized_{index}{suffix}"
        if not path_exists(candidate):
            return candidate
        index += 1


def _prepare_image_for_extension(image: Image.Image, suffix: str) -> Image.Image:
    if suffix in {".jpg", ".jpeg", ".bmp"}:
        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            canvas = Image.new("RGB", image.size, (255, 255, 255))
            rgba = image.convert("RGBA")
            canvas.paste(rgba, (0, 0), rgba)
            return canvas
        return image.convert("RGB")
    return image

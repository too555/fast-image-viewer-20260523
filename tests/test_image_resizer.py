from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app.core.image_resizer import (
    RESIZE_BASIS_HEIGHT,
    RESIZE_BASIS_WIDTH,
    next_resized_path,
    resize_image_file,
    resized_dimensions,
)
from app.core.image_scanner import ImageFile


def _image_file(path: Path) -> ImageFile:
    stat = path.stat()
    return ImageFile(path=path, name=path.name, suffix=path.suffix.lower(), size=stat.st_size, mtime=stat.st_mtime)


class ImageResizerTest(unittest.TestCase):
    def test_width_basis_preserves_aspect_ratio(self) -> None:
        self.assertEqual(resized_dimensions(400, 200, 800, RESIZE_BASIS_WIDTH), (800, 400))

    def test_height_basis_preserves_aspect_ratio(self) -> None:
        self.assertEqual(resized_dimensions(400, 200, 800, RESIZE_BASIS_HEIGHT), (1600, 800))

    def test_resize_width_basis_saves_resized_copy_without_overwriting_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "photo.jpg"
            Image.new("RGB", (400, 200), (20, 80, 140)).save(source)
            original_bytes = source.read_bytes()

            result = resize_image_file(_image_file(source), 800, RESIZE_BASIS_WIDTH)

            self.assertEqual(result.output_path.name, "photo_resized.jpg")
            self.assertEqual((result.width, result.height), (800, 400))
            self.assertTrue(result.output_path.exists())
            self.assertEqual(source.read_bytes(), original_bytes)
            with Image.open(result.output_path) as resized:
                self.assertEqual(resized.size, (800, 400))
            with Image.open(source) as original:
                self.assertEqual(original.size, (400, 200))

    def test_resize_height_basis_saves_resized_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "photo.png"
            Image.new("RGB", (400, 200), (20, 80, 140)).save(source)

            result = resize_image_file(_image_file(source), 1200, RESIZE_BASIS_HEIGHT)

            self.assertEqual(result.output_path.name, "photo_resized.png")
            self.assertEqual((result.width, result.height), (2400, 1200))
            with Image.open(result.output_path) as resized:
                self.assertEqual(resized.size, (2400, 1200))

    def test_next_resized_path_avoids_duplicate_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "photo.jpg"
            source.write_bytes(b"source")
            (Path(temp) / "photo_resized.jpg").write_bytes(b"existing")
            (Path(temp) / "photo_resized_1.jpg").write_bytes(b"existing")

            self.assertEqual(next_resized_path(source), Path(temp) / "photo_resized_2.jpg")

    def test_resize_can_save_to_selected_output_folder_without_overwriting_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source_folder = Path(temp) / "source"
            output_folder = Path(temp) / "output"
            source_folder.mkdir()
            output_folder.mkdir()
            source = source_folder / "photo.jpg"
            Image.new("RGB", (400, 200), (20, 80, 140)).save(source)
            original_bytes = source.read_bytes()
            (output_folder / "photo_resized.jpg").write_bytes(b"existing")

            result = resize_image_file(_image_file(source), 800, RESIZE_BASIS_WIDTH, output_folder)

            self.assertEqual(result.output_path, output_folder / "photo_resized_1.jpg")
            self.assertTrue(result.output_path.exists())
            self.assertEqual(source.read_bytes(), original_bytes)

    def test_next_resized_path_uses_selected_output_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source" / "photo.png"
            output_folder = Path(temp) / "output"
            source.parent.mkdir()
            output_folder.mkdir()
            source.write_bytes(b"source")

            self.assertEqual(next_resized_path(source, output_folder), output_folder / "photo_resized.png")


if __name__ == "__main__":
    unittest.main()

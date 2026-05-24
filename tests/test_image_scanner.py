from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.image_scanner import scan_image_files
from app.utils.long_path import filesystem_path


class ScanImageFilesTest(unittest.TestCase):
    def test_only_returns_supported_files_in_natural_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            for name in ["image10.jpg", "image2.PNG", "note.txt", "photo.webp", "animation.gif"]:
                (folder / name).write_text("dummy", encoding="utf-8")

            result = scan_image_files(folder)

            self.assertEqual(
                [image_file.name for image_file in result],
                ["animation.gif", "image2.PNG", "image10.jpg", "photo.webp"],
            )

    def test_empty_folder_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = scan_image_files(temp_dir)

            self.assertEqual(result, [])

    def test_extended_prefix_input_keeps_internal_path_unprefixed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            (folder / "image1.jpg").write_text("dummy", encoding="utf-8")

            result = scan_image_files(filesystem_path(folder))

            self.assertEqual(result[0].path, folder / "image1.jpg")


if __name__ == "__main__":
    unittest.main()

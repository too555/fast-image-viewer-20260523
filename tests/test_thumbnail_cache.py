from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app.core.image_scanner import scan_image_files
from app.core.thumbnail_cache import THUMBNAIL_SIZE, ensure_thumbnail


class ThumbnailCacheTest(unittest.TestCase):
    def test_generates_fixed_size_cached_bitmap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source = folder / "large.jpg"
            Image.new("RGB", (1200, 800), (40, 120, 210)).save(source)
            image_file = scan_image_files(folder)[0]

            result = ensure_thumbnail(0, image_file, cache_dir=folder / "cache")

            self.assertTrue(result.ok)
            self.assertFalse(result.cache_hit)
            self.assertIsNotNone(result.cache_path)
            with Image.open(result.cache_path) as thumbnail:
                self.assertEqual(thumbnail.size, (THUMBNAIL_SIZE, THUMBNAIL_SIZE))

            cached_result = ensure_thumbnail(0, image_file, cache_dir=folder / "cache")

            self.assertTrue(cached_result.ok)
            self.assertTrue(cached_result.cache_hit)
            self.assertEqual(cached_result.cache_path, result.cache_path)

    def test_generates_requested_thumbnail_sizes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source = folder / "wide.jpg"
            Image.new("RGB", (800, 300), (160, 80, 40)).save(source)
            image_file = scan_image_files(folder)[0]

            for thumbnail_size in (64, 96, 128, 160, 256):
                result = ensure_thumbnail(0, image_file, thumbnail_size=thumbnail_size, cache_dir=folder / "cache")

                self.assertTrue(result.ok)
                self.assertIsNotNone(result.cache_path)
                with Image.open(result.cache_path) as thumbnail:
                    self.assertEqual(thumbnail.size, (thumbnail_size, thumbnail_size))

    def test_returns_failure_for_invalid_image_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source = folder / "broken.png"
            source.write_text("not an image", encoding="utf-8")
            image_file = scan_image_files(folder)[0]

            result = ensure_thumbnail(0, image_file, cache_dir=folder / "cache")

            self.assertFalse(result.ok)
            self.assertIsNone(result.cache_path)
            self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()

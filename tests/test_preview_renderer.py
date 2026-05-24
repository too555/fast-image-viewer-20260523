from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app.core.image_scanner import scan_image_files
from app.core.preview_renderer import (
    PREVIEW_MODE_FIT_HEIGHT,
    PREVIEW_MODE_ORIGINAL,
    PREVIEW_MODE_SCALE_50,
    PREVIEW_MODE_SCALE_200,
    fit_size,
    preview_size_for_mode,
    render_preview,
)


class PreviewRendererTest(unittest.TestCase):
    def test_fit_size_never_upscales_and_preserves_ratio(self) -> None:
        self.assertEqual(fit_size(1200, 800, 300, 300), (300, 200))
        self.assertEqual(fit_size(80, 40, 300, 300), (80, 40))

    def test_preview_size_modes(self) -> None:
        self.assertEqual(preview_size_for_mode(1200, 600, 320, 220, PREVIEW_MODE_SCALE_50), (600, 300))
        self.assertEqual(preview_size_for_mode(1200, 600, 320, 220, PREVIEW_MODE_ORIGINAL), (1200, 600))
        self.assertEqual(preview_size_for_mode(1200, 600, 320, 220, PREVIEW_MODE_SCALE_200), (2400, 1200))
        self.assertEqual(preview_size_for_mode(1200, 600, 320, 220, PREVIEW_MODE_FIT_HEIGHT), (440, 220))

    def test_renders_preview_inside_requested_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source = folder / "wide.jpg"
            Image.new("RGB", (1200, 600), (80, 130, 180)).save(source)
            image_file = scan_image_files(folder)[0]

            result = render_preview(image_file, 320, 220, cache_dir=folder / "cache")

            self.assertTrue(result.ok)
            self.assertIsNotNone(result.cache_path)
            self.assertLessEqual(result.width, 320)
            self.assertLessEqual(result.height, 220)
            with Image.open(result.cache_path) as preview:
                self.assertEqual(preview.size, (result.width, result.height))

    def test_renders_original_size_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source = folder / "small.jpg"
            Image.new("RGB", (120, 80), (80, 130, 180)).save(source)
            image_file = scan_image_files(folder)[0]

            result = render_preview(image_file, 40, 40, cache_dir=folder / "cache", display_mode=PREVIEW_MODE_ORIGINAL)

            self.assertTrue(result.ok)
            self.assertEqual((result.width, result.height), (120, 80))

    def test_returns_failure_for_broken_image(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source = folder / "broken.png"
            source.write_text("not an image", encoding="utf-8")
            image_file = scan_image_files(folder)[0]

            result = render_preview(image_file, 320, 220, cache_dir=folder / "cache")

            self.assertFalse(result.ok)
            self.assertIsNone(result.cache_path)
            self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()

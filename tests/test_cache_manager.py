from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from app.core.cache_manager import cache_stats, cleanup_cache, clear_cache


def _write_cache_file(path: Path, size: int, age_seconds: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    timestamp = time.time() - age_seconds
    os.utime(path, (timestamp, timestamp))


class CacheManagerTest(unittest.TestCase):
    def test_cache_stats_counts_thumbnail_and_preview_bmp_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            thumbnails = root / "thumbnails"
            previews = root / "previews"
            _write_cache_file(thumbnails / "thumb.bmp", 10, 10)
            _write_cache_file(previews / "preview.bmp", 20, 20)
            _write_cache_file(previews / "ignored.txt", 30, 30)

            stats = cache_stats(thumbnails, previews)

        self.assertEqual(stats.thumbnails_bytes, 10)
        self.assertEqual(stats.previews_bytes, 20)
        self.assertEqual(stats.total_bytes, 30)
        self.assertEqual(stats.total_files, 2)

    def test_cleanup_cache_deletes_old_previews_before_thumbnails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            thumbnails = root / "thumbnails"
            previews = root / "previews"
            old_preview = previews / "old_preview.bmp"
            new_preview = previews / "new_preview.bmp"
            thumbnail = thumbnails / "thumbnail.bmp"
            _write_cache_file(old_preview, 60, 300)
            _write_cache_file(new_preview, 60, 200)
            _write_cache_file(thumbnail, 60, 100)

            result = cleanup_cache(100, thumbnails, previews)
            stats = cache_stats(thumbnails, previews)

            self.assertFalse(old_preview.exists())
            self.assertFalse(new_preview.exists())
            self.assertTrue(thumbnail.exists())
            self.assertEqual(result.deleted_files, 2)
            self.assertEqual(stats.total_bytes, 60)

    def test_clear_cache_deletes_only_cache_bmp_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            thumbnails = root / "thumbnails"
            previews = root / "previews"
            settings = root / "settings.json"
            original = root / "original.jpg"
            _write_cache_file(thumbnails / "thumb.bmp", 10, 10)
            _write_cache_file(previews / "compare_diff" / "preview.bmp", 20, 20)
            _write_cache_file(previews / "not-cache.txt", 30, 30)
            settings.write_text("{}", encoding="utf-8")
            original.write_bytes(b"original")

            result = clear_cache(thumbnails, previews)
            stats = cache_stats(thumbnails, previews)

            self.assertEqual(result.deleted_files, 2)
            self.assertEqual(stats.total_bytes, 0)
            self.assertTrue(settings.exists())
            self.assertTrue(original.exists())
            self.assertTrue((previews / "not-cache.txt").exists())

    def test_unexpected_cache_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with self.assertRaises(ValueError):
                clear_cache(root / "images", root / "previews")


if __name__ == "__main__":
    unittest.main()

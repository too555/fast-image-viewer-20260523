from __future__ import annotations

import unittest
from pathlib import Path

from app.core.image_scanner import ImageFile
from app.core.thumbnail_cache import ThumbnailResult
from app.ui.main_window import MainWindow, THUMBNAIL_DRAIN_BATCH_SIZE


def _items(count: int) -> list[ImageFile]:
    return [
        ImageFile(
            path=Path(f"image_{index}.jpg"),
            name=f"image_{index}.jpg",
            suffix=".jpg",
            size=100,
            mtime=1.0,
        )
        for index in range(count)
    ]


class ThumbnailPrefetchPriorityTest(unittest.TestCase):
    def test_prioritizes_indexes_inside_visible_range(self) -> None:
        window = MainWindow()
        pending = {0, 10, 20, 24, 29, 40}

        window._set_thumbnail_priority_range(20, 30)

        self.assertEqual(window._next_thumbnail_index(pending), 24)

    def test_uses_nearest_index_when_visible_range_is_missing(self) -> None:
        window = MainWindow()
        pending = {4, 2, 9}

        window._set_thumbnail_priority_range(0, 0)

        self.assertEqual(window._next_thumbnail_index(pending), 2)

    def test_thumbnail_queue_drain_is_batched_for_large_folders(self) -> None:
        window = MainWindow()
        window._load_id = 1
        window._thumbnail_total = THUMBNAIL_DRAIN_BATCH_SIZE + 5
        window.thumbnail_grid.set_items(_items(window._thumbnail_total))
        for index in range(window._thumbnail_total):
            window._thumbnail_queue.put((1, ThumbnailResult(index=index, cache_path=Path(f"cache_{index}.bmp"))))

        window._drain_thumbnail_queue()

        self.assertEqual(window._thumbnail_done, THUMBNAIL_DRAIN_BATCH_SIZE)
        self.assertEqual(window._thumbnail_queue.qsize(), 5)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from app.ui.main_window import MainWindow


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


if __name__ == "__main__":
    unittest.main()

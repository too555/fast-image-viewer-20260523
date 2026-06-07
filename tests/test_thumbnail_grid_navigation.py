from __future__ import annotations

import unittest
from pathlib import Path

from app.core.image_scanner import ImageFile
from app.ui import thumbnail_grid
from app.ui.thumbnail_grid import RECT, ThumbnailGrid, _rects_intersect


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


class ThumbnailGridNavigationTest(unittest.TestCase):
    def test_page_navigation_moves_by_visible_rows_and_columns(self) -> None:
        grid = ThumbnailGrid()
        grid._client_width = lambda: 400  # type: ignore[method-assign]
        grid._client_height = lambda: 430  # type: ignore[method-assign]
        grid.set_items(_items(20))

        grid.select_index(0)

        self.assertTrue(grid.select_page(1))
        self.assertEqual(grid.selected_index, 4)
        self.assertTrue(grid.select_page(1))
        self.assertEqual(grid.selected_index, 8)
        self.assertTrue(grid.select_page(-1))
        self.assertEqual(grid.selected_index, 4)

    def test_page_navigation_stops_at_edges(self) -> None:
        grid = ThumbnailGrid()
        grid._client_width = lambda: 400  # type: ignore[method-assign]
        grid._client_height = lambda: 430  # type: ignore[method-assign]
        grid.set_items(_items(20))

        grid.select_index(18)
        grid.select_page(1)
        self.assertEqual(grid.selected_index, 19)

        grid.select_index(1)
        grid.select_page(-1)
        self.assertEqual(grid.selected_index, 0)

    def test_page_navigation_uses_current_thumbnail_size(self) -> None:
        grid = ThumbnailGrid()
        grid._client_width = lambda: 340  # type: ignore[method-assign]
        grid._client_height = lambda: 280  # type: ignore[method-assign]
        grid.set_items(_items(20))
        grid.set_thumbnail_size(64)

        grid.select_index(2)
        grid.select_page(1)

        self.assertEqual(grid.selected_index, 8)

    def test_page_navigation_handles_empty_items(self) -> None:
        grid = ThumbnailGrid()

        self.assertFalse(grid.select_page(1))
        self.assertIsNone(grid.selected_index)

    def test_visible_index_range_includes_nearby_rows(self) -> None:
        grid = ThumbnailGrid()
        grid._client_width = lambda: 400  # type: ignore[method-assign]
        grid._client_height = lambda: 430  # type: ignore[method-assign]
        grid.set_items(_items(30))
        grid.scroll_y = grid._cell_height() * 3

        self.assertEqual(grid.visible_index_range(extra_rows=1), (4, 14))

    def test_index_near_visible_tracks_virtual_scroll_window(self) -> None:
        grid = ThumbnailGrid()
        grid._client_width = lambda: 400  # type: ignore[method-assign]
        grid._client_height = lambda: 430  # type: ignore[method-assign]
        grid.set_items(_items(100))
        grid.scroll_y = grid._cell_height() * 10

        start, end = grid.visible_index_range(extra_rows=1)

        self.assertTrue(grid._is_index_near_visible(start, extra_rows=1))
        self.assertFalse(grid._is_index_near_visible(start - 1, extra_rows=1))
        self.assertFalse(grid._is_index_near_visible(end, extra_rows=1))

    def test_bitmap_cache_limit_is_bounded_to_visible_window(self) -> None:
        grid = ThumbnailGrid()
        grid._client_width = lambda: 400  # type: ignore[method-assign]
        grid._client_height = lambda: 430  # type: ignore[method-assign]
        grid.set_items(_items(10000))
        grid.scroll_y = grid._cell_height() * 1000

        start, end = grid.visible_index_range(extra_rows=thumbnail_grid.BITMAP_CACHE_EXTRA_ROWS)

        self.assertEqual(grid._bitmap_cache_limit(), max(24, min(thumbnail_grid.MAX_BITMAP_CACHE, end - start)))
        self.assertLess(grid._bitmap_cache_limit(), len(grid.items))

    def test_visible_range_callback_prefetches_scroll_surroundings(self) -> None:
        grid = ThumbnailGrid()
        grid._client_width = lambda: 400  # type: ignore[method-assign]
        grid._client_height = lambda: 430  # type: ignore[method-assign]
        grid.set_items(_items(100))
        grid.scroll_y = grid._cell_height() * 10
        reported: list[tuple[int, int]] = []
        grid.on_visible_range_changed = lambda start, end: reported.append((start, end))  # type: ignore[method-assign]

        grid._notify_visible_range_changed()

        self.assertEqual(reported[-1], grid.visible_index_range(extra_rows=thumbnail_grid.PREFETCH_EXTRA_ROWS))

    def test_set_thumbnail_reports_only_real_cell_changes(self) -> None:
        grid = ThumbnailGrid()
        grid.set_items(_items(2))
        cache_path = Path("cache-image.bmp")

        self.assertTrue(grid.set_thumbnail(0, cache_path))
        self.assertFalse(grid.set_thumbnail(0, cache_path))
        self.assertEqual(grid.thumbnails[0], cache_path)

        self.assertTrue(grid.set_thumbnail(1, None, failed=True))
        self.assertFalse(grid.set_thumbnail(1, None, failed=True))
        self.assertIn(1, grid.failed_indexes)

    def test_item_rect_tracks_grid_position_and_scroll(self) -> None:
        grid = ThumbnailGrid()
        grid._client_width = lambda: 400  # type: ignore[method-assign]
        grid.set_items(_items(6))

        rect = grid._item_rect(3)
        self.assertIsNotNone(rect)
        assert rect is not None
        self.assertGreater(rect.right, rect.left)
        self.assertGreater(rect.bottom, rect.top)

        grid.scroll_y = grid._cell_height()
        scrolled_rect = grid._item_rect(3)
        self.assertIsNotNone(scrolled_rect)
        assert scrolled_rect is not None
        self.assertEqual(scrolled_rect.top, rect.top - grid._cell_height())

    def test_context_menu_reports_item_under_pointer(self) -> None:
        grid = ThumbnailGrid()
        grid._client_width = lambda: 400  # type: ignore[method-assign]
        grid.set_items(_items(3))
        reported: list[ImageFile | None] = []
        grid.on_context_menu = lambda _hwnd, _x, _y, item: reported.append(item)  # type: ignore[method-assign]

        grid._handle_context_menu(20, 20)

        self.assertEqual(reported, [grid.items[0]])

    def test_context_menu_reports_none_for_blank_area(self) -> None:
        grid = ThumbnailGrid()
        grid._client_width = lambda: 400  # type: ignore[method-assign]
        grid.set_items(_items(1))
        reported: list[ImageFile | None] = []
        grid.on_context_menu = lambda _hwnd, _x, _y, item: reported.append(item)  # type: ignore[method-assign]

        grid._handle_context_menu(390, 20)

        self.assertEqual(reported, [None])

    def test_copy_shortcut_callbacks_require_ctrl_and_shift(self) -> None:
        original_ctrl_pressed = thumbnail_grid._ctrl_pressed
        original_shift_pressed = thumbnail_grid._shift_pressed
        grid = ThumbnailGrid()
        calls: list[str] = []
        grid.on_copy_image_path = lambda: calls.append("image")
        grid.on_copy_folder_path = lambda: calls.append("folder")

        try:
            thumbnail_grid._ctrl_pressed = lambda: True  # type: ignore[assignment]
            thumbnail_grid._shift_pressed = lambda: True  # type: ignore[assignment]

            self.assertTrue(grid._handle_copy_shortcut(thumbnail_grid.VK_C))
            self.assertTrue(grid._handle_copy_shortcut(thumbnail_grid.VK_F))

            thumbnail_grid._shift_pressed = lambda: False  # type: ignore[assignment]
            self.assertFalse(grid._handle_copy_shortcut(thumbnail_grid.VK_C))
        finally:
            thumbnail_grid._ctrl_pressed = original_ctrl_pressed
            thumbnail_grid._shift_pressed = original_shift_pressed

        self.assertEqual(calls, ["image", "folder"])

    def test_ctrl_mouse_wheel_changes_thumbnail_size_instead_of_image(self) -> None:
        original_ctrl_pressed = thumbnail_grid._ctrl_pressed
        grid = ThumbnailGrid()
        calls: list[str] = []
        moves: list[str] = []
        grid.on_thumbnail_size_increase = lambda: calls.append("increase")
        grid.on_thumbnail_size_decrease = lambda: calls.append("decrease")
        grid.on_previous = lambda: moves.append("previous")
        grid.on_next = lambda: moves.append("next")

        try:
            thumbnail_grid._ctrl_pressed = lambda: True  # type: ignore[assignment]
            grid.handle_message(0, thumbnail_grid.WM_MOUSEWHEEL, 120 << 16, 0)
            grid.handle_message(0, thumbnail_grid.WM_MOUSEWHEEL, (-120 & 0xFFFF) << 16, 0)
        finally:
            thumbnail_grid._ctrl_pressed = original_ctrl_pressed

        self.assertEqual(calls, ["increase", "decrease"])
        self.assertEqual(moves, [])

    def test_mouse_wheel_without_ctrl_scrolls_thumbnail_list(self) -> None:
        original_ctrl_pressed = thumbnail_grid._ctrl_pressed
        grid = ThumbnailGrid()
        grid._client_width = lambda: 400  # type: ignore[method-assign]
        grid._client_height = lambda: 430  # type: ignore[method-assign]
        grid.set_items(_items(100))
        calls: list[str] = []
        moves: list[str] = []
        grid.on_thumbnail_size_increase = lambda: calls.append("increase")
        grid.on_thumbnail_size_decrease = lambda: calls.append("decrease")
        grid.on_previous = lambda: moves.append("previous")
        grid.on_next = lambda: moves.append("next")

        try:
            thumbnail_grid._ctrl_pressed = lambda: False  # type: ignore[assignment]
            grid.scroll_y = grid._cell_height()
            grid.handle_message(0, thumbnail_grid.WM_MOUSEWHEEL, 120 << 16, 0)
            self.assertEqual(grid.scroll_y, 0)
            grid.handle_message(0, thumbnail_grid.WM_MOUSEWHEEL, (-120 & 0xFFFF) << 16, 0)
            self.assertEqual(grid.scroll_y, grid._cell_height())
        finally:
            thumbnail_grid._ctrl_pressed = original_ctrl_pressed

        self.assertEqual(calls, [])
        self.assertEqual(moves, [])

    def test_rect_intersection_matches_paint_clip_expectations(self) -> None:
        self.assertTrue(_rects_intersect(RECT(0, 0, 10, 10), RECT(5, 5, 15, 15)))
        self.assertFalse(_rects_intersect(RECT(0, 0, 10, 10), RECT(10, 10, 20, 20)))


if __name__ == "__main__":
    unittest.main()

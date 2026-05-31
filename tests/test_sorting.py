from __future__ import annotations

import unittest
from pathlib import Path

from app.core.image_scanner import ImageFile
from app.ui import main_window
from app.ui.main_window import MainWindow


def _image_file(name: str, mtime: float, size: int = 100) -> ImageFile:
    return ImageFile(
        path=Path(f"C:/images/{name}"),
        name=name,
        suffix=Path(name).suffix.lower(),
        size=size,
        mtime=mtime,
    )


class SortingTest(unittest.TestCase):
    def test_sorts_by_natural_file_name(self) -> None:
        window = MainWindow()
        items = [
            _image_file("image10.jpg", 3),
            _image_file("image2.jpg", 2),
            _image_file("image1.jpg", 1),
        ]

        self.assertEqual(
            [item.name for item in window._sorted_image_files(items)],
            ["image1.jpg", "image2.jpg", "image10.jpg"],
        )

        window.sort_descending = True

        self.assertEqual(
            [item.name for item in window._sorted_image_files(items)],
            ["image10.jpg", "image2.jpg", "image1.jpg"],
        )

    def test_sorts_by_modified_time(self) -> None:
        window = MainWindow()
        items = [
            _image_file("b.jpg", 20),
            _image_file("a.jpg", 10),
            _image_file("c.jpg", 30),
        ]
        window.sort_field = "mtime"

        self.assertEqual(
            [item.name for item in window._sorted_image_files(items)],
            ["a.jpg", "b.jpg", "c.jpg"],
        )

        window.sort_descending = True

        self.assertEqual(
            [item.name for item in window._sorted_image_files(items)],
            ["c.jpg", "b.jpg", "a.jpg"],
        )

    def test_sorts_by_file_size(self) -> None:
        window = MainWindow()
        items = [
            _image_file("b.jpg", 20, size=300),
            _image_file("a.jpg", 10, size=100),
            _image_file("c.jpg", 30, size=200),
        ]
        window.sort_field = "size"

        self.assertEqual(
            [item.name for item in window._sorted_image_files(items)],
            ["a.jpg", "c.jpg", "b.jpg"],
        )

        window.sort_descending = True

        self.assertEqual(
            [item.name for item in window._sorted_image_files(items)],
            ["b.jpg", "c.jpg", "a.jpg"],
        )

    def test_apply_sort_preserves_selected_image(self) -> None:
        window = MainWindow()
        items = [
            _image_file("image10.jpg", 3),
            _image_file("image2.jpg", 2),
            _image_file("image1.jpg", 1),
        ]
        preview_requests: list[ImageFile] = []
        thumbnail_requests: list[list[str]] = []

        window.thumbnail_grid._client_width = lambda: 400  # type: ignore[method-assign]
        window.thumbnail_grid._client_height = lambda: 430  # type: ignore[method-assign]
        window.thumbnail_grid.set_items(items)
        window.thumbnail_grid.selected_index = 0
        window.thumbnail_grid.on_selection_changed = window._select_image
        window._selected_image_file = items[0]
        window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]
        window._start_preview_worker = lambda image_file, show_loading=True: preview_requests.append(image_file)  # type: ignore[method-assign]
        window._start_thumbnail_worker = (  # type: ignore[method-assign]
            lambda _load_id, image_files, _thumbnail_size: thumbnail_requests.append([item.name for item in image_files])
        )

        window._apply_sort_to_current_items()

        self.assertEqual([item.name for item in window.thumbnail_grid.items], ["image1.jpg", "image2.jpg", "image10.jpg"])
        self.assertEqual(window.thumbnail_grid.selected_index, 2)
        self.assertEqual(window._selected_image_file, items[0])
        self.assertEqual(preview_requests, [items[0]])
        self.assertEqual(thumbnail_requests, [["image1.jpg", "image2.jpg", "image10.jpg"]])

    def test_apply_sort_handles_empty_items(self) -> None:
        window = MainWindow()
        window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]

        window._apply_sort_to_current_items()

        self.assertEqual(window.thumbnail_grid.items, [])
        self.assertIsNone(window.thumbnail_grid.selected_index)

    def test_window_restores_saved_sort_preferences(self) -> None:
        original_load_viewer_options = main_window.load_viewer_options
        try:
            main_window.load_viewer_options = (  # type: ignore[assignment]
                lambda: {"file_list": {"sort_field": "size", "sort_descending": True}}
            )
            window = MainWindow()
        finally:
            main_window.load_viewer_options = original_load_viewer_options  # type: ignore[assignment]

        self.assertEqual(window.sort_field, "size")
        self.assertTrue(window.sort_descending)

    def test_sort_changes_are_saved(self) -> None:
        original_update_viewer_options = main_window.update_viewer_options
        calls: list[tuple[str, dict[str, object]]] = []
        window = MainWindow()
        window._check_sort_buttons = lambda: None  # type: ignore[method-assign]
        window._apply_sort_to_current_items = lambda: None  # type: ignore[method-assign]
        try:
            main_window.update_viewer_options = (  # type: ignore[assignment]
                lambda category, updates: calls.append((category, dict(updates))) or {"file_list": dict(updates)}
            )

            window._change_sort_field("size")
            window._change_sort_order(True)
        finally:
            main_window.update_viewer_options = original_update_viewer_options  # type: ignore[assignment]

        self.assertEqual(
            calls,
            [
                ("file_list", {"sort_field": "size", "sort_descending": False}),
                ("file_list", {"sort_field": "size", "sort_descending": True}),
            ],
        )


if __name__ == "__main__":
    unittest.main()

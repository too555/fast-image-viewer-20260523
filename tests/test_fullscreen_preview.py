from __future__ import annotations

import time
import unittest
from pathlib import Path

import app.ui.main_window as main_window
from app.core.image_scanner import ImageFile
from app.core.preview_renderer import PreviewResult


def _image_file(index: int) -> ImageFile:
    return ImageFile(
        path=Path(f"C:/images/image_{index}.jpg"),
        name=f"image_{index}.jpg",
        suffix=".jpg",
        size=100,
        mtime=float(index),
    )


class FakeFullscreenPreview:
    def __init__(self) -> None:
        self.visible = False
        self.loading: list[ImageFile] = []
        self.results: list[tuple[ImageFile, PreviewResult]] = []
        self.hidden = False

    def show_loading(self, image_file: ImageFile) -> None:
        self.visible = True
        self.hidden = False
        self.loading.append(image_file)

    def set_result(self, image_file: ImageFile, result: PreviewResult) -> None:
        self.results.append((image_file, result))

    def hide(self) -> None:
        self.visible = False
        self.hidden = True

    def preview_size(self) -> tuple[int, int]:
        return (640, 480)


class FullscreenPreviewTest(unittest.TestCase):
    def test_open_fullscreen_renders_selected_image(self) -> None:
        original_render_preview = main_window.render_preview
        image_file = _image_file(1)
        window = main_window.MainWindow()
        fake_fullscreen = FakeFullscreenPreview()
        window.fullscreen_preview = fake_fullscreen  # type: ignore[assignment]
        window._selected_image_file = image_file

        def fake_render_preview(image: ImageFile, max_width: int, max_height: int) -> PreviewResult:
            return PreviewResult(cache_path=Path(f"{image.name}.bmp"), width=max_width, height=max_height)

        try:
            main_window.render_preview = fake_render_preview
            window._open_fullscreen()

            deadline = time.time() + 2
            while window._fullscreen_queue.empty() and time.time() < deadline:
                time.sleep(0.01)
            window._drain_fullscreen_queue()
        finally:
            window._cancel_fullscreen_requests()
            main_window.render_preview = original_render_preview

        self.assertTrue(fake_fullscreen.visible)
        self.assertEqual(fake_fullscreen.loading[-1], image_file)
        self.assertEqual(fake_fullscreen.results[0][0], image_file)
        self.assertEqual(fake_fullscreen.results[0][1].width, 640)
        self.assertEqual(fake_fullscreen.results[0][1].height, 480)

    def test_fullscreen_queue_ignores_stale_result(self) -> None:
        window = main_window.MainWindow()
        fake_fullscreen = FakeFullscreenPreview()
        fake_fullscreen.visible = True
        window.fullscreen_preview = fake_fullscreen  # type: ignore[assignment]
        latest_image = _image_file(2)
        stale_image = _image_file(1)
        window._selected_image_file = latest_image

        with window._fullscreen_lock:
            window._fullscreen_id = 2
        window._fullscreen_queue.put((1, stale_image, PreviewResult(cache_path=Path("stale.bmp"))))
        window._fullscreen_queue.put((2, latest_image, PreviewResult(cache_path=Path("latest.bmp"))))

        window._drain_fullscreen_queue()

        self.assertEqual(fake_fullscreen.results, [(latest_image, PreviewResult(cache_path=Path("latest.bmp")))])

    def test_fullscreen_left_right_keeps_selection_in_sync(self) -> None:
        window = main_window.MainWindow()
        fake_fullscreen = FakeFullscreenPreview()
        fake_fullscreen.visible = True
        window.fullscreen_preview = fake_fullscreen  # type: ignore[assignment]
        items = [_image_file(index) for index in range(3)]
        fullscreen_requests: list[ImageFile] = []

        window.thumbnail_grid._client_width = lambda: 400  # type: ignore[method-assign]
        window.thumbnail_grid._client_height = lambda: 430  # type: ignore[method-assign]
        window.thumbnail_grid.set_items(items)
        window.thumbnail_grid.on_selection_changed = window._select_image
        window._start_preview_worker = lambda _image_file, show_loading=True: None  # type: ignore[method-assign]
        window._start_fullscreen_worker = lambda image_file: fullscreen_requests.append(image_file)  # type: ignore[method-assign]
        window.thumbnail_grid.select_index(1)
        fullscreen_requests.clear()

        window._fullscreen_select_relative(1)
        self.assertEqual(window.thumbnail_grid.selected_index, 2)
        self.assertEqual(window._selected_image_file, items[2])
        self.assertEqual(fullscreen_requests[-1], items[2])

        window._fullscreen_select_relative(-1)
        self.assertEqual(window.thumbnail_grid.selected_index, 1)
        self.assertEqual(window._selected_image_file, items[1])
        self.assertEqual(fullscreen_requests[-1], items[1])


if __name__ == "__main__":
    unittest.main()

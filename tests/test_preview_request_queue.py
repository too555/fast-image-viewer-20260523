from __future__ import annotations

import time
import unittest
from pathlib import Path

import app.ui.main_window as main_window
from app.core.image_scanner import ImageFile
from app.core.preview_renderer import PreviewResult


def _image_file(index: int) -> ImageFile:
    return ImageFile(
        path=Path(f"image_{index}.jpg"),
        name=f"image_{index}.jpg",
        suffix=".jpg",
        size=100,
        mtime=1.0,
    )


class FakePreview:
    def __init__(self) -> None:
        self.image_file: ImageFile | None = None
        self.result_image_file: ImageFile | None = None

    def preview_size(self) -> tuple[int, int]:
        return (320, 240)

    def set_loading(self, image_file: ImageFile | None) -> None:
        self.image_file = image_file

    def set_result(self, image_file: ImageFile, result: PreviewResult) -> None:
        self.result_image_file = image_file

    def set_pan_enabled(self, _enabled: bool) -> None:
        pass


class PreviewRequestQueueTest(unittest.TestCase):
    def test_rapid_preview_requests_render_latest_only(self) -> None:
        original_render_preview = main_window.render_preview
        original_delay = main_window.PREVIEW_START_DELAY_SECONDS
        calls: list[str] = []

        def fake_render_preview(
            image_file: ImageFile,
            max_width: int,
            max_height: int,
            *,
            display_mode: str = "fit_area",
        ) -> PreviewResult:
            calls.append(image_file.name)
            return PreviewResult(cache_path=Path(f"{image_file.name}.bmp"), width=max_width, height=max_height)

        window = main_window.MainWindow()
        window.image_preview = FakePreview()  # type: ignore[assignment]
        items = [_image_file(index) for index in range(5)]

        try:
            main_window.render_preview = fake_render_preview
            main_window.PREVIEW_START_DELAY_SECONDS = 0.02
            for image_file in items:
                window._selected_image_file = image_file
                window._start_preview_worker(image_file)

            deadline = time.time() + 2
            while window._preview_queue.empty() and time.time() < deadline:
                time.sleep(0.01)

            window._drain_preview_queue()

            self.assertEqual(calls, [items[-1].name])
            self.assertIs(window.image_preview.result_image_file, items[-1])
        finally:
            window._cancel_preview_requests()
            main_window.render_preview = original_render_preview
            main_window.PREVIEW_START_DELAY_SECONDS = original_delay

    def test_preview_queue_ignores_stale_result(self) -> None:
        window = main_window.MainWindow()
        window.image_preview = FakePreview()  # type: ignore[assignment]
        old_image = _image_file(1)
        latest_image = _image_file(2)

        with window._preview_lock:
            window._preview_id = 2
        window._selected_image_file = latest_image
        window.image_preview.set_loading(latest_image)
        window._preview_queue.put((1, old_image, PreviewResult(cache_path=Path("old.bmp"))))
        window._preview_queue.put((2, latest_image, PreviewResult(cache_path=Path("latest.bmp"))))

        window._drain_preview_queue()

        self.assertIs(window.image_preview.result_image_file, latest_image)


if __name__ == "__main__":
    unittest.main()

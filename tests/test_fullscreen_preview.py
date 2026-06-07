from __future__ import annotations

import time
import unittest
from pathlib import Path

import app.ui.main_window as main_window
from app.core.image_scanner import ImageFile
from app.core.preview_renderer import PREVIEW_MODE_FIT_HEIGHT, PREVIEW_MODE_SCALE_200, PreviewResult


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
        self.position_texts: list[str] = []
        self.zoom_texts: list[str] = []
        self.results: list[tuple[ImageFile, PreviewResult]] = []
        self.hidden = False
        self.feedback: list[str] = []

    def show_loading(self, image_file: ImageFile, position_text: str = "", zoom_text: str = "") -> None:
        self.visible = True
        self.hidden = False
        self.loading.append(image_file)
        self.position_texts.append(position_text)
        self.zoom_texts.append(zoom_text)

    def set_result(self, image_file: ImageFile, result: PreviewResult) -> None:
        self.results.append((image_file, result))

    def hide(self) -> None:
        self.visible = False
        self.hidden = True

    def preview_size(self) -> tuple[int, int]:
        return (640, 480)

    def set_pan_enabled(self, _enabled: bool) -> None:
        pass

    def show_feedback(self, text: str) -> None:
        self.feedback.append(text)


class FullscreenPreviewTest(unittest.TestCase):
    def test_open_fullscreen_renders_selected_image(self) -> None:
        original_render_preview = main_window.render_preview
        image_file = _image_file(1)
        window = main_window.MainWindow()
        fake_fullscreen = FakeFullscreenPreview()
        window.fullscreen_preview = fake_fullscreen  # type: ignore[assignment]
        window.thumbnail_grid.items = [_image_file(0), image_file, _image_file(2)]
        window._selected_image_file = image_file

        def fake_render_preview(
            image: ImageFile,
            max_width: int,
            max_height: int,
            *,
            display_mode: str = "fit_area",
        ) -> PreviewResult:
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
        self.assertEqual(fake_fullscreen.position_texts[-1], "2 / 3")
        self.assertEqual(fake_fullscreen.zoom_texts[-1], "100%")
        self.assertEqual(fake_fullscreen.results[0][0], image_file)
        self.assertEqual(fake_fullscreen.results[0][1].width, 640)
        self.assertEqual(fake_fullscreen.results[0][1].height, 480)

    def test_fullscreen_loading_receives_current_zoom_text(self) -> None:
        window = main_window.MainWindow()
        fake_fullscreen = FakeFullscreenPreview()
        window.fullscreen_preview = fake_fullscreen  # type: ignore[assignment]
        image_file = _image_file(0)
        window.thumbnail_grid.items = [image_file]
        window._selected_image_file = image_file

        window.display_mode = PREVIEW_MODE_SCALE_200
        window._start_fullscreen_worker(image_file)
        self.assertEqual(fake_fullscreen.zoom_texts[-1], "200%")

        window.display_mode = PREVIEW_MODE_FIT_HEIGHT
        window._start_fullscreen_worker(image_file)
        self.assertEqual(fake_fullscreen.zoom_texts[-1], "高さに合わせる")

    def test_fullscreen_position_text_uses_current_list_index(self) -> None:
        window = main_window.MainWindow()
        items = [_image_file(index) for index in range(4)]
        window.thumbnail_grid.items = items

        self.assertEqual(window._fullscreen_position_text(items[2]), "3 / 4")
        self.assertEqual(window._fullscreen_position_text(_image_file(9)), "- / 4")

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

    def test_fullscreen_copy_image_path_shows_feedback(self) -> None:
        window = main_window.MainWindow()
        fake_fullscreen = FakeFullscreenPreview()
        image_file = _image_file(1)
        copied: list[str] = []
        window.fullscreen_preview = fake_fullscreen  # type: ignore[assignment]
        window._selected_image_file = image_file
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]

        self.assertTrue(window._handle_fullscreen_copy_image_path())

        self.assertEqual(copied, [str(image_file.path)])
        self.assertEqual(fake_fullscreen.feedback, ["画像パスをコピーしました"])

    def test_fullscreen_copy_folder_path_shows_feedback(self) -> None:
        window = main_window.MainWindow()
        fake_fullscreen = FakeFullscreenPreview()
        copied: list[str] = []
        window.fullscreen_preview = fake_fullscreen  # type: ignore[assignment]
        window.current_folder = Path("C:/images")
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]

        self.assertTrue(window._handle_fullscreen_copy_folder_path())

        self.assertEqual(copied, [str(window.current_folder)])
        self.assertEqual(fake_fullscreen.feedback, ["フォルダパスをコピーしました"])

    def test_fullscreen_context_menu_copies_image_path_with_feedback(self) -> None:
        window = main_window.MainWindow()
        fake_fullscreen = FakeFullscreenPreview()
        image_file = _image_file(1)
        copied: list[str] = []
        menu_calls: list[tuple[int, int, int | None]] = []
        window.fullscreen_preview = fake_fullscreen  # type: ignore[assignment]
        window._selected_image_file = image_file
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]

        def fake_menu(x: int, y: int, owner_hwnd: int | None = None) -> int:
            menu_calls.append((x, y, owner_hwnd))
            return main_window.CONTEXT_COPY_IMAGE_PATH_ID

        window._control_point_to_screen = lambda _hwnd, x, y: (x + 100, y + 200)  # type: ignore[method-assign]
        window._show_path_context_menu = fake_menu  # type: ignore[method-assign]

        window._handle_fullscreen_context_menu(300, 10, 20)

        self.assertEqual(menu_calls, [(110, 220, 300)])
        self.assertEqual(copied, [str(image_file.path)])
        self.assertEqual(fake_fullscreen.feedback, ["画像パスをコピーしました"])

    def test_fullscreen_context_menu_copies_folder_path_with_feedback(self) -> None:
        window = main_window.MainWindow()
        fake_fullscreen = FakeFullscreenPreview()
        copied: list[str] = []
        window.fullscreen_preview = fake_fullscreen  # type: ignore[assignment]
        window.current_folder = Path("C:/images")
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]
        window._show_path_context_menu = (  # type: ignore[method-assign]
            lambda _x, _y, owner_hwnd=None: main_window.CONTEXT_COPY_FOLDER_PATH_ID
        )

        window._handle_fullscreen_context_menu(None, 10, 20)

        self.assertEqual(copied, [str(window.current_folder)])
        self.assertEqual(fake_fullscreen.feedback, ["フォルダパスをコピーしました"])

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

    def test_left_right_navigation_ignores_missing_selection(self) -> None:
        window = main_window.MainWindow()
        items = [_image_file(index) for index in range(3)]
        preview_requests: list[ImageFile] = []
        window.thumbnail_grid._client_width = lambda: 400  # type: ignore[method-assign]
        window.thumbnail_grid._client_height = lambda: 430  # type: ignore[method-assign]
        window.thumbnail_grid.set_items(items)
        window.thumbnail_grid.on_selection_changed = window._select_image
        window._start_preview_worker = lambda image_file, show_loading=True: preview_requests.append(image_file)  # type: ignore[method-assign]

        self.assertFalse(window._select_relative_image(1))
        self.assertIsNone(window.thumbnail_grid.selected_index)
        self.assertIsNone(window._selected_image_file)
        self.assertEqual(preview_requests, [])

    def test_left_right_navigation_stops_safely_at_edges(self) -> None:
        window = main_window.MainWindow()
        items = [_image_file(index) for index in range(3)]
        preview_requests: list[ImageFile] = []
        window.thumbnail_grid._client_width = lambda: 400  # type: ignore[method-assign]
        window.thumbnail_grid._client_height = lambda: 430  # type: ignore[method-assign]
        window.thumbnail_grid.set_items(items)
        window.thumbnail_grid.on_selection_changed = window._select_image
        window._start_preview_worker = lambda image_file, show_loading=True: preview_requests.append(image_file)  # type: ignore[method-assign]

        window.thumbnail_grid.select_index(0)
        preview_requests.clear()
        self.assertFalse(window._select_relative_image(-1))
        self.assertEqual(window.thumbnail_grid.selected_index, 0)
        self.assertEqual(window._selected_image_file, items[0])
        self.assertEqual(preview_requests, [])

        window.thumbnail_grid.select_index(2)
        preview_requests.clear()
        self.assertFalse(window._select_relative_image(1))
        self.assertEqual(window.thumbnail_grid.selected_index, 2)
        self.assertEqual(window._selected_image_file, items[2])
        self.assertEqual(preview_requests, [])

    def test_space_toggles_fullscreen_from_main_window(self) -> None:
        window = main_window.MainWindow()
        items = [_image_file(index) for index in range(3)]
        fullscreen_opened: list[bool] = []
        window.thumbnail_grid._client_width = lambda: 400  # type: ignore[method-assign]
        window.thumbnail_grid._client_height = lambda: 430  # type: ignore[method-assign]
        window.thumbnail_grid.set_items(items)
        window.thumbnail_grid.on_selection_changed = window._select_image
        window._start_preview_worker = lambda _image_file, show_loading=True: None  # type: ignore[method-assign]
        window._open_fullscreen = lambda *_args: fullscreen_opened.append(True)  # type: ignore[method-assign]
        window.thumbnail_grid.select_index(0)

        window.handle_message(0, main_window.WM_KEYDOWN, main_window.VK_SPACE, 0)

        self.assertEqual(window.thumbnail_grid.selected_index, 0)
        self.assertEqual(window._selected_image_file, items[0])
        self.assertEqual(fullscreen_opened, [True])

    def test_space_without_selection_stops_safely(self) -> None:
        window = main_window.MainWindow()
        fullscreen_opened: list[bool] = []
        window._open_fullscreen = lambda *_args: fullscreen_opened.append(True)  # type: ignore[method-assign]

        self.assertFalse(window._toggle_fullscreen())
        self.assertEqual(fullscreen_opened, [])

    def test_space_closes_fullscreen(self) -> None:
        window = main_window.MainWindow()
        fake_fullscreen = FakeFullscreenPreview()
        fake_fullscreen.visible = True
        window.fullscreen_preview = fake_fullscreen  # type: ignore[assignment]

        self.assertTrue(window._toggle_fullscreen())

        self.assertFalse(fake_fullscreen.visible)
        self.assertTrue(fake_fullscreen.hidden)

    def test_mouse_wheel_navigation_uses_selection_flow(self) -> None:
        window = main_window.MainWindow()
        items = [_image_file(index) for index in range(3)]
        preview_requests: list[ImageFile] = []
        window.thumbnail_grid._client_width = lambda: 400  # type: ignore[method-assign]
        window.thumbnail_grid._client_height = lambda: 430  # type: ignore[method-assign]
        window.thumbnail_grid.set_items(items)
        window.thumbnail_grid.on_selection_changed = window._select_image
        window._start_preview_worker = lambda image_file, show_loading=True: preview_requests.append(image_file)  # type: ignore[method-assign]
        window.thumbnail_grid.select_index(1)
        preview_requests.clear()

        wheel_down = (-120 & 0xFFFF) << 16
        wheel_up = (120 & 0xFFFF) << 16
        window.handle_message(0, main_window.WM_MOUSEWHEEL, wheel_down, 0)
        window.handle_message(0, main_window.WM_MOUSEWHEEL, wheel_up, 0)

        self.assertEqual(window.thumbnail_grid.selected_index, 1)
        self.assertEqual([image.name for image in preview_requests], ["image_2.jpg", "image_1.jpg"])


if __name__ == "__main__":
    unittest.main()

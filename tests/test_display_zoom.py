from __future__ import annotations

import unittest

from app.core.preview_renderer import (
    PREVIEW_MODE_FIT_HEIGHT,
    PREVIEW_MODE_ORIGINAL,
    PREVIEW_MODE_SCALE_50,
    PREVIEW_MODE_SCALE_200,
)
from app.ui import fullscreen_preview, image_preview, main_window


class DisplayZoomTest(unittest.TestCase):
    def test_main_window_zoom_steps_between_fixed_ratios(self) -> None:
        window = main_window.MainWindow()

        window.display_mode = PREVIEW_MODE_ORIGINAL
        window._zoom_out()
        self.assertEqual(window.display_mode, PREVIEW_MODE_SCALE_50)

        window._zoom_in()
        self.assertEqual(window.display_mode, PREVIEW_MODE_ORIGINAL)

        window._zoom_in()
        self.assertEqual(window.display_mode, PREVIEW_MODE_SCALE_200)

        window._zoom_in()
        self.assertEqual(window.display_mode, PREVIEW_MODE_SCALE_200)

    def test_zoom_from_fit_height_returns_to_fixed_ratio(self) -> None:
        window = main_window.MainWindow()

        window.display_mode = PREVIEW_MODE_FIT_HEIGHT
        window._zoom_in()
        self.assertEqual(window.display_mode, PREVIEW_MODE_ORIGINAL)

        window.display_mode = PREVIEW_MODE_FIT_HEIGHT
        window._zoom_out()
        self.assertEqual(window.display_mode, PREVIEW_MODE_SCALE_50)

    def test_thumbnail_ctrl_wheel_steps_between_configured_sizes(self) -> None:
        window = main_window.MainWindow()
        requested_sizes: list[int] = []
        window._change_thumbnail_size = lambda thumbnail_size: requested_sizes.append(thumbnail_size)  # type: ignore[method-assign]

        window.thumbnail_size = 128
        self.assertTrue(window._change_thumbnail_size_by_wheel(1))
        window.thumbnail_size = 128
        self.assertTrue(window._change_thumbnail_size_by_wheel(-1))

        window.thumbnail_size = 256
        self.assertFalse(window._change_thumbnail_size_by_wheel(1))
        window.thumbnail_size = 64
        self.assertFalse(window._change_thumbnail_size_by_wheel(-1))

        self.assertEqual(requested_sizes, [160, 96])

    def test_pan_is_enabled_for_fixed_ratios_only(self) -> None:
        self.assertTrue(main_window._pan_enabled_for_display_mode(PREVIEW_MODE_SCALE_50))
        self.assertTrue(main_window._pan_enabled_for_display_mode(PREVIEW_MODE_ORIGINAL))
        self.assertTrue(main_window._pan_enabled_for_display_mode(PREVIEW_MODE_SCALE_200))
        self.assertFalse(main_window._pan_enabled_for_display_mode(PREVIEW_MODE_FIT_HEIGHT))

    def test_normal_preview_ctrl_wheel_changes_zoom_instead_of_image(self) -> None:
        preview = image_preview.ImagePreview()
        zooms: list[str] = []
        moves: list[str] = []
        preview.on_zoom_in = lambda: zooms.append("in")
        preview.on_zoom_out = lambda: zooms.append("out")
        preview.on_previous = lambda: moves.append("previous")
        preview.on_next = lambda: moves.append("next")
        original_ctrl_pressed = image_preview._ctrl_pressed
        image_preview._ctrl_pressed = lambda: True  # type: ignore[assignment]
        try:
            preview.handle_message(0, image_preview.WM_MOUSEWHEEL, 120 << 16, 0)
            preview.handle_message(0, image_preview.WM_MOUSEWHEEL, (-120 & 0xFFFF) << 16, 0)
        finally:
            image_preview._ctrl_pressed = original_ctrl_pressed  # type: ignore[assignment]

        self.assertEqual(zooms, ["in", "out"])
        self.assertEqual(moves, [])

    def test_fullscreen_ctrl_wheel_changes_zoom_instead_of_image(self) -> None:
        preview = fullscreen_preview.FullscreenPreview()
        zooms: list[str] = []
        moves: list[str] = []
        preview.on_zoom_in = lambda: zooms.append("in")
        preview.on_zoom_out = lambda: zooms.append("out")
        preview.on_previous = lambda: moves.append("previous")
        preview.on_next = lambda: moves.append("next")
        original_ctrl_pressed = fullscreen_preview._ctrl_pressed
        fullscreen_preview._ctrl_pressed = lambda: True  # type: ignore[assignment]
        try:
            preview.handle_message(0, fullscreen_preview.WM_MOUSEWHEEL, 120 << 16, 0)
            preview.handle_message(0, fullscreen_preview.WM_MOUSEWHEEL, (-120 & 0xFFFF) << 16, 0)
        finally:
            fullscreen_preview._ctrl_pressed = original_ctrl_pressed  # type: ignore[assignment]

        self.assertEqual(zooms, ["in", "out"])
        self.assertEqual(moves, [])


if __name__ == "__main__":
    unittest.main()

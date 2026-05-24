from __future__ import annotations

import unittest
from pathlib import Path

from app.core.preview_renderer import PreviewResult
from app.ui import fullscreen_preview, image_preview


class PreviewPanTest(unittest.TestCase):
    def test_normal_preview_pan_clamps_and_resets(self) -> None:
        preview = image_preview.ImagePreview()
        preview.hwnd = 100
        preview._client_rect = lambda: image_preview.RECT(0, 0, 320, 240)  # type: ignore[method-assign]
        preview.set_pan_enabled(True)
        preview.result = PreviewResult(cache_path=Path("large.bmp"), width=640, height=480)

        self.assertTrue(preview._begin_pan(160, 120))
        preview._update_pan(500, 420)

        self.assertEqual((preview._pan_x, preview._pan_y), (160, 120))

        preview.set_loading(None)

        self.assertEqual((preview._pan_x, preview._pan_y), (0, 0))
        self.assertFalse(preview._dragging)

    def test_normal_preview_pan_ratio_round_trips_for_compare_sync(self) -> None:
        preview = image_preview.ImagePreview()
        preview.hwnd = 100
        preview._client_rect = lambda: image_preview.RECT(0, 0, 320, 240)  # type: ignore[method-assign]
        preview.set_pan_enabled(True)
        preview.result = PreviewResult(cache_path=Path("large.bmp"), width=960, height=480)

        preview.set_pan_ratio(0.5, -1.0)

        self.assertEqual(preview.pan_ratio(), (0.5, -1.0))
        self.assertEqual((preview._pan_x, preview._pan_y), (160, -120))

    def test_normal_preview_guides_can_be_enabled_without_pan_changes(self) -> None:
        preview = image_preview.ImagePreview()
        invalidated: list[bool] = []
        preview.invalidate = lambda: invalidated.append(True)  # type: ignore[method-assign]

        preview.set_guides(center=True, grid=False)
        preview.set_guides(center=True, grid=True)
        preview.set_guides(center=False, grid=False)

        self.assertFalse(preview._guide_center_enabled)
        self.assertFalse(preview._guide_grid_enabled)
        self.assertEqual(len(invalidated), 3)

    def test_guide_positions_are_viewport_based(self) -> None:
        self.assertEqual(image_preview._guide_positions(160, 0, 320, 80), [0, 80, 160, 240])
        self.assertEqual(image_preview._guide_positions(175, 20, 260, 80), [95, 175, 255])

    def test_normal_preview_pan_change_notifies_compare_sync_callback(self) -> None:
        preview = image_preview.ImagePreview()
        preview.hwnd = 100
        preview._client_rect = lambda: image_preview.RECT(0, 0, 320, 240)  # type: ignore[method-assign]
        preview.set_pan_enabled(True)
        preview.result = PreviewResult(cache_path=Path("large.bmp"), width=640, height=480)
        changes: list[tuple[int, int]] = []
        preview.on_pan_changed = lambda _preview, x, y: changes.append((x, y))

        self.assertTrue(preview._begin_pan(160, 120))
        preview._update_pan(200, 160)

        self.assertEqual(changes, [(40, 40)])

    def test_normal_preview_disables_pan_for_fit_mode(self) -> None:
        preview = image_preview.ImagePreview()
        preview.hwnd = 100
        preview._client_rect = lambda: image_preview.RECT(0, 0, 320, 240)  # type: ignore[method-assign]
        preview.set_pan_enabled(False)
        preview.result = PreviewResult(cache_path=Path("large.bmp"), width=640, height=480)

        self.assertFalse(preview._begin_pan(160, 120))

    def test_normal_preview_cursor_tracks_pan_state(self) -> None:
        preview = image_preview.ImagePreview()
        preview.hwnd = 100
        preview._client_rect = lambda: image_preview.RECT(0, 0, 320, 240)  # type: ignore[method-assign]
        preview.set_pan_enabled(True)
        preview.result = PreviewResult(cache_path=Path("large.bmp"), width=640, height=480)

        self.assertEqual(preview._cursor_id(), image_preview.IDC_HAND)

        self.assertTrue(preview._begin_pan(160, 120))
        self.assertEqual(preview._cursor_id(), image_preview.IDC_SIZEALL)

        preview._end_pan()
        self.assertEqual(preview._cursor_id(), image_preview.IDC_HAND)

        preview.set_pan_enabled(False)
        self.assertEqual(preview._cursor_id(), image_preview.IDC_ARROW)

    def test_normal_preview_double_click_reset_keeps_activation_when_centered(self) -> None:
        preview = image_preview.ImagePreview()
        preview.hwnd = 100
        preview._client_rect = lambda: image_preview.RECT(0, 0, 320, 240)  # type: ignore[method-assign]
        preview.set_pan_enabled(True)
        preview.result = PreviewResult(cache_path=Path("large.bmp"), width=640, height=480)
        activated = []
        preview.on_activated = lambda: activated.append(True)

        preview._pan_x = 80
        preview._pan_y = 60

        self.assertEqual(preview.handle_message(100, image_preview.WM_LBUTTONDBLCLK, 0, 0), 0)
        self.assertEqual((preview._pan_x, preview._pan_y), (0, 0))
        self.assertEqual(activated, [])

        self.assertEqual(preview.handle_message(100, image_preview.WM_LBUTTONDBLCLK, 0, 0), 0)
        self.assertEqual(activated, [True])

    def test_normal_preview_copy_shortcut_callbacks_require_ctrl_and_shift(self) -> None:
        original_ctrl_pressed = image_preview._ctrl_pressed
        original_shift_pressed = image_preview._shift_pressed
        preview = image_preview.ImagePreview()
        calls: list[str] = []
        preview.on_copy_image_path = lambda: calls.append("image")
        preview.on_copy_folder_path = lambda: calls.append("folder")

        try:
            image_preview._ctrl_pressed = lambda: True  # type: ignore[assignment]
            image_preview._shift_pressed = lambda: True  # type: ignore[assignment]

            self.assertTrue(preview._handle_copy_shortcut(image_preview.VK_C))
            self.assertTrue(preview._handle_copy_shortcut(image_preview.VK_F))

            image_preview._ctrl_pressed = lambda: False  # type: ignore[assignment]
            self.assertFalse(preview._handle_copy_shortcut(image_preview.VK_C))
        finally:
            image_preview._ctrl_pressed = original_ctrl_pressed
            image_preview._shift_pressed = original_shift_pressed

        self.assertEqual(calls, ["image", "folder"])

    def test_fullscreen_preview_pan_clamps_to_image_viewport(self) -> None:
        preview = fullscreen_preview.FullscreenPreview()
        preview.hwnd = 200
        preview._client_rect = lambda: fullscreen_preview.RECT(0, 0, 800, 600)  # type: ignore[method-assign]
        preview.set_pan_enabled(True)
        preview.result = PreviewResult(cache_path=Path("large.bmp"), width=1200, height=900)

        self.assertTrue(preview._begin_pan(400, 300))
        preview._update_pan(900, 800)

        self.assertEqual((preview._pan_x, preview._pan_y), (200, 193))

    def test_fullscreen_preview_cursor_tracks_pan_state(self) -> None:
        preview = fullscreen_preview.FullscreenPreview()
        preview.hwnd = 200
        preview._client_rect = lambda: fullscreen_preview.RECT(0, 0, 800, 600)  # type: ignore[method-assign]
        preview.set_pan_enabled(True)
        preview.result = PreviewResult(cache_path=Path("large.bmp"), width=1200, height=900)

        self.assertEqual(preview._cursor_id(), fullscreen_preview.IDC_HAND)

        self.assertTrue(preview._begin_pan(400, 300))
        self.assertEqual(preview._cursor_id(), fullscreen_preview.IDC_SIZEALL)

        preview._end_pan()
        self.assertEqual(preview._cursor_id(), fullscreen_preview.IDC_HAND)

        preview.set_pan_enabled(False)
        self.assertEqual(preview._cursor_id(), fullscreen_preview.IDC_ARROW)

    def test_fullscreen_preview_double_click_resets_pan(self) -> None:
        preview = fullscreen_preview.FullscreenPreview()
        preview.hwnd = 200
        preview._client_rect = lambda: fullscreen_preview.RECT(0, 0, 800, 600)  # type: ignore[method-assign]
        preview.set_pan_enabled(True)
        preview.result = PreviewResult(cache_path=Path("large.bmp"), width=1200, height=900)
        preview._pan_x = 120
        preview._pan_y = 80

        self.assertEqual(preview.handle_message(200, fullscreen_preview.WM_LBUTTONDBLCLK, 0, 0), 0)

        self.assertEqual((preview._pan_x, preview._pan_y), (0, 0))

    def test_fullscreen_preview_copy_shortcut_callbacks_require_ctrl_and_shift(self) -> None:
        original_ctrl_pressed = fullscreen_preview._ctrl_pressed
        original_shift_pressed = fullscreen_preview._shift_pressed
        preview = fullscreen_preview.FullscreenPreview()
        calls: list[str] = []
        preview.on_copy_image_path = lambda: calls.append("image")
        preview.on_copy_folder_path = lambda: calls.append("folder")

        try:
            fullscreen_preview._ctrl_pressed = lambda: True  # type: ignore[assignment]
            fullscreen_preview._shift_pressed = lambda: True  # type: ignore[assignment]

            self.assertTrue(preview._handle_copy_shortcut(fullscreen_preview.VK_C))
            self.assertTrue(preview._handle_copy_shortcut(fullscreen_preview.VK_F))

            fullscreen_preview._shift_pressed = lambda: False  # type: ignore[assignment]
            self.assertFalse(preview._handle_copy_shortcut(fullscreen_preview.VK_C))
        finally:
            fullscreen_preview._ctrl_pressed = original_ctrl_pressed
            fullscreen_preview._shift_pressed = original_shift_pressed

        self.assertEqual(calls, ["image", "folder"])

    def test_fullscreen_feedback_can_be_shown_and_cleared(self) -> None:
        preview = fullscreen_preview.FullscreenPreview()
        invalidated: list[bool] = []
        preview.invalidate = lambda: invalidated.append(True)  # type: ignore[method-assign]

        preview.show_feedback("画像パスをコピーしました")
        self.assertEqual(preview.feedback_text, "画像パスをコピーしました")

        preview.handle_message(0, fullscreen_preview.WM_TIMER, fullscreen_preview.COPY_FEEDBACK_TIMER_ID, 0)

        self.assertEqual(preview.feedback_text, "")
        self.assertGreaterEqual(len(invalidated), 2)

    def test_fullscreen_preview_right_click_reports_context_menu_position(self) -> None:
        preview = fullscreen_preview.FullscreenPreview()
        reported: list[tuple[int | None, int, int]] = []
        preview.hwnd = 200
        preview.on_context_menu = lambda hwnd, x, y: reported.append((hwnd, x, y))

        l_param = (34 & 0xFFFF) | ((56 & 0xFFFF) << 16)
        self.assertEqual(preview.handle_message(200, fullscreen_preview.WM_RBUTTONUP, 0, l_param), 0)

        self.assertEqual(reported, [(200, 34, 56)])


if __name__ == "__main__":
    unittest.main()

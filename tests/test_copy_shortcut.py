"""
コピーショートカットキーのテスト (Step 34)

Ctrl+Shift+C → 画像パスコピー
Ctrl+Shift+F → フォルダパスコピー

各コントロール（ThumbnailGrid / ImagePreview / MainWindow）で
ショートカットが正しく発火・拒否されることを確認する。
"""
from __future__ import annotations

import unittest

import app.ui.image_preview as image_preview
import app.ui.main_window as main_window
import app.ui.thumbnail_grid as thumbnail_grid
from app.ui.image_preview import ImagePreview
from app.ui.thumbnail_grid import ThumbnailGrid

WM_KEYDOWN = main_window.WM_KEYDOWN


# ─── ImagePreview ───────────────────────────────────────────────────────────

class ImagePreviewCopyShortcutTest(unittest.TestCase):
    """ImagePreview._handle_copy_shortcut および handle_message(WM_KEYDOWN) のテスト。"""

    def _with_ctrl_shift(
        self,
        ctrl: bool = True,
        shift: bool = True,
    ):
        """コンテキストマネージャの代わりにラムダで Ctrl/Shift 状態を設定するヘルパ。"""
        return ctrl, shift

    def _patch_keys(self, ctrl: bool, shift: bool):
        original_ctrl = image_preview._ctrl_pressed
        original_shift = image_preview._shift_pressed
        image_preview._ctrl_pressed = lambda: ctrl  # type: ignore[assignment]
        image_preview._shift_pressed = lambda: shift  # type: ignore[assignment]
        return original_ctrl, original_shift

    def _restore_keys(self, original_ctrl, original_shift):
        image_preview._ctrl_pressed = original_ctrl  # type: ignore[assignment]
        image_preview._shift_pressed = original_shift  # type: ignore[assignment]

    # ── _handle_copy_shortcut の直接テスト ───────────────────────────────

    def test_ctrl_shift_c_calls_on_copy_image_path(self) -> None:
        calls: list[str] = []
        preview = ImagePreview()
        preview.on_copy_image_path = lambda: calls.append("image")

        orig_ctrl, orig_shift = self._patch_keys(True, True)
        try:
            result = preview._handle_copy_shortcut(image_preview.VK_C)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertTrue(result)
        self.assertEqual(calls, ["image"])

    def test_ctrl_shift_f_calls_on_copy_folder_path(self) -> None:
        calls: list[str] = []
        preview = ImagePreview()
        preview.on_copy_folder_path = lambda: calls.append("folder")

        orig_ctrl, orig_shift = self._patch_keys(True, True)
        try:
            result = preview._handle_copy_shortcut(image_preview.VK_F)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertTrue(result)
        self.assertEqual(calls, ["folder"])

    def test_ctrl_shift_other_key_returns_false(self) -> None:
        preview = ImagePreview()
        orig_ctrl, orig_shift = self._patch_keys(True, True)
        try:
            result = preview._handle_copy_shortcut(image_preview.VK_LEFT)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertFalse(result)

    def test_without_shift_does_not_fire(self) -> None:
        calls: list[str] = []
        preview = ImagePreview()
        preview.on_copy_image_path = lambda: calls.append("image")

        orig_ctrl, orig_shift = self._patch_keys(ctrl=True, shift=False)
        try:
            result = preview._handle_copy_shortcut(image_preview.VK_C)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertFalse(result)
        self.assertEqual(calls, [])

    def test_without_ctrl_does_not_fire(self) -> None:
        calls: list[str] = []
        preview = ImagePreview()
        preview.on_copy_image_path = lambda: calls.append("image")

        orig_ctrl, orig_shift = self._patch_keys(ctrl=False, shift=True)
        try:
            result = preview._handle_copy_shortcut(image_preview.VK_C)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertFalse(result)
        self.assertEqual(calls, [])

    def test_without_ctrl_or_shift_does_not_fire(self) -> None:
        calls: list[str] = []
        preview = ImagePreview()
        preview.on_copy_image_path = lambda: calls.append("image")
        preview.on_copy_folder_path = lambda: calls.append("folder")

        orig_ctrl, orig_shift = self._patch_keys(ctrl=False, shift=False)
        try:
            preview._handle_copy_shortcut(image_preview.VK_C)
            preview._handle_copy_shortcut(image_preview.VK_F)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertEqual(calls, [])

    # ── handle_message(WM_KEYDOWN) 経由テスト ────────────────────────────

    def test_wm_keydown_ctrl_shift_c_fires_image_path_callback(self) -> None:
        calls: list[str] = []
        preview = ImagePreview()
        preview.on_copy_image_path = lambda: calls.append("image")

        orig_ctrl, orig_shift = self._patch_keys(True, True)
        try:
            result = preview.handle_message(0, WM_KEYDOWN, image_preview.VK_C, 0)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertEqual(result, 0)
        self.assertEqual(calls, ["image"])

    def test_wm_keydown_ctrl_shift_f_fires_folder_path_callback(self) -> None:
        calls: list[str] = []
        preview = ImagePreview()
        preview.on_copy_folder_path = lambda: calls.append("folder")

        orig_ctrl, orig_shift = self._patch_keys(True, True)
        try:
            result = preview.handle_message(0, WM_KEYDOWN, image_preview.VK_F, 0)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertEqual(result, 0)
        self.assertEqual(calls, ["folder"])

    def test_wm_keydown_no_modifiers_does_not_fire_copy(self) -> None:
        calls: list[str] = []
        preview = ImagePreview()
        preview.on_copy_image_path = lambda: calls.append("image")

        orig_ctrl, orig_shift = self._patch_keys(False, False)
        try:
            preview.handle_message(0, WM_KEYDOWN, image_preview.VK_C, 0)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertEqual(calls, [])

    def test_no_crash_when_callback_is_none(self) -> None:
        """コールバック未設定でも例外が起きないこと。"""
        preview = ImagePreview()
        # on_copy_image_path / on_copy_folder_path ともに None のまま
        orig_ctrl, orig_shift = self._patch_keys(True, True)
        try:
            self.assertTrue(preview._handle_copy_shortcut(image_preview.VK_C))
            self.assertTrue(preview._handle_copy_shortcut(image_preview.VK_F))
        finally:
            self._restore_keys(orig_ctrl, orig_shift)


# ─── ThumbnailGrid（既存テストと対称に追加分のみ） ─────────────────────────

class ThumbnailGridCopyShortcutExtraTest(unittest.TestCase):
    """test_thumbnail_grid_navigation.py に追加できなかった補完テスト。"""

    def _patch_keys(self, ctrl: bool, shift: bool):
        original_ctrl = thumbnail_grid._ctrl_pressed
        original_shift = thumbnail_grid._shift_pressed
        thumbnail_grid._ctrl_pressed = lambda: ctrl  # type: ignore[assignment]
        thumbnail_grid._shift_pressed = lambda: shift  # type: ignore[assignment]
        return original_ctrl, original_shift

    def _restore_keys(self, original_ctrl, original_shift):
        thumbnail_grid._ctrl_pressed = original_ctrl  # type: ignore[assignment]
        thumbnail_grid._shift_pressed = original_shift  # type: ignore[assignment]

    def test_no_crash_when_callback_is_none(self) -> None:
        """コールバック未設定でも例外が起きないこと。"""
        grid = ThumbnailGrid()
        orig_ctrl, orig_shift = self._patch_keys(True, True)
        try:
            self.assertTrue(grid._handle_copy_shortcut(thumbnail_grid.VK_C))
            self.assertTrue(grid._handle_copy_shortcut(thumbnail_grid.VK_F))
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

    def test_only_ctrl_without_shift_is_not_enough(self) -> None:
        calls: list[str] = []
        grid = ThumbnailGrid()
        grid.on_copy_image_path = lambda: calls.append("image")

        orig_ctrl, orig_shift = self._patch_keys(ctrl=True, shift=False)
        try:
            result = grid._handle_copy_shortcut(thumbnail_grid.VK_C)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertFalse(result)
        self.assertEqual(calls, [])


# ─── MainWindow（WM_KEYDOWN 経由の統合テスト） ────────────────────────────

class MainWindowCopyShortcutKeydownTest(unittest.TestCase):
    """handle_message(WM_KEYDOWN) から _handle_copy_shortcut が呼ばれることを確認。"""

    def _patch_keys(self, ctrl: bool, shift: bool):
        original_ctrl = main_window._ctrl_pressed
        original_shift = main_window._shift_pressed
        main_window._ctrl_pressed = lambda: ctrl  # type: ignore[assignment]
        main_window._shift_pressed = lambda: shift  # type: ignore[assignment]
        return original_ctrl, original_shift

    def _restore_keys(self, original_ctrl, original_shift):
        main_window._ctrl_pressed = original_ctrl  # type: ignore[assignment]
        main_window._shift_pressed = original_shift  # type: ignore[assignment]

    def test_wm_keydown_ctrl_shift_c_calls_copy_image_path(self) -> None:
        calls: list[str] = []
        window = main_window.MainWindow()
        window._handle_copy_image_path = lambda: calls.append("image") or True  # type: ignore[method-assign]

        orig_ctrl, orig_shift = self._patch_keys(True, True)
        try:
            result = window.handle_message(0, WM_KEYDOWN, main_window.VK_C, 0)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertEqual(result, 0)
        self.assertEqual(calls, ["image"])

    def test_wm_keydown_ctrl_shift_f_calls_copy_folder_path(self) -> None:
        calls: list[str] = []
        window = main_window.MainWindow()
        window._handle_copy_folder_path = lambda: calls.append("folder") or True  # type: ignore[method-assign]

        orig_ctrl, orig_shift = self._patch_keys(True, True)
        try:
            result = window.handle_message(0, WM_KEYDOWN, main_window.VK_F, 0)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertEqual(result, 0)
        self.assertEqual(calls, ["folder"])

    def test_wm_keydown_ctrl_only_does_not_copy(self) -> None:
        calls: list[str] = []
        window = main_window.MainWindow()
        window._handle_copy_image_path = lambda: calls.append("image") or True  # type: ignore[method-assign]

        orig_ctrl, orig_shift = self._patch_keys(ctrl=True, shift=False)
        try:
            window.handle_message(0, WM_KEYDOWN, main_window.VK_C, 0)
        finally:
            self._restore_keys(orig_ctrl, orig_shift)

        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()

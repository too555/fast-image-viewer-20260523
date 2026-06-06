from __future__ import annotations

import unittest
import ctypes
import tempfile
from pathlib import Path

from app.core.image_resizer import RESIZE_BASIS_HEIGHT, ResizeResult
from app.core.image_scanner import ImageFile
import app.ui.main_window as main_window


def _image_file(path: Path, index: int) -> ImageFile:
    return ImageFile(
        path=path,
        name=path.name,
        suffix=path.suffix.lower(),
        size=100 + index,
        mtime=float(index),
    )


class FakeShell32:
    def __init__(self) -> None:
        self.browse_called = False
        self.path_requested = False
        self.browse_lpfn = 0
        self.browse_lparam = 0
        self.initial_path: str | None = None

    def SHBrowseForFolderW(self, browse_info: object) -> int:
        self.browse_called = True
        browse_info_value = ctypes.cast(browse_info, ctypes.POINTER(main_window.BROWSEINFOW)).contents
        self.browse_lpfn = int(browse_info_value.lpfn or 0)
        self.browse_lparam = int(browse_info_value.lParam or 0)
        self.initial_path = ctypes.wstring_at(self.browse_lparam) if self.browse_lparam else None
        return 123

    def SHGetPathFromIDListW(self, _pidl: int, path_buffer: object) -> bool:
        self.path_requested = True
        pointer = ctypes.cast(path_buffer, ctypes.POINTER(ctypes.c_wchar))
        for index, character in enumerate("C:/selected-images\0"):
            pointer[index] = character
        return True


class FakeOle32:
    def __init__(self) -> None:
        self.freed: list[int] = []
        self.uninitialized = False

    def CoInitialize(self, _reserved: object) -> int:
        return 0

    def CoTaskMemFree(self, pidl: int) -> None:
        self.freed.append(pidl)

    def CoUninitialize(self) -> None:
        self.uninitialized = True


class FolderSelectionTest(unittest.TestCase):
    def test_choose_folder_calls_native_dialog_and_returns_path(self) -> None:
        original_shell32 = main_window.shell32
        original_ole32 = main_window.ole32
        fake_shell32 = FakeShell32()
        fake_ole32 = FakeOle32()

        try:
            main_window.shell32 = fake_shell32  # type: ignore[assignment]
            main_window.ole32 = fake_ole32  # type: ignore[assignment]
            window = main_window.MainWindow()

            self.assertEqual(window._choose_folder(), Path("C:/selected-images"))
        finally:
            main_window.shell32 = original_shell32  # type: ignore[assignment]
            main_window.ole32 = original_ole32  # type: ignore[assignment]

        self.assertTrue(fake_shell32.browse_called)
        self.assertTrue(fake_shell32.path_requested)
        self.assertEqual(fake_ole32.freed, [123])
        self.assertTrue(fake_ole32.uninitialized)
        self.assertFalse(fake_shell32.browse_lparam)
        self.assertFalse(fake_shell32.browse_lpfn)

    def test_choose_folder_uses_current_folder_as_initial_dialog_path(self) -> None:
        original_shell32 = main_window.shell32
        original_ole32 = main_window.ole32
        fake_shell32 = FakeShell32()
        fake_ole32 = FakeOle32()

        try:
            main_window.shell32 = fake_shell32  # type: ignore[assignment]
            main_window.ole32 = fake_ole32  # type: ignore[assignment]
            with tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                window = main_window.MainWindow()
                window.current_folder = folder

                self.assertEqual(window._choose_folder(), Path("C:/selected-images"))
        finally:
            main_window.shell32 = original_shell32  # type: ignore[assignment]
            main_window.ole32 = original_ole32  # type: ignore[assignment]

        self.assertTrue(fake_shell32.browse_lparam)
        self.assertTrue(fake_shell32.browse_lpfn)
        self.assertEqual(fake_shell32.initial_path, str(folder))

    def test_choose_folder_ignores_missing_current_folder_for_initial_dialog_path(self) -> None:
        original_shell32 = main_window.shell32
        original_ole32 = main_window.ole32
        fake_shell32 = FakeShell32()
        fake_ole32 = FakeOle32()

        try:
            main_window.shell32 = fake_shell32  # type: ignore[assignment]
            main_window.ole32 = fake_ole32  # type: ignore[assignment]
            window = main_window.MainWindow()
            window.current_folder = Path("C:/missing-step59-folder")

            self.assertEqual(window._choose_folder(), Path("C:/selected-images"))
        finally:
            main_window.shell32 = original_shell32  # type: ignore[assignment]
            main_window.ole32 = original_ole32  # type: ignore[assignment]

        self.assertFalse(fake_shell32.browse_lparam)
        self.assertFalse(fake_shell32.browse_lpfn)

    def test_choose_folder_strips_extended_prefix_for_initial_dialog_path(self) -> None:
        original_shell32 = main_window.shell32
        original_ole32 = main_window.ole32
        fake_shell32 = FakeShell32()
        fake_ole32 = FakeOle32()

        try:
            main_window.shell32 = fake_shell32  # type: ignore[assignment]
            main_window.ole32 = fake_ole32  # type: ignore[assignment]
            with tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                window = main_window.MainWindow()
                window.current_folder = Path("\\\\?\\" + str(folder))

                self.assertEqual(window._choose_folder(), Path("C:/selected-images"))
        finally:
            main_window.shell32 = original_shell32  # type: ignore[assignment]
            main_window.ole32 = original_ole32  # type: ignore[assignment]

        self.assertTrue(fake_shell32.browse_lparam)
        self.assertEqual(fake_shell32.initial_path, str(folder))

    def test_choose_folder_cancel_returns_none(self) -> None:
        original_shell32 = main_window.shell32
        original_ole32 = main_window.ole32
        fake_ole32 = FakeOle32()

        class CancelShell32:
            def SHBrowseForFolderW(self, _browse_info: object) -> int:
                return 0

        try:
            main_window.shell32 = CancelShell32()  # type: ignore[assignment]
            main_window.ole32 = fake_ole32  # type: ignore[assignment]
            self.assertIsNone(main_window.MainWindow()._choose_folder())
        finally:
            main_window.shell32 = original_shell32  # type: ignore[assignment]
            main_window.ole32 = original_ole32  # type: ignore[assignment]

        self.assertEqual(fake_ole32.freed, [])
        self.assertTrue(fake_ole32.uninitialized)

    def test_select_folder_command_routes_to_handler(self) -> None:
        window = main_window.MainWindow()
        calls: list[bool] = []
        window._handle_select_folder = lambda: calls.append(True)  # type: ignore[method-assign]

        w_param = main_window.SELECT_FOLDER_ID | (main_window.BN_CLICKED << 16)

        self.assertEqual(window.handle_message(0, main_window.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [True])

    def test_folder_navigation_commands_route_to_handlers(self) -> None:
        window = main_window.MainWindow()
        calls: list[str] = []
        window._handle_open_parent_folder = lambda: calls.append("parent") or True  # type: ignore[method-assign]
        window._handle_open_previous_folder = lambda: calls.append("previous") or True  # type: ignore[method-assign]
        window._handle_open_next_folder = lambda: calls.append("next") or True  # type: ignore[method-assign]

        for control_id in [
            main_window.PARENT_FOLDER_ID,
            main_window.PREVIOUS_FOLDER_ID,
            main_window.NEXT_FOLDER_ID,
        ]:
            w_param = control_id | (main_window.BN_CLICKED << 16)
            self.assertEqual(window.handle_message(0, main_window.WM_COMMAND, w_param, 0), 0)

        self.assertEqual(calls, ["parent", "previous", "next"])

    def test_alt_folder_navigation_shortcuts_route_to_handlers(self) -> None:
        original_alt_pressed = main_window._alt_pressed
        window = main_window.MainWindow()
        calls: list[str] = []
        window._handle_open_parent_folder = lambda: calls.append("parent") or True  # type: ignore[method-assign]
        window._handle_open_previous_folder = lambda: calls.append("previous") or True  # type: ignore[method-assign]
        window._handle_open_next_folder = lambda: calls.append("next") or True  # type: ignore[method-assign]

        try:
            main_window._alt_pressed = lambda: True  # type: ignore[assignment]

            self.assertTrue(window._handle_folder_navigation_shortcut(main_window.VK_UP))
            self.assertTrue(window._handle_folder_navigation_shortcut(main_window.VK_LEFT))
            self.assertTrue(window._handle_folder_navigation_shortcut(main_window.VK_RIGHT))
        finally:
            main_window._alt_pressed = original_alt_pressed  # type: ignore[assignment]

        self.assertEqual(calls, ["parent", "previous", "next"])

    def test_operation_guide_command_routes_to_handler(self) -> None:
        window = main_window.MainWindow()
        calls: list[bool] = []
        window._show_operation_guide = lambda: calls.append(True)  # type: ignore[method-assign]

        w_param = main_window.OPERATION_GUIDE_ID | (main_window.BN_CLICKED << 16)

        self.assertEqual(window.handle_message(0, main_window.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [True])

    def test_cache_commands_route_to_handlers(self) -> None:
        window = main_window.MainWindow()
        calls: list[str] = []
        window._handle_cache_cleanup = lambda: calls.append("cleanup") or True  # type: ignore[method-assign]
        window._handle_cache_clear = lambda: calls.append("clear") or True  # type: ignore[method-assign]

        for control_id in [main_window.CACHE_CLEANUP_ID, main_window.CACHE_CLEAR_ID]:
            w_param = control_id | (main_window.BN_CLICKED << 16)
            self.assertEqual(window.handle_message(0, main_window.WM_COMMAND, w_param, 0), 0)

        self.assertEqual(calls, ["cleanup", "clear"])

    def test_cache_limit_command_saves_selected_limit(self) -> None:
        window = main_window.MainWindow()
        calls: list[int] = []
        window._change_cache_size_limit = lambda limit: calls.append(limit)  # type: ignore[method-assign]

        w_param = main_window.CACHE_LIMIT_1GB_ID | (main_window.BN_CLICKED << 16)

        self.assertEqual(window.handle_message(0, main_window.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [1024 * 1024 * 1024])

    def test_compare_commands_route_to_handlers(self) -> None:
        window = main_window.MainWindow()
        calls: list[str] = []
        window._handle_set_compare_a = lambda: calls.append("a") or True  # type: ignore[method-assign]
        window._handle_set_compare_b = lambda: calls.append("b") or True  # type: ignore[method-assign]
        window._handle_open_compare_view = lambda: calls.append("open") or True  # type: ignore[method-assign]

        command_ids = [
            main_window.COMPARE_SET_A_ID,
            main_window.COMPARE_SET_B_ID,
            main_window.COMPARE_OPEN_ID,
        ]

        for control_id in command_ids:
            w_param = control_id | (main_window.BN_CLICKED << 16)
            self.assertEqual(window.handle_message(0, main_window.WM_COMMAND, w_param, 0), 0)

        self.assertEqual(calls, ["a", "b", "open"])

    def test_set_compare_without_selection_does_not_crash(self) -> None:
        window = main_window.MainWindow()
        messages: list[str] = []
        window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

        self.assertFalse(window._handle_set_compare_a())
        self.assertFalse(window._handle_set_compare_b())

        self.assertEqual(
            messages,
            [
                "比較Aに設定する画像が選択されていません",
                "比較Bに設定する画像が選択されていません",
            ],
        )

    def test_set_compare_a_and_b_store_selected_images(self) -> None:
        window = main_window.MainWindow()
        messages: list[str] = []
        first = _image_file(Path("C:/images/a.jpg"), 1)
        second = _image_file(Path("C:/images/b.jpg"), 2)
        window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

        window._selected_image_file = first
        self.assertTrue(window._handle_set_compare_a())
        window._selected_image_file = second
        self.assertTrue(window._handle_set_compare_b())

        self.assertEqual(window._compare_a_image_file, first)
        self.assertEqual(window._compare_b_image_file, second)
        self.assertEqual(
            messages,
            [
                "比較Aに設定しました: a.jpg",
                "比較Bに設定しました: b.jpg",
            ],
        )

    def test_open_compare_view_requires_both_images(self) -> None:
        window = main_window.MainWindow()
        messages: list[str] = []
        window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

        self.assertFalse(window._handle_open_compare_view())

        self.assertEqual(messages, ["比較Aと比較Bの画像を設定してください"])

    def test_open_compare_view_shows_dialog_with_current_display_mode(self) -> None:
        first = _image_file(Path("C:/images/a.jpg"), 1)
        second = _image_file(Path("C:/images/b.jpg"), 2)
        show_calls: list[tuple[int | None, ImageFile, ImageFile, str]] = []
        messages: list[str] = []

        class FakeCompareView:
            def show(
                self,
                owner: int | None,
                left_image: ImageFile,
                right_image: ImageFile,
                display_mode: str,
            ) -> None:
                show_calls.append((owner, left_image, right_image, display_mode))

        window = main_window.MainWindow()
        window.hwnd = 55
        window.compare_view = FakeCompareView()  # type: ignore[assignment]
        window._compare_a_image_file = first
        window._compare_b_image_file = second
        window.display_mode = main_window.PREVIEW_MODE_FIT_HEIGHT
        window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

        self.assertTrue(window._handle_open_compare_view())

        self.assertEqual(len(show_calls), 1)
        self.assertEqual(show_calls[0][0], 55)
        self.assertEqual(show_calls[0][1], first)
        self.assertEqual(show_calls[0][2], second)
        self.assertEqual(show_calls[0][3], main_window.PREVIEW_MODE_FIT_HEIGHT)
        self.assertEqual(messages, ["2枚比較表示を開きました: a.jpg / b.jpg"])

    def test_operation_guide_text_lists_supported_shortcuts(self) -> None:
        required_lines = [
            "【よく使う操作】",
            "ホイール：前後の画像",
            "【画像移動】",
            "← / →：前後の画像",
            "Space：次の画像",
            "Shift + Space：前の画像",
            "Home / End：先頭 / 末尾",
            "PageUp / PageDown：ページ移動",
            "【表示操作】",
            "Ctrl + ホイール：拡大 / 縮小",
            "表示倍率：50% / 100% / 200% / 高さに合わせる",
            "ダブルクリック：表示位置を中央リセット",
            "【全画面操作】",
            "Enter：全画面",
            "Esc：戻る",
            "ダブルクリック：全画面",
            "【パスコピー】",
            "Ctrl + Shift + C：画像パスコピー",
            "Ctrl + Shift + F：フォルダパスコピー",
            "右クリック：コピー メニュー",
            "【マウス操作】",
            "ホイール：前後の画像",
            "ドラッグ：表示位置を移動",
        ]

        for line in required_lines:
            self.assertIn(line, main_window.OPERATION_GUIDE_TEXT)
        self.assertNotIn("削除", main_window.OPERATION_GUIDE_TEXT)

    def test_operation_guide_text_groups_basic_categories_in_order(self) -> None:
        categories = ["【よく使う操作】", "【画像移動】", "【表示操作】", "【全画面操作】", "【パスコピー】", "【マウス操作】"]
        indexes = [main_window.OPERATION_GUIDE_TEXT.index(category) for category in categories]

        self.assertEqual(indexes, sorted(indexes))

    def test_show_operation_guide_uses_dedicated_dialog(self) -> None:
        captured: list[tuple[int | None, str, str]] = []

        class FakeOperationGuideDialog:
            def show(self, owner: int | None, title: str, text: str) -> None:
                captured.append((owner, title, text))

        window = main_window.MainWindow()
        window.hwnd = 55
        window.operation_guide_dialog = FakeOperationGuideDialog()  # type: ignore[assignment]

        window._show_operation_guide()

        self.assertEqual(captured, [(55, main_window.OPERATION_GUIDE_TITLE, main_window.OPERATION_GUIDE_TEXT)])

    def test_resize_save_without_selection_does_not_crash(self) -> None:
        window = main_window.MainWindow()
        messages: list[str] = []
        window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

        self.assertFalse(window._handle_resize_save())
        self.assertEqual(messages, ["リサイズ保存する画像が選択されていません"])

    def test_resize_save_uses_selected_size_and_basis(self) -> None:
        original_resize_image_file = main_window.resize_image_file
        original_image_file_from_path = main_window.image_file_from_path
        selected = _image_file(Path("C:/images/photo.jpg"), 1)
        saved = _image_file(Path("C:/images/photo_resized.jpg"), 2)
        calls: list[tuple[ImageFile, int, str, Path | None]] = []
        messages: list[str] = []
        preview_requests: list[ImageFile] = []
        thumbnail_requests: list[tuple[int, list[ImageFile], int]] = []

        def fake_resize_image_file(
            image_file: ImageFile,
            size: int,
            basis: str,
            output_folder: Path | None = None,
        ) -> ResizeResult:
            calls.append((image_file, size, basis, output_folder))
            return ResizeResult(output_path=Path("C:/images/photo_resized.jpg"), width=1800, height=1200)

        try:
            main_window.resize_image_file = fake_resize_image_file  # type: ignore[assignment]
            main_window.image_file_from_path = lambda _path: saved  # type: ignore[assignment]
            window = main_window.MainWindow()
            window._selected_image_file = selected
            window.thumbnail_grid.set_items([selected])
            window.thumbnail_grid.on_selection_changed = window._select_image
            window.resize_size = 1200
            window.resize_basis = RESIZE_BASIS_HEIGHT
            window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]
            window._start_preview_worker = lambda image_file: preview_requests.append(image_file)  # type: ignore[method-assign]
            window._start_thumbnail_worker = lambda load_id, image_files, size: thumbnail_requests.append((load_id, image_files, size))  # type: ignore[method-assign]

            self.assertTrue(window._handle_resize_save())
        finally:
            main_window.resize_image_file = original_resize_image_file  # type: ignore[assignment]
            main_window.image_file_from_path = original_image_file_from_path  # type: ignore[assignment]

        self.assertEqual(calls, [(selected, 1200, RESIZE_BASIS_HEIGHT, None)])
        self.assertEqual(window.thumbnail_grid.items, [selected, saved])
        self.assertEqual(window.thumbnail_grid.selected_index, 1)
        self.assertEqual(window._selected_image_file, saved)
        self.assertEqual(preview_requests, [saved])
        self.assertEqual(thumbnail_requests[-1][1], [selected, saved])
        self.assertEqual(messages[-1], "リサイズ保存しました: C:\\images\\photo_resized.jpg (1800x1200)")

    def test_saved_resized_image_is_inserted_using_current_sort_order(self) -> None:
        original_image_file_from_path = main_window.image_file_from_path
        older = _image_file(Path("C:/images/older.jpg"), 1)
        newer = _image_file(Path("C:/images/newer.jpg"), 3)
        saved = _image_file(Path("C:/images/resized.jpg"), 2)
        preview_requests: list[ImageFile] = []

        try:
            main_window.image_file_from_path = lambda _path: saved  # type: ignore[assignment]
            window = main_window.MainWindow()
            window.sort_field = "mtime"
            window.sort_descending = True
            window.thumbnail_grid.set_items([older, newer])
            window.thumbnail_grid.on_selection_changed = window._select_image
            window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]
            window._start_preview_worker = lambda image_file: preview_requests.append(image_file)  # type: ignore[method-assign]
            window._start_thumbnail_worker = lambda _load_id, _image_files, _size: None  # type: ignore[method-assign]

            result = window._add_saved_image_to_current_list(saved.path)
        finally:
            main_window.image_file_from_path = original_image_file_from_path  # type: ignore[assignment]

        self.assertEqual(result, saved)
        self.assertEqual(window.thumbnail_grid.items, [newer, saved, older])
        self.assertEqual(window.thumbnail_grid.selected_index, 1)
        self.assertEqual(preview_requests, [saved])

    def test_open_selected_image_folder_without_selection_does_not_crash(self) -> None:
        window = main_window.MainWindow()
        messages: list[str] = []
        window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

        self.assertFalse(window._handle_open_selected_image_folder())
        self.assertEqual(messages, ["保存先を開く画像が選択されていません"])

    def test_open_selected_image_folder_uses_explorer(self) -> None:
        original_path_is_dir = main_window.path_is_dir
        original_shell32 = main_window.shell32
        selected = _image_file(Path("C:/images/photo.jpg"), 1)
        calls: list[tuple[int | None, str, str, object, object, int]] = []
        messages: list[str] = []

        class FakeShell32:
            def ShellExecuteW(
                self,
                hwnd: int | None,
                operation: str,
                file_path: str,
                parameters: object,
                directory: object,
                show_command: int,
            ) -> int:
                calls.append((hwnd, operation, file_path, parameters, directory, show_command))
                return 33

        try:
            main_window.path_is_dir = lambda folder: folder == selected.path.parent  # type: ignore[assignment]
            main_window.shell32 = FakeShell32()  # type: ignore[assignment]
            window = main_window.MainWindow()
            window.hwnd = 55
            window._selected_image_file = selected
            window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

            self.assertTrue(window._handle_open_selected_image_folder())
        finally:
            main_window.path_is_dir = original_path_is_dir  # type: ignore[assignment]
            main_window.shell32 = original_shell32  # type: ignore[assignment]

        self.assertEqual(calls, [(55, "open", str(selected.path.parent), None, None, main_window.SW_SHOW)])
        self.assertEqual(messages, [f"保存先フォルダを開きました: {selected.path.parent}"])

    def test_open_selected_image_folder_missing_path_does_not_crash(self) -> None:
        original_path_is_dir = main_window.path_is_dir
        selected = _image_file(Path("C:/missing/photo.jpg"), 1)
        messages: list[str] = []

        try:
            main_window.path_is_dir = lambda _folder: False  # type: ignore[assignment]
            window = main_window.MainWindow()
            window._selected_image_file = selected
            window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

            self.assertFalse(window._handle_open_selected_image_folder())
        finally:
            main_window.path_is_dir = original_path_is_dir  # type: ignore[assignment]

        self.assertEqual(messages, [f"保存先フォルダが見つかりません: {selected.path.parent}"])

    def test_context_reveal_image_uses_explorer_select(self) -> None:
        original_shell32 = main_window.shell32
        selected = _image_file(Path("C:/images/photo.jpg"), 1)
        calls: list[tuple[int | None, str, str, object, object, int]] = []
        messages: list[str] = []

        class FakeShell32:
            def ShellExecuteW(
                self,
                hwnd: int | None,
                operation: str,
                file_path: str,
                parameters: object,
                directory: object,
                show_command: int,
            ) -> int:
                calls.append((hwnd, operation, file_path, parameters, directory, show_command))
                return 33

        try:
            main_window.shell32 = FakeShell32()  # type: ignore[assignment]
            window = main_window.MainWindow()
            window.hwnd = 55
            window.status_bar = 102
            window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

            self.assertTrue(window._handle_context_reveal_image_in_explorer(selected))
        finally:
            main_window.shell32 = original_shell32  # type: ignore[assignment]

        self.assertEqual(
            calls,
            [(55, "open", "explorer.exe", f'/select,"{selected.path}"', None, main_window.SW_SHOW)],
        )
        self.assertEqual(messages, [f"エクスプローラーで選択表示しました: {selected.name}"])

    def test_context_reveal_image_without_selection_does_not_crash(self) -> None:
        window = main_window.MainWindow()
        messages: list[str] = []
        window.status_bar = 102
        window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

        self.assertFalse(window._handle_context_reveal_image_in_explorer(None))
        self.assertEqual(messages, ["選択表示する画像が選択されていません"])

    def test_reveal_selected_image_button_uses_explorer_select(self) -> None:
        original_path_exists = main_window.path_exists
        original_shell32 = main_window.shell32
        selected = _image_file(Path("C:/images/photo.jpg"), 1)
        calls: list[tuple[int | None, str, str, object, object, int]] = []

        class FakeShell32:
            def ShellExecuteW(
                self,
                hwnd: int | None,
                operation: str,
                file_path: str,
                parameters: object,
                directory: object,
                show_command: int,
            ) -> int:
                calls.append((hwnd, operation, file_path, parameters, directory, show_command))
                return 33

        try:
            main_window.path_exists = lambda path: path == selected.path  # type: ignore[assignment]
            main_window.shell32 = FakeShell32()  # type: ignore[assignment]
            window = main_window.MainWindow()
            window.hwnd = 55
            window.status_bar = 102
            window._selected_image_file = selected
            window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]

            self.assertTrue(window._handle_reveal_selected_image_in_explorer())
        finally:
            main_window.path_exists = original_path_exists  # type: ignore[assignment]
            main_window.shell32 = original_shell32  # type: ignore[assignment]

        self.assertEqual(
            calls,
            [(55, "open", "explorer.exe", f'/select,"{selected.path}"', None, main_window.SW_SHOW)],
        )

    def test_reveal_selected_image_button_without_selection_does_not_crash(self) -> None:
        window = main_window.MainWindow()
        messages: list[str] = []
        window.status_bar = 102
        window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

        self.assertFalse(window._handle_reveal_selected_image_in_explorer())
        self.assertEqual(messages, ["画像場所を表示する画像が選択されていません"])

    def test_handle_select_folder_loads_selected_folder(self) -> None:
        window = main_window.MainWindow()
        selected = Path("C:/selected-images")
        loaded: list[Path] = []
        window._choose_folder = lambda: selected  # type: ignore[method-assign]
        window.load_folder = lambda folder: loaded.append(folder)  # type: ignore[method-assign]

        window._handle_select_folder()

        self.assertEqual(loaded, [selected])

    def test_parent_folder_button_loads_parent_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            current = parent / "current"
            current.mkdir()
            window = main_window.MainWindow()
            loaded: list[Path] = []
            window.current_folder = current
            window.load_folder = lambda folder: loaded.append(folder)  # type: ignore[method-assign]

            self.assertTrue(window._handle_open_parent_folder())

        self.assertEqual(loaded, [parent])

    def test_parent_folder_without_current_folder_does_not_crash(self) -> None:
        window = main_window.MainWindow()
        messages: list[str] = []
        window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

        self.assertFalse(window._handle_open_parent_folder())
        self.assertEqual(messages, ["現在フォルダがありません"])

    def test_previous_and_next_folder_buttons_load_sibling_folders_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            alpha = parent / "01_alpha"
            beta = parent / "02_beta"
            gamma = parent / "10_gamma"
            for folder in [alpha, beta, gamma]:
                folder.mkdir()

            window = main_window.MainWindow()
            loaded: list[Path] = []
            window.current_folder = beta
            window.load_folder = lambda folder: loaded.append(folder)  # type: ignore[method-assign]

            self.assertTrue(window._handle_open_previous_folder())
            window.current_folder = beta
            self.assertTrue(window._handle_open_next_folder())

        self.assertEqual(loaded, [alpha, gamma])

    def test_previous_and_next_folder_buttons_stop_at_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            alpha = parent / "01_alpha"
            beta = parent / "02_beta"
            for folder in [alpha, beta]:
                folder.mkdir()

            window = main_window.MainWindow()
            messages: list[str] = []
            loaded: list[Path] = []
            window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]
            window.load_folder = lambda folder: loaded.append(folder)  # type: ignore[method-assign]

            window.current_folder = alpha
            self.assertFalse(window._handle_open_previous_folder())
            window.current_folder = beta
            self.assertFalse(window._handle_open_next_folder())

        self.assertEqual(loaded, [])
        self.assertEqual(messages, ["前のフォルダはありません", "次のフォルダはありません"])

    def test_sibling_folder_without_current_folder_does_not_crash(self) -> None:
        window = main_window.MainWindow()
        messages: list[str] = []
        window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

        self.assertFalse(window._handle_open_next_folder())
        self.assertEqual(messages, ["現在フォルダがありません"])

    def test_open_resize_output_folder_uses_selected_destination(self) -> None:
        original_path_is_dir = main_window.path_is_dir
        original_shell32 = main_window.shell32
        output_folder = Path("C:/resize-output")
        calls: list[tuple[int | None, str, str, object, object, int]] = []

        class FakeShell32:
            def ShellExecuteW(
                self,
                hwnd: int | None,
                operation: str,
                file_path: str,
                parameters: object,
                directory: object,
                show_command: int,
            ) -> int:
                calls.append((hwnd, operation, file_path, parameters, directory, show_command))
                return 33

        try:
            main_window.path_is_dir = lambda folder: folder == output_folder  # type: ignore[assignment]
            main_window.shell32 = FakeShell32()  # type: ignore[assignment]
            window = main_window.MainWindow()
            window.hwnd = 55
            window.resize_output_folder = output_folder
            window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]

            self.assertTrue(window._handle_open_resize_output_folder())
        finally:
            main_window.path_is_dir = original_path_is_dir  # type: ignore[assignment]
            main_window.shell32 = original_shell32  # type: ignore[assignment]

        self.assertEqual(calls, [(55, "open", str(output_folder), None, None, main_window.SW_SHOW)])

    def test_open_resize_output_folder_without_destination_does_not_crash(self) -> None:
        window = main_window.MainWindow()
        messages: list[str] = []
        window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

        self.assertFalse(window._handle_open_resize_output_folder())
        self.assertEqual(messages, ["開く保存先フォルダがありません"])

    def test_select_resize_output_folder_saves_destination(self) -> None:
        original_save_resize_output_folder = main_window.save_resize_output_folder
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            saved: list[Path] = []
            messages: list[str] = []
            window = main_window.MainWindow()
            window._choose_folder = lambda title="画像フォルダを選択", initial_folder=None: output_folder  # type: ignore[method-assign]
            window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]

            try:
                main_window.save_resize_output_folder = lambda folder: saved.append(folder)  # type: ignore[assignment]

                self.assertTrue(window._handle_select_resize_output_folder())
            finally:
                main_window.save_resize_output_folder = original_save_resize_output_folder  # type: ignore[assignment]

        self.assertEqual(window.resize_output_folder, output_folder)
        self.assertEqual(saved, [output_folder])
        self.assertIn("リサイズ保存先を設定しました", messages[-1])

    def test_resize_save_passes_selected_output_folder_without_mixing_external_folder_into_list(self) -> None:
        original_resize_image_file = main_window.resize_image_file
        selected = _image_file(Path("C:/images/photo.jpg"), 1)
        output_folder = Path("D:/exports")
        output_path = output_folder / "photo_resized.jpg"
        calls: list[Path | None] = []
        messages: list[str] = []

        def fake_resize_image_file(
            _image_file: ImageFile,
            _size: int,
            _basis: str,
            output_folder_arg: Path | None = None,
        ) -> ResizeResult:
            calls.append(output_folder_arg)
            return ResizeResult(output_path=output_path, width=800, height=400)

        try:
            main_window.resize_image_file = fake_resize_image_file  # type: ignore[assignment]
            window = main_window.MainWindow()
            window.current_folder = selected.path.parent
            window.resize_output_folder = output_folder
            window._selected_image_file = selected
            window.thumbnail_grid.set_items([selected])
            window._set_window_text = lambda _hwnd, text: messages.append(text)  # type: ignore[method-assign]
            window._effective_resize_output_folder = lambda: output_folder  # type: ignore[method-assign]

            self.assertTrue(window._handle_resize_save())
        finally:
            main_window.resize_image_file = original_resize_image_file  # type: ignore[assignment]

        self.assertEqual(calls, [output_folder])
        self.assertEqual(window.thumbnail_grid.items, [selected])
        self.assertIn(str(output_path), messages[-1])

    def test_preview_width_is_clamped_and_uses_saved_setting(self) -> None:
        window = main_window.MainWindow()
        window.preview_width = 900

        self.assertEqual(window._effective_preview_width(980), 786)

    def test_splitter_hit_area_has_drag_padding(self) -> None:
        window = main_window.MainWindow()
        window._tree_splitter_rect = (100, 20, main_window.TREE_SPLITTER_WIDTH, 200)
        window._splitter_rect = (300, 20, main_window.PREVIEW_SPLITTER_WIDTH, 200)

        self.assertTrue(window._point_in_tree_splitter(99, 50))
        self.assertTrue(window._point_in_splitter(299, 50))
        self.assertFalse(window._point_in_tree_splitter(95, 50))
        self.assertFalse(window._point_in_splitter(295, 50))

    def test_long_folder_path_is_compacted_for_display(self) -> None:
        window = main_window.MainWindow()
        long_folder = Path("C:/images") / ("very-long-folder-name-" * 8) / "leaf-folder"

        display_text = window._folder_display_text(long_folder)

        self.assertLessEqual(len(display_text), main_window.FOLDER_PATH_DISPLAY_LIMIT)
        self.assertIn("...", display_text)
        self.assertTrue(display_text.startswith("C:"))
        self.assertTrue(display_text.endswith("leaf-folder"))

    def test_load_folder_keeps_full_path_internally(self) -> None:
        original_scan_image_files = main_window.scan_image_files
        window = main_window.MainWindow()
        long_folder = Path("C:/images") / ("very-long-folder-name-" * 8) / "leaf-folder"
        captured_text: dict[int, str] = {}
        window.folder_label = 101
        window.status_bar = 102
        window._require_controls = lambda: None  # type: ignore[method-assign]
        window._set_window_text = lambda hwnd, text: captured_text.__setitem__(hwnd, text) if hwnd else None  # type: ignore[method-assign]

        try:
            main_window.scan_image_files = lambda _folder: []  # type: ignore[assignment]

            window.load_folder(long_folder)
        finally:
            main_window.scan_image_files = original_scan_image_files  # type: ignore[assignment]

        self.assertEqual(window.current_folder, long_folder)
        self.assertLessEqual(len(captured_text[window.folder_label]), main_window.FOLDER_PATH_DISPLAY_LIMIT)
        self.assertIn("...", captured_text[window.folder_label])

    def test_dropped_folder_routes_to_load_folder_and_finishes_drop(self) -> None:
        original_dropped_paths = main_window._dropped_paths
        original_shell32 = main_window.shell32
        with tempfile.TemporaryDirectory() as temp_dir:
            dropped_folder = Path(temp_dir)
            window = main_window.MainWindow()
            loaded: list[Path] = []

            class DropShell32:
                def __init__(self) -> None:
                    self.finished: list[int] = []

                def DragFinish(self, drop_handle: int) -> None:
                    self.finished.append(drop_handle)

            fake_shell32 = DropShell32()

            try:
                main_window._dropped_paths = lambda _drop_handle: [dropped_folder]  # type: ignore[assignment]
                main_window.shell32 = fake_shell32  # type: ignore[assignment]
                window.load_folder = lambda folder: loaded.append(folder)  # type: ignore[method-assign]

                window._handle_drop_files(42)
            finally:
                main_window._dropped_paths = original_dropped_paths  # type: ignore[assignment]
                main_window.shell32 = original_shell32  # type: ignore[assignment]

            self.assertEqual(loaded, [dropped_folder])
            self.assertEqual(fake_shell32.finished, [42])

    def test_dropped_image_routes_to_parent_folder_and_selects_image(self) -> None:
        original_dropped_paths = main_window._dropped_paths
        original_shell32 = main_window.shell32
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            image_file = folder / "image.jpg"
            image_file.write_text("dummy", encoding="utf-8")
            window = main_window.MainWindow()
            loaded: list[tuple[Path, Path | None]] = []

            class DropShell32:
                def __init__(self) -> None:
                    self.finished: list[int] = []

                def DragFinish(self, drop_handle: int) -> None:
                    self.finished.append(drop_handle)

            fake_shell32 = DropShell32()

            try:
                main_window._dropped_paths = lambda _drop_handle: [image_file]  # type: ignore[assignment]
                main_window.shell32 = fake_shell32  # type: ignore[assignment]
                window.load_folder = lambda folder, select_path=None: loaded.append((folder, select_path))  # type: ignore[method-assign]

                window._handle_drop_files(43)
            finally:
                main_window._dropped_paths = original_dropped_paths  # type: ignore[assignment]
                main_window.shell32 = original_shell32  # type: ignore[assignment]

            self.assertEqual(loaded, [(folder, image_file)])
            self.assertEqual(fake_shell32.finished, [43])

    def test_dropped_image_routes_to_parent_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            image_file = folder / "image.jpg"
            image_file.write_text("dummy", encoding="utf-8")
            window = main_window.MainWindow()

            self.assertEqual(window._folder_from_dropped_path(image_file), folder)

    def test_dropped_non_image_file_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            text_file = Path(temp_dir) / "note.txt"
            text_file.write_text("dummy", encoding="utf-8")
            window = main_window.MainWindow()

            self.assertIsNone(window._folder_from_dropped_path(text_file))

    def test_load_folder_selects_requested_image_after_sorting(self) -> None:
        original_scan_image_files = main_window.scan_image_files
        folder = Path("C:/images")
        image_files = [
            _image_file(folder / "alpha.jpg", 1),
            _image_file(folder / "beta.jpg", 2),
            _image_file(folder / "gamma.jpg", 3),
        ]
        window = main_window.MainWindow()
        preview_requests: list[ImageFile] = []
        window.sort_descending = True
        window.folder_label = 101
        window.status_bar = 102
        window._require_controls = lambda: None  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]
        window._start_thumbnail_worker = lambda _load_id, _image_files, _size: None  # type: ignore[method-assign]
        window._start_preview_worker = lambda image_file, show_loading=True: preview_requests.append(image_file)  # type: ignore[method-assign]
        window.thumbnail_grid._client_width = lambda: 400  # type: ignore[method-assign]
        window.thumbnail_grid._client_height = lambda: 430  # type: ignore[method-assign]
        window.thumbnail_grid.on_selection_changed = window._select_image

        try:
            main_window.scan_image_files = lambda _folder: list(image_files)  # type: ignore[assignment]

            window.load_folder(folder, select_path=image_files[0].path)
        finally:
            main_window.scan_image_files = original_scan_image_files  # type: ignore[assignment]

        self.assertEqual([image_file.name for image_file in window.thumbnail_grid.items], ["gamma.jpg", "beta.jpg", "alpha.jpg"])
        self.assertEqual(window.thumbnail_grid.selected_index, 2)
        self.assertEqual(window._selected_image_file, image_files[0])
        self.assertEqual(preview_requests, [image_files[0]])


if __name__ == "__main__":
    unittest.main()

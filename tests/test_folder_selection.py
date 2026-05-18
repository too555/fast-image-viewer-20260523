from __future__ import annotations

import unittest
import ctypes
from pathlib import Path

import app.ui.main_window as main_window


class FakeShell32:
    def __init__(self) -> None:
        self.browse_called = False
        self.path_requested = False

    def SHBrowseForFolderW(self, _browse_info: object) -> int:
        self.browse_called = True
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

    def test_handle_select_folder_loads_selected_folder(self) -> None:
        window = main_window.MainWindow()
        selected = Path("C:/selected-images")
        loaded: list[Path] = []
        window._choose_folder = lambda: selected  # type: ignore[method-assign]
        window.load_folder = lambda folder: loaded.append(folder)  # type: ignore[method-assign]

        window._handle_select_folder()

        self.assertEqual(loaded, [selected])


if __name__ == "__main__":
    unittest.main()

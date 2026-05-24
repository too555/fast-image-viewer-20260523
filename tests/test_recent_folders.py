from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core.image_scanner import ImageFile
from app.core.recent_folders import (
    DEFAULT_CACHE_SIZE_LIMIT_BYTES,
    MAX_FAVORITE_FOLDERS,
    MAX_RECENT_FOLDERS,
    add_favorite_folder,
    add_recent_folder,
    load_cache_size_limit_bytes,
    load_favorite_folders,
    load_preview_width,
    load_recent_folders,
    load_resize_output_folder,
    move_favorite_folder,
    remove_favorite_folder,
    remove_recent_folder,
    save_cache_size_limit_bytes,
    save_favorite_folders,
    save_preview_width,
    save_recent_folders,
    save_resize_output_folder,
)
from app.ui import main_window


def _image_file(path: Path) -> ImageFile:
    return ImageFile(path=path, name=path.name, suffix=path.suffix, size=100, mtime=1.0)


class RecentFoldersTest(unittest.TestCase):
    def test_add_recent_folder_moves_existing_to_front_and_limits_count(self) -> None:
        folders = [Path(f"C:/images/folder-{index}") for index in range(12)]

        recent: list[Path] = []
        for folder in folders:
            recent = add_recent_folder(recent, folder)
        recent = add_recent_folder(recent, folders[3])

        self.assertEqual(recent[0], folders[3])
        self.assertEqual(len(recent), MAX_RECENT_FOLDERS)
        self.assertEqual(len({str(folder).casefold() for folder in recent}), MAX_RECENT_FOLDERS)

    def test_add_favorite_folder_avoids_duplicates_and_limits_count(self) -> None:
        folders = [Path(f"C:/images/favorite-{index}") for index in range(24)]

        favorites: list[Path] = []
        for folder in folders:
            favorites = add_favorite_folder(favorites, folder)
        favorites = add_favorite_folder(favorites, folders[10])

        self.assertEqual(favorites[0], folders[-1])
        self.assertEqual(len(favorites), MAX_FAVORITE_FOLDERS)
        self.assertEqual(favorites.count(folders[10]), 1)

    def test_save_and_load_recent_and_favorite_folders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            recent = [Path("C:/images/recent-a"), Path("C:/images/recent-b")]
            favorites = [Path("C:/images/favorite-a"), Path("C:/images/favorite-b")]

            save_recent_folders(recent, settings_path=settings_path)
            save_favorite_folders(favorites, settings_path=settings_path)

            self.assertEqual(load_recent_folders(settings_path=settings_path), recent)
            self.assertEqual(load_favorite_folders(settings_path=settings_path), favorites)

    def test_save_and_load_preview_width_and_resize_output_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            recent = [Path("C:/images/recent-a")]
            favorite = [Path("C:/images/favorite-a")]
            output_folder = Path("C:/exports/resized")

            save_recent_folders(recent, settings_path=settings_path)
            save_favorite_folders(favorite, settings_path=settings_path)
            save_preview_width(640, settings_path=settings_path)
            save_resize_output_folder(output_folder, settings_path=settings_path)

            self.assertEqual(load_preview_width(settings_path=settings_path), 640)
            self.assertEqual(load_resize_output_folder(settings_path=settings_path), output_folder)
            self.assertEqual(load_recent_folders(settings_path=settings_path), recent)
            self.assertEqual(load_favorite_folders(settings_path=settings_path), favorite)

    def test_invalid_preview_width_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text('{"preview_width": -1}', encoding="utf-8")

            self.assertIsNone(load_preview_width(settings_path=settings_path))

    def test_save_and_load_cache_size_limit_preserves_other_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            recent = [Path("C:/images/recent-a")]

            save_recent_folders(recent, settings_path=settings_path)
            save_cache_size_limit_bytes(512 * 1024 * 1024, settings_path=settings_path)

            self.assertEqual(load_cache_size_limit_bytes(settings_path=settings_path), 512 * 1024 * 1024)
            self.assertEqual(load_recent_folders(settings_path=settings_path), recent)

    def test_invalid_cache_size_limit_uses_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text('{"cache_size_limit_bytes": 0}', encoding="utf-8")

            self.assertEqual(load_cache_size_limit_bytes(settings_path=settings_path), DEFAULT_CACHE_SIZE_LIMIT_BYTES)

    def test_remove_recent_folder_matches_case_insensitively(self) -> None:
        folders = [Path("C:/Images/A"), Path("C:/Images/B")]

        self.assertEqual(remove_recent_folder(folders, Path("c:/images/a")), [folders[1]])

    def test_remove_favorite_folder_matches_case_insensitively(self) -> None:
        folders = [Path("C:/Images/Favorite-A"), Path("C:/Images/Favorite-B")]

        self.assertEqual(remove_favorite_folder(folders, Path("c:/images/favorite-a")), [folders[1]])

    def test_move_favorite_folder_reorders_with_bounds(self) -> None:
        folders = [Path("C:/Images/A"), Path("C:/Images/B"), Path("C:/Images/C")]

        moved_up, moved_up_index = move_favorite_folder(folders, 2, -1)
        moved_down, moved_down_index = move_favorite_folder(folders, 0, 1)
        unchanged_top, unchanged_top_index = move_favorite_folder(folders, 0, -1)

        self.assertEqual(moved_up, [folders[0], folders[2], folders[1]])
        self.assertEqual(moved_up_index, 1)
        self.assertEqual(moved_down, [folders[1], folders[0], folders[2]])
        self.assertEqual(moved_down_index, 1)
        self.assertEqual(unchanged_top, folders)
        self.assertEqual(unchanged_top_index, 0)

    def test_favorite_folder_display_text_uses_folder_name(self) -> None:
        folder = Path("C:/Albums/旅行")
        window = main_window.MainWindow()
        window.favorite_folders = [folder]

        self.assertEqual(window._favorite_folder_display_text(folder), "旅行")

    def test_favorite_folder_display_text_adds_parent_for_duplicate_names(self) -> None:
        first = Path("C:/2026静岡/写真")
        second = Path("D:/2026東京/写真")
        window = main_window.MainWindow()
        window.favorite_folders = [first, second]

        self.assertEqual(window._favorite_folder_display_text(first), "写真（2026静岡）")
        self.assertEqual(window._favorite_folder_display_text(second), "写真（2026東京）")

    def test_recent_folder_display_text_uses_folder_name(self) -> None:
        folder = Path("C:/Albums/Travel")
        window = main_window.MainWindow()
        window.recent_folders = [folder]

        self.assertEqual(window._recent_folder_display_text(folder), "Travel")

    def test_recent_folder_display_text_adds_parent_for_duplicate_names(self) -> None:
        first = Path("C:/Parent-A/Photos")
        second = Path("D:/Parent-B/Photos")
        window = main_window.MainWindow()
        window.recent_folders = [first, second]

        self.assertEqual(window._recent_folder_display_text(first), "Photos（Parent-A）")
        self.assertEqual(window._recent_folder_display_text(second), "Photos（Parent-B）")

    def test_folder_status_text_uses_full_path(self) -> None:
        folder = Path("C:/Very/Long/Album")
        window = main_window.MainWindow()

        self.assertEqual(window._folder_status_text("現在フォルダ", folder), f"現在フォルダ: {folder}")

    def test_load_folder_adds_successful_folder_to_history(self) -> None:
        original_scan_image_files = main_window.scan_image_files
        original_save_recent_folders = main_window.save_recent_folders
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            image_file = _image_file(folder / "image.jpg")
            saved: list[list[Path]] = []
            window = main_window.MainWindow()
            window.hwnd = 1
            window.folder_label = 101
            window.status_bar = 102
            window._require_controls = lambda: None  # type: ignore[method-assign]
            window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]
            window._start_thumbnail_worker = lambda _load_id, _image_files, _size: None  # type: ignore[method-assign]

            try:
                main_window.scan_image_files = lambda _folder: [image_file]  # type: ignore[assignment]
                main_window.save_recent_folders = lambda folders: saved.append(list(folders))  # type: ignore[assignment]

                window.load_folder(folder)
            finally:
                main_window.scan_image_files = original_scan_image_files
                main_window.save_recent_folders = original_save_recent_folders

        self.assertEqual(window.recent_folders[0], folder)
        self.assertEqual(saved[-1][0], folder)

    def test_load_folder_reports_full_path_in_status(self) -> None:
        original_scan_image_files = main_window.scan_image_files
        original_save_recent_folders = main_window.save_recent_folders
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            image_file = _image_file(folder / "image.jpg")
            status_text: list[str] = []
            window = main_window.MainWindow()
            window.hwnd = 1
            window.folder_label = 101
            window.status_bar = 102
            window._require_controls = lambda: None  # type: ignore[method-assign]
            window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]
            window._start_thumbnail_worker = lambda _load_id, _image_files, _size: None  # type: ignore[method-assign]

            try:
                main_window.scan_image_files = lambda _folder: [image_file]  # type: ignore[assignment]
                main_window.save_recent_folders = lambda _folders: None  # type: ignore[assignment]

                window.load_folder(folder)
            finally:
                main_window.scan_image_files = original_scan_image_files
                main_window.save_recent_folders = original_save_recent_folders

        self.assertTrue(any(str(folder) in text for text in status_text))

    def test_recent_selection_reports_full_path_before_loading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            status_text: list[str] = []
            loaded: list[Path] = []
            window = main_window.MainWindow()
            window.recent_folders = [folder]
            window.status_bar = 102
            window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]
            window.load_folder = lambda selected_folder: loaded.append(selected_folder)  # type: ignore[method-assign]

            result = window._load_recent_folder_from_history(0)

        self.assertTrue(result)
        self.assertEqual(loaded, [folder])
        self.assertIn(str(folder), status_text[-1])

    def test_favorite_selection_reports_full_path_before_loading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            status_text: list[str] = []
            loaded: list[Path] = []
            window = main_window.MainWindow()
            window.favorite_folders = [folder]
            window.status_bar = 102
            window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]
            window.load_folder = lambda selected_folder: loaded.append(selected_folder)  # type: ignore[method-assign]

            result = window._load_favorite_folder(0)

        self.assertTrue(result)
        self.assertEqual(loaded, [folder])
        self.assertIn(str(folder), status_text[-1])

    def test_copy_folder_path_uses_full_path(self) -> None:
        folder = Path("C:/Albums/Long/Folder")
        copied: list[str] = []
        status_text: list[str] = []
        window = main_window.MainWindow()
        window.hwnd = 1
        window.current_folder = folder
        window.status_bar = 102
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]

        result = window._handle_copy_folder_path()

        self.assertTrue(result)
        self.assertEqual(copied, [str(folder)])
        self.assertIn("フォルダパスをコピーしました", status_text[-1])
        self.assertIn(str(folder), status_text[-1])

    def test_copy_folder_path_without_folder_does_not_crash(self) -> None:
        copied: list[str] = []
        status_text: list[str] = []
        window = main_window.MainWindow()
        window.status_bar = 102
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]

        result = window._handle_copy_folder_path()

        self.assertFalse(result)
        self.assertEqual(copied, [])
        self.assertIn("コピーするフォルダがありません", status_text[-1])

    def test_copy_image_path_uses_selected_image_full_path(self) -> None:
        image_path = Path("C:/Albums/Long/Folder/image.jpg")
        copied: list[str] = []
        status_text: list[str] = []
        window = main_window.MainWindow()
        window.hwnd = 1
        window._selected_image_file = _image_file(image_path)
        window.status_bar = 102
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]

        result = window._handle_copy_image_path()

        self.assertTrue(result)
        self.assertEqual(copied, [str(image_path)])
        self.assertIn("画像パスをコピーしました", status_text[-1])
        self.assertIn(str(image_path), status_text[-1])

    def test_copy_image_path_without_selection_does_not_crash(self) -> None:
        copied: list[str] = []
        status_text: list[str] = []
        window = main_window.MainWindow()
        window.status_bar = 102
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]

        result = window._handle_copy_image_path()

        self.assertFalse(result)
        self.assertEqual(copied, [])
        self.assertIn("コピーする画像が選択されていません", status_text[-1])

    def test_copy_shortcut_dispatches_image_and_folder_copy(self) -> None:
        original_ctrl_pressed = main_window._ctrl_pressed
        original_shift_pressed = main_window._shift_pressed
        calls: list[str] = []
        window = main_window.MainWindow()
        window._handle_copy_image_path = lambda: calls.append("image") or True  # type: ignore[method-assign]
        window._handle_copy_folder_path = lambda: calls.append("folder") or True  # type: ignore[method-assign]

        try:
            main_window._ctrl_pressed = lambda: True  # type: ignore[assignment]
            main_window._shift_pressed = lambda: True  # type: ignore[assignment]

            self.assertTrue(window._handle_copy_shortcut(main_window.VK_C))
            self.assertTrue(window._handle_copy_shortcut(main_window.VK_F))
            self.assertFalse(window._handle_copy_shortcut(main_window.VK_RIGHT))
        finally:
            main_window._ctrl_pressed = original_ctrl_pressed
            main_window._shift_pressed = original_shift_pressed

        self.assertEqual(calls, ["image", "folder"])

    def test_copy_shortcut_requires_ctrl_and_shift(self) -> None:
        original_ctrl_pressed = main_window._ctrl_pressed
        original_shift_pressed = main_window._shift_pressed
        calls: list[str] = []
        window = main_window.MainWindow()
        window._handle_copy_image_path = lambda: calls.append("image") or True  # type: ignore[method-assign]

        try:
            main_window._ctrl_pressed = lambda: True  # type: ignore[assignment]
            main_window._shift_pressed = lambda: False  # type: ignore[assignment]

            self.assertFalse(window._handle_copy_shortcut(main_window.VK_C))
        finally:
            main_window._ctrl_pressed = original_ctrl_pressed
            main_window._shift_pressed = original_shift_pressed

        self.assertEqual(calls, [])

    def test_thumbnail_context_menu_copies_right_clicked_image_path(self) -> None:
        right_clicked = _image_file(Path("C:/Albums/right-clicked.jpg"))
        selected = _image_file(Path("C:/Albums/selected.jpg"))
        copied: list[str] = []
        window = main_window.MainWindow()
        window.hwnd = 1
        window.status_bar = 102
        window._selected_image_file = selected
        window._control_point_to_screen = lambda _hwnd, x, y: (x, y)  # type: ignore[method-assign]
        window._show_path_context_menu = lambda _x, _y: main_window.CONTEXT_COPY_IMAGE_PATH_ID  # type: ignore[method-assign]
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]

        window._handle_thumbnail_context_menu(1, 10, 10, right_clicked)

        self.assertEqual(copied, [str(right_clicked.path)])

    def test_thumbnail_context_menu_without_image_does_not_crash(self) -> None:
        copied: list[str] = []
        status_text: list[str] = []
        window = main_window.MainWindow()
        window.hwnd = 1
        window.status_bar = 102
        window._control_point_to_screen = lambda _hwnd, x, y: (x, y)  # type: ignore[method-assign]
        window._show_path_context_menu = lambda _x, _y: main_window.CONTEXT_COPY_IMAGE_PATH_ID  # type: ignore[method-assign]
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]

        window._handle_thumbnail_context_menu(1, 10, 10, None)

        self.assertEqual(copied, [])
        self.assertIn("コピーする画像がありません", status_text[-1])

    def test_preview_context_menu_copies_selected_image_path(self) -> None:
        image_file = _image_file(Path("C:/Albums/selected.jpg"))
        copied: list[str] = []
        window = main_window.MainWindow()
        window.hwnd = 1
        window.status_bar = 102
        window._selected_image_file = image_file
        window._control_point_to_screen = lambda _hwnd, x, y: (x, y)  # type: ignore[method-assign]
        window._show_path_context_menu = lambda _x, _y: main_window.CONTEXT_COPY_IMAGE_PATH_ID  # type: ignore[method-assign]
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]

        window._handle_preview_context_menu(1, 10, 10)

        self.assertEqual(copied, [str(image_file.path)])

    def test_preview_context_menu_copies_current_folder_path(self) -> None:
        folder = Path("C:/Albums")
        copied: list[str] = []
        window = main_window.MainWindow()
        window.hwnd = 1
        window.status_bar = 102
        window.current_folder = folder
        window._control_point_to_screen = lambda _hwnd, x, y: (x, y)  # type: ignore[method-assign]
        window._show_path_context_menu = lambda _x, _y: main_window.CONTEXT_COPY_FOLDER_PATH_ID  # type: ignore[method-assign]
        window._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, _text: None  # type: ignore[method-assign]

        window._handle_preview_context_menu(1, 10, 10)

        self.assertEqual(copied, [str(folder)])

    def test_add_current_folder_to_favorites(self) -> None:
        original_save_favorite_folders = main_window.save_favorite_folders
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            saved: list[list[Path]] = []
            status_text: list[str] = []
            window = main_window.MainWindow()
            window.current_folder = folder
            window.favorite_folders = []
            window.status_bar = 102
            window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]

            try:
                main_window.save_favorite_folders = lambda folders: saved.append(list(folders))  # type: ignore[assignment]

                window._handle_add_favorite_folder()
                window._handle_add_favorite_folder()
            finally:
                main_window.save_favorite_folders = original_save_favorite_folders

            self.assertEqual(window.favorite_folders, [folder])
            self.assertEqual(saved[-1], [folder])
            self.assertIn("すでにお気に入り", status_text[-1])

    def test_remove_selected_favorite_folder(self) -> None:
        original_save_favorite_folders = main_window.save_favorite_folders
        folders = [Path("C:/Images/Favorite-A"), Path("C:/Images/Favorite-B")]
        saved: list[list[Path]] = []
        status_text: list[str] = []
        window = main_window.MainWindow()
        window.favorite_folders = folders[:]
        window.status_bar = 102
        window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]

        try:
            main_window.save_favorite_folders = lambda favorite_folders: saved.append(list(favorite_folders))  # type: ignore[assignment]

            result = window._remove_favorite_folder_at(0)
        finally:
            main_window.save_favorite_folders = original_save_favorite_folders

        self.assertTrue(result)
        self.assertEqual(window.favorite_folders, [folders[1]])
        self.assertEqual(saved[-1], [folders[1]])
        self.assertIn("お気に入りから削除しました", status_text[-1])

    def test_move_selected_favorite_folder_saves_order(self) -> None:
        original_save_favorite_folders = main_window.save_favorite_folders
        folders = [Path("C:/Images/Favorite-A"), Path("C:/Images/Favorite-B"), Path("C:/Images/Favorite-C")]
        saved: list[list[Path]] = []
        status_text: list[str] = []
        window = main_window.MainWindow()
        window.favorite_folders = folders[:]
        window.status_bar = 102
        window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]

        try:
            main_window.save_favorite_folders = lambda favorite_folders: saved.append(list(favorite_folders))  # type: ignore[assignment]

            result = window._move_favorite_folder_at(2, -1)
        finally:
            main_window.save_favorite_folders = original_save_favorite_folders

        self.assertTrue(result)
        self.assertEqual(window.favorite_folders, [folders[0], folders[2], folders[1]])
        self.assertEqual(saved[-1], [folders[0], folders[2], folders[1]])
        self.assertIn("お気に入りの順序を変更しました", status_text[-1])

    def test_move_selected_favorite_folder_does_not_save_at_edge(self) -> None:
        original_save_favorite_folders = main_window.save_favorite_folders
        folders = [Path("C:/Images/Favorite-A"), Path("C:/Images/Favorite-B")]
        saved: list[list[Path]] = []
        status_text: list[str] = []
        window = main_window.MainWindow()
        window.favorite_folders = folders[:]
        window.status_bar = 102
        window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]

        try:
            main_window.save_favorite_folders = lambda favorite_folders: saved.append(list(favorite_folders))  # type: ignore[assignment]

            result = window._move_favorite_folder_at(0, -1)
        finally:
            main_window.save_favorite_folders = original_save_favorite_folders

        self.assertFalse(result)
        self.assertEqual(window.favorite_folders, folders)
        self.assertEqual(saved, [])
        self.assertIn("これ以上上へ移動できません", status_text[-1])

    def test_missing_recent_folder_is_removed_without_loading(self) -> None:
        original_save_recent_folders = main_window.save_recent_folders
        missing_folder = Path("C:/missing-recent-folder")
        saved: list[list[Path]] = []
        status_text: list[str] = []
        loaded: list[Path] = []
        window = main_window.MainWindow()
        window.recent_folders = [missing_folder]
        window.status_bar = 102
        window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]
        window.load_folder = lambda folder: loaded.append(folder)  # type: ignore[method-assign]

        try:
            main_window.save_recent_folders = lambda folders: saved.append(list(folders))  # type: ignore[assignment]

            result = window._load_recent_folder_from_history(0)
        finally:
            main_window.save_recent_folders = original_save_recent_folders

        self.assertFalse(result)
        self.assertEqual(window.recent_folders, [])
        self.assertEqual(saved[-1], [])
        self.assertEqual(loaded, [])
        self.assertIn("履歴のフォルダが見つかりません", status_text[-1])

    def test_cleanup_invalid_history_removes_missing_recent_and_favorites(self) -> None:
        original_save_recent_folders = main_window.save_recent_folders
        original_save_favorite_folders = main_window.save_favorite_folders
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_recent = Path(temp_dir) / "valid-recent"
            valid_favorite = Path(temp_dir) / "valid-favorite"
            valid_recent.mkdir()
            valid_favorite.mkdir()
            missing_recent = Path(temp_dir) / "missing-recent"
            missing_favorite = Path(temp_dir) / "missing-favorite"
            saved_recent: list[list[Path]] = []
            saved_favorites: list[list[Path]] = []
            window = main_window.MainWindow()
            window.recent_folders = [valid_recent, missing_recent]
            window.favorite_folders = [missing_favorite, valid_favorite]

            try:
                main_window.save_recent_folders = lambda folders: saved_recent.append(list(folders))  # type: ignore[assignment]
                main_window.save_favorite_folders = lambda folders: saved_favorites.append(list(folders))  # type: ignore[assignment]

                result = window._cleanup_invalid_history()
            finally:
                main_window.save_recent_folders = original_save_recent_folders
                main_window.save_favorite_folders = original_save_favorite_folders

            self.assertEqual(result, (1, 1))
            self.assertEqual(window.recent_folders, [valid_recent])
            self.assertEqual(window.favorite_folders, [valid_favorite])
            self.assertEqual(saved_recent[-1], [valid_recent])
            self.assertEqual(saved_favorites[-1], [valid_favorite])

    def test_cleanup_invalid_history_reports_when_nothing_removed(self) -> None:
        original_save_recent_folders = main_window.save_recent_folders
        original_save_favorite_folders = main_window.save_favorite_folders
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_recent = Path(temp_dir) / "valid-recent"
            valid_favorite = Path(temp_dir) / "valid-favorite"
            valid_recent.mkdir()
            valid_favorite.mkdir()
            saved_recent: list[list[Path]] = []
            saved_favorites: list[list[Path]] = []
            status_text: list[str] = []
            window = main_window.MainWindow()
            window.recent_folders = [valid_recent]
            window.favorite_folders = [valid_favorite]
            window.status_bar = 102
            window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]

            try:
                main_window.save_recent_folders = lambda folders: saved_recent.append(list(folders))  # type: ignore[assignment]
                main_window.save_favorite_folders = lambda folders: saved_favorites.append(list(folders))  # type: ignore[assignment]

                window._handle_cleanup_invalid_history()
            finally:
                main_window.save_recent_folders = original_save_recent_folders
                main_window.save_favorite_folders = original_save_favorite_folders

            self.assertEqual(saved_recent, [])
            self.assertEqual(saved_favorites, [])
            self.assertIn("整理対象はありません", status_text[-1])

    def test_load_folder_removes_missing_saved_folder_without_error_dialog(self) -> None:
        original_save_recent_folders = main_window.save_recent_folders
        original_save_favorite_folders = main_window.save_favorite_folders
        missing_folder = Path("C:/missing-saved-folder")
        saved_recent: list[list[Path]] = []
        saved_favorites: list[list[Path]] = []
        status_text: list[str] = []
        window = main_window.MainWindow()
        window.recent_folders = [missing_folder]
        window.favorite_folders = [missing_folder]
        window.status_bar = 102
        window._require_controls = lambda: None  # type: ignore[method-assign]
        window._refresh_recent_folder_combo = lambda: None  # type: ignore[method-assign]
        window._refresh_favorite_folder_combo = lambda selected_index=None: None  # type: ignore[method-assign]
        window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]

        try:
            main_window.save_recent_folders = lambda folders: saved_recent.append(list(folders))  # type: ignore[assignment]
            main_window.save_favorite_folders = lambda folders: saved_favorites.append(list(folders))  # type: ignore[assignment]

            window.load_folder(missing_folder)
        finally:
            main_window.save_recent_folders = original_save_recent_folders
            main_window.save_favorite_folders = original_save_favorite_folders

        self.assertEqual(window.recent_folders, [])
        self.assertEqual(window.favorite_folders, [])
        self.assertEqual(saved_recent[-1], [])
        self.assertEqual(saved_favorites[-1], [])
        self.assertIn("保存済みフォルダが見つからないため整理しました", status_text[-1])

    def test_missing_favorite_folder_is_removed_without_loading(self) -> None:
        original_save_favorite_folders = main_window.save_favorite_folders
        missing_folder = Path("C:/missing-favorite-folder")
        saved: list[list[Path]] = []
        status_text: list[str] = []
        loaded: list[Path] = []
        window = main_window.MainWindow()
        window.favorite_folders = [missing_folder]
        window.status_bar = 102
        window._set_window_text = lambda _hwnd, text: status_text.append(text)  # type: ignore[method-assign]
        window.load_folder = lambda folder: loaded.append(folder)  # type: ignore[method-assign]

        try:
            main_window.save_favorite_folders = lambda folders: saved.append(list(folders))  # type: ignore[assignment]

            result = window._load_favorite_folder(0)
        finally:
            main_window.save_favorite_folders = original_save_favorite_folders

        self.assertFalse(result)
        self.assertEqual(window.favorite_folders, [])
        self.assertEqual(saved[-1], [])
        self.assertEqual(loaded, [])
        self.assertIn("存在しないお気に入りを整理しました", status_text[-1])


if __name__ == "__main__":
    unittest.main()

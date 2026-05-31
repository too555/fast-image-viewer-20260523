from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.core.recent_folders import DEFAULT_THUMBNAIL_SIZE, load_thumbnail_size, save_thumbnail_size
from app.core.viewer_options import (
    OPTION_STATUS_LINES,
    OPTION_TABS,
    build_display_viewer_options,
    default_viewer_options,
    load_viewer_options,
    save_viewer_options,
    update_viewer_options,
)


class ViewerOptionsTest(unittest.TestCase):
    def test_acdsee_style_tabs_are_defined(self) -> None:
        self.assertEqual(
            [title for _key, title in OPTION_TABS],
            [
                "ブラウザ",
                "ファイルリスト",
                "サムネイル",
                "ビューア",
                "スライドショー",
                "画面表示",
                "ファイル操作",
                "その他",
            ],
        )

    def test_save_and_load_viewer_options_preserves_existing_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(json.dumps({"recent_folders": ["C:/Images"]}), encoding="utf-8")

            save_viewer_options(
                {
                    "thumbnail": {"thumbnail_size": 160},
                    "file_list": {"sort_field": "size", "sort_descending": True},
                },
                settings_path=settings_path,
            )

            data = json.loads(settings_path.read_text(encoding="utf-8"))
            options = load_viewer_options(settings_path=settings_path)
            self.assertEqual(data["recent_folders"], ["C:/Images"])
            self.assertEqual(options["thumbnail"]["thumbnail_size"], 160)
            self.assertEqual(options["file_list"]["sort_field"], "size")
            self.assertTrue(options["file_list"]["sort_descending"])
            self.assertTrue(options["browser"]["show_folder_tree"])

    def test_update_viewer_options_normalizes_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(
                json.dumps(
                    {
                        "viewer_options": {
                            "browser": {"show_toolbar": "yes"},
                            "file_list": {"sort_field": "unknown"},
                            "thumbnail": {"thumbnail_size": 999},
                            "slideshow": {"interval_ms": -1},
                        }
                    }
                ),
                encoding="utf-8",
            )

            options = update_viewer_options("thumbnail", {"thumbnail_size": 256}, settings_path=settings_path)

            self.assertTrue(options["browser"]["show_toolbar"])
            self.assertEqual(options["file_list"]["sort_field"], "name")
            self.assertEqual(options["thumbnail"]["thumbnail_size"], 256)
            self.assertEqual(options["slideshow"]["interval_ms"], 3000)

    def test_ok_style_save_persists_pending_options(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            pending = build_display_viewer_options(
                default_viewer_options(),
                thumbnail_size=256,
                show_status_bar=False,
                show_path_bar=False,
                show_folder_tree=True,
                show_preview=False,
            )

            save_viewer_options(pending, settings_path=settings_path)
            save_thumbnail_size(256, settings_path=settings_path)

            options = load_viewer_options(settings_path=settings_path)
            self.assertFalse(options["display"]["show_status_bar"])
            self.assertFalse(options["display"]["show_path_bar"])
            self.assertTrue(options["display"]["show_folder_tree"])
            self.assertFalse(options["browser"]["show_preview"])
            self.assertEqual(options["thumbnail"]["thumbnail_size"], 256)
            self.assertEqual(load_thumbnail_size(settings_path=settings_path), 256)

    def test_cancel_style_pending_options_do_not_save_until_ok(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            save_viewer_options(default_viewer_options(), settings_path=settings_path)

            build_display_viewer_options(
                default_viewer_options(),
                thumbnail_size=64,
                show_status_bar=False,
                show_path_bar=False,
                show_folder_tree=False,
                show_preview=False,
            )

            options = load_viewer_options(settings_path=settings_path)
            self.assertTrue(options["display"]["show_status_bar"])
            self.assertTrue(options["display"]["show_path_bar"])
            self.assertTrue(options["display"]["show_folder_tree"])
            self.assertTrue(options["browser"]["show_preview"])
            self.assertEqual(options["thumbnail"]["thumbnail_size"], DEFAULT_THUMBNAIL_SIZE)

    def test_default_button_values_are_pending_until_ok(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            custom = build_display_viewer_options(
                default_viewer_options(),
                thumbnail_size=256,
                show_status_bar=False,
                show_path_bar=False,
                show_folder_tree=False,
                show_preview=False,
            )
            save_viewer_options(custom, settings_path=settings_path)

            default_viewer_options()
            options = load_viewer_options(settings_path=settings_path)
            self.assertFalse(options["display"]["show_status_bar"])
            self.assertEqual(options["thumbnail"]["thumbnail_size"], 256)

            save_viewer_options(default_viewer_options(), settings_path=settings_path)
            options = load_viewer_options(settings_path=settings_path)
            self.assertTrue(options["display"]["show_status_bar"])
            self.assertEqual(options["thumbnail"]["thumbnail_size"], DEFAULT_THUMBNAIL_SIZE)

    def test_future_file_operations_are_marked_as_future_only(self) -> None:
        file_operation_text = "\n".join(f"{label}: {status}" for label, status in OPTION_STATUS_LINES["file_operation"])

        self.assertIn("削除前に確認する", file_operation_text)
        self.assertIn("削除機能はまだありません", file_operation_text)
        self.assertIn("同名ファイルの扱い", file_operation_text)
        self.assertIn("Descriptionファイル関連", file_operation_text)
        self.assertIn("将来拡張", file_operation_text)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from app.core.recent_folders import (
    DEFAULT_THUMBNAIL_SIZE,
    THUMBNAIL_SIZE_OPTIONS,
    settings_file_path,
)
from app.utils.long_path import make_dirs


VIEWER_OPTIONS_KEY = "viewer_options"

OPTION_TABS: tuple[tuple[str, str], ...] = (
    ("browser", "ブラウザ"),
    ("file_list", "ファイルリスト"),
    ("thumbnail", "サムネイル"),
    ("viewer", "ビューア"),
    ("slideshow", "スライドショー"),
    ("display", "画面表示"),
    ("file_operation", "ファイル操作"),
    ("other", "その他"),
)

OPTION_STATUS_LINES: dict[str, tuple[tuple[str, str], ...]] = {
    "browser": (
        ("ツールバーを表示", "今後対応"),
        ("ステータスバーを表示", "反映済み（即時）"),
        ("メニューを表示", "今後対応"),
        ("フォルダパスを表示", "反映済み（即時）"),
        ("フォルダツリーを表示", "反映済み（即時）"),
        ("プレビューを表示", "反映済み（即時）"),
        ("前回使用したフォルダで起動", "今後対応"),
    ),
    "file_list": (
        ("画像以外のファイルを表示", "今後対応"),
        ("隠しファイルを表示", "今後対応"),
        ("システムアイコンを使用", "今後対応"),
        ("グリッド線を表示", "今後対応"),
        ("行全体を選択", "今後対応"),
        ("新しいファイルを自動選択", "一部反映済み"),
    ),
    "thumbnail": (
        ("サムネイルサイズ", "反映済み（即時）"),
        ("境界線幅", "今後対応"),
        ("キャッシュを保存する", "今後対応（現在は使用する固定）"),
        ("キャッシュ保存先", "今後対応"),
        ("フォルダ項目を表示", "今後対応"),
        ("画像以外のファイルを表示", "今後対応"),
    ),
    "viewer": (
        ("ツールバーを表示", "今後対応"),
        ("ステータスバーを表示", "反映済み（即時）"),
        ("メニューを表示", "今後対応"),
        ("ファイルパスを表示", "反映済み"),
        ("画像に合わせてウィンドウサイズ変更", "今後対応"),
        ("画像を中央に表示", "反映済み"),
        ("フォルダ内のすべての画像を表示", "対応済み"),
        ("マウスホイール・キー移動", "対応済み"),
    ),
    "slideshow": (
        ("昇順", "今後対応"),
        ("降順", "今後対応"),
        ("ランダム", "今後対応"),
        ("繰り返し", "今後対応"),
        ("表示間隔ミリ秒", "今後対応"),
        ("次画像の先読み", "今後対応"),
        ("読み込み完了まで表示遅延", "今後対応"),
    ),
    "display": (
        ("上部をコンパクトに表示", "反映済み"),
        ("パスバーを表示", "反映済み（即時）"),
        ("ステータスバーを表示", "反映済み（即時）"),
        ("左フォルダツリーを表示", "反映済み（即時）"),
        ("比較表示レイアウト", "対応済み"),
    ),
    "file_operation": (
        ("削除前に確認する", "今後対応（削除機能はまだありません）"),
        ("ごみ箱を使用する", "今後対応（削除機能はまだありません）"),
        ("同名ファイルの扱い", "今後対応（移動・コピー機能はまだありません）"),
        ("Descriptionファイル関連", "将来拡張"),
    ),
    "other": (
        ("設定をJSONに保存", "対応済み"),
        ("ベンチマークモード", "対応済み"),
        ("配布前チェック", "対応済み"),
        ("外部通信なしの軽量動作", "維持中"),
    ),
}

DEFAULT_VIEWER_OPTIONS: dict[str, dict[str, object]] = {
    "browser": {
        "show_toolbar": True,
        "show_status_bar": True,
        "show_menu": False,
        "show_path_box": True,
        "show_folder_tree": True,
        "show_preview": True,
        "restore_last_folder": False,
    },
    "file_list": {
        "show_non_images": False,
        "show_hidden_files": False,
        "use_system_icons": False,
        "show_grid_lines": False,
        "full_row_select": True,
        "auto_select_new_file": True,
    },
    "thumbnail": {
        "thumbnail_size": DEFAULT_THUMBNAIL_SIZE,
        "border_width": 1,
        "save_cache": True,
        "cache_folder": "",
        "show_folders": False,
        "show_non_images": False,
    },
    "viewer": {
        "show_toolbar": False,
        "show_status_bar": True,
        "show_menu": False,
        "show_file_path": True,
        "fit_window_to_image": False,
        "center_image": True,
        "show_all_folder_images": True,
        "mouse_wheel_key_navigation": True,
    },
    "slideshow": {
        "order": "ascending",
        "repeat": False,
        "interval_ms": 3000,
        "preload_next": True,
        "delay_until_loaded": True,
    },
    "display": {
        "compact_top_ui": True,
        "show_path_bar": True,
        "show_status_bar": True,
        "show_folder_tree": True,
    },
    "file_operation": {
        "confirm_delete": True,
        "use_recycle_bin": True,
        "duplicate_action": "ask",
    },
    "other": {
        "lightweight_mode": True,
    },
}


def default_viewer_options() -> dict[str, dict[str, object]]:
    return copy.deepcopy(DEFAULT_VIEWER_OPTIONS)


def load_viewer_options(settings_path: Path | None = None) -> dict[str, dict[str, object]]:
    data = _load_settings(settings_path)
    return _normalize_options(data.get(VIEWER_OPTIONS_KEY) if isinstance(data, dict) else None)


def save_viewer_options(options: dict[str, Any], settings_path: Path | None = None) -> None:
    _save_setting(VIEWER_OPTIONS_KEY, _normalize_options(options), settings_path)


def build_display_viewer_options(
    options: dict[str, Any],
    *,
    thumbnail_size: int,
    show_status_bar: bool,
    show_path_bar: bool,
    show_folder_tree: bool,
    show_preview: bool,
) -> dict[str, dict[str, object]]:
    updated = _normalize_options(options)
    updated["display"]["show_status_bar"] = bool(show_status_bar)
    updated["display"]["show_path_bar"] = bool(show_path_bar)
    updated["display"]["show_folder_tree"] = bool(show_folder_tree)
    updated["browser"]["show_status_bar"] = bool(show_status_bar)
    updated["browser"]["show_path_box"] = bool(show_path_bar)
    updated["browser"]["show_folder_tree"] = bool(show_folder_tree)
    updated["browser"]["show_preview"] = bool(show_preview)
    updated["thumbnail"]["thumbnail_size"] = (
        int(thumbnail_size) if thumbnail_size in THUMBNAIL_SIZE_OPTIONS else DEFAULT_THUMBNAIL_SIZE
    )
    return updated


def update_viewer_options(
    category: str,
    updates: dict[str, object],
    settings_path: Path | None = None,
) -> dict[str, dict[str, object]]:
    options = load_viewer_options(settings_path)
    if category not in options:
        return options
    options[category].update(updates)
    options = _normalize_options(options)
    _save_setting(VIEWER_OPTIONS_KEY, options, settings_path)
    return options


def _normalize_options(raw_options: object) -> dict[str, dict[str, object]]:
    options = default_viewer_options()
    if not isinstance(raw_options, dict):
        return options

    for category, defaults in DEFAULT_VIEWER_OPTIONS.items():
        raw_category = raw_options.get(category)
        if not isinstance(raw_category, dict):
            continue
        for key, default_value in defaults.items():
            raw_value = raw_category.get(key)
            normalized = _normalize_value(default_value, raw_value)
            if key == "thumbnail_size" and normalized not in THUMBNAIL_SIZE_OPTIONS:
                normalized = DEFAULT_THUMBNAIL_SIZE
            options[category][key] = normalized
    return options


def _normalize_value(default_value: object, raw_value: object) -> object:
    if isinstance(default_value, bool):
        return raw_value if isinstance(raw_value, bool) else default_value
    if isinstance(default_value, int) and not isinstance(default_value, bool):
        return raw_value if isinstance(raw_value, int) and not isinstance(raw_value, bool) and raw_value > 0 else default_value
    if isinstance(default_value, str):
        return raw_value if isinstance(raw_value, str) else default_value
    return raw_value if type(raw_value) is type(default_value) else default_value


def _save_setting(key: str, value: object, settings_path: Path | None = None) -> None:
    path = settings_path or settings_file_path()
    make_dirs(path.parent)
    data = _load_settings(path)
    data[key] = value
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_settings(settings_path: Path | None = None) -> dict[str, object]:
    path = settings_path or settings_file_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}

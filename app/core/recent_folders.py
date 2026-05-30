from __future__ import annotations

import json
import os
from pathlib import Path

from app.utils.long_path import display_path, make_dirs

MAX_RECENT_FOLDERS = 10
MAX_FAVORITE_FOLDERS = 20
SETTINGS_DIR_NAME = "FastImageViewer"
SETTINGS_FILE_NAME = "settings.json"
RECENT_FOLDERS_KEY = "recent_folders"
FAVORITE_FOLDERS_KEY = "favorite_folders"
PREVIEW_WIDTH_KEY = "preview_width"
RESIZE_OUTPUT_FOLDER_KEY = "resize_output_folder"
CACHE_SIZE_LIMIT_BYTES_KEY = "cache_size_limit_bytes"
THUMBNAIL_SIZE_KEY = "thumbnail_size"
DEFAULT_CACHE_SIZE_LIMIT_BYTES = 1024 * 1024 * 1024
DEFAULT_THUMBNAIL_SIZE = 128
THUMBNAIL_SIZE_OPTIONS = {64, 96, 128, 160, 256}


def settings_file_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / SETTINGS_DIR_NAME / SETTINGS_FILE_NAME
    return Path.home() / ".fast_image_viewer" / SETTINGS_FILE_NAME


def load_recent_folders(settings_path: Path | None = None) -> list[Path]:
    return _load_folder_list(RECENT_FOLDERS_KEY, MAX_RECENT_FOLDERS, settings_path)


def load_favorite_folders(settings_path: Path | None = None) -> list[Path]:
    return _load_folder_list(FAVORITE_FOLDERS_KEY, MAX_FAVORITE_FOLDERS, settings_path)


def load_preview_width(settings_path: Path | None = None) -> int | None:
    data = _load_settings(settings_path)
    raw_width = data.get(PREVIEW_WIDTH_KEY) if isinstance(data, dict) else None
    if isinstance(raw_width, bool):
        return None
    if isinstance(raw_width, int) and raw_width > 0:
        return raw_width
    return None


def load_resize_output_folder(settings_path: Path | None = None) -> Path | None:
    data = _load_settings(settings_path)
    raw_folder = data.get(RESIZE_OUTPUT_FOLDER_KEY) if isinstance(data, dict) else None
    if not isinstance(raw_folder, str) or not raw_folder:
        return None
    return display_path(raw_folder)


def load_cache_size_limit_bytes(settings_path: Path | None = None) -> int:
    data = _load_settings(settings_path)
    raw_limit = data.get(CACHE_SIZE_LIMIT_BYTES_KEY) if isinstance(data, dict) else None
    if isinstance(raw_limit, bool):
        return DEFAULT_CACHE_SIZE_LIMIT_BYTES
    if isinstance(raw_limit, int) and raw_limit > 0:
        return raw_limit
    return DEFAULT_CACHE_SIZE_LIMIT_BYTES


def load_thumbnail_size(settings_path: Path | None = None) -> int:
    data = _load_settings(settings_path)
    raw_size = data.get(THUMBNAIL_SIZE_KEY) if isinstance(data, dict) else None
    if isinstance(raw_size, bool):
        return DEFAULT_THUMBNAIL_SIZE
    if isinstance(raw_size, int) and raw_size in THUMBNAIL_SIZE_OPTIONS:
        return raw_size
    return DEFAULT_THUMBNAIL_SIZE


def save_recent_folders(folders: list[Path], settings_path: Path | None = None) -> None:
    _save_folder_list(RECENT_FOLDERS_KEY, folders, MAX_RECENT_FOLDERS, settings_path)


def save_favorite_folders(folders: list[Path], settings_path: Path | None = None) -> None:
    _save_folder_list(FAVORITE_FOLDERS_KEY, folders, MAX_FAVORITE_FOLDERS, settings_path)


def save_preview_width(width: int, settings_path: Path | None = None) -> None:
    if width <= 0:
        return
    _save_setting(PREVIEW_WIDTH_KEY, int(width), settings_path)


def save_resize_output_folder(folder: str | Path, settings_path: Path | None = None) -> None:
    _save_setting(RESIZE_OUTPUT_FOLDER_KEY, str(display_path(folder)), settings_path)


def save_cache_size_limit_bytes(limit_bytes: int, settings_path: Path | None = None) -> None:
    if limit_bytes <= 0:
        return
    _save_setting(CACHE_SIZE_LIMIT_BYTES_KEY, int(limit_bytes), settings_path)


def save_thumbnail_size(thumbnail_size: int, settings_path: Path | None = None) -> None:
    if thumbnail_size not in THUMBNAIL_SIZE_OPTIONS:
        return
    _save_setting(THUMBNAIL_SIZE_KEY, int(thumbnail_size), settings_path)


def add_recent_folder(folders: list[Path], folder: str | Path) -> list[Path]:
    normalized = display_path(folder)
    normalized_key = _folder_key(normalized)
    updated = [normalized]
    updated.extend(existing for existing in folders if _folder_key(existing) != normalized_key)
    return updated[:MAX_RECENT_FOLDERS]


def add_favorite_folder(folders: list[Path], folder: str | Path) -> list[Path]:
    normalized = display_path(folder)
    normalized_key = _folder_key(normalized)
    if any(_folder_key(existing) == normalized_key for existing in folders):
        return folders[:MAX_FAVORITE_FOLDERS]
    return [normalized, *folders][:MAX_FAVORITE_FOLDERS]


def remove_recent_folder(folders: list[Path], folder: str | Path) -> list[Path]:
    return _remove_folder(folders, folder)


def remove_favorite_folder(folders: list[Path], folder: str | Path) -> list[Path]:
    return _remove_folder(folders, folder)


def move_favorite_folder(folders: list[Path], selected_index: int, offset: int) -> tuple[list[Path], int]:
    limited = folders[:MAX_FAVORITE_FOLDERS]
    if selected_index < 0 or selected_index >= len(limited) or offset == 0:
        return limited, selected_index

    target_index = max(0, min(len(limited) - 1, selected_index + offset))
    if target_index == selected_index:
        return limited, selected_index

    folder = limited.pop(selected_index)
    limited.insert(target_index, folder)
    return limited, target_index


def _load_folder_list(key: str, limit: int, settings_path: Path | None = None) -> list[Path]:
    data = _load_settings(settings_path)
    raw_folders = data.get(key, []) if isinstance(data, dict) else []
    folders: list[Path] = []
    seen: set[str] = set()
    for raw_folder in raw_folders:
        if not isinstance(raw_folder, str) or not raw_folder:
            continue
        folder = display_path(raw_folder)
        folder_key = _folder_key(folder)
        if folder_key in seen:
            continue
        seen.add(folder_key)
        folders.append(folder)
        if len(folders) >= limit:
            break
    return folders


def _save_folder_list(key: str, folders: list[Path], limit: int, settings_path: Path | None = None) -> None:
    _save_setting(key, [str(folder) for folder in folders[:limit]], settings_path)


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


def _remove_folder(folders: list[Path], folder: str | Path) -> list[Path]:
    remove_key = _folder_key(folder)
    return [existing for existing in folders if _folder_key(existing) != remove_key]


def _folder_key(folder: str | Path) -> str:
    return str(display_path(folder)).casefold()

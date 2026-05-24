from __future__ import annotations

import os
from pathlib import Path

EXTENDED_PATH_PREFIX = "\\\\?\\"
EXTENDED_UNC_PREFIX = "\\\\?\\UNC\\"
DEVICE_PATH_PREFIX = "\\\\.\\"


def display_path(path: str | Path) -> Path:
    return Path(strip_extended_prefix(str(path)))


def strip_extended_prefix(path_text: str) -> str:
    if path_text.startswith(EXTENDED_UNC_PREFIX):
        return "\\\\" + path_text[len(EXTENDED_UNC_PREFIX) :]
    if path_text.startswith(EXTENDED_PATH_PREFIX):
        return path_text[len(EXTENDED_PATH_PREFIX) :]
    return path_text


def filesystem_path(path: str | Path) -> str:
    path_text = str(path)
    if os.name != "nt":
        return path_text

    if path_text.startswith(EXTENDED_PATH_PREFIX) or path_text.startswith(DEVICE_PATH_PREFIX):
        return path_text

    absolute_path = os.path.abspath(path_text)
    if absolute_path.startswith("\\\\"):
        return EXTENDED_UNC_PREFIX + absolute_path.lstrip("\\")
    return EXTENDED_PATH_PREFIX + absolute_path


def path_exists(path: str | Path) -> bool:
    return os.path.exists(filesystem_path(path))


def path_is_dir(path: str | Path) -> bool:
    return os.path.isdir(filesystem_path(path))


def path_stat(path: str | Path) -> os.stat_result:
    return os.stat(filesystem_path(path))


def make_dirs(path: str | Path) -> None:
    os.makedirs(filesystem_path(path), exist_ok=True)

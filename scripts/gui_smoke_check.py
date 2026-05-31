from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = str(os.getpid())
LOCALAPPDATA = ROOT / "test_artifacts" / "gui_smoke_localappdata" / RUN_ID
IMAGE_ROOT = ROOT / "test_artifacts" / "gui_smoke" / RUN_ID
os.environ["LOCALAPPDATA"] = str(LOCALAPPDATA)
sys.path.insert(0, str(ROOT))

from app.core.cache_manager import cache_stats  # noqa: E402
from app.core.recent_folders import settings_file_path  # noqa: E402
from app.ui import compare_view  # noqa: E402
from app.ui.main_window import (  # noqa: E402
    BN_CLICKED,
    CACHE_CLEAR_ID,
    CACHE_CLEANUP_ID,
    COMPARE_OPEN_ID,
    COMPARE_SET_A_ID,
    COMPARE_SET_B_ID,
    CONTEXT_COPY_FILE_NAME_ID,
    CONTEXT_COPY_IMAGE_PATH_ID,
    CONTEXT_OPEN_IMAGE_FOLDER_ID,
    CONTEXT_OPEN_IMAGE_ID,
    CONTEXT_REVEAL_IMAGE_ID,
    CONTEXT_SHOW_PROPERTIES_ID,
    FAVORITE_FOLDER_ADD_ID,
    RESIZE_SAVE_ID,
    SELECT_FOLDER_ID,
    SORT_ASCENDING_ID,
    SORT_BY_MTIME_ID,
    SORT_BY_NAME_ID,
    SORT_BY_SIZE_ID,
    SORT_DESCENDING_ID,
    MainWindow,
    SW_SHOW,
    WM_COMMAND,
    WM_KEYDOWN,
    user32,
)


PM_REMOVE = 0x0001
user32.PeekMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
    wintypes.UINT,
]
user32.PeekMessageW.restype = wintypes.BOOL


def pump(seconds: float = 0.2) -> None:
    deadline = time.time() + seconds
    msg = wintypes.MSG()
    while time.time() < deadline:
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.01)


def click(hwnd: int, control_id: int, wait: float = 0.35) -> None:
    user32.SendMessageW(hwnd, WM_COMMAND, control_id | (BN_CLICKED << 16), 0)
    pump(wait)


def make_smoke_images(folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, color in enumerate([(50, 120, 210), (210, 90, 70), (60, 170, 110)], start=1):
        path = folder / f"smoke_{index}.png"
        image = Image.new("RGB", (520 + index * 60, 360 + index * 40), color)
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 55, 320, 260), fill=(245, 220 - index * 20, 80 + index * 35))
        draw.line((0, image.height - 1, image.width - 1, 0), fill=(255, 255, 255), width=5)
        draw.text((72, 84), f"GUI smoke {index}", fill=(20, 20, 20))
        image.save(path)
        paths.append(path)
    return paths


def wait_for(condition: object, label: str, seconds: float = 5.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        pump(0.1)
        if condition():
            return
    raise AssertionError(f"Timed out waiting for {label}")


def verify_sort_preferences(window: MainWindow) -> None:
    assert window.hwnd is not None

    sort_checks = [
        (SORT_BY_NAME_ID, SORT_ASCENDING_ID, "name", False),
        (SORT_BY_MTIME_ID, SORT_DESCENDING_ID, "mtime", True),
        (SORT_BY_SIZE_ID, SORT_ASCENDING_ID, "size", False),
        (SORT_BY_SIZE_ID, SORT_DESCENDING_ID, "size", True),
    ]
    for field_id, order_id, expected_field, expected_descending in sort_checks:
        click(window.hwnd, field_id, wait=0.2)
        click(window.hwnd, order_id, wait=0.2)
        if window.sort_field != expected_field or window.sort_descending != expected_descending:
            raise AssertionError("Sort setting did not update through the GUI")

    reloaded = MainWindow()
    if reloaded.sort_field != "size" or not reloaded.sort_descending:
        raise AssertionError("Sort setting was not restored from settings.json")


def verify_context_menu_commands(window: MainWindow) -> None:
    image_file = window._selected_image_file
    if image_file is None:
        raise AssertionError("No image selected for context menu smoke")

    calls: list[str] = []
    original_open = window._handle_context_open_image
    original_open_folder = window._handle_context_open_image_folder
    original_reveal = window._handle_context_reveal_image_in_explorer
    original_copy_path = window._handle_context_copy_image_path
    original_copy_name = window._handle_context_copy_file_name
    original_properties = window._handle_context_show_properties
    try:
        window._handle_context_open_image = lambda _image=None: calls.append("開く") or True  # type: ignore[method-assign]
        window._handle_context_open_image_folder = lambda _image=None: calls.append("フォルダを開く") or True  # type: ignore[method-assign]
        window._handle_context_reveal_image_in_explorer = lambda _image=None: calls.append("エクスプローラーで選択表示") or True  # type: ignore[method-assign]
        window._handle_context_copy_image_path = lambda _image=None: calls.append("パスをコピー") or True  # type: ignore[method-assign]
        window._handle_context_copy_file_name = lambda _image=None: calls.append("ファイル名をコピー") or True  # type: ignore[method-assign]
        window._handle_context_show_properties = lambda _image=None: calls.append("プロパティ") or True  # type: ignore[method-assign]

        for command_id in (
            CONTEXT_OPEN_IMAGE_ID,
            CONTEXT_OPEN_IMAGE_FOLDER_ID,
            CONTEXT_COPY_IMAGE_PATH_ID,
            CONTEXT_COPY_FILE_NAME_ID,
            CONTEXT_REVEAL_IMAGE_ID,
            CONTEXT_SHOW_PROPERTIES_ID,
        ):
            if not window._handle_safe_image_context_command(command_id, image_file):
                raise AssertionError(f"Context menu command failed: {command_id}")
    finally:
        window._handle_context_open_image = original_open  # type: ignore[method-assign]
        window._handle_context_open_image_folder = original_open_folder  # type: ignore[method-assign]
        window._handle_context_reveal_image_in_explorer = original_reveal  # type: ignore[method-assign]
        window._handle_context_copy_image_path = original_copy_path  # type: ignore[method-assign]
        window._handle_context_copy_file_name = original_copy_name  # type: ignore[method-assign]
        window._handle_context_show_properties = original_properties  # type: ignore[method-assign]

    expected = [
        "開く",
        "フォルダを開く",
        "パスをコピー",
        "ファイル名をコピー",
        "エクスプローラーで選択表示",
        "プロパティ",
    ]
    if calls != expected:
        raise AssertionError(f"Unexpected context menu commands: {calls}")


def main() -> None:
    image_folder = IMAGE_ROOT / "images"
    original_images = make_smoke_images(image_folder)

    window = MainWindow()
    window.create()
    assert window.hwnd is not None
    user32.ShowWindow(window.hwnd, SW_SHOW)
    user32.UpdateWindow(window.hwnd)
    pump(0.6)

    try:
        window._choose_folder = lambda title="画像フォルダを選択", initial_folder=None: image_folder  # type: ignore[method-assign]
        click(window.hwnd, SELECT_FOLDER_ID, wait=0.8)
        wait_for(lambda: window.current_folder == image_folder and len(window.thumbnail_grid.items) >= 3, "folder load")

        if not window.recent_folders or window.recent_folders[0] != image_folder:
            raise AssertionError("Recent folder was not recorded")

        click(window.hwnd, FAVORITE_FOLDER_ADD_ID)
        if not window.favorite_folders or window.favorite_folders[0] != image_folder:
            raise AssertionError("Favorite folder was not recorded")

        window.thumbnail_grid.select_index(0)
        wait_for(lambda: window._selected_image_file is not None, "preview selection")
        wait_for(lambda: cache_stats().thumbnails_files > 0, "thumbnail cache")
        wait_for(lambda: cache_stats().previews_files > 0, "preview cache")

        verify_sort_preferences(window)
        verify_context_menu_commands(window)

        window._open_fullscreen()
        wait_for(lambda: window.fullscreen_preview.visible, "fullscreen open")
        window._close_fullscreen()
        pump(0.3)

        window.thumbnail_grid.select_index(0)
        pump(0.3)
        click(window.hwnd, COMPARE_SET_A_ID)
        window.thumbnail_grid.select_index(1)
        pump(0.3)
        click(window.hwnd, COMPARE_SET_B_ID)
        click(window.hwnd, COMPARE_OPEN_ID, wait=0.8)
        compare = window.compare_view
        if not compare.visible or compare.hwnd is None:
            raise AssertionError("Compare view did not open")
        compare.handle_message(compare.hwnd, WM_KEYDOWN, compare_view.VK_ESCAPE, 0)
        pump(0.4)
        if compare.visible:
            raise AssertionError("Compare view did not close")

        before_count = len(window.thumbnail_grid.items)
        window.thumbnail_grid.select_index(0)
        pump(0.3)
        resize_source = window._selected_image_file
        if resize_source is None:
            raise AssertionError("No image selected for resize smoke")
        click(window.hwnd, RESIZE_SAVE_ID, wait=1.0)
        if len(window.thumbnail_grid.items) <= before_count:
            raise AssertionError("Resize save did not add the saved image to the list")
        expected_resize_prefix = f"{resize_source.path.stem}_resized"
        if not any(path.name.startswith(expected_resize_prefix) for path in image_folder.glob("*.png")):
            raise AssertionError("Resize output was not created")

        settings_path = settings_file_path()
        if not settings_path.exists():
            raise AssertionError("settings.json was not created")

        click(window.hwnd, CACHE_CLEANUP_ID, wait=0.8)
        if not settings_path.exists():
            raise AssertionError("settings.json disappeared after cache cleanup")
        if not all(path.exists() for path in original_images):
            raise AssertionError("Original image disappeared after cache cleanup")

        click(window.hwnd, CACHE_CLEAR_ID, wait=1.2)
        if not settings_path.exists():
            raise AssertionError("settings.json disappeared after cache clear")
        if not all(path.exists() for path in original_images):
            raise AssertionError("Original image disappeared after cache clear")
        wait_for(lambda: cache_stats().total_files > 0, "cache regeneration after clear")
    finally:
        window.destroy()
        pump(0.4)

    print(
        "GUI_SMOKE_OK app launch, folder selection, thumbnails, preview, fullscreen, "
        "compare, resize save, cache management, favorites, recent folders, "
        "sort restore, context menu commands"
    )


if __name__ == "__main__":
    main()

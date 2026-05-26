from __future__ import annotations

import ctypes
import os
import queue
import sys
import threading
import time
import traceback
from ctypes import wintypes
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.core.image_resizer import (
    RESIZE_BASIS_HEIGHT,
    RESIZE_BASIS_WIDTH,
    RESIZE_SIZE_OPTIONS as CORE_RESIZE_SIZE_OPTIONS,
    resize_image_file,
)
from app.core.image_scanner import ImageFile, image_file_from_path, scan_image_files
from app.core.cache_manager import CacheCleanupResult, cache_stats, cleanup_cache, clear_cache
from app.core.preview_renderer import (
    PREVIEW_MODE_FIT_HEIGHT,
    PREVIEW_MODE_ORIGINAL,
    PREVIEW_MODE_SCALE_50,
    PREVIEW_MODE_SCALE_200,
    PreviewResult,
    render_preview,
)
from app.core.recent_folders import (
    DEFAULT_CACHE_SIZE_LIMIT_BYTES,
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
from app.core.thumbnail_cache import THUMBNAIL_SIZE, ThumbnailResult, ensure_thumbnail
from app.ui.compare_view import CompareView
from app.ui.fullscreen_preview import FullscreenPreview
from app.ui.folder_tree import FolderTree
from app.ui.image_preview import ImagePreview
from app.ui.operation_guide_dialog import OperationGuideDialog
from app.ui.thumbnail_grid import PREFETCH_EXTRA_ROWS, ThumbnailGrid
from app.utils.image_types import SUPPORTED_IMAGE_EXTENSIONS
from app.utils.long_path import display_path, filesystem_path, path_exists, path_is_dir


if not hasattr(ctypes, "windll"):
    raise RuntimeError("このUIは現在Windowsのみ対応しています。")


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
shell32 = ctypes.windll.shell32
ole32 = ctypes.windll.ole32
kernel32 = ctypes.windll.kernel32

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HANDLE
kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalFree.argtypes = [wintypes.HANDLE]
kernel32.GlobalFree.restype = wintypes.HANDLE

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    ctypes.c_void_p,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DispatchMessageW.argtypes = [ctypes.c_void_p]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.GetMessageW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
user32.LoadCursorW.restype = wintypes.HANDLE
user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.ClientToScreen.restype = wintypes.BOOL
user32.CreatePopupMenu.argtypes = []
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
user32.AppendMenuW.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    ctypes.c_void_p,
]
user32.TrackPopupMenu.restype = ctypes.c_int
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.DestroyMenu.restype = wintypes.BOOL
user32.MoveWindow.argtypes = [
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.BOOL,
]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.RegisterClassW.argtypes = [ctypes.c_void_p]
user32.RegisterClassW.restype = wintypes.ATOM
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.CheckRadioButton.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int]
user32.CheckRadioButton.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short
user32.SetCapture.argtypes = [wintypes.HWND]
user32.SetCapture.restype = wintypes.HWND
user32.ReleaseCapture.argtypes = []
user32.ReleaseCapture.restype = wintypes.BOOL
user32.SetCursor.argtypes = [wintypes.HANDLE]
user32.SetCursor.restype = wintypes.HANDLE
user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.TranslateMessage.argtypes = [ctypes.c_void_p]
user32.UpdateWindow.argtypes = [wintypes.HWND]

gdi32.GetStockObject.argtypes = [ctypes.c_int]
gdi32.GetStockObject.restype = ctypes.c_void_p

shell32.SHBrowseForFolderW.argtypes = [ctypes.c_void_p]
shell32.SHBrowseForFolderW.restype = ctypes.c_void_p
shell32.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]
shell32.SHGetPathFromIDListW.restype = wintypes.BOOL
shell32.ShellExecuteW.argtypes = [
    wintypes.HWND,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    ctypes.c_int,
]
shell32.ShellExecuteW.restype = ctypes.c_void_p
shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
shell32.DragFinish.argtypes = [ctypes.c_void_p]
shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
shell32.DragQueryFileW.restype = wintypes.UINT
try:
    shell32.SHGetPathFromIDListEx.argtypes = [ctypes.c_void_p, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    shell32.SHGetPathFromIDListEx.restype = wintypes.BOOL
except AttributeError:
    shell32.SHGetPathFromIDListEx = None  # type: ignore[assignment]

ole32.CoInitialize.argtypes = [ctypes.c_void_p]
ole32.CoInitialize.restype = ctypes.c_long
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
ole32.CoUninitialize.argtypes = []


WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_COMMAND = 0x0111
WM_NOTIFY = 0x004E
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
WM_MOUSEWHEEL = 0x020A
WM_DROPFILES = 0x0233
WM_USER = 0x0400
WM_APP = 0x8000
WM_SETFONT = 0x0030
WM_THUMBNAIL_READY = WM_APP + 1
WM_PREVIEW_READY = WM_APP + 2
WM_FULLSCREEN_READY = WM_APP + 3
PREVIEW_START_DELAY_SECONDS = 0.08

BN_CLICKED = 0
CBN_SELCHANGE = 1
BS_AUTORADIOBUTTON = 0x00000009
BS_GROUPBOX = 0x00000007
CBS_DROPDOWNLIST = 0x00000003
BST_CHECKED = 1
BM_SETCHECK = 0x00F1
CB_ADDSTRING = 0x0143
CB_GETCURSEL = 0x0147
CB_RESETCONTENT = 0x014B
CB_SETCURSEL = 0x014E
CB_ERR = -1
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040
MF_STRING = 0x0000
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100
BIF_RETURNONLYFSDIRS = 0x0001
BIF_NEWDIALOGSTYLE = 0x0040
BFFM_INITIALIZED = 1
BFFM_SETSELECTIONW = WM_USER + 103
MB_OK = 0x00000000
MB_ICONINFORMATION = 0x00000040

WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_GROUP = 0x00020000
WS_VSCROLL = 0x00200000
SS_ENDELLIPSIS = 0x00004000
SS_PATHELLIPSIS = 0x00008000

CW_USEDEFAULT = -2147483648
SW_SHOW = 5
DEFAULT_GUI_FONT = 17
IDC_ARROW = 32512
IDC_SIZEWE = 32644
FOLDER_TREE_DEFAULT_WIDTH = 260
FOLDER_TREE_MIN_WIDTH = 180
FOLDER_TREE_MAX_WIDTH = 420
MAX_PATH = 260
MAX_LONG_PATH = 32768
FOLDER_PATH_DISPLAY_LIMIT = 120
STATUS_FILENAME_DISPLAY_LIMIT = 72
RECENT_FOLDER_DISPLAY_LIMIT = 76
FAVORITE_FOLDER_DISPLAY_LIMIT = 72
THUMBNAIL_DRAIN_BATCH_SIZE = 96
THUMBNAIL_WORKER_YIELD_INTERVAL = 32
THUMBNAIL_QUEUE_BACKLOG_LIMIT = 192
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_RETURN = 0x0D
VK_HOME = 0x24
VK_END = 0x23
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_SPACE = 0x20
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_C = 0x43
VK_F = 0x46

SELECT_FOLDER_ID = 1001
RECENT_FOLDER_COMBO_ID = 1002
FAVORITE_FOLDER_ADD_ID = 1003
FAVORITE_FOLDER_COMBO_ID = 1004
FAVORITE_FOLDER_REMOVE_ID = 1005
FAVORITE_FOLDER_MOVE_UP_ID = 1006
FAVORITE_FOLDER_MOVE_DOWN_ID = 1007
INVALID_HISTORY_CLEANUP_ID = 1008
COPY_FOLDER_PATH_ID = 1009
COPY_IMAGE_PATH_ID = 1010
OPEN_SELECTED_FOLDER_ID = 1011
CONTEXT_COPY_IMAGE_PATH_ID = 1012
CONTEXT_COPY_FOLDER_PATH_ID = 1013
OPERATION_GUIDE_ID = 1014
RESIZE_SIZE_800_ID = 1015
RESIZE_SIZE_1200_ID = 1016
RESIZE_SIZE_1920_ID = 1017
RESIZE_BASIS_WIDTH_ID = 1018
RESIZE_BASIS_HEIGHT_ID = 1019
RESIZE_SAVE_ID = 1020
COMPARE_SET_A_ID = 1021
COMPARE_SET_B_ID = 1022
COMPARE_OPEN_ID = 1023
PARENT_FOLDER_ID = 1024
PREVIOUS_FOLDER_ID = 1025
NEXT_FOLDER_ID = 1026
RESIZE_OUTPUT_FOLDER_ID = 1027
CACHE_CLEANUP_ID = 1028
CACHE_CLEAR_ID = 1029
CACHE_LIMIT_512MB_ID = 1030
CACHE_LIMIT_1GB_ID = 1031
CACHE_LIMIT_2GB_ID = 1032
OPEN_CURRENT_FOLDER_ID = 1033
THUMBNAIL_SIZE_64_ID = 1101
THUMBNAIL_SIZE_128_ID = 1102
THUMBNAIL_SIZE_256_ID = 1103
THUMBNAIL_SIZE_OPTIONS = {
    THUMBNAIL_SIZE_64_ID: 64,
    THUMBNAIL_SIZE_128_ID: 128,
    THUMBNAIL_SIZE_256_ID: 256,
}
SORT_BY_NAME_ID = 1201
SORT_BY_MTIME_ID = 1202
SORT_ASCENDING_ID = 1211
SORT_DESCENDING_ID = 1212
SORT_FIELD_OPTIONS = {
    SORT_BY_NAME_ID: ("name", "ファイル名"),
    SORT_BY_MTIME_ID: ("mtime", "更新日"),
}
SORT_ORDER_OPTIONS = {
    SORT_ASCENDING_ID: (False, "昇順"),
    SORT_DESCENDING_ID: (True, "降順"),
}
DISPLAY_SCALE_50_ID = 1301
DISPLAY_ORIGINAL_ID = 1302
DISPLAY_SCALE_200_ID = 1303
DISPLAY_FIT_HEIGHT_ID = 1304
DISPLAY_MODE_OPTIONS = {
    DISPLAY_SCALE_50_ID: (PREVIEW_MODE_SCALE_50, "50%"),
    DISPLAY_ORIGINAL_ID: (PREVIEW_MODE_ORIGINAL, "100%"),
    DISPLAY_SCALE_200_ID: (PREVIEW_MODE_SCALE_200, "200%"),
    DISPLAY_FIT_HEIGHT_ID: (PREVIEW_MODE_FIT_HEIGHT, "高さに合わせる"),
}
RESIZE_UI_SIZE_OPTIONS = {
    RESIZE_SIZE_800_ID: 800,
    RESIZE_SIZE_1200_ID: 1200,
    RESIZE_SIZE_1920_ID: 1920,
}
RESIZE_BASIS_OPTIONS = {
    RESIZE_BASIS_WIDTH_ID: (RESIZE_BASIS_WIDTH, "幅"),
    RESIZE_BASIS_HEIGHT_ID: (RESIZE_BASIS_HEIGHT, "高さ"),
}
CACHE_SIZE_LIMIT_OPTIONS = {
    CACHE_LIMIT_512MB_ID: 512 * 1024 * 1024,
    CACHE_LIMIT_1GB_ID: DEFAULT_CACHE_SIZE_LIMIT_BYTES,
    CACHE_LIMIT_2GB_ID: 2 * 1024 * 1024 * 1024,
}
ZOOM_DISPLAY_MODES = [PREVIEW_MODE_SCALE_50, PREVIEW_MODE_ORIGINAL, PREVIEW_MODE_SCALE_200]
PAN_DISPLAY_MODES = {PREVIEW_MODE_SCALE_50, PREVIEW_MODE_ORIGINAL, PREVIEW_MODE_SCALE_200}
CLASS_NAME = "FastImageViewerStep16Window"
DRAG_QUERY_FILE_COUNT = 0xFFFFFFFF
OPERATION_GUIDE_TITLE = "操作ガイド"
OPERATION_GUIDE_TEXT = "\n".join(
    [
        "【よく使う操作】",
        "← / →：前後の画像",
        "Alt + ← / →：前後のフォルダ",
        "Alt + ↑：親フォルダ",
        "Space：次の画像",
        "ホイール：前後の画像",
        "Enter：全画面",
        "Esc：戻る",
        "Ctrl + ホイール：拡大 / 縮小",
        "",
        "【画像移動】",
        "← / →：前後の画像",
        "Space：次の画像",
        "Shift + Space：前の画像",
        "Home / End：先頭 / 末尾",
        "PageUp / PageDown：ページ移動",
        "Alt + ← / →：前後のフォルダ",
        "Alt + ↑：親フォルダ",
        "",
        "【表示操作】",
        "Ctrl + ホイール：拡大 / 縮小",
        "表示倍率：50% / 100% / 200% / 高さに合わせる",
        "プレビュー境界ドラッグ：プレビュー幅変更",
        "ダブルクリック：表示位置を中央リセット",
        "",
        "【全画面操作】",
        "Enter：全画面",
        "Esc：戻る",
        "ダブルクリック：全画面",
        "",
        "【パスコピー】",
        "Ctrl + Shift + C：画像パスコピー",
        "Ctrl + Shift + F：フォルダパスコピー",
        "右クリック：コピー メニュー",
        "",
        "【マウス操作】",
        "ホイール：前後の画像",
        "ドラッグ：表示位置を移動",
        "右クリック：コピー メニュー",
    ]
)


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
BFFCALLBACK = ctypes.WINFUNCTYPE(
    ctypes.c_int,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.LPARAM,
    wintypes.LPARAM,
)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


class BROWSEINFOW(ctypes.Structure):
    _fields_ = [
        ("hwndOwner", wintypes.HWND),
        ("pidlRoot", ctypes.c_void_p),
        ("pszDisplayName", wintypes.LPWSTR),
        ("lpszTitle", wintypes.LPCWSTR),
        ("ulFlags", wintypes.UINT),
        ("lpfn", ctypes.c_void_p),
        ("lParam", wintypes.LPARAM),
        ("iImage", ctypes.c_int),
    ]


_window_proc_ref: WNDPROC | None = None
_window_instances: dict[int, MainWindow] = {}
_class_registered = False


def run_app() -> None:
    MainWindow().run()


class MainWindow:
    def __init__(self) -> None:
        self.hwnd: int | None = None
        self.folder_group_box: int | None = None
        self.favorite_group_box: int | None = None
        self.view_group_box: int | None = None
        self.open_button: int | None = None
        self.parent_folder_button: int | None = None
        self.previous_folder_button: int | None = None
        self.next_folder_button: int | None = None
        self.cleanup_invalid_button: int | None = None
        self.recent_label: int | None = None
        self.recent_combo: int | None = None
        self.favorite_add_button: int | None = None
        self.favorite_remove_button: int | None = None
        self.favorite_move_up_button: int | None = None
        self.favorite_move_down_button: int | None = None
        self.favorite_label: int | None = None
        self.favorite_combo: int | None = None
        self.thumbnail_label: int | None = None
        self.thumbnail_size_buttons: dict[int, int] = {}
        self.sort_label: int | None = None
        self.sort_buttons: dict[int, int] = {}
        self.order_label: int | None = None
        self.order_buttons: dict[int, int] = {}
        self.display_label: int | None = None
        self.display_buttons: dict[int, int] = {}
        self.resize_label: int | None = None
        self.resize_size_buttons: dict[int, int] = {}
        self.resize_basis_label: int | None = None
        self.resize_basis_buttons: dict[int, int] = {}
        self.resize_save_button: int | None = None
        self.resize_output_button: int | None = None
        self.resize_output_label: int | None = None
        self.cache_group_box: int | None = None
        self.cache_status_label: int | None = None
        self.cache_cleanup_button: int | None = None
        self.cache_clear_button: int | None = None
        self.cache_limit_label: int | None = None
        self.cache_limit_buttons: dict[int, int] = {}
        self.compare_a_button: int | None = None
        self.compare_b_button: int | None = None
        self.compare_open_button: int | None = None
        self.operation_guide_button: int | None = None
        self.folder_label: int | None = None
        self.current_path_label: int | None = None
        self.current_path_open_button: int | None = None
        self.status_count_label: int | None = None
        self.status_name_label: int | None = None
        self.status_dimensions_label: int | None = None
        self.status_file_size_label: int | None = None
        self.status_loading_label: int | None = None
        self.status_bar: int | None = None
        self.copy_folder_path_button: int | None = None
        self.copy_image_path_button: int | None = None
        self.open_selected_folder_button: int | None = None
        self.folder_tree = FolderTree()
        self.thumbnail_grid = ThumbnailGrid()
        self.thumbnail_size = THUMBNAIL_SIZE
        self.sort_field = "name"
        self.sort_descending = False
        self.display_mode = PREVIEW_MODE_ORIGINAL
        self.resize_size = CORE_RESIZE_SIZE_OPTIONS[0]
        self.resize_basis = RESIZE_BASIS_WIDTH
        self.resize_output_folder = load_resize_output_folder()
        self.cache_size_limit_bytes = load_cache_size_limit_bytes()
        self.preview_width = load_preview_width()
        self.image_preview = ImagePreview()
        self.fullscreen_preview = FullscreenPreview()
        self.compare_view = CompareView()
        self.operation_guide_dialog = OperationGuideDialog()
        self.current_folder: Path | None = None
        self.recent_folders = load_recent_folders()
        self.favorite_folders = load_favorite_folders()
        self._selected_image_file: ImageFile | None = None
        self._compare_a_image_file: ImageFile | None = None
        self._compare_b_image_file: ImageFile | None = None
        self._load_id = 0
        self._preview_id = 0
        self._fullscreen_id = 0
        self._preview_lock = threading.Lock()
        self._fullscreen_lock = threading.Lock()
        self._preview_condition = threading.Condition(self._preview_lock)
        self._preview_request: tuple[int, ImageFile, int, int, str] | None = None
        self._preview_worker_started = False
        self._thumbnail_total = 0
        self._thumbnail_done = 0
        self._thumbnail_priority_lock = threading.Lock()
        self._thumbnail_priority_range: tuple[int, int] = (0, 0)
        self._thumbnail_queue: queue.Queue[tuple[int, ThumbnailResult]] = queue.Queue()
        self._preview_queue: queue.Queue[tuple[int, ImageFile, PreviewResult]] = queue.Queue()
        self._fullscreen_queue: queue.Queue[tuple[int, ImageFile, PreviewResult]] = queue.Queue()
        self._status_loading_text = ""
        self._image_dimension_cache: dict[Path, tuple[int, int] | None] = {}
        self.folder_tree_width = FOLDER_TREE_DEFAULT_WIDTH
        self._tree_splitter_rect: tuple[int, int, int, int] | None = None
        self._tree_splitter_dragging = False
        self._tree_splitter_drag_start_x = 0
        self._tree_splitter_drag_start_width = FOLDER_TREE_DEFAULT_WIDTH
        self._splitter_rect: tuple[int, int, int, int] | None = None
        self._splitter_dragging = False
        self._splitter_drag_start_x = 0
        self._splitter_drag_start_width = 0

    def run(self) -> None:
        self.create()
        user32.ShowWindow(self.hwnd, SW_SHOW)
        user32.UpdateWindow(self.hwnd)
        self._message_loop()

    def create(self) -> None:
        _register_window_class()
        hinstance = kernel32.GetModuleHandleW(None)
        hwnd = user32.CreateWindowExW(
            0,
            CLASS_NAME,
            "高速画像ビューア",
            WS_OVERLAPPEDWINDOW,
            CW_USEDEFAULT,
            CW_USEDEFAULT,
            980,
            680,
            None,
            None,
            hinstance,
            None,
        )
        if not hwnd:
            raise ctypes.WinError()

        self.hwnd = int(hwnd)
        _window_instances[self.hwnd] = self
        shell32.DragAcceptFiles(self.hwnd, True)
        self._create_controls()
        self._layout()
        self._refresh_cache_status()

    def destroy(self) -> None:
        self._load_id += 1
        self._cancel_preview_requests()
        self._close_fullscreen()
        self.folder_tree.destroy()
        self.thumbnail_grid.destroy()
        self.image_preview.destroy()
        self.fullscreen_preview.destroy()
        self.compare_view.destroy()
        self.operation_guide_dialog.destroy()
        if self.hwnd:
            shell32.DragAcceptFiles(self.hwnd, False)
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None

    def load_folder(self, folder: Path, select_path: Path | None = None, show_error_dialog: bool = True) -> None:
        folder = display_path(folder)
        select_path = display_path(select_path) if select_path is not None else None
        self._require_controls()
        if not path_is_dir(folder) and self._remove_missing_saved_folder(folder):
            self._set_folder_status("保存済みフォルダが見つからないため整理しました", folder)
            return
        self._load_id += 1
        self._cancel_preview_requests()
        self._close_fullscreen()
        load_id = self._load_id
        self.current_folder = folder
        self._selected_image_file = None
        self._thumbnail_done = 0
        self._thumbnail_total = 0
        self.thumbnail_grid.set_items([])
        self.image_preview.clear()
        self._drain_thumbnail_queue(ignore_all=True)
        self._drain_preview_queue(ignore_all=True)
        self._set_folder_label(folder)
        self._refresh_status_details("読み込み中")
        self._set_folder_status("フォルダを読み込み中", folder)

        try:
            image_files = self._sorted_image_files(scan_image_files(folder))
        except (FileNotFoundError, NotADirectoryError, PermissionError) as error:
            self.current_folder = None
            self._set_folder_label(None)
            self._refresh_status_details("")
            self._set_folder_status("フォルダを読み込めません", folder)
            if show_error_dialog:
                user32.MessageBoxW(self.hwnd, self._folder_error_message(folder, error), "\u30d5\u30a9\u30eb\u30c0\u3092\u958b\u3051\u307e\u305b\u3093", 0x10)
            return

        self.thumbnail_grid.set_items(image_files)
        self._thumbnail_total = len(image_files)
        self._refresh_status_details("読み込み中" if image_files else "")
        self._remember_recent_folder(folder)
        if self.thumbnail_grid.hwnd:
            user32.SetFocus(self.thumbnail_grid.hwnd)

        if not image_files:
            self._refresh_status_details("")
            self._set_folder_status("画像が見つかりません", folder)
            return

        self._set_folder_status(f"{len(image_files)}件の画像が見つかりました。周辺サムネイルを先読み中", folder)
        selected_index = self._index_for_path(image_files, select_path)
        if selected_index is not None:
            self.thumbnail_grid.select_index(selected_index)
        self._start_thumbnail_worker(load_id, image_files, self.thumbnail_size)

    def handle_message(
        self,
        hwnd: int,
        message: int,
        w_param: int,
        l_param: int,
    ) -> int | None:
        if message == WM_SIZE:
            self._layout()
            if self._selected_image_file is not None:
                self._start_preview_worker(self._selected_image_file, show_loading=False)
            return 0

        if message == WM_THUMBNAIL_READY:
            self._drain_thumbnail_queue()
            return 0

        if message == WM_PREVIEW_READY:
            self._drain_preview_queue()
            return 0

        if message == WM_FULLSCREEN_READY:
            self._drain_fullscreen_queue()
            return 0

        if message == WM_DROPFILES:
            self._handle_drop_files(w_param)
            return 0

        if message == WM_NOTIFY:
            if self.folder_tree.handle_notify(l_param):
                return 0

        if message == WM_SYSKEYDOWN:
            if self._handle_folder_navigation_shortcut(int(w_param)):
                return 0

        if message == WM_LBUTTONDOWN:
            if self._handle_splitter_mouse_down(_signed_loword(int(l_param)), _signed_hiword(int(l_param))):
                return 0

        if message == WM_MOUSEMOVE:
            if self._handle_splitter_mouse_move(_signed_loword(int(l_param)), _signed_hiword(int(l_param))):
                return 0

        if message == WM_LBUTTONUP:
            if self._handle_splitter_mouse_up():
                return 0

        if message == WM_MOUSEWHEEL:
            self._handle_mouse_wheel(w_param)
            return 0

        if message == WM_KEYDOWN:
            if self._handle_copy_shortcut(int(w_param)):
                return 0
            if int(w_param) == VK_LEFT:
                self.thumbnail_grid.select_relative(-1)
                return 0
            if int(w_param) == VK_RIGHT:
                self.thumbnail_grid.select_relative(1)
                return 0
            if int(w_param) == VK_HOME:
                self.thumbnail_grid.select_first()
                return 0
            if int(w_param) == VK_END:
                self.thumbnail_grid.select_last()
                return 0
            if int(w_param) == VK_PRIOR:
                self.thumbnail_grid.select_page(-1)
                return 0
            if int(w_param) == VK_NEXT:
                self.thumbnail_grid.select_page(1)
                return 0
            if int(w_param) == VK_RETURN:
                self._open_fullscreen()
                return 0
            if int(w_param) == VK_SPACE:
                self.thumbnail_grid.select_relative(-1 if _shift_pressed() else 1)
                return 0

        if message == WM_COMMAND:
            control_id = int(w_param) & 0xFFFF
            notification = (int(w_param) >> 16) & 0xFFFF
            if control_id == SELECT_FOLDER_ID and notification == BN_CLICKED:
                self._handle_select_folder()
                return 0
            if control_id == PARENT_FOLDER_ID and notification == BN_CLICKED:
                self._handle_open_parent_folder()
                return 0
            if control_id == PREVIOUS_FOLDER_ID and notification == BN_CLICKED:
                self._handle_open_previous_folder()
                return 0
            if control_id == NEXT_FOLDER_ID and notification == BN_CLICKED:
                self._handle_open_next_folder()
                return 0
            if control_id == INVALID_HISTORY_CLEANUP_ID and notification == BN_CLICKED:
                self._handle_cleanup_invalid_history()
                return 0
            if control_id == RECENT_FOLDER_COMBO_ID and notification == CBN_SELCHANGE:
                self._handle_recent_folder_selected()
                return 0
            if control_id == FAVORITE_FOLDER_ADD_ID and notification == BN_CLICKED:
                self._handle_add_favorite_folder()
                return 0
            if control_id == FAVORITE_FOLDER_REMOVE_ID and notification == BN_CLICKED:
                self._handle_remove_favorite_folder()
                return 0
            if control_id == FAVORITE_FOLDER_MOVE_UP_ID and notification == BN_CLICKED:
                self._handle_move_favorite_folder(-1)
                return 0
            if control_id == FAVORITE_FOLDER_MOVE_DOWN_ID and notification == BN_CLICKED:
                self._handle_move_favorite_folder(1)
                return 0
            if control_id == FAVORITE_FOLDER_COMBO_ID and notification == CBN_SELCHANGE:
                self._handle_favorite_folder_selected()
                return 0
            if control_id == COPY_FOLDER_PATH_ID and notification == BN_CLICKED:
                self._handle_copy_folder_path()
                return 0
            if control_id == COPY_IMAGE_PATH_ID and notification == BN_CLICKED:
                self._handle_copy_image_path()
                return 0
            if control_id == OPEN_SELECTED_FOLDER_ID and notification == BN_CLICKED:
                self._handle_open_selected_image_folder()
                return 0
            if control_id == OPEN_CURRENT_FOLDER_ID and notification == BN_CLICKED:
                self._handle_open_current_folder()
                return 0
            if control_id in THUMBNAIL_SIZE_OPTIONS and notification == BN_CLICKED:
                self._change_thumbnail_size(THUMBNAIL_SIZE_OPTIONS[control_id])
                return 0
            if control_id in SORT_FIELD_OPTIONS and notification == BN_CLICKED:
                self._change_sort_field(SORT_FIELD_OPTIONS[control_id][0])
                return 0
            if control_id in SORT_ORDER_OPTIONS and notification == BN_CLICKED:
                self._change_sort_order(SORT_ORDER_OPTIONS[control_id][0])
                return 0
            if control_id in DISPLAY_MODE_OPTIONS and notification == BN_CLICKED:
                self._change_display_mode(DISPLAY_MODE_OPTIONS[control_id][0])
                return 0
            if control_id in RESIZE_UI_SIZE_OPTIONS and notification == BN_CLICKED:
                self._change_resize_size(RESIZE_UI_SIZE_OPTIONS[control_id])
                return 0
            if control_id in RESIZE_BASIS_OPTIONS and notification == BN_CLICKED:
                self._change_resize_basis(RESIZE_BASIS_OPTIONS[control_id][0])
                return 0
            if control_id == RESIZE_OUTPUT_FOLDER_ID and notification == BN_CLICKED:
                self._handle_select_resize_output_folder()
                return 0
            if control_id == RESIZE_SAVE_ID and notification == BN_CLICKED:
                self._handle_resize_save()
                return 0
            if control_id == CACHE_CLEANUP_ID and notification == BN_CLICKED:
                self._handle_cache_cleanup()
                return 0
            if control_id == CACHE_CLEAR_ID and notification == BN_CLICKED:
                self._handle_cache_clear()
                return 0
            if control_id in CACHE_SIZE_LIMIT_OPTIONS and notification == BN_CLICKED:
                self._change_cache_size_limit(CACHE_SIZE_LIMIT_OPTIONS[control_id])
                return 0
            if control_id == COMPARE_SET_A_ID and notification == BN_CLICKED:
                self._handle_set_compare_a()
                return 0
            if control_id == COMPARE_SET_B_ID and notification == BN_CLICKED:
                self._handle_set_compare_b()
                return 0
            if control_id == COMPARE_OPEN_ID and notification == BN_CLICKED:
                self._handle_open_compare_view()
                return 0
            if control_id == OPERATION_GUIDE_ID and notification == BN_CLICKED:
                self._show_operation_guide()
                return 0

        if message == WM_DESTROY:
            self._load_id += 1
            self._cancel_preview_requests()
            self._close_fullscreen()
            self.folder_tree.destroy()
            self.thumbnail_grid.destroy()
            self.image_preview.destroy()
            self.fullscreen_preview.destroy()
            self.compare_view.destroy()
            self.operation_guide_dialog.destroy()
            shell32.DragAcceptFiles(hwnd, False)
            _window_instances.pop(int(hwnd), None)
            user32.PostQuitMessage(0)
            return 0

        return None

    def _create_controls(self) -> None:
        self._require_window()
        self.folder_group_box = self._create_child("BUTTON", "フォルダ操作", WS_CHILD | WS_VISIBLE | BS_GROUPBOX, 0)
        self.favorite_group_box = self._create_child("BUTTON", "お気に入り", WS_CHILD | WS_VISIBLE | BS_GROUPBOX, 0)
        self.view_group_box = self._create_child("BUTTON", "表示設定", WS_CHILD | WS_VISIBLE | BS_GROUPBOX, 0)
        self.cache_group_box = self._create_child("BUTTON", "キャッシュ管理", WS_CHILD | WS_VISIBLE | BS_GROUPBOX, 0)
        self.open_button = self._create_child(
            "BUTTON",
            "フォルダ選択",
            WS_CHILD | WS_VISIBLE,
            SELECT_FOLDER_ID,
        )
        self.parent_folder_button = self._create_child(
            "BUTTON",
            "親フォルダへ",
            WS_CHILD | WS_VISIBLE,
            PARENT_FOLDER_ID,
        )
        self.previous_folder_button = self._create_child(
            "BUTTON",
            "前のフォルダ",
            WS_CHILD | WS_VISIBLE,
            PREVIOUS_FOLDER_ID,
        )
        self.next_folder_button = self._create_child(
            "BUTTON",
            "次のフォルダ",
            WS_CHILD | WS_VISIBLE,
            NEXT_FOLDER_ID,
        )
        self.cleanup_invalid_button = self._create_child(
            "BUTTON",
            "無効な履歴整理",
            WS_CHILD | WS_VISIBLE,
            INVALID_HISTORY_CLEANUP_ID,
        )
        self.recent_label = self._create_child("STATIC", "最近開いたフォルダ:", WS_CHILD | WS_VISIBLE, 0)
        self.recent_combo = self._create_child(
            "COMBOBOX",
            "",
            WS_CHILD | WS_VISIBLE | WS_VSCROLL | CBS_DROPDOWNLIST,
            RECENT_FOLDER_COMBO_ID,
        )
        self.favorite_add_button = self._create_child(
            "BUTTON",
            "お気に入り追加",
            WS_CHILD | WS_VISIBLE,
            FAVORITE_FOLDER_ADD_ID,
        )
        self.favorite_remove_button = self._create_child(
            "BUTTON",
            "お気に入り削除",
            WS_CHILD | WS_VISIBLE,
            FAVORITE_FOLDER_REMOVE_ID,
        )
        self.favorite_move_up_button = self._create_child(
            "BUTTON",
            "上へ",
            WS_CHILD | WS_VISIBLE,
            FAVORITE_FOLDER_MOVE_UP_ID,
        )
        self.favorite_move_down_button = self._create_child(
            "BUTTON",
            "下へ",
            WS_CHILD | WS_VISIBLE,
            FAVORITE_FOLDER_MOVE_DOWN_ID,
        )
        self.favorite_label = self._create_child("STATIC", "お気に入り:", WS_CHILD | WS_VISIBLE, 0)
        self.favorite_combo = self._create_child(
            "COMBOBOX",
            "",
            WS_CHILD | WS_VISIBLE | WS_VSCROLL | CBS_DROPDOWNLIST,
            FAVORITE_FOLDER_COMBO_ID,
        )
        self.thumbnail_label = self._create_child("STATIC", "サムネイル:", WS_CHILD | WS_VISIBLE, 0)
        for control_id, thumbnail_size in THUMBNAIL_SIZE_OPTIONS.items():
            style = WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON
            if control_id == THUMBNAIL_SIZE_64_ID:
                style |= WS_GROUP
            self.thumbnail_size_buttons[control_id] = self._create_child(
                "BUTTON",
                f"{thumbnail_size}px",
                style,
                control_id,
            )
        self._check_thumbnail_size_button(self.thumbnail_size)
        self.sort_label = self._create_child("STATIC", "並び替え:", WS_CHILD | WS_VISIBLE, 0)
        for control_id, (_, label) in SORT_FIELD_OPTIONS.items():
            style = WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON
            if control_id == SORT_BY_NAME_ID:
                style |= WS_GROUP
            self.sort_buttons[control_id] = self._create_child("BUTTON", label, style, control_id)
        self.order_label = self._create_child("STATIC", "順序:", WS_CHILD | WS_VISIBLE, 0)
        for control_id, (_, label) in SORT_ORDER_OPTIONS.items():
            style = WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON
            if control_id == SORT_ASCENDING_ID:
                style |= WS_GROUP
            self.order_buttons[control_id] = self._create_child("BUTTON", label, style, control_id)
        self.display_label = self._create_child("STATIC", "表示:", WS_CHILD | WS_VISIBLE, 0)
        for control_id, (_, label) in DISPLAY_MODE_OPTIONS.items():
            style = WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON
            if control_id == DISPLAY_SCALE_50_ID:
                style |= WS_GROUP
            self.display_buttons[control_id] = self._create_child("BUTTON", label, style, control_id)
        self.resize_label = self._create_child("STATIC", "リサイズ:", WS_CHILD | WS_VISIBLE, 0)
        for control_id, resize_size in RESIZE_UI_SIZE_OPTIONS.items():
            style = WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON
            if control_id == RESIZE_SIZE_800_ID:
                style |= WS_GROUP
            self.resize_size_buttons[control_id] = self._create_child(
                "BUTTON",
                f"{resize_size}px",
                style,
                control_id,
            )
        self.resize_basis_label = self._create_child("STATIC", "基準:", WS_CHILD | WS_VISIBLE, 0)
        for control_id, (_, label) in RESIZE_BASIS_OPTIONS.items():
            style = WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON
            if control_id == RESIZE_BASIS_WIDTH_ID:
                style |= WS_GROUP
            self.resize_basis_buttons[control_id] = self._create_child("BUTTON", label, style, control_id)
        self.resize_save_button = self._create_child(
            "BUTTON",
            "リサイズ保存",
            WS_CHILD | WS_VISIBLE,
            RESIZE_SAVE_ID,
        )
        self.resize_output_button = self._create_child(
            "BUTTON",
            "保存先選択",
            WS_CHILD | WS_VISIBLE,
            RESIZE_OUTPUT_FOLDER_ID,
        )
        self.resize_output_label = self._create_child(
            "STATIC",
            self._resize_output_display_text(),
            WS_CHILD | WS_VISIBLE | SS_ENDELLIPSIS,
            0,
        )
        self.cache_status_label = self._create_child("STATIC", "キャッシュ: 確認中", WS_CHILD | WS_VISIBLE | SS_ENDELLIPSIS, 0)
        self.cache_limit_label = self._create_child("STATIC", "上限:", WS_CHILD | WS_VISIBLE, 0)
        for control_id, limit_bytes in CACHE_SIZE_LIMIT_OPTIONS.items():
            style = WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON
            if control_id == CACHE_LIMIT_512MB_ID:
                style |= WS_GROUP
            self.cache_limit_buttons[control_id] = self._create_child(
                "BUTTON",
                _format_cache_size(limit_bytes),
                style,
                control_id,
            )
        self.cache_cleanup_button = self._create_child(
            "BUTTON",
            "キャッシュ整理",
            WS_CHILD | WS_VISIBLE,
            CACHE_CLEANUP_ID,
        )
        self.cache_clear_button = self._create_child(
            "BUTTON",
            "キャッシュ全削除",
            WS_CHILD | WS_VISIBLE,
            CACHE_CLEAR_ID,
        )
        self.compare_a_button = self._create_child(
            "BUTTON",
            "比較Aに設定",
            WS_CHILD | WS_VISIBLE,
            COMPARE_SET_A_ID,
        )
        self.compare_b_button = self._create_child(
            "BUTTON",
            "比較Bに設定",
            WS_CHILD | WS_VISIBLE,
            COMPARE_SET_B_ID,
        )
        self.compare_open_button = self._create_child(
            "BUTTON",
            "2枚比較表示",
            WS_CHILD | WS_VISIBLE,
            COMPARE_OPEN_ID,
        )
        self.operation_guide_button = self._create_child(
            "BUTTON",
            OPERATION_GUIDE_TITLE,
            WS_CHILD | WS_VISIBLE,
            OPERATION_GUIDE_ID,
        )
        self._check_sort_buttons()
        self._check_display_mode_buttons()
        self._check_resize_buttons()
        self._check_cache_limit_buttons()
        self.folder_label = self._create_child("STATIC", "フォルダ未選択", WS_CHILD | WS_VISIBLE | SS_PATHELLIPSIS, 0)
        self.current_path_label = self._create_child("STATIC", "\u30d5\u30a9\u30eb\u30c0\u672a\u9078\u629e", WS_CHILD | WS_VISIBLE | SS_PATHELLIPSIS, 0)
        self.current_path_open_button = self._create_child(
            "BUTTON",
            "\u30a8\u30af\u30b9\u30d7\u30ed\u30fc\u30e9\u30fc\u3067\u958b\u304f",
            WS_CHILD | WS_VISIBLE,
            OPEN_CURRENT_FOLDER_ID,
        )
        self._refresh_recent_folder_combo()
        self._refresh_favorite_folder_combo()
        self.folder_tree.create(self.hwnd)
        self.folder_tree.on_folder_selected = self._handle_tree_folder_selected
        self.thumbnail_grid.create(self.hwnd)
        self.thumbnail_grid.on_selection_changed = self._select_image
        self.thumbnail_grid.on_item_activated = self._open_fullscreen
        self.thumbnail_grid.on_visible_range_changed = self._set_thumbnail_priority_range
        self.thumbnail_grid.on_files_dropped = self._handle_drop_files
        self.thumbnail_grid.on_context_menu = self._handle_thumbnail_context_menu
        self.thumbnail_grid.on_copy_image_path = self._handle_copy_image_path
        self.thumbnail_grid.on_copy_folder_path = self._handle_copy_folder_path
        self.thumbnail_grid.on_previous = lambda: self.thumbnail_grid.select_relative(-1)
        self.thumbnail_grid.on_next = lambda: self.thumbnail_grid.select_relative(1)
        self.thumbnail_grid.on_parent_folder = self._handle_open_parent_folder
        self.thumbnail_grid.on_previous_folder = self._handle_open_previous_folder
        self.thumbnail_grid.on_next_folder = self._handle_open_next_folder
        self.image_preview.create(self.hwnd)
        self.image_preview.on_activated = self._open_fullscreen
        self.image_preview.on_files_dropped = self._handle_drop_files
        self.image_preview.on_context_menu = self._handle_preview_context_menu
        self.image_preview.on_copy_image_path = self._handle_copy_image_path
        self.image_preview.on_copy_folder_path = self._handle_copy_folder_path
        self.image_preview.on_previous = lambda: self.thumbnail_grid.select_relative(-1)
        self.image_preview.on_next = lambda: self.thumbnail_grid.select_relative(1)
        self.image_preview.on_parent_folder = self._handle_open_parent_folder
        self.image_preview.on_previous_folder = self._handle_open_previous_folder
        self.image_preview.on_next_folder = self._handle_open_next_folder
        self.image_preview.on_zoom_in = self._zoom_in
        self.image_preview.on_zoom_out = self._zoom_out
        self.fullscreen_preview.create(self.hwnd)
        self.fullscreen_preview.on_close = self._close_fullscreen
        self.fullscreen_preview.on_previous = lambda: self._fullscreen_select_relative(-1)
        self.fullscreen_preview.on_next = lambda: self._fullscreen_select_relative(1)
        self.fullscreen_preview.on_parent_folder = self._handle_open_parent_folder
        self.fullscreen_preview.on_previous_folder = self._handle_open_previous_folder
        self.fullscreen_preview.on_next_folder = self._handle_open_next_folder
        self.fullscreen_preview.on_files_dropped = self._handle_drop_files
        self.fullscreen_preview.on_zoom_in = self._zoom_in
        self.fullscreen_preview.on_zoom_out = self._zoom_out
        self.fullscreen_preview.on_context_menu = self._handle_fullscreen_context_menu
        self.fullscreen_preview.on_copy_image_path = self._handle_fullscreen_copy_image_path
        self.fullscreen_preview.on_copy_folder_path = self._handle_fullscreen_copy_folder_path
        self.status_count_label = self._create_child("STATIC", "\u753b\u50cf: -", WS_CHILD | WS_VISIBLE | SS_ENDELLIPSIS, 0)
        self.status_name_label = self._create_child("STATIC", "", WS_CHILD | WS_VISIBLE | SS_ENDELLIPSIS, 0)
        self.status_dimensions_label = self._create_child("STATIC", "", WS_CHILD | WS_VISIBLE | SS_ENDELLIPSIS, 0)
        self.status_file_size_label = self._create_child("STATIC", "", WS_CHILD | WS_VISIBLE | SS_ENDELLIPSIS, 0)
        self.status_loading_label = self._create_child("STATIC", "", WS_CHILD | WS_VISIBLE | SS_ENDELLIPSIS, 0)
        self.status_bar = self._create_child("STATIC", "フォルダを選択してください", WS_CHILD | WS_VISIBLE | SS_ENDELLIPSIS, 0)
        self.copy_folder_path_button = self._create_child(
            "BUTTON",
            "フォルダパスコピー",
            WS_CHILD | WS_VISIBLE,
            COPY_FOLDER_PATH_ID,
        )
        self.copy_image_path_button = self._create_child(
            "BUTTON",
            "画像パスコピー",
            WS_CHILD | WS_VISIBLE,
            COPY_IMAGE_PATH_ID,
        )
        self.open_selected_folder_button = self._create_child(
            "BUTTON",
            "保存先を開く",
            WS_CHILD | WS_VISIBLE,
            OPEN_SELECTED_FOLDER_ID,
        )

    def _create_child(self, class_name: str, text: str, style: int, control_id: int) -> int:
        hinstance = kernel32.GetModuleHandleW(None)
        hwnd = user32.CreateWindowExW(
            0,
            class_name,
            text,
            style,
            0,
            0,
            0,
            0,
            self.hwnd,
            wintypes.HMENU(control_id),
            hinstance,
            None,
        )
        if not hwnd:
            raise ctypes.WinError()
        font = gdi32.GetStockObject(DEFAULT_GUI_FONT)
        user32.SendMessageW(hwnd, WM_SETFONT, font, True)
        return int(hwnd)

    def _choose_folder(self, title: str = "画像フォルダを選択", initial_folder: Path | None = None) -> Path | None:
        display_name = ctypes.create_unicode_buffer(MAX_LONG_PATH)
        initial_folder = self._folder_dialog_initial_folder() if initial_folder is None else display_path(initial_folder)
        if initial_folder is not None and not path_is_dir(initial_folder):
            initial_folder = None
        initial_folder_buffer = ctypes.create_unicode_buffer(str(initial_folder)) if initial_folder is not None else None
        initial_folder_pointer = (
            ctypes.cast(initial_folder_buffer, ctypes.c_void_p).value
            if initial_folder_buffer is not None
            else 0
        )

        callback_ref = None
        if initial_folder_pointer:
            callback_ref = BFFCALLBACK(_browse_folder_callback)

        browse_info = BROWSEINFOW(
            hwndOwner=self.hwnd,
            pidlRoot=None,
            pszDisplayName=ctypes.cast(display_name, wintypes.LPWSTR),
            lpszTitle=title,
            ulFlags=BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE,
            lpfn=ctypes.cast(callback_ref, ctypes.c_void_p) if callback_ref is not None else None,
            lParam=initial_folder_pointer or 0,
            iImage=0,
        )

        pidl = None
        co_result = int(ole32.CoInitialize(None))
        co_initialized = co_result >= 0
        try:
            pidl = shell32.SHBrowseForFolderW(ctypes.byref(browse_info))
            if not pidl:
                return None

            path_buffer = ctypes.create_unicode_buffer(MAX_LONG_PATH)
            if not _get_shell_path_from_id_list(pidl, path_buffer):
                raise OSError("選択したフォルダのパスを取得できませんでした")
            if not path_buffer.value:
                return None
            return Path(path_buffer.value)
        finally:
            if pidl:
                ole32.CoTaskMemFree(pidl)
            if co_initialized:
                ole32.CoUninitialize()

    def _folder_dialog_initial_folder(self) -> Path | None:
        if self.current_folder is None:
            return None
        folder = display_path(self.current_folder)
        if path_is_dir(folder):
            return folder
        return None

    def _handle_select_folder(self) -> None:
        try:
            folder = self._choose_folder()
            if folder is not None:
                self.load_folder(folder)
        except Exception as error:
            traceback.print_exc(file=sys.stderr)
            user32.MessageBoxW(
                self.hwnd,
                f"フォルダ選択中にエラーが発生しました:\n{error}",
                "フォルダ選択エラー",
                0x10,
            )

    def _handle_open_parent_folder(self) -> bool:
        if self.current_folder is None:
            self._set_window_text(self.status_bar, "現在フォルダがありません")
            return False

        folder = display_path(self.current_folder)
        parent = display_path(folder.parent)
        if _same_path(parent, folder) or not path_is_dir(parent):
            self._set_window_text(self.status_bar, "親フォルダへ移動できません")
            return False

        self.load_folder(parent)
        return True

    def _handle_open_previous_folder(self) -> bool:
        return self._handle_open_sibling_folder(-1)

    def _handle_open_next_folder(self) -> bool:
        return self._handle_open_sibling_folder(1)

    def _handle_folder_navigation_shortcut(self, key: int) -> bool:
        if not _alt_pressed():
            return False
        if key == VK_UP:
            self._handle_open_parent_folder()
            return True
        if key == VK_LEFT:
            self._handle_open_previous_folder()
            return True
        if key == VK_RIGHT:
            self._handle_open_next_folder()
            return True
        return False

    def _handle_open_sibling_folder(self, offset: int) -> bool:
        if self.current_folder is None:
            self._set_window_text(self.status_bar, "現在フォルダがありません")
            return False

        current = display_path(self.current_folder)
        siblings = self._sibling_folders(current)
        if not siblings:
            self._set_window_text(self.status_bar, "同階層のフォルダが見つかりません")
            return False

        current_index = next((index for index, folder in enumerate(siblings) if _same_path(folder, current)), None)
        if current_index is None:
            self._set_window_text(self.status_bar, "現在フォルダを同階層で確認できません")
            return False

        target_index = current_index + offset
        if target_index < 0:
            self._set_window_text(self.status_bar, "前のフォルダはありません")
            return False
        if target_index >= len(siblings):
            self._set_window_text(self.status_bar, "次のフォルダはありません")
            return False

        self.load_folder(siblings[target_index])
        return True

    def _sibling_folders(self, folder: Path) -> list[Path]:
        parent = display_path(folder).parent
        if _same_path(parent, folder) or not path_is_dir(parent):
            return []

        siblings: list[Path] = []
        try:
            with os.scandir(filesystem_path(parent)) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir():
                            siblings.append(display_path(Path(entry.path)))
                    except OSError:
                        continue
        except OSError:
            return []

        siblings.sort(key=lambda path: (_natural_text_key(_folder_display_name(path)), str(path).casefold()))
        return siblings

    def _handle_splitter_mouse_down(self, x: int, y: int) -> bool:
        if not self.hwnd:
            return False
        if self._point_in_tree_splitter(x, y):
            self._tree_splitter_dragging = True
            self._tree_splitter_drag_start_x = x
            self._tree_splitter_drag_start_width = self._current_folder_tree_width()
            user32.SetCapture(self.hwnd)
            self._set_splitter_cursor()
            return True
        if not self._point_in_splitter(x, y):
            return False
        self._splitter_dragging = True
        self._splitter_drag_start_x = x
        self._splitter_drag_start_width = self._current_preview_width()
        user32.SetCapture(self.hwnd)
        self._set_splitter_cursor()
        return True

    def _handle_splitter_mouse_move(self, x: int, y: int) -> bool:
        if self._tree_splitter_dragging:
            self.folder_tree_width = self._clamp_folder_tree_width(
                self._tree_splitter_drag_start_width + (x - self._tree_splitter_drag_start_x)
            )
            self._layout()
            self._set_splitter_cursor()
            return True
        if self._splitter_dragging:
            self.preview_width = self._clamp_preview_width(self._splitter_drag_start_width - (x - self._splitter_drag_start_x))
            self._layout()
            self._set_splitter_cursor()
            return True
        if self._point_in_tree_splitter(x, y) or self._point_in_splitter(x, y):
            self._set_splitter_cursor()
            return True
        return False

    def _handle_splitter_mouse_up(self) -> bool:
        if self._tree_splitter_dragging:
            self._tree_splitter_dragging = False
            user32.ReleaseCapture()
            self._set_window_text(self.status_bar, f"フォルダTREE幅を変更しました: {self.folder_tree_width}px")
            return True
        if not self._splitter_dragging:
            return False
        self._splitter_dragging = False
        user32.ReleaseCapture()
        if self.preview_width is not None:
            self._save_preview_width()
            self._set_window_text(self.status_bar, f"プレビュー幅を保存しました: {self.preview_width}px")
        return True

    def _point_in_splitter(self, x: int, y: int) -> bool:
        if self._splitter_rect is None:
            return False
        rect_x, rect_y, rect_width, rect_height = self._splitter_rect
        return rect_x <= x < rect_x + rect_width and rect_y <= y < rect_y + rect_height

    def _point_in_tree_splitter(self, x: int, y: int) -> bool:
        if self._tree_splitter_rect is None:
            return False
        rect_x, rect_y, rect_width, rect_height = self._tree_splitter_rect
        return rect_x <= x < rect_x + rect_width and rect_y <= y < rect_y + rect_height

    def _set_splitter_cursor(self) -> None:
        user32.SetCursor(user32.LoadCursorW(None, ctypes.cast(ctypes.c_void_p(IDC_SIZEWE), wintypes.LPCWSTR)))

    def _current_folder_tree_width(self) -> int:
        if self.hwnd:
            rect = RECT()
            user32.GetClientRect(self.hwnd, ctypes.byref(rect))
            return self._effective_folder_tree_width(max(0, rect.right - rect.left))
        return self.folder_tree_width

    def _current_preview_width(self) -> int:
        if self.hwnd:
            rect = RECT()
            user32.GetClientRect(self.hwnd, ctypes.byref(rect))
            return self._effective_preview_width(max(0, rect.right - rect.left))
        return self.preview_width or 520

    def _default_folder_tree_width(self, window_width: int) -> int:
        return max(FOLDER_TREE_MIN_WIDTH, min(FOLDER_TREE_DEFAULT_WIDTH, max(FOLDER_TREE_MIN_WIDTH, window_width // 4)))

    def _folder_tree_width_bounds(self, window_width: int) -> tuple[int, int]:
        min_image_area_width = 420
        max_width = max(
            FOLDER_TREE_MIN_WIDTH,
            min(FOLDER_TREE_MAX_WIDTH, window_width - 12 * 2 - 8 - min_image_area_width),
        )
        return FOLDER_TREE_MIN_WIDTH, max_width

    def _effective_folder_tree_width(self, window_width: int) -> int:
        return self._clamp_folder_tree_width(self.folder_tree_width, window_width)

    def _clamp_folder_tree_width(self, folder_tree_width: int, window_width: int | None = None) -> int:
        if window_width is None and self.hwnd:
            rect = RECT()
            user32.GetClientRect(self.hwnd, ctypes.byref(rect))
            window_width = max(0, rect.right - rect.left)
        window_width = max(window_width or 980, 420)
        min_width, max_width = self._folder_tree_width_bounds(window_width)
        return max(min_width, min(max_width, int(folder_tree_width)))

    def _default_preview_width(self, window_width: int) -> int:
        return max(280, min(520, int(window_width * 0.42)))

    def _preview_width_bounds(self, window_width: int) -> tuple[int, int]:
        min_grid_width = 160
        min_preview_width = 240
        max_preview_width = max(min_preview_width, window_width - 12 * 2 - 10 - min_grid_width)
        return min_preview_width, max_preview_width

    def _effective_preview_width(self, window_width: int) -> int:
        width = self.preview_width if self.preview_width is not None else self._default_preview_width(window_width)
        return self._clamp_preview_width(width, window_width)

    def _clamp_preview_width(self, preview_width: int, window_width: int | None = None) -> int:
        if window_width is None and self.hwnd:
            rect = RECT()
            user32.GetClientRect(self.hwnd, ctypes.byref(rect))
            window_width = max(0, rect.right - rect.left)
        window_width = max(window_width or 980, 320)
        min_width, max_width = self._preview_width_bounds(window_width)
        return max(min_width, min(max_width, int(preview_width)))

    def _handle_drop_files(self, drop_handle: int) -> None:
        try:
            for dropped_path in _dropped_paths(drop_handle):
                if self._open_dropped_path(dropped_path):
                    return
            self._set_window_text(self.status_bar, "フォルダまたは画像ファイルをドロップしてください")
        except Exception as error:
            traceback.print_exc(file=sys.stderr)
            user32.MessageBoxW(
                self.hwnd,
                f"ドロップした項目を開けませんでした:\n{error}",
                "ドラッグ＆ドロップエラー",
                0x10,
            )
        finally:
            shell32.DragFinish(drop_handle)

    def _open_dropped_path(self, dropped_path: Path) -> bool:
        drop_target = self._drop_target_from_path(dropped_path)
        if drop_target is None:
            return False
        folder, select_path = drop_target
        if select_path is None:
            self.load_folder(folder)
            return True

        if self.current_folder is not None and _same_path(self.current_folder, folder):
            self._remember_recent_folder(folder)
            selected_index = self._index_for_path(self.thumbnail_grid.items, select_path)
            if selected_index is not None:
                self.thumbnail_grid.select_index(selected_index)
                return True

        self.load_folder(folder, select_path=select_path)
        return True

    def _handle_recent_folder_selected(self) -> None:
        if not self.recent_combo:
            return
        selected_index = int(user32.SendMessageW(self.recent_combo, CB_GETCURSEL, 0, 0))
        self._load_recent_folder_from_history(selected_index)

    def _handle_cleanup_invalid_history(self) -> None:
        recent_removed, favorite_removed = self._cleanup_invalid_history()
        if recent_removed == 0 and favorite_removed == 0:
            self._set_window_text(self.status_bar, "整理対象はありません")
            return
        self._set_window_text(
            self.status_bar,
            f"無効な履歴を整理しました: 最近 {recent_removed}件 / お気に入り {favorite_removed}件",
        )

    def _cleanup_invalid_history(self) -> tuple[int, int]:
        valid_recent_folders = [folder for folder in self.recent_folders if path_is_dir(folder)]
        valid_favorite_folders = [folder for folder in self.favorite_folders if path_is_dir(folder)]
        recent_removed = len(self.recent_folders) - len(valid_recent_folders)
        favorite_removed = len(self.favorite_folders) - len(valid_favorite_folders)

        if recent_removed:
            self.recent_folders = valid_recent_folders
            self._save_recent_folders()
            self._refresh_recent_folder_combo()
        if favorite_removed:
            self.favorite_folders = valid_favorite_folders
            self._save_favorite_folders()
            self._refresh_favorite_folder_combo()
        return recent_removed, favorite_removed

    def _remove_missing_saved_folder(self, folder: Path) -> bool:
        recent_removed = any(_same_path(folder, recent_folder) for recent_folder in self.recent_folders)
        favorite_removed = any(_same_path(folder, favorite_folder) for favorite_folder in self.favorite_folders)
        if not recent_removed and not favorite_removed:
            return False

        if recent_removed:
            self.recent_folders = remove_recent_folder(self.recent_folders, folder)
            self._save_recent_folders()
            self._refresh_recent_folder_combo()
        if favorite_removed:
            self.favorite_folders = remove_favorite_folder(self.favorite_folders, folder)
            self._save_favorite_folders()
            self._refresh_favorite_folder_combo()
        return True

    def _handle_add_favorite_folder(self) -> None:
        if self.current_folder is None:
            self._set_window_text(self.status_bar, "お気に入りに追加するフォルダがありません")
            return
        if not path_is_dir(self.current_folder):
            self._set_window_text(self.status_bar, "現在のフォルダをお気に入りに追加できません")
            return

        previous = [str(path) for path in self.favorite_folders]
        self.favorite_folders = add_favorite_folder(self.favorite_folders, self.current_folder)
        if [str(path) for path in self.favorite_folders] == previous:
            self._set_window_text(self.status_bar, "このフォルダはすでにお気に入りに登録されています")
        else:
            self._save_favorite_folders()
            self._set_window_text(self.status_bar, f"お気に入りに追加しました: {self._folder_display_text(self.current_folder)}")
        self._refresh_favorite_folder_combo()

    def _handle_remove_favorite_folder(self) -> None:
        if not self.favorite_combo:
            return
        selected_index = int(user32.SendMessageW(self.favorite_combo, CB_GETCURSEL, 0, 0))
        self._remove_favorite_folder_at(selected_index)

    def _remove_favorite_folder_at(self, selected_index: int) -> bool:
        if selected_index == CB_ERR or selected_index < 0 or selected_index >= len(self.favorite_folders):
            self._set_window_text(self.status_bar, "削除するお気に入りがありません")
            return False

        folder = self.favorite_folders[selected_index]
        self.favorite_folders = remove_favorite_folder(self.favorite_folders, folder)
        self._save_favorite_folders()
        self._refresh_favorite_folder_combo()
        self._set_window_text(self.status_bar, f"お気に入りから削除しました: {self._folder_display_text(folder)}")
        return True

    def _handle_move_favorite_folder(self, offset: int) -> None:
        if not self.favorite_combo:
            return
        selected_index = int(user32.SendMessageW(self.favorite_combo, CB_GETCURSEL, 0, 0))
        self._move_favorite_folder_at(selected_index, offset)

    def _move_favorite_folder_at(self, selected_index: int, offset: int) -> bool:
        if selected_index == CB_ERR or selected_index < 0 or selected_index >= len(self.favorite_folders):
            self._set_window_text(self.status_bar, "移動するお気に入りがありません")
            return False

        folder = self.favorite_folders[selected_index]
        updated, new_index = move_favorite_folder(self.favorite_folders, selected_index, offset)
        if new_index == selected_index:
            direction_text = "上" if offset < 0 else "下"
            self._set_window_text(self.status_bar, f"これ以上{direction_text}へ移動できません")
            return False

        self.favorite_folders = updated
        self._save_favorite_folders()
        self._refresh_favorite_folder_combo(selected_index=new_index)
        self._set_window_text(self.status_bar, f"お気に入りの順序を変更しました: {self._folder_display_text(folder)}")
        return True

    def _handle_favorite_folder_selected(self) -> None:
        if not self.favorite_combo:
            return
        selected_index = int(user32.SendMessageW(self.favorite_combo, CB_GETCURSEL, 0, 0))
        self._load_favorite_folder(selected_index)

    def _load_recent_folder_from_history(self, selected_index: int) -> bool:
        if selected_index == CB_ERR or selected_index < 0 or selected_index >= len(self.recent_folders):
            return False

        folder = self.recent_folders[selected_index]
        if not path_is_dir(folder):
            self.recent_folders = remove_recent_folder(self.recent_folders, folder)
            self._save_recent_folders()
            self._refresh_recent_folder_combo()
            self._set_folder_status("履歴のフォルダが見つかりません", folder)
            return False

        self._set_folder_status("最近開いたフォルダを開きます", folder)
        self.load_folder(folder)
        return True

    def _load_favorite_folder(self, selected_index: int) -> bool:
        if selected_index == CB_ERR or selected_index < 0 or selected_index >= len(self.favorite_folders):
            return False

        folder = self.favorite_folders[selected_index]
        if not path_is_dir(folder):
            self.favorite_folders = remove_favorite_folder(self.favorite_folders, folder)
            self._save_favorite_folders()
            self._refresh_favorite_folder_combo()
            self._set_folder_status("存在しないお気に入りを整理しました", folder)
            return False

        self._set_folder_status("お気に入りを開きます", folder)
        self.load_folder(folder)
        return True

    def _handle_copy_folder_path(self) -> bool:
        if self.current_folder is None:
            self._set_window_text(self.status_bar, "コピーするフォルダがありません")
            return False
        return self._copy_path_to_clipboard(self.current_folder, "フォルダパス")

    def _handle_copy_image_path(self) -> bool:
        if self._selected_image_file is None:
            self._set_window_text(self.status_bar, "コピーする画像が選択されていません")
            return False
        return self._copy_path_to_clipboard(self._selected_image_file.path, "画像パス")

    def _handle_open_current_folder(self) -> bool:
        if self.current_folder is None:
            self._set_window_text(self.status_bar, "\u958b\u304f\u30d5\u30a9\u30eb\u30c0\u304c\u3042\u308a\u307e\u305b\u3093")
            return False
        return self._open_folder_in_explorer(self.current_folder, "\u73fe\u5728\u30d5\u30a9\u30eb\u30c0")

    def _handle_open_selected_image_folder(self) -> bool:
        if self._selected_image_file is None:
            self._set_window_text(self.status_bar, "保存先を開く画像が選択されていません")
            return False
        return self._open_folder_in_explorer(self._selected_image_file.path.parent, "保存先フォルダ")

    def _open_folder_in_explorer(self, folder: Path, label: str) -> bool:
        folder = display_path(folder)
        if not path_is_dir(folder):
            self._set_window_text(self.status_bar, f"{label}が見つかりません: {folder}")
            return False

        try:
            result = shell32.ShellExecuteW(self.hwnd, "open", str(folder), None, None, SW_SHOW)
        except OSError as error:
            traceback.print_exc(file=sys.stderr)
            self._set_window_text(self.status_bar, f"{label}を開けませんでした: {error}")
            return False

        if _shell_execute_failed(result):
            self._set_window_text(self.status_bar, f"{label}を開けませんでした: {folder}")
            return False

        self._set_window_text(self.status_bar, f"{label}を開きました: {folder}")
        return True

    def _handle_fullscreen_copy_image_path(self) -> bool:
        copied = self._handle_copy_image_path()
        if copied:
            self.fullscreen_preview.show_feedback("画像パスをコピーしました")
        return copied

    def _handle_fullscreen_copy_folder_path(self) -> bool:
        copied = self._handle_copy_folder_path()
        if copied:
            self.fullscreen_preview.show_feedback("フォルダパスをコピーしました")
        return copied

    def _show_operation_guide(self) -> None:
        self.operation_guide_dialog.show(self.hwnd, OPERATION_GUIDE_TITLE, OPERATION_GUIDE_TEXT)

    def _handle_set_compare_a(self) -> bool:
        return self._set_compare_image("A")

    def _handle_set_compare_b(self) -> bool:
        return self._set_compare_image("B")

    def _set_compare_image(self, slot: str) -> bool:
        if self._selected_image_file is None:
            self._set_window_text(self.status_bar, f"比較{slot}に設定する画像が選択されていません")
            return False

        if slot == "A":
            self._compare_a_image_file = self._selected_image_file
        else:
            self._compare_b_image_file = self._selected_image_file
        self._set_window_text(self.status_bar, f"比較{slot}に設定しました: {self._selected_image_file.name}")
        return True

    def _handle_open_compare_view(self) -> bool:
        if self._compare_a_image_file is None or self._compare_b_image_file is None:
            self._set_window_text(self.status_bar, "比較Aと比較Bの画像を設定してください")
            return False

        try:
            self.compare_view.show(
                self.hwnd,
                self._compare_a_image_file,
                self._compare_b_image_file,
                self.display_mode,
            )
        except Exception as error:
            traceback.print_exc(file=sys.stderr)
            self._set_window_text(self.status_bar, f"2枚比較表示を開けませんでした: {error}")
            return False

        self._set_window_text(
            self.status_bar,
            f"2枚比較表示を開きました: {self._compare_a_image_file.name} / {self._compare_b_image_file.name}",
        )
        return True

    def _handle_copy_shortcut(self, key: int) -> bool:
        if not (_ctrl_pressed() and _shift_pressed()):
            return False
        if key == VK_C:
            self._handle_copy_image_path()
            return True
        if key == VK_F:
            self._handle_copy_folder_path()
            return True
        return False

    def _handle_thumbnail_context_menu(
        self,
        source_hwnd: int | None,
        x: int,
        y: int,
        image_file: ImageFile | None,
    ) -> None:
        screen_x, screen_y = self._control_point_to_screen(source_hwnd, x, y)
        command = self._show_path_context_menu(screen_x, screen_y)
        if command == CONTEXT_COPY_IMAGE_PATH_ID:
            if image_file is None:
                self._set_window_text(self.status_bar, "コピーする画像がありません")
                return
            self._copy_path_to_clipboard(image_file.path, "画像パス")
        elif command == CONTEXT_COPY_FOLDER_PATH_ID:
            self._handle_copy_folder_path()

    def _handle_preview_context_menu(self, source_hwnd: int | None, x: int, y: int) -> None:
        screen_x, screen_y = self._control_point_to_screen(source_hwnd, x, y)
        command = self._show_path_context_menu(screen_x, screen_y)
        if command == CONTEXT_COPY_IMAGE_PATH_ID:
            self._handle_copy_image_path()
        elif command == CONTEXT_COPY_FOLDER_PATH_ID:
            self._handle_copy_folder_path()

    def _handle_fullscreen_context_menu(self, source_hwnd: int | None, x: int, y: int) -> None:
        screen_x, screen_y = self._control_point_to_screen(source_hwnd, x, y)
        command = self._show_path_context_menu(screen_x, screen_y, owner_hwnd=source_hwnd)
        if command == CONTEXT_COPY_IMAGE_PATH_ID:
            self._handle_fullscreen_copy_image_path()
        elif command == CONTEXT_COPY_FOLDER_PATH_ID:
            self._handle_fullscreen_copy_folder_path()

    def _show_path_context_menu(self, screen_x: int, screen_y: int, owner_hwnd: int | None = None) -> int:
        menu_owner = owner_hwnd or self.hwnd
        if not menu_owner:
            return 0
        menu = user32.CreatePopupMenu()
        if not menu:
            return 0
        try:
            user32.AppendMenuW(menu, MF_STRING, CONTEXT_COPY_IMAGE_PATH_ID, "画像パスをコピー")
            user32.AppendMenuW(menu, MF_STRING, CONTEXT_COPY_FOLDER_PATH_ID, "フォルダパスをコピー")
            user32.SetForegroundWindow(menu_owner)
            return int(
                user32.TrackPopupMenu(
                    menu,
                    TPM_RIGHTBUTTON | TPM_RETURNCMD,
                    screen_x,
                    screen_y,
                    0,
                    menu_owner,
                    None,
                )
            )
        finally:
            user32.DestroyMenu(menu)

    def _control_point_to_screen(self, source_hwnd: int | None, x: int, y: int) -> tuple[int, int]:
        if not source_hwnd:
            return (x, y)
        point = POINT(x, y)
        if not user32.ClientToScreen(source_hwnd, ctypes.byref(point)):
            return (x, y)
        return (int(point.x), int(point.y))

    def _copy_path_to_clipboard(self, path: Path, label: str) -> bool:
        path_text = str(display_path(path))
        try:
            self._copy_text_to_clipboard(path_text)
        except OSError:
            traceback.print_exc(file=sys.stderr)
            self._set_window_text(self.status_bar, f"{label}をコピーできませんでした")
            return False
        self._set_window_text(self.status_bar, f"{label}をコピーしました: {path_text}")
        return True

    def _copy_text_to_clipboard(self, text: str) -> None:
        self._require_window()
        data = (text + "\0").encode("utf-16-le")
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, len(data))
        if not handle:
            raise ctypes.WinError()

        locked = kernel32.GlobalLock(handle)
        if not locked:
            kernel32.GlobalFree(handle)
            raise ctypes.WinError()

        try:
            ctypes.memmove(locked, data, len(data))
        finally:
            kernel32.GlobalUnlock(handle)

        if not user32.OpenClipboard(self.hwnd):
            kernel32.GlobalFree(handle)
            raise ctypes.WinError()

        clipboard_owns_handle = False
        try:
            if not user32.EmptyClipboard():
                raise ctypes.WinError()
            if not user32.SetClipboardData(CF_UNICODETEXT, handle):
                raise ctypes.WinError()
            clipboard_owns_handle = True
        finally:
            user32.CloseClipboard()
            if not clipboard_owns_handle:
                kernel32.GlobalFree(handle)

    def _remember_recent_folder(self, folder: Path) -> None:
        if not self.hwnd:
            return
        updated = add_recent_folder(self.recent_folders, folder)
        if [str(path) for path in updated] != [str(path) for path in self.recent_folders]:
            self.recent_folders = updated
            self._save_recent_folders()
        else:
            self.recent_folders = updated
        self._refresh_recent_folder_combo()
        self._refresh_favorite_folder_combo()

    def _save_recent_folders(self) -> None:
        try:
            save_recent_folders(self.recent_folders)
        except OSError:
            traceback.print_exc(file=sys.stderr)
            self._set_window_text(self.status_bar, "最近開いたフォルダ履歴を保存できませんでした")

    def _save_favorite_folders(self) -> None:
        try:
            save_favorite_folders(self.favorite_folders)
        except OSError:
            traceback.print_exc(file=sys.stderr)
            self._set_window_text(self.status_bar, "お気に入りフォルダを保存できませんでした")

    def _refresh_recent_folder_combo(self) -> None:
        if not self.recent_combo:
            return
        user32.SendMessageW(self.recent_combo, CB_RESETCONTENT, 0, 0)

        selected_index = CB_ERR
        for index, folder in enumerate(self.recent_folders):
            _combo_add_string(self.recent_combo, self._recent_folder_display_text(folder))
            if self.current_folder is not None and _same_path(folder, self.current_folder):
                selected_index = index

        if selected_index != CB_ERR:
            user32.SendMessageW(self.recent_combo, CB_SETCURSEL, selected_index, 0)

    def _recent_folder_display_text(self, folder: Path) -> str:
        return _folder_list_display_label(folder, self.recent_folders, RECENT_FOLDER_DISPLAY_LIMIT)

    def _refresh_favorite_folder_combo(self, selected_index: int | None = None) -> None:
        if not self.favorite_combo:
            return
        user32.SendMessageW(self.favorite_combo, CB_RESETCONTENT, 0, 0)

        current_folder_index = CB_ERR
        for index, folder in enumerate(self.favorite_folders):
            _combo_add_string(self.favorite_combo, self._favorite_folder_display_text(folder))
            if selected_index is None and self.current_folder is not None and _same_path(folder, self.current_folder):
                current_folder_index = index

        if selected_index is not None and 0 <= selected_index < len(self.favorite_folders):
            combo_index = selected_index
        else:
            combo_index = current_folder_index

        if combo_index != CB_ERR:
            user32.SendMessageW(self.favorite_combo, CB_SETCURSEL, combo_index, 0)

    def _favorite_folder_display_text(self, folder: Path) -> str:
        return _folder_list_display_label(folder, self.favorite_folders, FAVORITE_FOLDER_DISPLAY_LIMIT)

    def _handle_tree_folder_selected(self, folder: Path) -> None:
        folder = display_path(folder)
        if self.current_folder is not None and _same_path(self.current_folder, folder):
            return
        try:
            if not path_is_dir(folder):
                self._set_folder_status("フォルダへアクセスできません", folder)
                return
            self.load_folder(folder, show_error_dialog=False)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self._set_folder_status("フォルダを開けません", folder)

    def _folder_from_dropped_path(self, dropped_path: str | Path) -> Path | None:
        drop_target = self._drop_target_from_path(dropped_path)
        return None if drop_target is None else drop_target[0]

    def _drop_target_from_path(self, dropped_path: str | Path) -> tuple[Path, Path | None] | None:
        path = display_path(dropped_path)
        if path_is_dir(path):
            return path, None
        if path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS and path_exists(path):
            return path.parent, path
        return None

    def _layout(self) -> None:
        if not all([
            self.hwnd,
            self.folder_group_box,
            self.favorite_group_box,
            self.view_group_box,
            self.cache_group_box,
            self.open_button,
            self.parent_folder_button,
            self.previous_folder_button,
            self.next_folder_button,
            self.cleanup_invalid_button,
            self.recent_label,
            self.recent_combo,
            self.favorite_add_button,
            self.favorite_remove_button,
            self.favorite_move_up_button,
            self.favorite_move_down_button,
            self.favorite_label,
            self.favorite_combo,
            self.thumbnail_label,
            self.operation_guide_button,
            self.resize_label,
            self.resize_basis_label,
            self.resize_save_button,
            self.resize_output_button,
            self.resize_output_label,
            self.cache_status_label,
            self.cache_cleanup_button,
            self.cache_clear_button,
            self.cache_limit_label,
            self.compare_a_button,
            self.compare_b_button,
            self.compare_open_button,
            self.folder_label,
            self.current_path_label,
            self.current_path_open_button,
            self.status_count_label,
            self.status_name_label,
            self.status_dimensions_label,
            self.status_file_size_label,
            self.status_loading_label,
            self.status_bar,
            self.copy_folder_path_button,
            self.copy_image_path_button,
            self.open_selected_folder_button,
        ]):
            return

        rect = RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        width = max(0, rect.right - rect.left)
        height = max(0, rect.bottom - rect.top)

        margin = 12
        group_margin = 8
        group_inner_margin = 10
        compact = width < 760
        button_width = 112 if compact else 120
        folder_nav_button_width = 82 if compact else 96
        cleanup_button_width = 112 if compact else 124
        favorite_button_width = 94 if compact else 108
        favorite_move_button_width = 46 if compact else 56
        size_button_width = 50 if compact else 58
        size_button_gap = 5 if compact else 6
        thumbnail_label_width = 72
        sort_label_width = 64
        sort_button_width = 72 if compact else 82
        order_label_width = 44
        order_button_width = 52 if compact else 58
        display_label_width = 44
        guide_button_width = 92 if compact else 104
        resize_label_width = 70
        resize_size_button_width = 72 if compact else 78
        resize_basis_label_width = 44
        resize_basis_button_width = 54 if compact else 60
        resize_save_button_width = 106 if compact else 120
        resize_output_button_width = 96 if compact else 110
        compare_button_width = 102 if compact else 112
        compare_open_button_width = 110 if compact else 124
        cache_status_width = 174 if compact else 220
        cache_limit_label_width = 42
        cache_limit_button_width = 58 if compact else 66
        cache_button_width = 104 if compact else 116
        cache_clear_button_width = 116 if compact else 128
        display_button_widths = {
            DISPLAY_SCALE_50_ID: 44 if compact else 48,
            DISPLAY_ORIGINAL_ID: 50 if compact else 54,
            DISPLAY_SCALE_200_ID: 50 if compact else 54,
            DISPLAY_FIT_HEIGHT_ID: 102 if compact else 112,
        }
        copy_folder_button_width = 112 if compact else 128
        copy_image_button_width = 100 if compact else 116
        open_folder_button_width = 104 if compact else 118
        group_width = max(120, width - margin * 2)
        folder_group_height = 64
        favorite_group_height = 38
        view_group_height = 116
        cache_group_height = 38
        top_height = folder_group_height + favorite_group_height + view_group_height + cache_group_height + group_margin * 3
        status_height = 54
        content_top = margin + top_height + 10
        content_height = max(120, height - content_top - status_height - margin)
        gap = 10
        tree_gap = 8
        path_bar_height = 24
        path_bar_gap = 6
        tree_width = self._effective_folder_tree_width(width)
        image_area_x = margin + tree_width + tree_gap
        image_area_width = max(160, width - image_area_x - margin)
        image_content_top = content_top + path_bar_height + path_bar_gap
        image_content_height = max(80, content_height - path_bar_height - path_bar_gap)
        preview_width = self._effective_preview_width(width)
        preview_width = min(preview_width, max(120, image_area_width - gap - 160))
        grid_width = max(160, image_area_width - preview_width - gap)
        self._tree_splitter_rect = (margin + tree_width, content_top, tree_gap, content_height)
        if image_area_width < 540:
            self._splitter_rect = None
            preview_height = max(160, int(image_content_height * 0.46))
            grid_height = max(120, image_content_height - preview_height - gap)
            grid_width = max(120, image_area_width)
            preview_x = image_area_x
            preview_y = image_content_top + grid_height + gap
            preview_width = max(120, image_area_width)
        else:
            grid_height = image_content_height
            preview_x = image_area_x + grid_width + gap
            preview_y = image_content_top
            preview_height = image_content_height
            self._splitter_rect = (image_area_x + grid_width, image_content_top, gap, image_content_height)

        folder_group_y = margin
        favorite_group_y = folder_group_y + folder_group_height + group_margin
        view_group_y = favorite_group_y + favorite_group_height + group_margin
        cache_group_y = view_group_y + view_group_height + group_margin
        folder_row1_y = folder_group_y + 13
        folder_row2_y = folder_group_y + 38
        favorite_control_y = favorite_group_y + 13
        view_row1_y = view_group_y + 13
        view_row2_y = view_group_y + 38
        view_row3_y = view_group_y + 63
        view_row4_y = view_group_y + 88
        cache_control_y = cache_group_y + 13

        user32.MoveWindow(self.folder_group_box, margin, folder_group_y, group_width, folder_group_height, True)
        user32.MoveWindow(
            self.favorite_group_box,
            margin,
            favorite_group_y,
            group_width,
            favorite_group_height,
            True,
        )
        user32.MoveWindow(self.view_group_box, margin, view_group_y, group_width, view_group_height, True)
        user32.MoveWindow(self.cache_group_box, margin, cache_group_y, group_width, cache_group_height, True)

        inner_x = margin + group_inner_margin
        inner_right = width - margin - group_inner_margin
        folder_button_x = inner_x
        user32.MoveWindow(self.open_button, folder_button_x, folder_row1_y, button_width, 22, True)
        folder_button_x += button_width + 6
        user32.MoveWindow(
            self.parent_folder_button,
            folder_button_x,
            folder_row1_y,
            folder_nav_button_width,
            22,
            True,
        )
        folder_button_x += folder_nav_button_width + 6
        user32.MoveWindow(
            self.previous_folder_button,
            folder_button_x,
            folder_row1_y,
            folder_nav_button_width,
            22,
            True,
        )
        folder_button_x += folder_nav_button_width + 6
        user32.MoveWindow(
            self.next_folder_button,
            folder_button_x,
            folder_row1_y,
            folder_nav_button_width,
            22,
            True,
        )
        folder_button_x += folder_nav_button_width + 10
        cleanup_button_x = min(folder_button_x, max(inner_x, inner_right - cleanup_button_width))
        user32.MoveWindow(
            self.cleanup_invalid_button,
            cleanup_button_x,
            folder_row1_y,
            cleanup_button_width,
            22,
            True,
        )
        recent_label_width = 112
        recent_label_x = inner_x
        recent_combo_x = recent_label_x + recent_label_width + 6
        remaining_after_recent = max(120, inner_right - recent_combo_x)
        recent_combo_target_width = int(remaining_after_recent * 0.45) if compact else 300
        recent_combo_width = min(320, max(120, recent_combo_target_width))
        folder_x = recent_combo_x + recent_combo_width + 10
        user32.MoveWindow(self.recent_label, recent_label_x, folder_row2_y + 3, recent_label_width, 18, True)
        user32.MoveWindow(self.recent_combo, recent_combo_x, folder_row2_y, recent_combo_width, 220, True)
        user32.MoveWindow(
            self.folder_label,
            folder_x,
            folder_row2_y + 3,
            max(90, inner_right - folder_x),
            18,
            True,
        )

        favorite_label_width = 72
        favorite_label_x = inner_x
        favorite_combo_x = favorite_label_x + favorite_label_width + 6
        favorite_buttons_width = (
            favorite_button_width * 2
            + favorite_move_button_width * 2
            + size_button_gap * 4
            + 10
        )
        favorite_combo_width = max(110, inner_right - favorite_combo_x - favorite_buttons_width)
        favorite_button_x = favorite_combo_x + favorite_combo_width + 10
        favorite_remove_button_x = favorite_button_x + favorite_button_width + 6
        favorite_move_up_button_x = favorite_remove_button_x + favorite_button_width + 6
        favorite_move_down_button_x = favorite_move_up_button_x + favorite_move_button_width + 6
        user32.MoveWindow(self.favorite_label, favorite_label_x, favorite_control_y + 3, favorite_label_width, 18, True)
        user32.MoveWindow(self.favorite_combo, favorite_combo_x, favorite_control_y, favorite_combo_width, 220, True)
        user32.MoveWindow(
            self.favorite_add_button,
            favorite_button_x,
            favorite_control_y,
            favorite_button_width,
            22,
            True,
        )
        user32.MoveWindow(
            self.favorite_remove_button,
            favorite_remove_button_x,
            favorite_control_y,
            favorite_button_width,
            22,
            True,
        )
        user32.MoveWindow(
            self.favorite_move_up_button,
            favorite_move_up_button_x,
            favorite_control_y,
            favorite_move_button_width,
            22,
            True,
        )
        user32.MoveWindow(
            self.favorite_move_down_button,
            favorite_move_down_button_x,
            favorite_control_y,
            favorite_move_button_width,
            22,
            True,
        )

        size_x = inner_x
        user32.MoveWindow(self.thumbnail_label, size_x, view_row1_y + 3, thumbnail_label_width, 18, True)
        size_x += thumbnail_label_width
        for control_id in THUMBNAIL_SIZE_OPTIONS:
            user32.MoveWindow(
                self.thumbnail_size_buttons[control_id],
                size_x,
                view_row1_y,
                size_button_width,
                22,
                True,
            )
            size_x += size_button_width + size_button_gap
        sort_x = size_x + 14
        user32.MoveWindow(self.sort_label, sort_x, view_row1_y + 3, sort_label_width, 18, True)
        sort_x += sort_label_width
        for control_id in SORT_FIELD_OPTIONS:
            user32.MoveWindow(self.sort_buttons[control_id], sort_x, view_row1_y, sort_button_width, 22, True)
            sort_x += sort_button_width + size_button_gap
        sort_x += 8
        user32.MoveWindow(self.order_label, sort_x, view_row1_y + 3, order_label_width, 18, True)
        sort_x += order_label_width
        for control_id in SORT_ORDER_OPTIONS:
            user32.MoveWindow(self.order_buttons[control_id], sort_x, view_row1_y, order_button_width, 22, True)
            sort_x += order_button_width + size_button_gap

        display_x = inner_x
        user32.MoveWindow(self.display_label, display_x, view_row2_y + 3, display_label_width, 18, True)
        display_x += display_label_width
        for control_id in DISPLAY_MODE_OPTIONS:
            button_width_for_mode = display_button_widths[control_id]
            user32.MoveWindow(
                self.display_buttons[control_id],
                display_x,
                view_row2_y,
                button_width_for_mode,
                22,
                True,
            )
            display_x += button_width_for_mode + size_button_gap
        guide_button_x = min(display_x + 10, max(inner_x, inner_right - guide_button_width))
        user32.MoveWindow(
            self.operation_guide_button,
            guide_button_x,
            view_row2_y,
            guide_button_width,
            22,
            True,
        )
        resize_x = inner_x
        user32.MoveWindow(self.resize_label, resize_x, view_row3_y + 3, resize_label_width, 18, True)
        resize_x += resize_label_width
        for control_id in RESIZE_UI_SIZE_OPTIONS:
            user32.MoveWindow(
                self.resize_size_buttons[control_id],
                resize_x,
                view_row3_y,
                resize_size_button_width,
                22,
                True,
            )
            resize_x += resize_size_button_width + size_button_gap
        resize_x += 8
        user32.MoveWindow(self.resize_basis_label, resize_x, view_row3_y + 3, resize_basis_label_width, 18, True)
        resize_x += resize_basis_label_width
        for control_id in RESIZE_BASIS_OPTIONS:
            user32.MoveWindow(
                self.resize_basis_buttons[control_id],
                resize_x,
                view_row3_y,
                resize_basis_button_width,
                22,
                True,
            )
            resize_x += resize_basis_button_width + size_button_gap
        user32.MoveWindow(
            self.resize_save_button,
            resize_x + 8,
            view_row3_y,
            resize_save_button_width,
            22,
            True,
        )
        resize_x += resize_save_button_width + 16
        user32.MoveWindow(
            self.resize_output_button,
            resize_x,
            view_row3_y,
            resize_output_button_width,
            22,
            True,
        )
        resize_x += resize_output_button_width + 8
        user32.MoveWindow(
            self.resize_output_label,
            resize_x,
            view_row3_y + 3,
            max(70, inner_right - resize_x),
            18,
            True,
        )
        compare_x = inner_x
        user32.MoveWindow(self.compare_a_button, compare_x, view_row4_y, compare_button_width, 22, True)
        compare_x += compare_button_width + size_button_gap
        user32.MoveWindow(self.compare_b_button, compare_x, view_row4_y, compare_button_width, 22, True)
        compare_x += compare_button_width + size_button_gap
        user32.MoveWindow(
            self.compare_open_button,
            compare_x,
            view_row4_y,
            compare_open_button_width,
            22,
            True,
        )
        cache_x = inner_x
        user32.MoveWindow(self.cache_status_label, cache_x, cache_control_y + 3, cache_status_width, 18, True)
        cache_x += cache_status_width + 10
        user32.MoveWindow(self.cache_limit_label, cache_x, cache_control_y + 3, cache_limit_label_width, 18, True)
        cache_x += cache_limit_label_width
        for control_id in CACHE_SIZE_LIMIT_OPTIONS:
            user32.MoveWindow(
                self.cache_limit_buttons[control_id],
                cache_x,
                cache_control_y,
                cache_limit_button_width,
                22,
                True,
            )
            cache_x += cache_limit_button_width + size_button_gap
        cache_x += 8
        user32.MoveWindow(
            self.cache_cleanup_button,
            cache_x,
            cache_control_y,
            cache_button_width,
            22,
            True,
        )
        cache_x += cache_button_width + size_button_gap
        user32.MoveWindow(
            self.cache_clear_button,
            cache_x,
            cache_control_y,
            cache_clear_button_width,
            22,
            True,
        )
        current_path_button_width = 138 if compact else 160
        current_path_label_width = max(80, image_area_width - current_path_button_width - size_button_gap)
        user32.MoveWindow(self.current_path_label, image_area_x, content_top + 3, current_path_label_width, 18, True)
        user32.MoveWindow(
            self.current_path_open_button,
            image_area_x + current_path_label_width + size_button_gap,
            content_top,
            current_path_button_width,
            22,
            True,
        )
        self.folder_tree.move(margin, content_top, tree_width, content_height)
        self.thumbnail_grid.move(image_area_x, image_content_top, grid_width, grid_height)
        self.image_preview.move(preview_x, preview_y, preview_width, preview_height)
        status_info_y = max(content_top + content_height + 6, height - status_height)
        status_message_y = status_info_y + 26
        status_right = width - margin
        fixed_status_width = 96 + 120 + 112 + (132 if compact else 156) + size_button_gap * 4
        status_name_width = max(90, status_right - margin - fixed_status_width)
        status_x = margin
        user32.MoveWindow(self.status_count_label, status_x, status_info_y + 3, 96, 18, True)
        status_x += 96 + size_button_gap
        user32.MoveWindow(self.status_name_label, status_x, status_info_y + 3, status_name_width, 18, True)
        status_x += status_name_width + size_button_gap
        user32.MoveWindow(self.status_dimensions_label, status_x, status_info_y + 3, 120, 18, True)
        status_x += 120 + size_button_gap
        user32.MoveWindow(self.status_file_size_label, status_x, status_info_y + 3, 112, 18, True)
        status_x += 112 + size_button_gap
        user32.MoveWindow(self.status_loading_label, status_x, status_info_y + 3, max(80, status_right - status_x), 18, True)
        open_folder_x = width - margin - open_folder_button_width
        copy_image_x = open_folder_x - size_button_gap - copy_image_button_width
        copy_folder_x = copy_image_x - size_button_gap - copy_folder_button_width
        status_width = max(120, copy_folder_x - margin - size_button_gap)
        user32.MoveWindow(
            self.status_bar,
            margin,
            status_message_y,
            status_width,
            22,
            True,
        )
        user32.MoveWindow(
            self.copy_folder_path_button,
            copy_folder_x,
            status_message_y,
            copy_folder_button_width,
            22,
            True,
        )
        user32.MoveWindow(
            self.copy_image_path_button,
            copy_image_x,
            status_message_y,
            copy_image_button_width,
            22,
            True,
        )
        user32.MoveWindow(
            self.open_selected_folder_button,
            open_folder_x,
            status_message_y,
            open_folder_button_width,
            22,
            True,
        )

    def _change_thumbnail_size(self, thumbnail_size: int) -> None:
        if thumbnail_size == self.thumbnail_size:
            return

        self.thumbnail_size = thumbnail_size
        self._load_id += 1
        load_id = self._load_id
        image_files = list(self.thumbnail_grid.items)
        self._drain_thumbnail_queue(ignore_all=True)
        self.thumbnail_grid.set_thumbnail_size(thumbnail_size)
        self._check_thumbnail_size_button(thumbnail_size)
        self._thumbnail_done = 0
        self._thumbnail_total = len(image_files)

        if not image_files:
            self._refresh_status_details("")
            self._set_window_text(self.status_bar, "画像が見つかりません" if self.current_folder else "フォルダを選択してください")
            return

        self._refresh_status_details("サムネイル読み込み中")
        self._set_window_text(
            self.status_bar,
            f"{len(image_files)}件の画像が見つかりました。{thumbnail_size}pxサムネイルを先読み中...",
        )
        self._start_thumbnail_worker(load_id, image_files, thumbnail_size)

    def _check_thumbnail_size_button(self, thumbnail_size: int) -> None:
        if not self.hwnd:
            return

        selected_id = next(
            (control_id for control_id, size in THUMBNAIL_SIZE_OPTIONS.items() if size == thumbnail_size),
            THUMBNAIL_SIZE_128_ID,
        )
        user32.CheckRadioButton(self.hwnd, THUMBNAIL_SIZE_64_ID, THUMBNAIL_SIZE_256_ID, selected_id)
        selected_button = self.thumbnail_size_buttons.get(selected_id)
        if selected_button:
            user32.SendMessageW(selected_button, BM_SETCHECK, BST_CHECKED, 0)

    def _check_sort_buttons(self) -> None:
        if not self.hwnd:
            return

        selected_sort_id = next(
            (control_id for control_id, (field, _) in SORT_FIELD_OPTIONS.items() if field == self.sort_field),
            SORT_BY_NAME_ID,
        )
        selected_order_id = SORT_DESCENDING_ID if self.sort_descending else SORT_ASCENDING_ID
        user32.CheckRadioButton(self.hwnd, SORT_BY_NAME_ID, SORT_BY_MTIME_ID, selected_sort_id)
        user32.CheckRadioButton(self.hwnd, SORT_ASCENDING_ID, SORT_DESCENDING_ID, selected_order_id)
        selected_sort_button = self.sort_buttons.get(selected_sort_id)
        if selected_sort_button:
            user32.SendMessageW(selected_sort_button, BM_SETCHECK, BST_CHECKED, 0)
        selected_order_button = self.order_buttons.get(selected_order_id)
        if selected_order_button:
            user32.SendMessageW(selected_order_button, BM_SETCHECK, BST_CHECKED, 0)

    def _check_display_mode_buttons(self) -> None:
        if not self.hwnd:
            return

        selected_id = next(
            (control_id for control_id, (mode, _) in DISPLAY_MODE_OPTIONS.items() if mode == self.display_mode),
            DISPLAY_ORIGINAL_ID,
        )
        user32.CheckRadioButton(self.hwnd, DISPLAY_SCALE_50_ID, DISPLAY_FIT_HEIGHT_ID, selected_id)
        selected_button = self.display_buttons.get(selected_id)
        if selected_button:
            user32.SendMessageW(selected_button, BM_SETCHECK, BST_CHECKED, 0)

    def _check_resize_buttons(self) -> None:
        if not self.hwnd:
            return

        selected_size_id = next(
            (control_id for control_id, size in RESIZE_UI_SIZE_OPTIONS.items() if size == self.resize_size),
            RESIZE_SIZE_800_ID,
        )
        selected_basis_id = next(
            (control_id for control_id, (basis, _) in RESIZE_BASIS_OPTIONS.items() if basis == self.resize_basis),
            RESIZE_BASIS_WIDTH_ID,
        )
        user32.CheckRadioButton(self.hwnd, RESIZE_SIZE_800_ID, RESIZE_SIZE_1920_ID, selected_size_id)
        user32.CheckRadioButton(self.hwnd, RESIZE_BASIS_WIDTH_ID, RESIZE_BASIS_HEIGHT_ID, selected_basis_id)
        selected_size_button = self.resize_size_buttons.get(selected_size_id)
        if selected_size_button:
            user32.SendMessageW(selected_size_button, BM_SETCHECK, BST_CHECKED, 0)
        selected_basis_button = self.resize_basis_buttons.get(selected_basis_id)
        if selected_basis_button:
            user32.SendMessageW(selected_basis_button, BM_SETCHECK, BST_CHECKED, 0)

    def _check_cache_limit_buttons(self) -> None:
        if not self.hwnd:
            return

        selected_id = next(
            (
                control_id
                for control_id, limit_bytes in CACHE_SIZE_LIMIT_OPTIONS.items()
                if limit_bytes == self.cache_size_limit_bytes
            ),
            CACHE_LIMIT_1GB_ID,
        )
        user32.CheckRadioButton(self.hwnd, CACHE_LIMIT_512MB_ID, CACHE_LIMIT_2GB_ID, selected_id)
        selected_button = self.cache_limit_buttons.get(selected_id)
        if selected_button:
            user32.SendMessageW(selected_button, BM_SETCHECK, BST_CHECKED, 0)

    def _change_cache_size_limit(self, limit_bytes: int) -> None:
        self.cache_size_limit_bytes = limit_bytes
        self._check_cache_limit_buttons()
        try:
            save_cache_size_limit_bytes(limit_bytes)
        except OSError:
            self._set_window_text(self.status_bar, "キャッシュ上限を保存できませんでした")
            return
        result = self._enforce_cache_limit()
        suffix = "" if result is None or result.deleted_files == 0 else f"、{result.deleted_files}件整理"
        self._set_window_text(self.status_bar, f"キャッシュ上限を保存しました: {_format_cache_size(limit_bytes)}{suffix}")
        self._refresh_cache_status()

    def _handle_cache_cleanup(self) -> bool:
        try:
            result = cleanup_cache(self.cache_size_limit_bytes)
        except Exception as error:
            self._set_window_text(self.status_bar, f"キャッシュ整理に失敗しました: {error}")
            return False
        self._set_cache_cleanup_status("キャッシュを整理しました", result)
        self._refresh_cache_status()
        return True

    def _handle_cache_clear(self) -> bool:
        selected_path = self._selected_image_file.path if self._selected_image_file is not None else None
        try:
            result = clear_cache()
        except Exception as error:
            self._set_window_text(self.status_bar, f"キャッシュ全削除に失敗しました: {error}")
            return False

        self._set_cache_cleanup_status("キャッシュを全削除しました", result)
        self._refresh_cache_status()
        if self.current_folder is not None and path_is_dir(self.current_folder):
            self.load_folder(self.current_folder, select_path=selected_path)
            self._set_cache_cleanup_status("キャッシュを全削除しました", result)
        return True

    def _set_cache_cleanup_status(self, message: str, result: CacheCleanupResult) -> None:
        if result.deleted_files == 0:
            detail = "整理対象はありません"
        else:
            detail = f"{result.deleted_files}件 / {_format_cache_size(result.deleted_bytes)}削除"
        if result.failed_files:
            detail = f"{detail}（{result.failed_files}件は使用中のため残しました）"
        self._set_window_text(self.status_bar, f"{message}: {detail}")

    def _enforce_cache_limit(self) -> CacheCleanupResult | None:
        try:
            stats = cache_stats()
            if stats.total_bytes <= self.cache_size_limit_bytes:
                return None
            return cleanup_cache(self.cache_size_limit_bytes)
        except Exception:
            return None

    def _refresh_cache_status(self, enforce_limit: bool = False) -> None:
        if enforce_limit:
            self._enforce_cache_limit()
        try:
            stats = cache_stats()
        except Exception:
            self._set_window_text(self.cache_status_label, "キャッシュ: 確認できません")
            return
        self._set_window_text(self.cache_status_label, self._cache_status_text(stats.total_bytes))

    def _cache_status_text(self, total_bytes: int) -> str:
        return f"キャッシュ: {_format_cache_size(total_bytes)} / 上限 {_format_cache_size(self.cache_size_limit_bytes)}"

    def _change_resize_size(self, resize_size: int) -> None:
        self.resize_size = resize_size
        self._check_resize_buttons()
        self._set_window_text(self.status_bar, f"リサイズサイズ: {resize_size}px")

    def _change_resize_basis(self, resize_basis: str) -> None:
        self.resize_basis = resize_basis
        self._check_resize_buttons()
        label = "幅" if resize_basis == RESIZE_BASIS_WIDTH else "高さ"
        self._set_window_text(self.status_bar, f"リサイズ基準: {label}")

    def _handle_select_resize_output_folder(self) -> bool:
        try:
            folder = self._choose_folder("リサイズ保存先を選択", self._resize_output_initial_folder())
        except Exception as error:
            traceback.print_exc(file=sys.stderr)
            self._set_window_text(self.status_bar, f"リサイズ保存先を選択できませんでした: {error}")
            return False

        if folder is None:
            return False
        folder = display_path(folder)
        if not path_is_dir(folder):
            self._set_window_text(self.status_bar, f"リサイズ保存先が見つかりません: {folder}")
            return False

        self.resize_output_folder = folder
        self._save_resize_output_folder()
        self._refresh_resize_output_label()
        self._set_folder_status("リサイズ保存先を設定しました", folder)
        return True

    def _resize_output_initial_folder(self) -> Path | None:
        if self.resize_output_folder is not None and path_is_dir(self.resize_output_folder):
            return self.resize_output_folder
        if self._selected_image_file is not None and path_is_dir(self._selected_image_file.path.parent):
            return self._selected_image_file.path.parent
        if self.current_folder is not None and path_is_dir(self.current_folder):
            return self.current_folder
        return None

    def _effective_resize_output_folder(self) -> Path | None:
        if self.resize_output_folder is None:
            return None
        folder = display_path(self.resize_output_folder)
        if path_is_dir(folder):
            return folder
        self.resize_output_folder = None
        self._refresh_resize_output_label()
        self._set_window_text(self.status_bar, "前回のリサイズ保存先が見つからないため元画像フォルダへ保存します")
        return None

    def _refresh_resize_output_label(self) -> None:
        self._set_window_text(self.resize_output_label, self._resize_output_display_text())

    def _resize_output_display_text(self) -> str:
        if self.resize_output_folder is None:
            return "保存先: 元画像と同じ"
        return f"保存先: {self._folder_display_text(self.resize_output_folder)}"

    def _save_resize_output_folder(self) -> None:
        if self.resize_output_folder is None:
            return
        try:
            save_resize_output_folder(self.resize_output_folder)
        except OSError:
            traceback.print_exc(file=sys.stderr)
            self._set_window_text(self.status_bar, "リサイズ保存先を保存できませんでした")

    def _save_preview_width(self) -> None:
        if self.preview_width is None:
            return
        try:
            save_preview_width(self.preview_width)
        except OSError:
            traceback.print_exc(file=sys.stderr)
            self._set_window_text(self.status_bar, "プレビュー幅を保存できませんでした")

    def _handle_resize_save(self) -> bool:
        if self._selected_image_file is None:
            self._set_window_text(self.status_bar, "リサイズ保存する画像が選択されていません")
            return False

        output_folder = self._effective_resize_output_folder()
        try:
            result = resize_image_file(self._selected_image_file, self.resize_size, self.resize_basis, output_folder)
        except (OSError, ValueError) as error:
            traceback.print_exc(file=sys.stderr)
            self._set_window_text(self.status_bar, f"リサイズ保存できませんでした: {error}")
            return False

        if output_folder is None or (self.current_folder is not None and _same_path(result.output_path.parent, self.current_folder)):
            self._add_saved_image_to_current_list(result.output_path)
        self._set_window_text(
            self.status_bar,
            f"リサイズ保存しました: {result.output_path} ({result.width}x{result.height})",
        )
        return True

    def _add_saved_image_to_current_list(self, saved_path: Path) -> ImageFile | None:
        try:
            saved_image = image_file_from_path(saved_path)
        except OSError as error:
            traceback.print_exc(file=sys.stderr)
            self._set_window_text(self.status_bar, f"保存画像を一覧へ追加できませんでした: {error}")
            return None

        image_files = [image_file for image_file in self.thumbnail_grid.items if not _same_path(image_file.path, saved_image.path)]
        image_files.append(saved_image)
        image_files = self._sorted_image_files(image_files)

        self._load_id += 1
        self._cancel_preview_requests()
        load_id = self._load_id
        self._drain_thumbnail_queue(ignore_all=True)
        self._drain_preview_queue(ignore_all=True)
        self.thumbnail_grid.set_items(image_files)
        self._thumbnail_done = 0
        self._thumbnail_total = len(image_files)

        selected_index = self._index_for_path(image_files, saved_image.path)
        if selected_index is not None:
            self.thumbnail_grid.select_index(selected_index)
        else:
            self._selected_image_file = saved_image
            self._start_preview_worker(saved_image)

        self._start_thumbnail_worker(load_id, image_files, self.thumbnail_size)
        return saved_image

    def _change_display_mode(self, display_mode: str) -> None:
        if display_mode == self.display_mode:
            return
        self.display_mode = display_mode
        self._sync_pan_mode()
        self._check_display_mode_buttons()
        if self._selected_image_file is not None:
            self._start_preview_worker(self._selected_image_file)
            if self.fullscreen_preview.visible:
                self._start_fullscreen_worker(self._selected_image_file)
        self._set_window_text(self.status_bar, f"表示: {self._display_mode_label()}")

    def _display_mode_label(self) -> str:
        for mode, label in DISPLAY_MODE_OPTIONS.values():
            if mode == self.display_mode:
                return label
        return "100%"

    def _zoom_in(self) -> None:
        self._change_display_mode(self._stepped_display_mode(1))

    def _zoom_out(self) -> None:
        self._change_display_mode(self._stepped_display_mode(-1))

    def _stepped_display_mode(self, direction: int) -> str:
        if self.display_mode not in ZOOM_DISPLAY_MODES:
            return PREVIEW_MODE_ORIGINAL if direction > 0 else PREVIEW_MODE_SCALE_50
        index = ZOOM_DISPLAY_MODES.index(self.display_mode)
        next_index = max(0, min(len(ZOOM_DISPLAY_MODES) - 1, index + direction))
        return ZOOM_DISPLAY_MODES[next_index]

    def _change_sort_field(self, sort_field: str) -> None:
        if sort_field == self.sort_field:
            return
        self.sort_field = sort_field
        self._check_sort_buttons()
        self._apply_sort_to_current_items()

    def _change_sort_order(self, sort_descending: bool) -> None:
        if sort_descending == self.sort_descending:
            return
        self.sort_descending = sort_descending
        self._check_sort_buttons()
        self._apply_sort_to_current_items()

    def _apply_sort_to_current_items(self) -> None:
        image_files = self._sorted_image_files(list(self.thumbnail_grid.items))
        selected_path = self._selected_image_file.path if self._selected_image_file is not None else None

        self._load_id += 1
        self._cancel_preview_requests()
        load_id = self._load_id
        self._drain_thumbnail_queue(ignore_all=True)
        self._drain_preview_queue(ignore_all=True)
        self.thumbnail_grid.set_items(image_files)
        self._thumbnail_done = 0
        self._thumbnail_total = len(image_files)

        if not image_files:
            self._selected_image_file = None
            self.image_preview.clear()
            self._set_window_text(self.status_bar, "画像が見つかりません" if self.current_folder else "フォルダを選択してください")
            return

        selected_index = self._index_for_path(image_files, selected_path)
        if selected_index is not None:
            self.thumbnail_grid.select_index(selected_index)
        else:
            self._selected_image_file = None
            self.image_preview.clear()
            self._refresh_status_details("")

        self._refresh_status_details("サムネイル読み込み中")
        self._set_window_text(
            self.status_bar,
            f"{len(image_files)}件の画像を並び替えました。サムネイルを更新中...",
        )
        self._start_thumbnail_worker(load_id, image_files, self.thumbnail_size)

    def _sorted_image_files(self, image_files: list[ImageFile]) -> list[ImageFile]:
        name_sorted = sorted(image_files, key=lambda image_file: _natural_text_key(image_file.name))
        if self.sort_field == "mtime":
            return sorted(name_sorted, key=lambda image_file: image_file.mtime, reverse=self.sort_descending)
        if self.sort_descending:
            return list(reversed(name_sorted))
        return name_sorted

    def _index_for_path(self, image_files: list[ImageFile], selected_path: Path | None) -> int | None:
        if selected_path is None:
            return None
        for index, image_file in enumerate(image_files):
            if _same_path(image_file.path, selected_path):
                return index
        return None

    def _start_thumbnail_worker(self, load_id: int, image_files: list[ImageFile], thumbnail_size: int) -> None:
        self._set_thumbnail_priority_range(*self.thumbnail_grid.visible_index_range(extra_rows=PREFETCH_EXTRA_ROWS))

        def worker() -> None:
            pending_indexes = set(range(len(image_files)))
            generated_count = 0
            while pending_indexes:
                if load_id != self._load_id:
                    return
                index = self._next_thumbnail_index(pending_indexes)
                pending_indexes.remove(index)
                image_file = image_files[index]
                result = ensure_thumbnail(index, image_file, thumbnail_size=thumbnail_size)
                if load_id != self._load_id:
                    return
                self._thumbnail_queue.put((load_id, result))
                hwnd = self.hwnd
                if hwnd:
                    user32.PostMessageW(hwnd, WM_THUMBNAIL_READY, 0, 0)
                generated_count += 1
                if generated_count % THUMBNAIL_WORKER_YIELD_INTERVAL == 0:
                    while load_id == self._load_id and self._thumbnail_queue.qsize() > THUMBNAIL_QUEUE_BACKLOG_LIMIT:
                        time.sleep(0.01)
                    time.sleep(0.001)

        thread = threading.Thread(target=worker, name="thumbnail-worker", daemon=True)
        thread.start()

    def _set_thumbnail_priority_range(self, start: int, end: int) -> None:
        with self._thumbnail_priority_lock:
            self._thumbnail_priority_range = (max(0, start), max(0, end))

    def _next_thumbnail_index(self, pending_indexes: set[int]) -> int:
        with self._thumbnail_priority_lock:
            start, end = self._thumbnail_priority_range

        if end <= start:
            return min(pending_indexes)

        center = (start + end - 1) / 2

        def priority(index: int) -> tuple[int, float, int]:
            if start <= index < end:
                return (0, abs(index - center), index)
            if index < start:
                return (1, start - index, index)
            return (1, index - end + 1, index)

        return min(pending_indexes, key=priority)

    def _drain_thumbnail_queue(self, ignore_all: bool = False) -> None:
        cache_changed = False
        processed_count = 0
        while True:
            if not ignore_all and processed_count >= THUMBNAIL_DRAIN_BATCH_SIZE:
                break
            try:
                load_id, result = self._thumbnail_queue.get_nowait()
            except queue.Empty:
                break

            if ignore_all or load_id != self._load_id:
                continue

            self._thumbnail_done += 1
            self.thumbnail_grid.set_thumbnail(result.index, result.cache_path, failed=not result.ok)
            cache_changed = cache_changed or result.ok
            processed_count += 1

        if self._thumbnail_total and not ignore_all:
            if self._thumbnail_done >= self._thumbnail_total:
                self._refresh_status_details("完了")
                self._set_folder_status(
                    f"{self._thumbnail_total}件の画像が見つかりました。サムネイルサイズ {self.thumbnail_size}px",
                    self.current_folder,
                )
            else:
                self._refresh_status_details(f"読込中 {self._thumbnail_done}/{self._thumbnail_total}")
                self._set_folder_status(
                    f"{self._thumbnail_total}件の画像が見つかりました。サムネイル {self._thumbnail_done}/{self._thumbnail_total} ({self.thumbnail_size}px)",
                    self.current_folder,
                )
        if cache_changed and not ignore_all:
            self._refresh_cache_status(enforce_limit=True)
        if not ignore_all and not self._thumbnail_queue.empty() and self.hwnd:
            user32.PostMessageW(self.hwnd, WM_THUMBNAIL_READY, 0, 0)

    def _select_image(self, index: int, image_file: ImageFile) -> None:
        self._selected_image_file = image_file
        self._sync_pan_mode()
        self._start_preview_worker(image_file)
        if self.fullscreen_preview.visible:
            self._start_fullscreen_worker(image_file)
        self._refresh_status_details("プレビュー読み込み中")
        self._set_window_text(self.status_bar, f"選択中: {image_file.name}")

    def _open_fullscreen(self, *_args: object) -> None:
        if self._selected_image_file is None:
            return
        self._start_fullscreen_worker(self._selected_image_file)

    def _close_fullscreen(self) -> None:
        self._cancel_fullscreen_requests()
        self.fullscreen_preview.hide()
        if self.thumbnail_grid.hwnd:
            user32.SetFocus(self.thumbnail_grid.hwnd)

    def _fullscreen_select_relative(self, delta: int) -> None:
        if self.thumbnail_grid.select_relative(delta):
            return
        if self._selected_image_file is not None and self.fullscreen_preview.visible:
            self._start_fullscreen_worker(self._selected_image_file)

    def _handle_mouse_wheel(self, w_param: int) -> None:
        if _ctrl_pressed():
            delta = _signed_hiword(int(w_param))
            if delta > 0:
                self._zoom_in()
            elif delta < 0:
                self._zoom_out()
            return
        self._select_from_wheel(w_param)

    def _select_from_wheel(self, w_param: int) -> None:
        delta = _signed_hiword(int(w_param))
        if delta > 0:
            self.thumbnail_grid.select_relative(-1)
        elif delta < 0:
            self.thumbnail_grid.select_relative(1)

    def _start_preview_worker(self, image_file: ImageFile, show_loading: bool = True) -> None:
        max_width, max_height = self.image_preview.preview_size()
        display_mode = self.display_mode
        self.image_preview.set_pan_enabled(_pan_enabled_for_display_mode(display_mode))
        with self._preview_condition:
            self._preview_id += 1
            preview_id = self._preview_id
            self._preview_request = (preview_id, image_file, max_width, max_height, display_mode)
            if not self._preview_worker_started:
                self._preview_worker_started = True
                thread = threading.Thread(target=self._preview_worker_loop, name="preview-worker", daemon=True)
                thread.start()
            self._preview_condition.notify()

        self._drain_preview_queue(ignore_all=True)
        if show_loading:
            self.image_preview.set_loading(image_file)
            self._refresh_status_details("プレビュー読み込み中")

    def _start_fullscreen_worker(self, image_file: ImageFile) -> None:
        self.fullscreen_preview.show_loading(
            image_file,
            self._fullscreen_position_text(image_file),
            self._fullscreen_zoom_text(),
        )
        max_width, max_height = self.fullscreen_preview.preview_size()
        display_mode = self.display_mode
        self.fullscreen_preview.set_pan_enabled(_pan_enabled_for_display_mode(display_mode))
        with self._fullscreen_lock:
            self._fullscreen_id += 1
            fullscreen_id = self._fullscreen_id

        def worker() -> None:
            result = render_preview(image_file, max_width, max_height, display_mode=display_mode)
            if not self._is_current_fullscreen(fullscreen_id, image_file):
                return
            self._fullscreen_queue.put((fullscreen_id, image_file, result))
            hwnd = self.hwnd
            if hwnd:
                user32.PostMessageW(hwnd, WM_FULLSCREEN_READY, 0, 0)

        thread = threading.Thread(target=worker, name="fullscreen-preview-worker", daemon=True)
        thread.start()

    def _fullscreen_position_text(self, image_file: ImageFile) -> str:
        total = len(self.thumbnail_grid.items)
        if total <= 0:
            return ""
        for index, item in enumerate(self.thumbnail_grid.items):
            if item.path == image_file.path:
                return f"{index + 1} / {total}"
        return f"- / {total}"

    def _fullscreen_zoom_text(self) -> str:
        return self._display_mode_label()

    def _sync_pan_mode(self) -> None:
        pan_enabled = _pan_enabled_for_display_mode(self.display_mode)
        self.image_preview.set_pan_enabled(pan_enabled)
        self.fullscreen_preview.set_pan_enabled(pan_enabled)

    def _preview_worker_loop(self) -> None:
        while True:
            with self._preview_condition:
                while self._preview_request is None:
                    self._preview_condition.wait()
                preview_id, image_file, max_width, max_height, display_mode = self._preview_request
                self._preview_request = None
                self._preview_condition.wait(timeout=PREVIEW_START_DELAY_SECONDS)
                if self._preview_request is not None:
                    continue

            if not self._is_current_preview(preview_id, image_file):
                continue

            result = render_preview(image_file, max_width, max_height, display_mode=display_mode)
            if not self._is_current_preview(preview_id, image_file):
                continue

            self._preview_queue.put((preview_id, image_file, result))
            hwnd = self.hwnd
            if hwnd:
                user32.PostMessageW(hwnd, WM_PREVIEW_READY, 0, 0)

    def _cancel_preview_requests(self) -> None:
        with self._preview_condition:
            self._preview_id += 1
            self._preview_request = None
            self._preview_condition.notify()

    def _cancel_fullscreen_requests(self) -> None:
        with self._fullscreen_lock:
            self._fullscreen_id += 1

    def _drain_preview_queue(self, ignore_all: bool = False) -> None:
        cache_changed = False
        while True:
            try:
                preview_id, image_file, result = self._preview_queue.get_nowait()
            except queue.Empty:
                break

            if ignore_all or not self._is_current_preview(preview_id, image_file):
                continue

            self.image_preview.set_result(image_file, result)
            cache_changed = cache_changed or result.ok
            self._refresh_status_details("完了" if result.ok else "プレビュー不可")
            if not result.ok:
                self._set_window_text(self.status_bar, f"プレビューできません: {image_file.name}")
        if cache_changed and not ignore_all:
            self._refresh_cache_status(enforce_limit=True)

    def _drain_fullscreen_queue(self, ignore_all: bool = False) -> None:
        cache_changed = False
        while True:
            try:
                fullscreen_id, image_file, result = self._fullscreen_queue.get_nowait()
            except queue.Empty:
                break

            if ignore_all or not self._is_current_fullscreen(fullscreen_id, image_file):
                continue

            self.fullscreen_preview.set_result(image_file, result)
            cache_changed = cache_changed or result.ok
            if not result.ok:
                self._set_window_text(self.status_bar, f"プレビューできません: {image_file.name}")
        if cache_changed and not ignore_all:
            self._refresh_cache_status(enforce_limit=True)

    def _is_current_preview(self, preview_id: int, image_file: ImageFile | None = None) -> bool:
        with self._preview_lock:
            is_current = preview_id == self._preview_id
        if image_file is None:
            return is_current
        return is_current and image_file == self._selected_image_file

    def _is_current_fullscreen(self, fullscreen_id: int, image_file: ImageFile | None = None) -> bool:
        with self._fullscreen_lock:
            is_current = fullscreen_id == self._fullscreen_id
        if image_file is None:
            return is_current and self.fullscreen_preview.visible
        return is_current and self.fullscreen_preview.visible and image_file == self._selected_image_file

    def _refresh_status_details(self, loading_text: str | None = None) -> None:
        if loading_text is not None:
            self._status_loading_text = loading_text
        total = len(self.thumbnail_grid.items)
        image_count_text = f"画像: {total}件" if self.current_folder is not None else "画像: -"
        image_file = self._selected_image_file
        if image_file is None:
            name_text = ""
            dimensions_text = ""
            file_size_text = ""
        else:
            name_text = f"選択: {_compact_middle_text(image_file.name, STATUS_FILENAME_DISPLAY_LIMIT)}"
            dimensions_text = f"サイズ: {self._image_dimensions_text(image_file)}"
            file_size_text = f"容量: {_format_cache_size(image_file.size)}"
        self._set_window_text(self.status_count_label, image_count_text)
        self._set_window_text(self.status_name_label, name_text)
        self._set_window_text(self.status_dimensions_label, dimensions_text)
        self._set_window_text(self.status_file_size_label, file_size_text)
        self._set_window_text(self.status_loading_label, self._status_loading_text)

    def _image_dimensions_text(self, image_file: ImageFile) -> str:
        dimensions = self._image_dimensions(image_file)
        if dimensions is None:
            return "不明"
        width, height = dimensions
        return f"{width}×{height}"

    def _image_dimensions(self, image_file: ImageFile) -> tuple[int, int] | None:
        key = display_path(image_file.path)
        if key in self._image_dimension_cache:
            return self._image_dimension_cache[key]
        try:
            with Image.open(filesystem_path(key)) as image:
                dimensions = (int(image.width), int(image.height))
        except (OSError, UnidentifiedImageError, ValueError):
            dimensions = None
        self._image_dimension_cache[key] = dimensions
        return dimensions

    def _message_loop(self) -> None:
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _set_window_text(self, hwnd: int | None, text: str) -> None:
        if hwnd:
            user32.SetWindowTextW(hwnd, text)

    def _set_folder_status(self, message: str, folder: Path | None) -> None:
        self._set_window_text(self.status_bar, self._folder_status_text(message, folder))

    def _folder_status_text(self, message: str, folder: Path | None) -> str:
        if folder is None:
            return message
        return f"{message}: {display_path(folder)}"

    def _set_folder_label(self, folder: Path | None) -> None:
        folder_text = "\u30d5\u30a9\u30eb\u30c0\u672a\u9078\u629e" if folder is None else self._folder_display_text(folder)
        path_text = "\u30d5\u30a9\u30eb\u30c0\u672a\u9078\u629e" if folder is None else str(display_path(folder))
        self._set_window_text(self.folder_label, folder_text)
        self._set_window_text(self.current_path_label, path_text)

    def _folder_display_text(self, folder: Path) -> str:
        return _compact_middle_text(str(folder), FOLDER_PATH_DISPLAY_LIMIT)

    def _folder_error_message(self, folder: Path, error: Exception) -> str:
        if isinstance(error, FileNotFoundError):
            return f"フォルダが存在しません: {folder}"
        if isinstance(error, NotADirectoryError):
            return f"フォルダではありません: {folder}"
        if isinstance(error, PermissionError):
            return f"フォルダへアクセスできません: {folder}"
        return f"フォルダを開けません: {folder}"

    def _require_window(self) -> None:
        if not self.hwnd:
            raise RuntimeError("Window has not been created.")

    def _require_controls(self) -> None:
        self._require_window()
        if not all([
            self.folder_label,
            self.current_path_label,
            self.current_path_open_button,
            self.status_count_label,
            self.status_name_label,
            self.status_dimensions_label,
            self.status_file_size_label,
            self.status_loading_label,
            self.status_bar,
            self.thumbnail_grid.hwnd,
            self.image_preview.hwnd,
        ]):
            raise RuntimeError("Window controls have not been created.")


def _natural_text_key(value: str) -> tuple[tuple[int, object], ...]:
    parts: list[tuple[int, object]] = []
    current = ""
    for char in value.casefold():
        if char.isdigit() == (current[:1].isdigit() if current else char.isdigit()):
            current += char
            continue
        parts.append(_text_part_key(current))
        current = char
    if current:
        parts.append(_text_part_key(current))
    return tuple(parts)


def _text_part_key(value: str) -> tuple[int, object]:
    if value.isdigit():
        return (0, int(value))
    return (1, value)


def _compact_middle_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return "." * max(0, max_chars)

    head_chars = max(8, max_chars // 3)
    tail_chars = max_chars - head_chars - 3
    if tail_chars <= 0:
        return text[: max_chars - 3] + "..."
    return f"{text[:head_chars]}...{text[-tail_chars:]}"


def _folder_list_display_label(folder: Path, folders: list[Path], max_chars: int) -> str:
    folder = display_path(folder)
    name = _folder_display_name(folder)
    same_name_folders = [
        display_path(existing)
        for existing in folders
        if _folder_display_name(display_path(existing)).casefold() == name.casefold()
    ]
    if len(same_name_folders) <= 1:
        return _compact_middle_text(name, max_chars)

    parent_name = _folder_parent_display_name(folder)
    label = f"{name}（{parent_name}）" if parent_name else name
    same_label_count = sum(
        1
        for existing in same_name_folders
        if _folder_parent_display_name(existing).casefold() == parent_name.casefold()
    )
    if same_label_count > 1:
        parent_text_limit = max(12, max_chars - len(name) - 2)
        label = f"{name}（{_compact_middle_text(str(folder.parent), parent_text_limit)}）"
    return _compact_middle_text(label, max_chars)


def _folder_display_name(folder: Path) -> str:
    folder = display_path(folder)
    return folder.name or folder.drive or folder.anchor or str(folder)


def _folder_parent_display_name(folder: Path) -> str:
    parent = display_path(folder).parent
    return parent.name or parent.drive or parent.anchor or str(parent)


def _format_cache_size(size_bytes: int) -> str:
    size = max(0, int(size_bytes))
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)}B"
            if value.is_integer():
                return f"{int(value)}{unit}"
            if value >= 100:
                return f"{value:.0f}{unit}"
            if value >= 10:
                return f"{value:.1f}{unit}"
            return f"{value:.2f}{unit}"
        value /= 1024


def _same_path(left: str | Path, right: str | Path) -> bool:
    left_text = str(display_path(left))
    right_text = str(display_path(right))
    return left_text == right_text or left_text.casefold() == right_text.casefold()


def _shell_execute_failed(result: object) -> bool:
    try:
        return int(result or 0) <= 32
    except (TypeError, ValueError):
        return True


def _combo_add_string(hwnd: int, text: str) -> None:
    text_buffer = ctypes.create_unicode_buffer(text)
    text_pointer = ctypes.cast(text_buffer, ctypes.c_void_p).value or 0
    user32.SendMessageW(hwnd, CB_ADDSTRING, 0, text_pointer)


def _signed_hiword(value: int) -> int:
    word = (value >> 16) & 0xFFFF
    if word >= 0x8000:
        word -= 0x10000
    return word


def _signed_loword(value: int) -> int:
    word = value & 0xFFFF
    if word >= 0x8000:
        word -= 0x10000
    return word


def _shift_pressed() -> bool:
    return bool(user32.GetKeyState(VK_SHIFT) & 0x8000)


def _ctrl_pressed() -> bool:
    return bool(user32.GetKeyState(VK_CONTROL) & 0x8000)


def _alt_pressed() -> bool:
    return bool(user32.GetKeyState(VK_MENU) & 0x8000)


def _pan_enabled_for_display_mode(display_mode: str) -> bool:
    return display_mode in PAN_DISPLAY_MODES


def _get_shell_path_from_id_list(pidl: object, path_buffer: ctypes.Array[ctypes.c_wchar]) -> bool:
    buffer_pointer = ctypes.cast(path_buffer, wintypes.LPWSTR)
    get_path_ex = getattr(shell32, "SHGetPathFromIDListEx", None)
    if get_path_ex is not None:
        return bool(get_path_ex(pidl, buffer_pointer, len(path_buffer), 0))
    return bool(shell32.SHGetPathFromIDListW(pidl, buffer_pointer))


def _browse_folder_callback(hwnd: int, message: int, _l_param: int, data: int) -> int:
    if message == BFFM_INITIALIZED and data:
        user32.SendMessageW(hwnd, BFFM_SETSELECTIONW, 1, data)
    return 0


def _dropped_paths(drop_handle: int) -> list[Path]:
    count = int(shell32.DragQueryFileW(drop_handle, DRAG_QUERY_FILE_COUNT, None, 0))
    paths: list[Path] = []
    for index in range(count):
        length = int(shell32.DragQueryFileW(drop_handle, index, None, 0))
        if length <= 0:
            continue
        path_buffer = ctypes.create_unicode_buffer(length + 1)
        copied = int(shell32.DragQueryFileW(drop_handle, index, path_buffer, length + 1))
        if copied > 0 and path_buffer.value:
            paths.append(display_path(path_buffer.value))
    return paths


def _register_window_class() -> None:
    global _class_registered, _window_proc_ref
    if _class_registered:
        return

    hinstance = kernel32.GetModuleHandleW(None)
    _window_proc_ref = WNDPROC(_window_proc)
    wndclass = WNDCLASSW(
        style=0,
        lpfnWndProc=_window_proc_ref,
        cbClsExtra=0,
        cbWndExtra=0,
        hInstance=hinstance,
        hIcon=None,
        hCursor=user32.LoadCursorW(None, ctypes.cast(ctypes.c_void_p(IDC_ARROW), wintypes.LPCWSTR)),
        hbrBackground=wintypes.HBRUSH(6),
        lpszMenuName=None,
        lpszClassName=CLASS_NAME,
    )

    atom = user32.RegisterClassW(ctypes.byref(wndclass))
    if not atom:
        raise ctypes.WinError()
    _class_registered = True


def _window_proc(hwnd: int, message: int, w_param: int, l_param: int) -> int:
    window = _window_instances.get(int(hwnd))
    if window is not None:
        result = window.handle_message(hwnd, message, w_param, l_param)
        if result is not None:
            return result

    return user32.DefWindowProcW(hwnd, message, w_param, l_param)


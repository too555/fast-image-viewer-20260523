from __future__ import annotations

import ctypes
import queue
import sys
import threading
import traceback
from ctypes import wintypes
from pathlib import Path

from app.core.image_scanner import ImageFile, scan_image_files
from app.core.preview_renderer import PreviewResult, render_preview
from app.core.thumbnail_cache import THUMBNAIL_SIZE, ThumbnailResult, ensure_thumbnail
from app.ui.fullscreen_preview import FullscreenPreview
from app.ui.image_preview import ImagePreview
from app.ui.thumbnail_grid import ThumbnailGrid


if not hasattr(ctypes, "windll"):
    raise RuntimeError("このUIは現在Windowsのみ対応しています。")


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
shell32 = ctypes.windll.shell32
ole32 = ctypes.windll.ole32
kernel32 = ctypes.windll.kernel32

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

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
user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND
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

ole32.CoInitialize.argtypes = [ctypes.c_void_p]
ole32.CoInitialize.restype = ctypes.c_long
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
ole32.CoUninitialize.argtypes = []


WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_COMMAND = 0x0111
WM_KEYDOWN = 0x0100
WM_APP = 0x8000
WM_SETFONT = 0x0030
WM_THUMBNAIL_READY = WM_APP + 1
WM_PREVIEW_READY = WM_APP + 2
WM_FULLSCREEN_READY = WM_APP + 3
PREVIEW_START_DELAY_SECONDS = 0.08

BN_CLICKED = 0
BS_AUTORADIOBUTTON = 0x00000009
BST_CHECKED = 1
BM_SETCHECK = 0x00F1
BIF_RETURNONLYFSDIRS = 0x0001
BIF_NEWDIALOGSTYLE = 0x0040

WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_GROUP = 0x00020000

CW_USEDEFAULT = -2147483648
SW_SHOW = 5
DEFAULT_GUI_FONT = 17
IDC_ARROW = 32512
MAX_PATH = 260
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_RETURN = 0x0D
VK_HOME = 0x24
VK_END = 0x23
VK_PRIOR = 0x21
VK_NEXT = 0x22

SELECT_FOLDER_ID = 1001
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
CLASS_NAME = "FastImageViewerStep12Window"


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
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
        self.open_button: int | None = None
        self.thumbnail_size_buttons: dict[int, int] = {}
        self.sort_label: int | None = None
        self.sort_buttons: dict[int, int] = {}
        self.order_label: int | None = None
        self.order_buttons: dict[int, int] = {}
        self.folder_label: int | None = None
        self.status_bar: int | None = None
        self.thumbnail_grid = ThumbnailGrid()
        self.thumbnail_size = THUMBNAIL_SIZE
        self.sort_field = "name"
        self.sort_descending = False
        self.image_preview = ImagePreview()
        self.fullscreen_preview = FullscreenPreview()
        self.current_folder: Path | None = None
        self._selected_image_file: ImageFile | None = None
        self._load_id = 0
        self._preview_id = 0
        self._fullscreen_id = 0
        self._preview_lock = threading.Lock()
        self._fullscreen_lock = threading.Lock()
        self._preview_condition = threading.Condition(self._preview_lock)
        self._preview_request: tuple[int, ImageFile, int, int] | None = None
        self._preview_worker_started = False
        self._thumbnail_total = 0
        self._thumbnail_done = 0
        self._thumbnail_priority_lock = threading.Lock()
        self._thumbnail_priority_range: tuple[int, int] = (0, 0)
        self._thumbnail_queue: queue.Queue[tuple[int, ThumbnailResult]] = queue.Queue()
        self._preview_queue: queue.Queue[tuple[int, ImageFile, PreviewResult]] = queue.Queue()
        self._fullscreen_queue: queue.Queue[tuple[int, ImageFile, PreviewResult]] = queue.Queue()

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
        self._create_controls()
        self._layout()

    def destroy(self) -> None:
        self._load_id += 1
        self._cancel_preview_requests()
        self._close_fullscreen()
        self.thumbnail_grid.destroy()
        self.image_preview.destroy()
        self.fullscreen_preview.destroy()
        if self.hwnd:
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None

    def load_folder(self, folder: Path) -> None:
        self._require_controls()
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
        self._set_window_text(self.folder_label, str(folder))
        self._set_window_text(self.status_bar, "フォルダを読み込み中...")

        try:
            image_files = self._sorted_image_files(scan_image_files(folder))
        except (FileNotFoundError, NotADirectoryError, PermissionError) as error:
            self.current_folder = None
            self._set_window_text(self.folder_label, "フォルダ未選択")
            self._set_window_text(self.status_bar, "フォルダを読み込めません")
            user32.MessageBoxW(self.hwnd, self._folder_error_message(folder, error), "フォルダを開けません", 0x10)
            return

        self.thumbnail_grid.set_items(image_files)
        self._thumbnail_total = len(image_files)
        if self.thumbnail_grid.hwnd:
            user32.SetFocus(self.thumbnail_grid.hwnd)

        if not image_files:
            self._set_window_text(self.status_bar, "画像が見つかりません")
            return

        self._set_window_text(
            self.status_bar,
            f"{len(image_files)}件の画像が見つかりました。周辺サムネイルを先読み中...",
        )
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

        if message == WM_KEYDOWN:
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

        if message == WM_COMMAND:
            control_id = int(w_param) & 0xFFFF
            notification = (int(w_param) >> 16) & 0xFFFF
            if control_id == SELECT_FOLDER_ID and notification == BN_CLICKED:
                self._handle_select_folder()
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

        if message == WM_DESTROY:
            self._load_id += 1
            self._cancel_preview_requests()
            self._close_fullscreen()
            self.thumbnail_grid.destroy()
            self.image_preview.destroy()
            self.fullscreen_preview.destroy()
            _window_instances.pop(int(hwnd), None)
            user32.PostQuitMessage(0)
            return 0

        return None

    def _create_controls(self) -> None:
        self._require_window()
        self.open_button = self._create_child(
            "BUTTON",
            "フォルダ選択",
            WS_CHILD | WS_VISIBLE,
            SELECT_FOLDER_ID,
        )
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
        self._check_sort_buttons()
        self.folder_label = self._create_child("STATIC", "フォルダ未選択", WS_CHILD | WS_VISIBLE, 0)
        self.thumbnail_grid.create(self.hwnd)
        self.thumbnail_grid.on_selection_changed = self._select_image
        self.thumbnail_grid.on_item_activated = self._open_fullscreen
        self.thumbnail_grid.on_visible_range_changed = self._set_thumbnail_priority_range
        self.image_preview.create(self.hwnd)
        self.image_preview.on_activated = self._open_fullscreen
        self.fullscreen_preview.create(self.hwnd)
        self.fullscreen_preview.on_close = self._close_fullscreen
        self.fullscreen_preview.on_previous = lambda: self._fullscreen_select_relative(-1)
        self.fullscreen_preview.on_next = lambda: self._fullscreen_select_relative(1)
        self.status_bar = self._create_child("STATIC", "フォルダを選択してください", WS_CHILD | WS_VISIBLE, 0)

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

    def _choose_folder(self) -> Path | None:
        display_name = ctypes.create_unicode_buffer(MAX_PATH)
        browse_info = BROWSEINFOW(
            hwndOwner=self.hwnd,
            pidlRoot=None,
            pszDisplayName=ctypes.cast(display_name, wintypes.LPWSTR),
            lpszTitle="画像フォルダを選択",
            ulFlags=BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE,
            lpfn=None,
            lParam=0,
            iImage=0,
        )

        pidl = None
        co_result = int(ole32.CoInitialize(None))
        co_initialized = co_result >= 0
        try:
            pidl = shell32.SHBrowseForFolderW(ctypes.byref(browse_info))
            if not pidl:
                return None

            path_buffer = ctypes.create_unicode_buffer(MAX_PATH)
            if not shell32.SHGetPathFromIDListW(pidl, ctypes.cast(path_buffer, wintypes.LPWSTR)):
                raise OSError("選択したフォルダのパスを取得できませんでした")
            if not path_buffer.value:
                return None
            return Path(path_buffer.value)
        finally:
            if pidl:
                ole32.CoTaskMemFree(pidl)
            if co_initialized:
                ole32.CoUninitialize()

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

    def _layout(self) -> None:
        if not self.hwnd or not self.open_button:
            return

        rect = RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        width = max(0, rect.right - rect.left)
        height = max(0, rect.bottom - rect.top)

        margin = 12
        button_width = 120
        size_button_width = 58
        size_button_gap = 6
        sort_label_width = 64
        sort_button_width = 82
        order_label_width = 44
        order_button_width = 58
        top_height = 58
        status_height = 28
        content_top = margin + top_height + 10
        content_height = max(120, height - content_top - status_height - margin)
        preview_width = max(280, min(520, int(width * 0.42)))
        gap = 10
        grid_width = max(160, width - margin * 2 - preview_width - gap)
        if width < 720:
            preview_height = max(160, int(content_height * 0.46))
            grid_height = max(120, content_height - preview_height - gap)
            grid_width = max(120, width - margin * 2)
            preview_x = margin
            preview_y = content_top + grid_height + gap
            preview_width = max(120, width - margin * 2)
        else:
            grid_height = content_height
            preview_x = margin + grid_width + gap
            preview_y = content_top
            preview_height = content_height

        row1_y = margin
        row2_y = margin + 33
        user32.MoveWindow(self.open_button, margin, row1_y, button_width, 28, True)
        user32.MoveWindow(
            self.folder_label,
            margin + button_width + 12,
            row1_y + 5,
            max(100, width - margin * 2 - button_width - 12),
            22,
            True,
        )

        size_x = margin
        for control_id in THUMBNAIL_SIZE_OPTIONS:
            user32.MoveWindow(
                self.thumbnail_size_buttons[control_id],
                size_x,
                row2_y,
                size_button_width,
                22,
                True,
            )
            size_x += size_button_width + size_button_gap
        sort_x = size_x + 14
        user32.MoveWindow(self.sort_label, sort_x, row2_y + 3, sort_label_width, 18, True)
        sort_x += sort_label_width
        for control_id in SORT_FIELD_OPTIONS:
            user32.MoveWindow(self.sort_buttons[control_id], sort_x, row2_y, sort_button_width, 22, True)
            sort_x += sort_button_width + size_button_gap
        sort_x += 8
        user32.MoveWindow(self.order_label, sort_x, row2_y + 3, order_label_width, 18, True)
        sort_x += order_label_width
        for control_id in SORT_ORDER_OPTIONS:
            user32.MoveWindow(self.order_buttons[control_id], sort_x, row2_y, order_button_width, 22, True)
            sort_x += order_button_width + size_button_gap
        self.thumbnail_grid.move(margin, content_top, grid_width, grid_height)
        self.image_preview.move(preview_x, preview_y, preview_width, preview_height)
        user32.MoveWindow(
            self.status_bar,
            margin,
            max(content_top + content_height + 6, height - status_height),
            max(120, width - margin * 2),
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
            self._set_window_text(self.status_bar, "画像が見つかりません" if self.current_folder else "フォルダを選択してください")
            return

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
            if image_file.path == selected_path:
                return index
        return None

    def _start_thumbnail_worker(self, load_id: int, image_files: list[ImageFile], thumbnail_size: int) -> None:
        self._set_thumbnail_priority_range(*self.thumbnail_grid.visible_index_range(extra_rows=2))

        def worker() -> None:
            pending_indexes = set(range(len(image_files)))
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
        while True:
            try:
                load_id, result = self._thumbnail_queue.get_nowait()
            except queue.Empty:
                break

            if ignore_all or load_id != self._load_id:
                continue

            self._thumbnail_done += 1
            self.thumbnail_grid.set_thumbnail(result.index, result.cache_path, failed=not result.ok)

        if self._thumbnail_total and not ignore_all:
            if self._thumbnail_done >= self._thumbnail_total:
                self._set_window_text(
                    self.status_bar,
                    f"{self._thumbnail_total}件の画像が見つかりました。サムネイルサイズ {self.thumbnail_size}px",
                )
            else:
                self._set_window_text(
                    self.status_bar,
                    f"{self._thumbnail_total}件の画像が見つかりました。サムネイル {self._thumbnail_done}/{self._thumbnail_total} ({self.thumbnail_size}px)",
                )

    def _select_image(self, index: int, image_file: ImageFile) -> None:
        self._selected_image_file = image_file
        self._start_preview_worker(image_file)
        if self.fullscreen_preview.visible:
            self._start_fullscreen_worker(image_file)
        self._set_window_text(self.status_bar, f"選択中: {image_file.name}")

    def _open_fullscreen(self, *_args: object) -> None:
        if self._selected_image_file is None:
            return
        self.fullscreen_preview.show_loading(self._selected_image_file)
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

    def _start_preview_worker(self, image_file: ImageFile, show_loading: bool = True) -> None:
        max_width, max_height = self.image_preview.preview_size()
        with self._preview_condition:
            self._preview_id += 1
            preview_id = self._preview_id
            self._preview_request = (preview_id, image_file, max_width, max_height)
            if not self._preview_worker_started:
                self._preview_worker_started = True
                thread = threading.Thread(target=self._preview_worker_loop, name="preview-worker", daemon=True)
                thread.start()
            self._preview_condition.notify()

        self._drain_preview_queue(ignore_all=True)
        if show_loading:
            self.image_preview.set_loading(image_file)

    def _start_fullscreen_worker(self, image_file: ImageFile) -> None:
        if not self.fullscreen_preview.visible:
            return

        max_width, max_height = self.fullscreen_preview.preview_size()
        with self._fullscreen_lock:
            self._fullscreen_id += 1
            fullscreen_id = self._fullscreen_id

        self.fullscreen_preview.show_loading(image_file)

        def worker() -> None:
            result = render_preview(image_file, max_width, max_height)
            if not self._is_current_fullscreen(fullscreen_id, image_file):
                return
            self._fullscreen_queue.put((fullscreen_id, image_file, result))
            hwnd = self.hwnd
            if hwnd:
                user32.PostMessageW(hwnd, WM_FULLSCREEN_READY, 0, 0)

        thread = threading.Thread(target=worker, name="fullscreen-preview-worker", daemon=True)
        thread.start()

    def _preview_worker_loop(self) -> None:
        while True:
            with self._preview_condition:
                while self._preview_request is None:
                    self._preview_condition.wait()
                preview_id, image_file, max_width, max_height = self._preview_request
                self._preview_request = None
                self._preview_condition.wait(timeout=PREVIEW_START_DELAY_SECONDS)
                if self._preview_request is not None:
                    continue

            if not self._is_current_preview(preview_id, image_file):
                continue

            result = render_preview(image_file, max_width, max_height)
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
        while True:
            try:
                preview_id, image_file, result = self._preview_queue.get_nowait()
            except queue.Empty:
                break

            if ignore_all or not self._is_current_preview(preview_id, image_file):
                continue

            self.image_preview.set_result(image_file, result)
            if not result.ok:
                self._set_window_text(self.status_bar, f"プレビューできません: {image_file.name}")

    def _drain_fullscreen_queue(self, ignore_all: bool = False) -> None:
        while True:
            try:
                fullscreen_id, image_file, result = self._fullscreen_queue.get_nowait()
            except queue.Empty:
                break

            if ignore_all or not self._is_current_fullscreen(fullscreen_id, image_file):
                continue

            self.fullscreen_preview.set_result(image_file, result)
            if not result.ok:
                self._set_window_text(self.status_bar, f"プレビューできません: {image_file.name}")

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

    def _message_loop(self) -> None:
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _set_window_text(self, hwnd: int | None, text: str) -> None:
        if hwnd:
            user32.SetWindowTextW(hwnd, text)

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
        if not all([self.folder_label, self.status_bar, self.thumbnail_grid.hwnd, self.image_preview.hwnd]):
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

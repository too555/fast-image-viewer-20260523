from __future__ import annotations

import ctypes
import sys
import traceback
from collections.abc import Callable
from ctypes import wintypes

from app.core.recent_folders import DEFAULT_THUMBNAIL_SIZE, THUMBNAIL_SIZE_OPTIONS, save_thumbnail_size
from app.core.viewer_options import (
    OPTION_STATUS_LINES,
    OPTION_TABS,
    build_display_viewer_options,
    default_viewer_options,
    load_viewer_options,
    save_viewer_options,
)


if not hasattr(ctypes, "windll"):
    raise RuntimeError("このUIは現在Windowsのみ対応しています。")


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32
comctl32 = ctypes.windll.comctl32

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
comctl32.InitCommonControlsEx.argtypes = [ctypes.c_void_p]
comctl32.InitCommonControlsEx.restype = wintypes.BOOL

user32.CallWindowProcW.argtypes = [
    ctypes.c_void_p,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CallWindowProcW.restype = ctypes.c_ssize_t
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
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
user32.LoadCursorW.restype = wintypes.HANDLE
user32.MoveWindow.argtypes = [
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.BOOL,
]
user32.RegisterClassW.argtypes = [ctypes.c_void_p]
user32.RegisterClassW.restype = wintypes.ATOM
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UpdateWindow.argtypes = [wintypes.HWND]

try:
    _set_window_long_ptr = user32.SetWindowLongPtrW
except AttributeError:
    _set_window_long_ptr = user32.SetWindowLongW
_set_window_long_ptr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
_set_window_long_ptr.restype = ctypes.c_void_p

gdi32.GetStockObject.argtypes = [ctypes.c_int]
gdi32.GetStockObject.restype = ctypes.c_void_p


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


class INITCOMMONCONTROLSEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("dwICC", wintypes.DWORD),
    ]


class TCITEMW(ctypes.Structure):
    _fields_ = [
        ("mask", wintypes.UINT),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("pszText", wintypes.LPWSTR),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("lParam", wintypes.LPARAM),
    ]


class NMHDR(ctypes.Structure):
    _fields_ = [
        ("hwndFrom", wintypes.HWND),
        ("idFrom", ctypes.c_size_t),
        ("code", wintypes.UINT),
    ]


WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_COMMAND = 0x0111
WM_NOTIFY = 0x004E
WM_KEYDOWN = 0x0100
WM_SETFONT = 0x0030
BN_CLICKED = 0
VK_ESCAPE = 0x1B

WS_OVERLAPPED = 0x00000000
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_VSCROLL = 0x00200000
WS_BORDER = 0x00800000
WS_TABSTOP = 0x00010000
BS_AUTOCHECKBOX = 0x00000003

ES_MULTILINE = 0x0004
ES_AUTOVSCROLL = 0x0040
ES_READONLY = 0x0800
EM_SETSEL = 0x00B1
BM_GETCHECK = 0x00F0
BM_SETCHECK = 0x00F1
BST_CHECKED = 1

CBS_DROPDOWNLIST = 0x0003
CBS_HASSTRINGS = 0x0200
CB_ADDSTRING = 0x0143
CB_SETCURSEL = 0x014E
CB_GETCURSEL = 0x0147
CB_ERR = -1

TCM_FIRST = 0x1300
TCM_GETCURSEL = TCM_FIRST + 11
TCM_SETCURSEL = TCM_FIRST + 12
TCM_INSERTITEMW = TCM_FIRST + 62
TCN_FIRST = -550
TCN_SELCHANGE = TCN_FIRST - 1
TCIF_TEXT = 0x0001
ICC_TAB_CLASSES = 0x00000008

GWLP_WNDPROC = -4
DEFAULT_GUI_FONT = 17
IDC_ARROW = 32512
SW_HIDE = 0
SW_SHOW = 5

CLASS_NAME = "FastImageViewerOptionsDialog"
TAB_CONTROL_ID = 4101
TEXT_CONTROL_ID = 4102
THUMBNAIL_LABEL_ID = 4103
THUMBNAIL_COMBO_ID = 4104
SAVE_BUTTON_ID = 4105
CLOSE_BUTTON_ID = 4106
DEFAULT_BUTTON_ID = 4111
SHOW_STATUS_BAR_ID = 4107
SHOW_PATH_BAR_ID = 4108
SHOW_FOLDER_TREE_ID = 4109
SHOW_PREVIEW_ID = 4110
THUMBNAIL_SIZE_VALUES = sorted(THUMBNAIL_SIZE_OPTIONS)
DISPLAY_CHECKBOXES = (
    ("show_status_bar", SHOW_STATUS_BAR_ID, "ステータスバーを表示"),
    ("show_path_bar", SHOW_PATH_BAR_ID, "パスを表示"),
    ("show_folder_tree", SHOW_FOLDER_TREE_ID, "フォルダツリーを表示"),
    ("show_preview", SHOW_PREVIEW_ID, "プレビューを表示"),
)

_dialog_proc_ref: WNDPROC | None = None
_class_registered = False
_instances: dict[int, "OptionsDialog"] = {}


class OptionsDialog:
    def __init__(self) -> None:
        self.hwnd: int | None = None
        self.tab_hwnd: int | None = None
        self.text_hwnd: int | None = None
        self.thumbnail_label: int | None = None
        self.thumbnail_combo: int | None = None
        self.display_checkboxes: dict[str, int] = {}
        self.save_button: int | None = None
        self.close_button: int | None = None
        self.default_button: int | None = None
        self._tab_text_buffers: list[ctypes.Array[ctypes.c_wchar]] = []
        self.selected_tab_index = 0
        self.thumbnail_size = 128
        self.viewer_options = load_viewer_options()
        self._thumbnail_size_callback: Callable[[int], None] | None = None
        self._options_callback: Callable[[dict[str, dict[str, object]]], None] | None = None
        self._child_proc_ref: WNDPROC | None = None
        self._child_old_procs: dict[int, int] = {}

    def show(
        self,
        owner: int | None,
        thumbnail_size: int,
        viewer_options: dict[str, dict[str, object]] | None = None,
        on_thumbnail_size_changed: Callable[[int], None] | None = None,
        on_options_changed: Callable[[dict[str, dict[str, object]]], None] | None = None,
    ) -> None:
        self.thumbnail_size = thumbnail_size if thumbnail_size in THUMBNAIL_SIZE_VALUES else 128
        self.viewer_options = viewer_options or load_viewer_options()
        self._thumbnail_size_callback = on_thumbnail_size_changed
        self._options_callback = on_options_changed
        if self.hwnd:
            self._select_tab(self.selected_tab_index)
            user32.SetForegroundWindow(self.hwnd)
            return

        _register_dialog_class()
        _init_tab_controls()
        hinstance = kernel32.GetModuleHandleW(None)
        hwnd = user32.CreateWindowExW(
            0,
            CLASS_NAME,
            "設定",
            WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_MINIMIZEBOX | WS_VISIBLE,
            140,
            140,
            680,
            500,
            owner,
            None,
            hinstance,
            None,
        )
        if not hwnd:
            raise ctypes.WinError()

        self.hwnd = int(hwnd)
        _instances[self.hwnd] = self
        self._create_controls()
        self._layout()
        self._select_tab(self.selected_tab_index)
        user32.ShowWindow(self.hwnd, SW_SHOW)
        user32.UpdateWindow(self.hwnd)

    def destroy(self) -> None:
        self._restore_child_procs()
        if self.hwnd:
            hwnd = self.hwnd
            self.hwnd = None
            user32.DestroyWindow(hwnd)

    def handle_message(self, hwnd: int, message: int, w_param: int, l_param: int) -> int | None:
        if message == WM_SIZE:
            self._layout()
            return 0

        if message == WM_KEYDOWN and int(w_param) == VK_ESCAPE:
            self.destroy()
            return 0

        if message == WM_NOTIFY and self._tab_selection_changed(l_param):
            self._select_tab(self._current_tab_index())
            return 0

        if message == WM_COMMAND:
            control_id = int(w_param) & 0xFFFF
            notification = (int(w_param) >> 16) & 0xFFFF
            if control_id == SAVE_BUTTON_ID and notification == BN_CLICKED:
                self._save()
                return 0
            if control_id == CLOSE_BUTTON_ID and notification == BN_CLICKED:
                self.destroy()
                return 0
            if control_id == DEFAULT_BUTTON_ID and notification == BN_CLICKED:
                self._restore_defaults()
                return 0

        if message == WM_CLOSE:
            self.destroy()
            return 0

        if message == WM_DESTROY:
            self._restore_child_procs()
            _instances.pop(int(hwnd), None)
            if self.hwnd == int(hwnd):
                self.hwnd = None
            self.tab_hwnd = None
            self.text_hwnd = None
            self.thumbnail_label = None
            self.thumbnail_combo = None
            self.display_checkboxes.clear()
            self._tab_text_buffers.clear()
            self.save_button = None
            self.close_button = None
            self.default_button = None
            return 0

        return None

    def _create_controls(self) -> None:
        if not self.hwnd:
            return
        hinstance = kernel32.GetModuleHandleW(None)
        font = gdi32.GetStockObject(DEFAULT_GUI_FONT)

        self.tab_hwnd = int(
            user32.CreateWindowExW(
                0,
                "SysTabControl32",
                "",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(TAB_CONTROL_ID),
                hinstance,
                None,
            )
        )
        if not self.tab_hwnd:
            raise ctypes.WinError()
        user32.SendMessageW(self.tab_hwnd, WM_SETFONT, font, True)
        self._insert_tabs()

        self.thumbnail_label = int(
            user32.CreateWindowExW(
                0,
                "STATIC",
                "サムネイルサイズ:",
                WS_CHILD | WS_VISIBLE,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(THUMBNAIL_LABEL_ID),
                hinstance,
                None,
            )
        )
        self.thumbnail_combo = int(
            user32.CreateWindowExW(
                0,
                "COMBOBOX",
                "",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP | CBS_DROPDOWNLIST | CBS_HASSTRINGS,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(THUMBNAIL_COMBO_ID),
                hinstance,
                None,
            )
        )
        if not self.thumbnail_label or not self.thumbnail_combo:
            raise ctypes.WinError()
        user32.SendMessageW(self.thumbnail_label, WM_SETFONT, font, True)
        user32.SendMessageW(self.thumbnail_combo, WM_SETFONT, font, True)
        for size in THUMBNAIL_SIZE_VALUES:
            _combo_add_string(self.thumbnail_combo, f"{size}px")

        for key, control_id, label in DISPLAY_CHECKBOXES:
            checkbox = int(
                user32.CreateWindowExW(
                    0,
                    "BUTTON",
                    label,
                    WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_AUTOCHECKBOX,
                    0,
                    0,
                    0,
                    0,
                    self.hwnd,
                    wintypes.HMENU(control_id),
                    hinstance,
                    None,
                )
            )
            if not checkbox:
                raise ctypes.WinError()
            user32.SendMessageW(checkbox, WM_SETFONT, font, True)
            self.display_checkboxes[key] = checkbox

        self.text_hwnd = int(
            user32.CreateWindowExW(
                0,
                "EDIT",
                "",
                WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_BORDER | WS_TABSTOP | ES_MULTILINE | ES_AUTOVSCROLL | ES_READONLY,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(TEXT_CONTROL_ID),
                hinstance,
                None,
            )
        )
        self.save_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "OK",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(SAVE_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.close_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "キャンセル",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(CLOSE_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.default_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "既定値",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(DEFAULT_BUTTON_ID),
                hinstance,
                None,
            )
        )
        if not self.text_hwnd or not self.save_button or not self.close_button or not self.default_button:
            raise ctypes.WinError()
        for child in (self.text_hwnd, self.save_button, self.close_button, self.default_button):
            user32.SendMessageW(child, WM_SETFONT, font, True)
            self._subclass_child(child)

    def _layout(self) -> None:
        if not all([
            self.hwnd,
            self.tab_hwnd,
            self.text_hwnd,
            self.thumbnail_label,
            self.thumbnail_combo,
            *self.display_checkboxes.values(),
            self.save_button,
            self.close_button,
            self.default_button,
        ]):
            return
        rect = RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        width = max(1, rect.right - rect.left)
        height = max(1, rect.bottom - rect.top)
        margin = 12
        tab_height = 30
        option_height = 58
        button_width = 96
        button_height = 30
        gap = 8
        user32.MoveWindow(self.tab_hwnd, margin, margin, max(1, width - margin * 2), tab_height, True)
        user32.MoveWindow(self.thumbnail_label, margin, margin + tab_height + gap + 4, 120, 18, True)
        user32.MoveWindow(self.thumbnail_combo, margin + 126, margin + tab_height + gap, 110, 180, True)
        checkbox_x = margin
        checkbox_y = margin + tab_height + gap + 28
        for key, _control_id, _label in DISPLAY_CHECKBOXES:
            user32.MoveWindow(self.display_checkboxes[key], checkbox_x, checkbox_y, 126, 20, True)
            checkbox_x += 132
        text_y = margin + tab_height + gap + option_height
        user32.MoveWindow(
            self.text_hwnd,
            margin,
            text_y,
            max(1, width - margin * 2),
            max(1, height - text_y - button_height - margin - gap),
            True,
        )
        button_y = max(margin, height - margin - button_height)
        button_x = max(margin, width - margin - button_width * 3 - gap * 2)
        for child in (self.save_button, self.close_button, self.default_button):
            user32.MoveWindow(child, button_x, button_y, button_width, button_height, True)
            button_x += button_width + gap

    def _insert_tabs(self) -> None:
        if not self.tab_hwnd:
            return
        self._tab_text_buffers.clear()
        for index, (_, title) in enumerate(OPTION_TABS):
            text_buffer = ctypes.create_unicode_buffer(title)
            self._tab_text_buffers.append(text_buffer)
            item = TCITEMW()
            item.mask = TCIF_TEXT
            item.pszText = ctypes.cast(text_buffer, wintypes.LPWSTR)
            item.cchTextMax = len(title)
            item_ptr = ctypes.cast(ctypes.byref(item), ctypes.c_void_p).value or 0
            user32.SendMessageW(self.tab_hwnd, TCM_INSERTITEMW, index, item_ptr)

    def _select_tab(self, index: int) -> None:
        if not self.tab_hwnd:
            return
        self.selected_tab_index = max(0, min(len(OPTION_TABS) - 1, index))
        user32.SendMessageW(self.tab_hwnd, TCM_SETCURSEL, self.selected_tab_index, 0)
        key, title = OPTION_TABS[self.selected_tab_index]
        self._set_text(_tab_text(key, title, self.thumbnail_size))
        show_thumbnail_controls = key == "thumbnail"
        show_display_controls = key in {"browser", "display"}
        for child in (self.thumbnail_label, self.thumbnail_combo):
            if child:
                user32.ShowWindow(child, SW_SHOW if show_thumbnail_controls else SW_HIDE)
        for child in self.display_checkboxes.values():
            user32.ShowWindow(child, SW_SHOW if show_display_controls else SW_HIDE)
        self._sync_thumbnail_combo()
        self._sync_display_checkboxes()

    def _current_tab_index(self) -> int:
        if not self.tab_hwnd:
            return self.selected_tab_index
        selected = int(user32.SendMessageW(self.tab_hwnd, TCM_GETCURSEL, 0, 0))
        return self.selected_tab_index if selected < 0 else selected

    def _tab_selection_changed(self, l_param: int) -> bool:
        if not l_param or not self.tab_hwnd:
            return False
        hdr = ctypes.cast(l_param, ctypes.POINTER(NMHDR)).contents
        code = ctypes.c_int32(hdr.code).value
        return int(hdr.hwndFrom or 0) == self.tab_hwnd and code == TCN_SELCHANGE

    def _save(self) -> None:
        selected_size = self._selected_thumbnail_size()
        options = self._pending_options(selected_size)
        try:
            save_thumbnail_size(selected_size)
            save_viewer_options(options)
        except OSError:
            traceback.print_exc(file=sys.stderr)
            self._set_text("設定を保存できませんでした。\r\nPowerShellのエラー表示を確認してください。")
            return

        self.thumbnail_size = selected_size
        self.viewer_options = options
        if self._thumbnail_size_callback:
            self._thumbnail_size_callback(selected_size)
        if self._options_callback:
            self._options_callback(options)
        self.destroy()

    def _restore_defaults(self) -> None:
        self.thumbnail_size = DEFAULT_THUMBNAIL_SIZE
        self.viewer_options = default_viewer_options()
        self._select_tab(self.selected_tab_index)

    def _pending_options(self, selected_size: int) -> dict[str, dict[str, object]]:
        return build_display_viewer_options(
            self.viewer_options,
            thumbnail_size=selected_size,
            show_status_bar=self._checkbox_checked("show_status_bar"),
            show_path_bar=self._checkbox_checked("show_path_bar"),
            show_folder_tree=self._checkbox_checked("show_folder_tree"),
            show_preview=self._checkbox_checked("show_preview"),
        )

    def _selected_thumbnail_size(self) -> int:
        if not self.thumbnail_combo:
            return self.thumbnail_size
        selected = int(user32.SendMessageW(self.thumbnail_combo, CB_GETCURSEL, 0, 0))
        if selected == CB_ERR or selected < 0 or selected >= len(THUMBNAIL_SIZE_VALUES):
            return self.thumbnail_size
        return THUMBNAIL_SIZE_VALUES[selected]

    def _sync_thumbnail_combo(self) -> None:
        if not self.thumbnail_combo:
            return
        try:
            index = THUMBNAIL_SIZE_VALUES.index(self.thumbnail_size)
        except ValueError:
            index = THUMBNAIL_SIZE_VALUES.index(128)
        user32.SendMessageW(self.thumbnail_combo, CB_SETCURSEL, index, 0)

    def _sync_display_checkboxes(self) -> None:
        display_options = self.viewer_options.get("display", {})
        browser_options = self.viewer_options.get("browser", {})
        values = {
            "show_status_bar": bool(display_options.get("show_status_bar", True)),
            "show_path_bar": bool(display_options.get("show_path_bar", True)),
            "show_folder_tree": bool(display_options.get("show_folder_tree", True)),
            "show_preview": bool(browser_options.get("show_preview", True)),
        }
        for key, checked in values.items():
            hwnd = self.display_checkboxes.get(key)
            if hwnd:
                user32.SendMessageW(hwnd, BM_SETCHECK, BST_CHECKED if checked else 0, 0)

    def _checkbox_checked(self, key: str) -> bool:
        hwnd = self.display_checkboxes.get(key)
        if not hwnd:
            return True
        return int(user32.SendMessageW(hwnd, BM_GETCHECK, 0, 0)) == BST_CHECKED

    def _set_text(self, text: str) -> None:
        if not self.text_hwnd:
            return
        user32.SetWindowTextW(self.text_hwnd, text.replace("\n", "\r\n"))
        user32.SendMessageW(self.text_hwnd, EM_SETSEL, 0, 0)

    def _subclass_child(self, child_hwnd: int) -> None:
        if self._child_proc_ref is None:
            self._child_proc_ref = WNDPROC(self._child_proc)
        old_proc = _set_window_long_ptr(
            child_hwnd,
            GWLP_WNDPROC,
            ctypes.cast(self._child_proc_ref, ctypes.c_void_p),
        )
        if old_proc:
            self._child_old_procs[child_hwnd] = int(old_proc)

    def _restore_child_procs(self) -> None:
        for child_hwnd, old_proc in list(self._child_old_procs.items()):
            _set_window_long_ptr(child_hwnd, GWLP_WNDPROC, ctypes.c_void_p(old_proc))
        self._child_old_procs.clear()

    def _child_proc(self, hwnd: int, message: int, w_param: int, l_param: int) -> int:
        if message == WM_KEYDOWN and int(w_param) == VK_ESCAPE:
            self.destroy()
            return 0
        old_proc = self._child_old_procs.get(int(hwnd))
        if old_proc:
            return int(user32.CallWindowProcW(ctypes.c_void_p(old_proc), hwnd, message, w_param, l_param))
        return int(user32.DefWindowProcW(hwnd, message, w_param, l_param))


def _tab_text(key: str, title: str, thumbnail_size: int) -> str:
    lines = [
        f"{title}設定",
        "",
        "このページの項目:",
    ]
    for label, status in OPTION_STATUS_LINES.get(key, ()):
        suffix = f"（現在 {thumbnail_size}px）" if key == "thumbnail" and label == "サムネイルサイズ" else ""
        lines.append(f"・{label}：{status}{suffix}")
    lines.extend(
        [
            "",
            "反映済みの項目は保存後すぐに画面へ反映します。",
            "今後対応の項目は表示だけです。動作はまだ変更しません。",
        ]
    )
    return "\n".join(lines)


def _combo_add_string(hwnd: int, text: str) -> None:
    text_buffer = ctypes.create_unicode_buffer(text)
    text_pointer = ctypes.cast(text_buffer, ctypes.c_void_p).value or 0
    user32.SendMessageW(hwnd, CB_ADDSTRING, 0, text_pointer)


def _init_tab_controls() -> None:
    init = INITCOMMONCONTROLSEX(ctypes.sizeof(INITCOMMONCONTROLSEX), ICC_TAB_CLASSES)
    comctl32.InitCommonControlsEx(ctypes.byref(init))


def _register_dialog_class() -> None:
    global _class_registered, _dialog_proc_ref
    if _class_registered:
        return

    hinstance = kernel32.GetModuleHandleW(None)
    _dialog_proc_ref = WNDPROC(_dialog_proc)
    wndclass = WNDCLASSW(
        style=0,
        lpfnWndProc=_dialog_proc_ref,
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


def _dialog_proc(hwnd: int, message: int, w_param: int, l_param: int) -> int:
    dialog = _instances.get(int(hwnd))
    if dialog is not None:
        result = dialog.handle_message(hwnd, message, w_param, l_param)
        if result is not None:
            return result
    return int(user32.DefWindowProcW(hwnd, message, w_param, l_param))

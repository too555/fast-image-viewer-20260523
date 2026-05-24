from __future__ import annotations

import ctypes
import hashlib
import os
import sys
import traceback
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageChops, UnidentifiedImageError

from app.core.image_scanner import ImageFile
from app.core.preview_renderer import (
    PREVIEW_MODE_FIT_HEIGHT,
    PREVIEW_MODE_ORIGINAL,
    PREVIEW_MODE_SCALE_50,
    PREVIEW_MODE_SCALE_200,
    PreviewResult,
    default_preview_cache_dir,
    render_preview,
)
from app.ui.image_preview import ImagePreview
from app.utils.long_path import display_path, filesystem_path, make_dirs, path_exists


if not hasattr(ctypes, "windll"):
    raise RuntimeError("このUIは現在Windowsのみ対応しています。")


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
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
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
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
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
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
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p]
user32.SetTimer.restype = ctypes.c_size_t
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
user32.KillTimer.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UpdateWindow.argtypes = [wintypes.HWND]

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


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_COMMAND = 0x0111
WM_KEYDOWN = 0x0100
WM_TIMER = 0x0113
WM_SETFONT = 0x0030
BN_CLICKED = 0
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_LEFT = 0x25
VK_RIGHT = 0x27

WS_OVERLAPPED = 0x00000000
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_TABSTOP = 0x00010000
SS_CENTER = 0x00000001
SS_ENDELLIPSIS = 0x00004000

DEFAULT_GUI_FONT = 17
IDC_ARROW = 32512
SW_HIDE = 0
SW_SHOW = 5
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040
MF_STRING = 0x00000000
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100
COPY_MESSAGE_TIMER_ID = 4201
COPY_MESSAGE_DURATION_MS = 2200

CLASS_NAME = "FastImageViewerCompareView"
LEFT_LABEL_ID = 4101
RIGHT_LABEL_ID = 4102
INFO_LABEL_ID = 4103
CENTER_RESET_BUTTON_ID = 4104
LEFT_DETAIL_LABEL_ID = 4105
RIGHT_DETAIL_LABEL_ID = 4106
SYNC_TOGGLE_BUTTON_ID = 4107
SWAP_BUTTON_ID = 4108
LEFT_COPY_PATH_BUTTON_ID = 4109
RIGHT_COPY_PATH_BUTTON_ID = 4110
CONTEXT_COPY_IMAGE_INFO_ID = 4111
VIEW_MODE_BUTTON_ID = 4112
LAYOUT_MODE_BUTTON_ID = 4113
OVERLAY_RATIO_BUTTON_ID = 4114
GUIDE_MODE_BUTTON_ID = 4115
MASK_STYLE_BUTTON_ID = 4116
MASK_THRESHOLD_BUTTON_ID = 4117
DIFF_TOGGLE_BUTTON_ID = VIEW_MODE_BUTTON_ID
COMPARE_ZOOM_MODES = [PREVIEW_MODE_SCALE_50, PREVIEW_MODE_ORIGINAL, PREVIEW_MODE_SCALE_200]
COMPARE_PAN_MODES = {PREVIEW_MODE_SCALE_50, PREVIEW_MODE_ORIGINAL, PREVIEW_MODE_SCALE_200}
DIFF_HIGHLIGHT_THRESHOLD = 24
DIFF_HIGHLIGHT_BLEND = 0.55
OVERLAY_ALPHA_PERCENTS = [25, 50, 75]
MASK_STYLE_RED = "red"
MASK_STYLE_GREEN = "green"
MASK_STYLE_TRANSLUCENT = "translucent"
MASK_STYLES = [MASK_STYLE_RED, MASK_STYLE_GREEN, MASK_STYLE_TRANSLUCENT]
MASK_THRESHOLD_WEAK = "weak"
MASK_THRESHOLD_MEDIUM = "medium"
MASK_THRESHOLD_STRONG = "strong"
MASK_THRESHOLDS = [MASK_THRESHOLD_WEAK, MASK_THRESHOLD_MEDIUM, MASK_THRESHOLD_STRONG]
MASK_THRESHOLD_VALUES = {
    MASK_THRESHOLD_WEAK: 48,
    MASK_THRESHOLD_MEDIUM: 24,
    MASK_THRESHOLD_STRONG: 12,
}
ALTERNATE_TIMER_ID = 4202
ALTERNATE_INTERVAL_MS = 1000
COMPARE_VIEW_MODE_NORMAL = "normal"
COMPARE_VIEW_MODE_DIFF = "diff"
COMPARE_VIEW_MODE_ALTERNATE = "alternate"
COMPARE_VIEW_MODE_OVERLAY = "overlay"
COMPARE_VIEW_MODE_MASK = "mask"
COMPARE_VIEW_MODES = [
    COMPARE_VIEW_MODE_NORMAL,
    COMPARE_VIEW_MODE_DIFF,
    COMPARE_VIEW_MODE_ALTERNATE,
    COMPARE_VIEW_MODE_OVERLAY,
    COMPARE_VIEW_MODE_MASK,
]
COMPARE_LAYOUT_SIDE_BY_SIDE = "side_by_side"
COMPARE_LAYOUT_TOP_BOTTOM = "top_bottom"
COMPARE_LAYOUT_CENTER = "center"
COMPARE_LAYOUT_MODES = [COMPARE_LAYOUT_SIDE_BY_SIDE, COMPARE_LAYOUT_TOP_BOTTOM, COMPARE_LAYOUT_CENTER]
COMPARE_GUIDE_MODE_OFF = "off"
COMPARE_GUIDE_MODE_CENTER = "center"
COMPARE_GUIDE_MODE_GRID = "grid"
COMPARE_GUIDE_MODE_BOTH = "both"
COMPARE_GUIDE_MODES = [
    COMPARE_GUIDE_MODE_OFF,
    COMPARE_GUIDE_MODE_CENTER,
    COMPARE_GUIDE_MODE_GRID,
    COMPARE_GUIDE_MODE_BOTH,
]

_compare_proc_ref: WNDPROC | None = None
_class_registered = False
_instances: dict[int, "CompareView"] = {}


class CompareView:
    def __init__(self) -> None:
        self.hwnd: int | None = None
        self.left_label: int | None = None
        self.right_label: int | None = None
        self.left_detail_label: int | None = None
        self.right_detail_label: int | None = None
        self.info_label: int | None = None
        self.center_reset_button: int | None = None
        self.sync_toggle_button: int | None = None
        self.swap_button: int | None = None
        self.left_copy_path_button: int | None = None
        self.right_copy_path_button: int | None = None
        self.layout_mode_button: int | None = None
        self.view_mode_button: int | None = None
        self.overlay_ratio_button: int | None = None
        self.guide_mode_button: int | None = None
        self.mask_style_button: int | None = None
        self.mask_threshold_button: int | None = None
        self.diff_toggle_button: int | None = None
        self.left_preview = ImagePreview()
        self.right_preview = ImagePreview()
        self._left_image: ImageFile | None = None
        self._right_image: ImageFile | None = None
        self._display_mode = PREVIEW_MODE_ORIGINAL
        self._left_display_mode = PREVIEW_MODE_ORIGINAL
        self._right_display_mode = PREVIEW_MODE_ORIGINAL
        self._sync_enabled = True
        self._layout_mode = COMPARE_LAYOUT_SIDE_BY_SIDE
        self._center_side = "left"
        self._view_mode = COMPARE_VIEW_MODE_NORMAL
        self._overlay_alpha_percent = 50
        self._guide_mode = COMPARE_GUIDE_MODE_OFF
        self._mask_style = MASK_STYLE_RED
        self._mask_threshold = MASK_THRESHOLD_MEDIUM
        self._diff_enabled = False
        self._alternate_phase = False
        self._syncing_pan = False

    @property
    def visible(self) -> bool:
        return self.hwnd is not None

    def show(
        self,
        owner: int | None,
        left_image: ImageFile,
        right_image: ImageFile,
        display_mode: str = PREVIEW_MODE_ORIGINAL,
    ) -> None:
        if not self.hwnd:
            self._create(owner)

        self._left_image = left_image
        self._right_image = right_image
        self._display_mode = display_mode
        self._left_display_mode = display_mode
        self._right_display_mode = display_mode
        self._sync_enabled = True
        self._layout_mode = COMPARE_LAYOUT_SIDE_BY_SIDE
        self._center_side = "left"
        self._overlay_alpha_percent = 50
        self._mask_style = MASK_STYLE_RED
        self._mask_threshold = MASK_THRESHOLD_MEDIUM
        self._set_guide_mode(COMPARE_GUIDE_MODE_OFF, update_label=False)
        self._set_view_mode(COMPARE_VIEW_MODE_NORMAL, render=False)
        self._update_image_info_labels()
        self._update_sync_button_label()
        self._update_layout_mode_button_label()
        self._update_view_mode_button_label()
        self._update_overlay_ratio_button_label()
        self._update_guide_mode_button_label()
        self._update_mask_style_button_label()
        self._update_mask_threshold_button_label()
        self._layout()
        self._render_current_pair(reset_pan=True)

        if self.hwnd:
            user32.ShowWindow(self.hwnd, SW_SHOW)
            user32.SetForegroundWindow(self.hwnd)
            user32.SetFocus(self.hwnd)
            user32.UpdateWindow(self.hwnd)

    def destroy(self) -> None:
        if not self.hwnd:
            return
        hwnd = self.hwnd
        user32.KillTimer(hwnd, COPY_MESSAGE_TIMER_ID)
        user32.KillTimer(hwnd, ALTERNATE_TIMER_ID)
        _instances.pop(hwnd, None)
        self.hwnd = None
        self.left_preview.destroy()
        self.right_preview.destroy()
        self.left_label = None
        self.right_label = None
        self.left_detail_label = None
        self.right_detail_label = None
        self.info_label = None
        self.center_reset_button = None
        self.sync_toggle_button = None
        self.swap_button = None
        self.left_copy_path_button = None
        self.right_copy_path_button = None
        self.layout_mode_button = None
        self.view_mode_button = None
        self.overlay_ratio_button = None
        self.guide_mode_button = None
        self.diff_toggle_button = None
        self._left_image = None
        self._right_image = None
        user32.DestroyWindow(hwnd)

    def handle_message(self, hwnd: int, message: int, w_param: int, l_param: int) -> int | None:
        if message == WM_SIZE:
            self._layout()
            return 0

        if message == WM_KEYDOWN and int(w_param) == VK_ESCAPE:
            self.destroy()
            return 0

        if message == WM_KEYDOWN and self._handle_center_key(int(w_param)):
            return 0

        if message == WM_TIMER and int(w_param) == COPY_MESSAGE_TIMER_ID:
            if self.hwnd:
                user32.KillTimer(self.hwnd, COPY_MESSAGE_TIMER_ID)
            self._update_info_label()
            return 0

        if message == WM_TIMER and int(w_param) == ALTERNATE_TIMER_ID:
            self._advance_alternate_phase()
            return 0

        if message == WM_COMMAND:
            control_id = int(w_param) & 0xFFFF
            notification = (int(w_param) >> 16) & 0xFFFF
            if control_id == LEFT_COPY_PATH_BUTTON_ID and notification == BN_CLICKED:
                self._copy_left_image_path()
                return 0
            if control_id == RIGHT_COPY_PATH_BUTTON_ID and notification == BN_CLICKED:
                self._copy_right_image_path()
                return 0
            if control_id == CENTER_RESET_BUTTON_ID and notification == BN_CLICKED:
                self._reset_center()
                return 0
            if control_id == SYNC_TOGGLE_BUTTON_ID and notification == BN_CLICKED:
                self._toggle_sync_enabled()
                return 0
            if control_id == SWAP_BUTTON_ID and notification == BN_CLICKED:
                self._swap_sides()
                return 0
            if control_id == VIEW_MODE_BUTTON_ID and notification == BN_CLICKED:
                self._cycle_view_mode()
                return 0
            if control_id == OVERLAY_RATIO_BUTTON_ID and notification == BN_CLICKED:
                self._cycle_overlay_ratio()
                return 0
            if control_id == GUIDE_MODE_BUTTON_ID and notification == BN_CLICKED:
                self._cycle_guide_mode()
                return 0
            if control_id == MASK_STYLE_BUTTON_ID and notification == BN_CLICKED:
                self._cycle_mask_style()
                return 0
            if control_id == MASK_THRESHOLD_BUTTON_ID and notification == BN_CLICKED:
                self._cycle_mask_threshold()
                return 0
            if control_id == LAYOUT_MODE_BUTTON_ID and notification == BN_CLICKED:
                self._cycle_layout_mode()
                return 0

        if message == WM_CLOSE:
            self.destroy()
            return 0

        if message == WM_DESTROY:
            user32.KillTimer(hwnd, COPY_MESSAGE_TIMER_ID)
            user32.KillTimer(hwnd, ALTERNATE_TIMER_ID)
            _instances.pop(int(hwnd), None)
            if self.hwnd == int(hwnd):
                self.hwnd = None
            self.left_preview.destroy()
            self.right_preview.destroy()
            self.left_label = None
            self.right_label = None
            self.left_detail_label = None
            self.right_detail_label = None
            self.info_label = None
            self.center_reset_button = None
            self.sync_toggle_button = None
            self.swap_button = None
            self.left_copy_path_button = None
            self.right_copy_path_button = None
            self.layout_mode_button = None
            self.view_mode_button = None
            self.overlay_ratio_button = None
            self.guide_mode_button = None
            self.mask_style_button = None
            self.mask_threshold_button = None
            self.diff_toggle_button = None
            self._left_image = None
            self._right_image = None
            return 0

        return None

    def _create(self, owner: int | None) -> None:
        _register_compare_class()
        hinstance = kernel32.GetModuleHandleW(None)
        hwnd = user32.CreateWindowExW(
            0,
            CLASS_NAME,
            "2枚比較表示",
            WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_MINIMIZEBOX | WS_VISIBLE,
            120,
            120,
            1360,
            650,
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

    def _create_controls(self) -> None:
        if not self.hwnd:
            return
        hinstance = kernel32.GetModuleHandleW(None)
        font = gdi32.GetStockObject(DEFAULT_GUI_FONT)
        label_style = WS_CHILD | WS_VISIBLE | SS_CENTER | SS_ENDELLIPSIS
        self.left_label = int(
            user32.CreateWindowExW(0, "STATIC", "", label_style, 0, 0, 0, 0, self.hwnd, wintypes.HMENU(LEFT_LABEL_ID), hinstance, None)
        )
        self.right_label = int(
            user32.CreateWindowExW(0, "STATIC", "", label_style, 0, 0, 0, 0, self.hwnd, wintypes.HMENU(RIGHT_LABEL_ID), hinstance, None)
        )
        self.left_detail_label = int(
            user32.CreateWindowExW(0, "STATIC", "", WS_CHILD | WS_VISIBLE | SS_CENTER | SS_ENDELLIPSIS, 0, 0, 0, 0, self.hwnd, wintypes.HMENU(LEFT_DETAIL_LABEL_ID), hinstance, None)
        )
        self.right_detail_label = int(
            user32.CreateWindowExW(0, "STATIC", "", WS_CHILD | WS_VISIBLE | SS_CENTER | SS_ENDELLIPSIS, 0, 0, 0, 0, self.hwnd, wintypes.HMENU(RIGHT_DETAIL_LABEL_ID), hinstance, None)
        )
        self.info_label = int(
            user32.CreateWindowExW(0, "STATIC", "", WS_CHILD | WS_VISIBLE | SS_ENDELLIPSIS, 0, 0, 0, 0, self.hwnd, wintypes.HMENU(INFO_LABEL_ID), hinstance, None)
        )
        self.center_reset_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "中央リセット",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(CENTER_RESET_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.sync_toggle_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "同期ON",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(SYNC_TOGGLE_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.left_copy_path_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "左画像パスコピー",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(LEFT_COPY_PATH_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.right_copy_path_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "右画像パスコピー",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(RIGHT_COPY_PATH_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.swap_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "左右入替",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(SWAP_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.layout_mode_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "配置: 左右",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(LAYOUT_MODE_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.overlay_ratio_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "重ね: 50%",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(OVERLAY_RATIO_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.guide_mode_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "補助: OFF",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(GUIDE_MODE_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.view_mode_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "表示: 通常",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(VIEW_MODE_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.mask_style_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "色: 赤",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(MASK_STYLE_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.mask_threshold_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "感度: 中",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                0,
                0,
                0,
                0,
                self.hwnd,
                wintypes.HMENU(MASK_THRESHOLD_BUTTON_ID),
                hinstance,
                None,
            )
        )
        self.diff_toggle_button = self.view_mode_button
        if not all([
            self.left_label,
            self.right_label,
            self.left_detail_label,
            self.right_detail_label,
            self.info_label,
            self.center_reset_button,
            self.sync_toggle_button,
            self.swap_button,
            self.left_copy_path_button,
            self.right_copy_path_button,
            self.layout_mode_button,
            self.overlay_ratio_button,
            self.guide_mode_button,
            self.view_mode_button,
            self.mask_style_button,
            self.mask_threshold_button,
        ]):
            raise ctypes.WinError()
        user32.SendMessageW(self.left_label, WM_SETFONT, font, True)
        user32.SendMessageW(self.right_label, WM_SETFONT, font, True)
        user32.SendMessageW(self.left_detail_label, WM_SETFONT, font, True)
        user32.SendMessageW(self.right_detail_label, WM_SETFONT, font, True)
        user32.SendMessageW(self.info_label, WM_SETFONT, font, True)
        user32.SendMessageW(self.center_reset_button, WM_SETFONT, font, True)
        user32.SendMessageW(self.sync_toggle_button, WM_SETFONT, font, True)
        user32.SendMessageW(self.swap_button, WM_SETFONT, font, True)
        user32.SendMessageW(self.left_copy_path_button, WM_SETFONT, font, True)
        user32.SendMessageW(self.right_copy_path_button, WM_SETFONT, font, True)
        user32.SendMessageW(self.layout_mode_button, WM_SETFONT, font, True)
        user32.SendMessageW(self.overlay_ratio_button, WM_SETFONT, font, True)
        user32.SendMessageW(self.guide_mode_button, WM_SETFONT, font, True)
        user32.SendMessageW(self.view_mode_button, WM_SETFONT, font, True)
        user32.SendMessageW(self.mask_style_button, WM_SETFONT, font, True)
        user32.SendMessageW(self.mask_threshold_button, WM_SETFONT, font, True)
        self.left_preview.create(self.hwnd)
        self.right_preview.create(self.hwnd)
        self.left_preview.on_escape = self.destroy
        self.right_preview.on_escape = self.destroy
        self.left_preview.on_zoom_in = lambda: self._zoom_in("left")
        self.left_preview.on_zoom_out = lambda: self._zoom_out("left")
        self.right_preview.on_zoom_in = lambda: self._zoom_in("right")
        self.right_preview.on_zoom_out = lambda: self._zoom_out("right")
        self.left_preview.on_previous = lambda: self._handle_center_key(VK_LEFT)
        self.left_preview.on_next = lambda: self._handle_center_key(VK_RIGHT)
        self.left_preview.on_space = self._toggle_center_side
        self.right_preview.on_previous = lambda: self._handle_center_key(VK_LEFT)
        self.right_preview.on_next = lambda: self._handle_center_key(VK_RIGHT)
        self.right_preview.on_space = self._toggle_center_side
        self.left_preview.on_pan_changed = self._sync_pan_from
        self.right_preview.on_pan_changed = self._sync_pan_from
        self.left_preview.on_context_menu = lambda source_hwnd, x, y: self._handle_preview_context_menu("left", source_hwnd, x, y)
        self.right_preview.on_context_menu = lambda source_hwnd, x, y: self._handle_preview_context_menu("right", source_hwnd, x, y)

    def _layout(self) -> None:
        if not all([
            self.hwnd,
            self.left_label,
            self.right_label,
            self.left_detail_label,
            self.right_detail_label,
            self.info_label,
            self.center_reset_button,
            self.sync_toggle_button,
            self.swap_button,
            self.left_copy_path_button,
            self.right_copy_path_button,
            self.layout_mode_button,
            self.overlay_ratio_button,
            self.guide_mode_button,
            self.view_mode_button,
            self.mask_style_button,
            self.mask_threshold_button,
            self.left_preview.hwnd,
            self.right_preview.hwnd,
        ]):
            return
        rect = RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        width = max(1, rect.right - rect.left)
        height = max(1, rect.bottom - rect.top)
        margin = 14
        gap = 12
        label_height = 24
        detail_height = 22
        bottom_height = 28
        panel_width = max(1, (width - margin * 2 - gap) // 2)
        preview_height = max(1, height - margin * 2 - label_height - detail_height - bottom_height - 22)
        left_x = margin
        right_x = margin + panel_width + gap
        label_y = margin
        detail_y = label_y + label_height
        preview_y = detail_y + detail_height + 8
        bottom_y = max(margin, height - margin - bottom_height)
        reset_button_width = 100
        sync_button_width = 82
        swap_button_width = 84
        layout_button_width = 96
        overlay_ratio_button_width = 82
        guide_button_width = 84
        view_mode_button_width = 96
        mask_style_button_width = 68
        mask_threshold_button_width = 76
        copy_button_width = 118
        reset_x = max(margin, width - margin - reset_button_width)
        sync_x = max(margin, reset_x - gap - sync_button_width)
        guide_x = max(margin, sync_x - gap - guide_button_width)
        mask_threshold_x = max(margin, guide_x - gap - mask_threshold_button_width)
        mask_style_x = max(margin, mask_threshold_x - gap - mask_style_button_width)
        view_mode_x = max(margin, mask_style_x - gap - view_mode_button_width)
        overlay_ratio_x = max(margin, view_mode_x - gap - overlay_ratio_button_width)
        layout_x = max(margin, overlay_ratio_x - gap - layout_button_width)
        swap_x = max(margin, layout_x - gap - swap_button_width)
        right_copy_x = max(margin, swap_x - gap - copy_button_width)
        left_copy_x = max(margin, right_copy_x - gap - copy_button_width)
        info_width = max(1, left_copy_x - margin - gap)
        self._show_compare_controls(True)
        if self._layout_mode == COMPARE_LAYOUT_TOP_BOTTOM:
            full_width = max(1, width - margin * 2)
            content_height = max(1, height - margin * 2 - bottom_height - 22)
            panel_height = max(1, (content_height - gap) // 2)
            top_preview_height = max(1, panel_height - label_height - detail_height - 8)
            bottom_y_panel = margin + panel_height + gap
            bottom_preview_height = max(1, height - margin - bottom_height - 22 - (bottom_y_panel + label_height + detail_height + 8))
            user32.MoveWindow(self.left_label, margin, margin, full_width, label_height, True)
            user32.MoveWindow(self.left_detail_label, margin, margin + label_height, full_width, detail_height, True)
            self.left_preview.move(margin, margin + label_height + detail_height + 8, full_width, top_preview_height)
            user32.MoveWindow(self.right_label, margin, bottom_y_panel, full_width, label_height, True)
            user32.MoveWindow(self.right_detail_label, margin, bottom_y_panel + label_height, full_width, detail_height, True)
            self.right_preview.move(margin, bottom_y_panel + label_height + detail_height + 8, full_width, bottom_preview_height)
        elif self._layout_mode == COMPARE_LAYOUT_CENTER:
            full_width = max(1, width - margin * 2)
            center_preview_height = max(1, height - margin * 2 - label_height - detail_height - bottom_height - 22)
            user32.MoveWindow(self.left_label, margin, label_y, full_width, label_height, True)
            user32.MoveWindow(self.left_detail_label, margin, detail_y, full_width, detail_height, True)
            self.left_preview.move(margin, preview_y, full_width, center_preview_height)
            self._show_control(self.right_label, False)
            self._show_control(self.right_detail_label, False)
            if self.right_preview.hwnd:
                user32.ShowWindow(self.right_preview.hwnd, SW_HIDE)
        else:
            user32.MoveWindow(self.left_label, left_x, label_y, panel_width, label_height, True)
            user32.MoveWindow(self.right_label, right_x, label_y, panel_width, label_height, True)
            user32.MoveWindow(self.left_detail_label, left_x, detail_y, panel_width, detail_height, True)
            user32.MoveWindow(self.right_detail_label, right_x, detail_y, panel_width, detail_height, True)
            self.left_preview.move(left_x, preview_y, panel_width, preview_height)
            self.right_preview.move(right_x, preview_y, panel_width, preview_height)
        user32.MoveWindow(
            self.info_label,
            margin,
            bottom_y + 4,
            info_width,
            18,
            True,
        )
        user32.MoveWindow(self.left_copy_path_button, left_copy_x, bottom_y, copy_button_width, 24, True)
        user32.MoveWindow(self.right_copy_path_button, right_copy_x, bottom_y, copy_button_width, 24, True)
        user32.MoveWindow(self.swap_button, swap_x, bottom_y, swap_button_width, 24, True)
        user32.MoveWindow(self.layout_mode_button, layout_x, bottom_y, layout_button_width, 24, True)
        user32.MoveWindow(self.overlay_ratio_button, overlay_ratio_x, bottom_y, overlay_ratio_button_width, 24, True)
        user32.MoveWindow(self.view_mode_button, view_mode_x, bottom_y, view_mode_button_width, 24, True)
        user32.MoveWindow(self.mask_style_button, mask_style_x, bottom_y, mask_style_button_width, 24, True)
        user32.MoveWindow(self.mask_threshold_button, mask_threshold_x, bottom_y, mask_threshold_button_width, 24, True)
        user32.MoveWindow(self.guide_mode_button, guide_x, bottom_y, guide_button_width, 24, True)
        user32.MoveWindow(self.sync_toggle_button, sync_x, bottom_y, sync_button_width, 24, True)
        user32.MoveWindow(
            self.center_reset_button,
            reset_x,
            bottom_y,
            reset_button_width,
            24,
            True,
        )

    def _render_current_pair(self, reset_pan: bool = False) -> None:
        if self._left_image is None or self._right_image is None:
            return
        left_ratio = self.left_preview.pan_ratio()
        right_ratio = self.right_preview.pan_ratio()
        display_left_image, display_right_image = self._display_pair_images()
        left_render = self._render_result_for_side("left", display_left_image)
        right_render = self._render_result_for_side("right", display_right_image)
        if left_render is None or right_render is None:
            return
        left_image, left_preview, left_result = left_render
        right_image, right_preview, right_result = right_render
        if self._view_mode == COMPARE_VIEW_MODE_DIFF:
            left_result, right_result = _diff_emphasized_results(left_result, right_result)
        elif self._view_mode == COMPARE_VIEW_MODE_OVERLAY:
            left_result, right_result = _overlay_blended_results(
                left_result,
                right_result,
                self._overlay_alpha_percent,
            )
        elif self._view_mode == COMPARE_VIEW_MODE_MASK:
            left_result, right_result = _diff_mask_results(
                left_result,
                right_result,
                self._mask_style,
                self._mask_threshold,
            )
        left_preview.set_result(left_image, left_result)
        right_preview.set_result(right_image, right_result)
        if reset_pan:
            self._set_pair_pan_ratio(0.0, 0.0)
        else:
            self._syncing_pan = True
            try:
                self.left_preview.set_pan_ratio(*left_ratio)
                self.right_preview.set_pan_ratio(*right_ratio)
            finally:
                self._syncing_pan = False
        self._update_image_info_labels()
        self._update_info_label()

    def _render_side(self, side: str) -> None:
        render_data = self._render_result_for_side(side)
        if render_data is None:
            return
        image_file, preview, result = render_data
        preview.set_result(image_file, result)

    def _render_result_for_side(self, side: str, image_file: ImageFile | None = None) -> tuple[ImageFile, ImagePreview, PreviewResult] | None:
        if image_file is None:
            image_file = self._left_image if side == "left" else self._right_image
        preview = self.left_preview if side == "left" else self.right_preview
        display_mode = self._left_display_mode if side == "left" else self._right_display_mode
        if image_file is None:
            return None
        preview.set_pan_enabled(display_mode in COMPARE_PAN_MODES)
        preview.set_loading(image_file)
        width, height = preview.preview_size()
        result = render_preview(image_file, width, height, display_mode=display_mode)
        return (image_file, preview, result)

    def _display_pair_images(self) -> tuple[ImageFile, ImageFile]:
        if self._left_image is None or self._right_image is None:
            raise ValueError("Compare images are not set")
        if self._layout_mode == COMPARE_LAYOUT_CENTER:
            active_side = self._center_active_side()
            if active_side == "right":
                return (self._right_image, self._left_image)
            return (self._left_image, self._right_image)
        if self._view_mode == COMPARE_VIEW_MODE_ALTERNATE and self._alternate_phase:
            return (self._right_image, self._left_image)
        return (self._left_image, self._right_image)

    def _center_active_side(self) -> str:
        active_side = "right" if self._center_side == "right" else "left"
        if self._view_mode == COMPARE_VIEW_MODE_ALTERNATE and self._alternate_phase:
            return "left" if active_side == "right" else "right"
        return active_side

    def _current_image_for_side(self, side: str) -> ImageFile | None:
        if self._left_image is None or self._right_image is None:
            return None
        left_image, right_image = self._display_pair_images()
        return right_image if side == "right" else left_image

    def _zoom_in(self, source: str = "left") -> None:
        self._change_display_mode(self._stepped_display_mode(self._display_mode_for_source(source), 1), source)

    def _zoom_out(self, source: str = "left") -> None:
        self._change_display_mode(self._stepped_display_mode(self._display_mode_for_source(source), -1), source)

    def _change_display_mode(self, display_mode: str, source: str = "left") -> None:
        if self._sync_enabled:
            if display_mode == self._left_display_mode and display_mode == self._right_display_mode:
                return
            self._display_mode = display_mode
            self._left_display_mode = display_mode
            self._right_display_mode = display_mode
            self._render_current_pair(reset_pan=True)
            return

        side = "right" if source == "right" else "left"
        if side == "left":
            if display_mode == self._left_display_mode:
                return
            self._left_display_mode = display_mode
            self._display_mode = self._left_display_mode
        else:
            if display_mode == self._right_display_mode:
                return
            self._right_display_mode = display_mode
        if self._view_mode != COMPARE_VIEW_MODE_NORMAL or self._layout_mode == COMPARE_LAYOUT_CENTER:
            self._render_current_pair(reset_pan=True)
            return
        self._render_side(side)
        self._update_info_label()

    def _display_mode_for_source(self, source: str) -> str:
        return self._right_display_mode if source == "right" else self._left_display_mode

    def _stepped_display_mode(self, display_mode: str, direction: int) -> str:
        if display_mode not in COMPARE_ZOOM_MODES:
            return PREVIEW_MODE_ORIGINAL if direction > 0 else PREVIEW_MODE_SCALE_50
        index = COMPARE_ZOOM_MODES.index(display_mode)
        next_index = max(0, min(len(COMPARE_ZOOM_MODES) - 1, index + direction))
        return COMPARE_ZOOM_MODES[next_index]

    def _sync_pan_from(self, source: ImagePreview, _pan_x: int, _pan_y: int) -> None:
        if self._syncing_pan:
            return
        if source not in {self.left_preview, self.right_preview}:
            return
        if not self._sync_enabled:
            self._update_info_label()
            return
        ratio_x, ratio_y = source.pan_ratio()
        target = self.right_preview if source is self.left_preview else self.left_preview
        self._syncing_pan = True
        try:
            target.set_pan_ratio(ratio_x, ratio_y)
        finally:
            self._syncing_pan = False
        self._update_info_label()

    def _set_pair_pan_ratio(self, ratio_x: float, ratio_y: float) -> None:
        self._syncing_pan = True
        try:
            self.left_preview.set_pan_ratio(ratio_x, ratio_y)
            self.right_preview.set_pan_ratio(ratio_x, ratio_y)
        finally:
            self._syncing_pan = False

    def _reset_center(self) -> bool:
        self._set_pair_pan_ratio(0.0, 0.0)
        self._update_info_label()
        return True

    def _toggle_sync_enabled(self) -> bool:
        self._sync_enabled = not self._sync_enabled
        if self._sync_enabled:
            self._right_display_mode = self._left_display_mode
            self._display_mode = self._left_display_mode
            self._render_current_pair(reset_pan=True)
        self._update_sync_button_label()
        self._update_info_label()
        return True

    def _cycle_layout_mode(self) -> bool:
        index = COMPARE_LAYOUT_MODES.index(self._layout_mode) if self._layout_mode in COMPARE_LAYOUT_MODES else 0
        next_mode = COMPARE_LAYOUT_MODES[(index + 1) % len(COMPARE_LAYOUT_MODES)]
        return self._set_layout_mode(next_mode)

    def _set_layout_mode(self, layout_mode: str, render: bool = True) -> bool:
        if layout_mode not in COMPARE_LAYOUT_MODES:
            return False
        if self._layout_mode == layout_mode and render:
            return True
        self._layout_mode = layout_mode
        if layout_mode != COMPARE_LAYOUT_CENTER:
            self._center_side = "left"
        self._update_layout_mode_button_label()
        self._layout()
        if render:
            self._render_current_pair(reset_pan=False)
        return True

    def _handle_center_key(self, key: int) -> bool:
        if self._layout_mode != COMPARE_LAYOUT_CENTER:
            return False
        if key == VK_LEFT:
            return self._set_center_side("left")
        if key == VK_RIGHT:
            return self._set_center_side("right")
        if key == VK_SPACE:
            return self._toggle_center_side()
        return False

    def _toggle_center_side(self) -> bool:
        return self._set_center_side("right" if self._center_side == "left" else "left")

    def _set_center_side(self, side: str) -> bool:
        side = "right" if side == "right" else "left"
        if self._layout_mode != COMPARE_LAYOUT_CENTER:
            self._center_side = side
            return False
        if self._center_side == side:
            self._update_info_label()
            return True
        self._center_side = side
        self._render_current_pair(reset_pan=False)
        return True

    def _cycle_view_mode(self) -> bool:
        index = COMPARE_VIEW_MODES.index(self._view_mode) if self._view_mode in COMPARE_VIEW_MODES else 0
        next_mode = COMPARE_VIEW_MODES[(index + 1) % len(COMPARE_VIEW_MODES)]
        return self._set_view_mode(next_mode)

    def _set_view_mode(self, view_mode: str, render: bool = True) -> bool:
        if view_mode not in COMPARE_VIEW_MODES:
            return False
        if self._view_mode == view_mode and render:
            return True
        was_alternate = self._view_mode == COMPARE_VIEW_MODE_ALTERNATE
        self._view_mode = view_mode
        self._diff_enabled = view_mode == COMPARE_VIEW_MODE_DIFF
        if view_mode == COMPARE_VIEW_MODE_ALTERNATE:
            self._alternate_phase = False
            self._start_alternate_timer()
        elif was_alternate:
            self._alternate_phase = False
            self._stop_alternate_timer()
        else:
            self._alternate_phase = False
        self._update_view_mode_button_label()
        if render:
            self._render_current_pair(reset_pan=False)
        return True

    def _cycle_overlay_ratio(self) -> bool:
        index = (
            OVERLAY_ALPHA_PERCENTS.index(self._overlay_alpha_percent)
            if self._overlay_alpha_percent in OVERLAY_ALPHA_PERCENTS
            else 1
        )
        return self._set_overlay_ratio(OVERLAY_ALPHA_PERCENTS[(index + 1) % len(OVERLAY_ALPHA_PERCENTS)])

    def _set_overlay_ratio(self, alpha_percent: int, render: bool = True) -> bool:
        if alpha_percent not in OVERLAY_ALPHA_PERCENTS:
            return False
        if self._overlay_alpha_percent == alpha_percent and render:
            return True
        self._overlay_alpha_percent = alpha_percent
        self._update_overlay_ratio_button_label()
        if render and self._view_mode == COMPARE_VIEW_MODE_OVERLAY:
            self._render_current_pair(reset_pan=False)
        else:
            self._update_info_label()
        return True

    def _cycle_mask_style(self) -> bool:
        index = MASK_STYLES.index(self._mask_style) if self._mask_style in MASK_STYLES else 0
        next_style = MASK_STYLES[(index + 1) % len(MASK_STYLES)]
        return self._set_mask_style(next_style)

    def _set_mask_style(self, mask_style: str, render: bool = True) -> bool:
        if mask_style not in MASK_STYLES:
            return False
        if self._mask_style == mask_style and render:
            return True
        self._mask_style = mask_style
        self._update_mask_style_button_label()
        if render and self._view_mode == COMPARE_VIEW_MODE_MASK:
            self._render_current_pair(reset_pan=False)
        else:
            self._update_info_label()
        return True

    def _cycle_mask_threshold(self) -> bool:
        index = MASK_THRESHOLDS.index(self._mask_threshold) if self._mask_threshold in MASK_THRESHOLDS else 1
        next_threshold = MASK_THRESHOLDS[(index + 1) % len(MASK_THRESHOLDS)]
        return self._set_mask_threshold(next_threshold)

    def _set_mask_threshold(self, mask_threshold: str, render: bool = True) -> bool:
        if mask_threshold not in MASK_THRESHOLDS:
            return False
        if self._mask_threshold == mask_threshold and render:
            return True
        self._mask_threshold = mask_threshold
        self._update_mask_threshold_button_label()
        if render and self._view_mode == COMPARE_VIEW_MODE_MASK:
            self._render_current_pair(reset_pan=False)
        else:
            self._update_info_label()
        return True

    def _cycle_guide_mode(self) -> bool:
        index = COMPARE_GUIDE_MODES.index(self._guide_mode) if self._guide_mode in COMPARE_GUIDE_MODES else 0
        next_mode = COMPARE_GUIDE_MODES[(index + 1) % len(COMPARE_GUIDE_MODES)]
        return self._set_guide_mode(next_mode)

    def _set_guide_mode(self, guide_mode: str, update_label: bool = True) -> bool:
        if guide_mode not in COMPARE_GUIDE_MODES:
            return False
        self._guide_mode = guide_mode
        center = guide_mode in {COMPARE_GUIDE_MODE_CENTER, COMPARE_GUIDE_MODE_BOTH}
        grid = guide_mode in {COMPARE_GUIDE_MODE_GRID, COMPARE_GUIDE_MODE_BOTH}
        self.left_preview.set_guides(center=center, grid=grid)
        self.right_preview.set_guides(center=center, grid=grid)
        if update_label:
            self._update_guide_mode_button_label()
            self._update_info_label()
        return True

    def _toggle_diff_enabled(self) -> bool:
        return self._set_view_mode(COMPARE_VIEW_MODE_NORMAL if self._view_mode == COMPARE_VIEW_MODE_DIFF else COMPARE_VIEW_MODE_DIFF)

    def _advance_alternate_phase(self) -> bool:
        if self._view_mode != COMPARE_VIEW_MODE_ALTERNATE:
            self._stop_alternate_timer()
            return False
        self._alternate_phase = not self._alternate_phase
        self._render_current_pair(reset_pan=False)
        return True

    def _start_alternate_timer(self) -> None:
        if self.hwnd:
            user32.KillTimer(self.hwnd, ALTERNATE_TIMER_ID)
            user32.SetTimer(self.hwnd, ALTERNATE_TIMER_ID, ALTERNATE_INTERVAL_MS, None)

    def _stop_alternate_timer(self) -> None:
        if self.hwnd:
            user32.KillTimer(self.hwnd, ALTERNATE_TIMER_ID)

    def _swap_sides(self) -> bool:
        if self._left_image is None or self._right_image is None:
            return False
        left_ratio = self.left_preview.pan_ratio()
        right_ratio = self.right_preview.pan_ratio()
        self._left_image, self._right_image = self._right_image, self._left_image
        self._left_display_mode, self._right_display_mode = self._right_display_mode, self._left_display_mode
        self._display_mode = self._left_display_mode
        self._update_image_info_labels()
        self._render_current_pair(reset_pan=False)
        self._syncing_pan = True
        try:
            self.left_preview.set_pan_ratio(*right_ratio)
            self.right_preview.set_pan_ratio(*left_ratio)
        finally:
            self._syncing_pan = False
        self._update_info_label()
        return True

    def _copy_left_image_path(self) -> bool:
        return self._copy_image_path("left")

    def _copy_right_image_path(self) -> bool:
        return self._copy_image_path("right")

    def _copy_left_image_info(self) -> bool:
        return self._copy_image_info("left")

    def _copy_right_image_info(self) -> bool:
        return self._copy_image_info("right")

    def _copy_image_path(self, side: str) -> bool:
        image_file = self._current_image_for_side(side)
        label = "左画像パス" if side == "left" else "右画像パス"
        if image_file is None:
            self._show_temporary_message(f"{label}をコピーする画像がありません")
            return False

        path_text = str(display_path(image_file.path))
        try:
            self._copy_text_to_clipboard(path_text)
        except OSError:
            traceback.print_exc(file=sys.stderr)
            self._show_temporary_message(f"{label}をコピーできませんでした")
            return False

        self._show_temporary_message(f"{label}をコピーしました")
        return True

    def _copy_image_info(self, side: str) -> bool:
        image_file = self._current_image_for_side(side)
        label = "左画像情報" if side == "left" else "右画像情報"
        if image_file is None:
            self._show_temporary_message(f"{label}をコピーする画像がありません")
            return False

        try:
            self._copy_text_to_clipboard(_image_info_text(image_file))
        except OSError:
            traceback.print_exc(file=sys.stderr)
            self._show_temporary_message(f"{label}をコピーできませんでした")
            return False

        self._show_temporary_message(f"{label}をコピーしました")
        return True

    def _handle_preview_context_menu(self, side: str, source_hwnd: int | None, x: int, y: int) -> None:
        screen_x, screen_y = self._control_point_to_screen(source_hwnd, x, y)
        command = self._show_info_context_menu(side, screen_x, screen_y, owner_hwnd=source_hwnd)
        if command == CONTEXT_COPY_IMAGE_INFO_ID:
            self._copy_image_info(side)

    def _show_info_context_menu(self, side: str, screen_x: int, screen_y: int, owner_hwnd: int | None = None) -> int:
        menu_owner = owner_hwnd or self.hwnd
        if not menu_owner:
            return 0
        menu = user32.CreatePopupMenu()
        if not menu:
            return 0
        try:
            label = "左画像情報コピー" if side == "left" else "右画像情報コピー"
            user32.AppendMenuW(menu, MF_STRING, CONTEXT_COPY_IMAGE_INFO_ID, label)
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

    def _copy_text_to_clipboard(self, text: str) -> None:
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

    def _show_temporary_message(self, message: str, duration_ms: int = COPY_MESSAGE_DURATION_MS) -> None:
        self._set_label(self.info_label, message)
        if self.hwnd:
            user32.KillTimer(self.hwnd, COPY_MESSAGE_TIMER_ID)
            user32.SetTimer(self.hwnd, COPY_MESSAGE_TIMER_ID, duration_ms, None)

    def _update_image_info_labels(self) -> None:
        left_image = self._current_image_for_side("left")
        right_image = self._current_image_for_side("right")
        if self._layout_mode == COMPARE_LAYOUT_CENTER:
            if left_image is not None:
                active_label = "右画像" if self._center_active_side() == "right" else "左画像"
                self._set_label(self.left_label, f"中央: {active_label} - {left_image.name}")
                self._set_label(self.left_detail_label, _image_detail_text(left_image))
            if right_image is not None:
                self._set_label(self.right_label, f"待機: {right_image.name}")
                self._set_label(self.right_detail_label, _image_detail_text(right_image))
            return
        if left_image is not None:
            self._set_label(self.left_label, f"左: {left_image.name}")
            self._set_label(self.left_detail_label, _image_detail_text(left_image))
        if right_image is not None:
            self._set_label(self.right_label, f"右: {right_image.name}")
            self._set_label(self.right_detail_label, _image_detail_text(right_image))

    def _update_info_label(self) -> None:
        layout_state = self._layout_mode_label()
        view_state = self._view_mode_label()
        guide_state = self._guide_mode_label()
        sync_state = "同期ON" if self._sync_enabled else "同期OFF"
        zoom_hint = "同期ズーム" if self._sync_enabled else "個別ズーム"
        pan_hint = "同期移動" if self._sync_enabled else "個別移動"
        self._set_label(
            self.info_label,
            f"{layout_state} / {view_state} / {guide_state} / {sync_state} / 左: {self._display_mode_label(self._left_display_mode)} / "
            f"右: {self._display_mode_label(self._right_display_mode)} / "
            f"Ctrl+ホイール: {zoom_hint} / ドラッグ: {pan_hint}",
        )

    def _update_sync_button_label(self) -> None:
        self._set_label(self.sync_toggle_button, "同期ON" if self._sync_enabled else "同期OFF")

    def _update_layout_mode_button_label(self) -> None:
        self._set_label(self.layout_mode_button, f"配置: {self._layout_mode_short_label()}")

    def _update_view_mode_button_label(self) -> None:
        self._set_label(self.view_mode_button or self.diff_toggle_button, f"表示: {self._view_mode_short_label()}")

    def _update_overlay_ratio_button_label(self) -> None:
        self._set_label(self.overlay_ratio_button, f"重ね: {self._overlay_alpha_percent}%")

    def _update_guide_mode_button_label(self) -> None:
        self._set_label(self.guide_mode_button, f"補助: {self._guide_mode_short_label()}")

    def _update_mask_style_button_label(self) -> None:
        self._set_label(self.mask_style_button, f"色: {self._mask_style_short_label()}")

    def _update_mask_threshold_button_label(self) -> None:
        self._set_label(self.mask_threshold_button, f"感度: {self._mask_threshold_short_label()}")

    def _update_diff_button_label(self) -> None:
        self._update_view_mode_button_label()

    def _view_mode_short_label(self) -> str:
        if self._view_mode == COMPARE_VIEW_MODE_DIFF:
            return "差分"
        if self._view_mode == COMPARE_VIEW_MODE_ALTERNATE:
            return "交互"
        if self._view_mode == COMPARE_VIEW_MODE_OVERLAY:
            return "重ね"
        if self._view_mode == COMPARE_VIEW_MODE_MASK:
            return "マスク"
        return "通常"

    def _view_mode_label(self) -> str:
        if self._view_mode == COMPARE_VIEW_MODE_DIFF:
            return "差分強調表示"
        if self._view_mode == COMPARE_VIEW_MODE_ALTERNATE:
            phase = "左右入替表示" if self._alternate_phase else "通常位置"
            return f"左右交互表示中: {phase} ({ALTERNATE_INTERVAL_MS // 1000}秒間隔)"
        if self._view_mode == COMPARE_VIEW_MODE_OVERLAY:
            return f"重ね合わせ表示 ({self._overlay_alpha_percent}%)"
        if self._view_mode == COMPARE_VIEW_MODE_MASK:
            return f"差分マスク表示 ({self._mask_style_short_label()} / 感度: {self._mask_threshold_short_label()})"
        return "通常表示"

    def _mask_style_short_label(self) -> str:
        if self._mask_style == MASK_STYLE_GREEN:
            return "緑"
        if self._mask_style == MASK_STYLE_TRANSLUCENT:
            return "半透"
        return "赤"

    def _mask_threshold_short_label(self) -> str:
        if self._mask_threshold == MASK_THRESHOLD_WEAK:
            return "弱"
        if self._mask_threshold == MASK_THRESHOLD_STRONG:
            return "強"
        return "中"

    def _guide_mode_short_label(self) -> str:
        if self._guide_mode == COMPARE_GUIDE_MODE_CENTER:
            return "中央"
        if self._guide_mode == COMPARE_GUIDE_MODE_GRID:
            return "格子"
        if self._guide_mode == COMPARE_GUIDE_MODE_BOTH:
            return "両方"
        return "OFF"

    def _guide_mode_label(self) -> str:
        if self._guide_mode == COMPARE_GUIDE_MODE_CENTER:
            return "補助: 中央ガイド線"
        if self._guide_mode == COMPARE_GUIDE_MODE_GRID:
            return "補助: 縦横グリッド"
        if self._guide_mode == COMPARE_GUIDE_MODE_BOTH:
            return "補助: 中央ガイド線+縦横グリッド"
        return "補助: OFF"

    def _layout_mode_short_label(self) -> str:
        if self._layout_mode == COMPARE_LAYOUT_TOP_BOTTOM:
            return "上下"
        if self._layout_mode == COMPARE_LAYOUT_CENTER:
            return "中央"
        return "左右"

    def _layout_mode_label(self) -> str:
        if self._layout_mode == COMPARE_LAYOUT_TOP_BOTTOM:
            return "上下並び"
        if self._layout_mode == COMPARE_LAYOUT_CENTER:
            active = "右画像" if self._center_active_side() == "right" else "左画像"
            return f"中央切替表示中: {active}"
        return "左右並び"

    def _display_mode_label(self, display_mode: str) -> str:
        if display_mode == PREVIEW_MODE_SCALE_50:
            return "50%"
        if display_mode == PREVIEW_MODE_ORIGINAL:
            return "100%"
        if display_mode == PREVIEW_MODE_SCALE_200:
            return "200%"
        if display_mode == PREVIEW_MODE_FIT_HEIGHT:
            return "高さに合わせる"
        return display_mode

    def _set_label(self, hwnd: int | None, text: str) -> None:
        if hwnd:
            user32.SetWindowTextW(hwnd, text)

    def _show_compare_controls(self, visible: bool) -> None:
        self._show_control(self.left_label, visible)
        self._show_control(self.right_label, visible)
        self._show_control(self.left_detail_label, visible)
        self._show_control(self.right_detail_label, visible)
        if self.left_preview.hwnd:
            user32.ShowWindow(self.left_preview.hwnd, SW_SHOW if visible else SW_HIDE)
        if self.right_preview.hwnd:
            user32.ShowWindow(self.right_preview.hwnd, SW_SHOW if visible else SW_HIDE)

    def _show_control(self, hwnd: int | None, visible: bool) -> None:
        if hwnd:
            user32.ShowWindow(hwnd, SW_SHOW if visible else SW_HIDE)


def _diff_emphasized_results(
    left_result: PreviewResult,
    right_result: PreviewResult,
) -> tuple[PreviewResult, PreviewResult]:
    if not left_result.ok or not right_result.ok:
        return (left_result, right_result)
    if left_result.cache_path is None or right_result.cache_path is None:
        return (left_result, right_result)

    left_diff_path = _diff_cache_path(left_result, right_result, "left")
    right_diff_path = _diff_cache_path(left_result, right_result, "right")
    if path_exists(left_diff_path) and path_exists(right_diff_path):
        return (
            PreviewResult(left_diff_path, left_result.width, left_result.height),
            PreviewResult(right_diff_path, right_result.width, right_result.height),
        )

    try:
        make_dirs(left_diff_path.parent)
        with Image.open(filesystem_path(left_result.cache_path)) as left_image:
            left_base = left_image.convert("RGB")
        with Image.open(filesystem_path(right_result.cache_path)) as right_image:
            right_base = right_image.convert("RGB")

        _save_diff_overlay(left_base, right_base, left_diff_path)
        _save_diff_overlay(right_base, left_base, right_diff_path)
    except (OSError, UnidentifiedImageError, ValueError):
        traceback.print_exc(file=sys.stderr)
        return (left_result, right_result)

    return (
        PreviewResult(left_diff_path, left_base.width, left_base.height),
        PreviewResult(right_diff_path, right_base.width, right_base.height),
    )


def _overlay_blended_results(
    left_result: PreviewResult,
    right_result: PreviewResult,
    alpha_percent: int,
) -> tuple[PreviewResult, PreviewResult]:
    if not left_result.ok or not right_result.ok:
        return (left_result, right_result)
    if left_result.cache_path is None or right_result.cache_path is None:
        return (left_result, right_result)
    if alpha_percent not in OVERLAY_ALPHA_PERCENTS:
        alpha_percent = 50

    left_overlay_path = _overlay_cache_path(left_result, right_result, "left", alpha_percent)
    right_overlay_path = _overlay_cache_path(left_result, right_result, "right", alpha_percent)
    if path_exists(left_overlay_path) and path_exists(right_overlay_path):
        return (
            PreviewResult(left_overlay_path, left_result.width, left_result.height),
            PreviewResult(right_overlay_path, right_result.width, right_result.height),
        )

    try:
        make_dirs(left_overlay_path.parent)
        with Image.open(filesystem_path(left_result.cache_path)) as left_image:
            left_base = left_image.convert("RGB")
        with Image.open(filesystem_path(right_result.cache_path)) as right_image:
            right_base = right_image.convert("RGB")

        _save_overlay_blend(left_base, right_base, left_overlay_path, alpha_percent)
        _save_overlay_blend(right_base, left_base, right_overlay_path, alpha_percent)
    except (OSError, UnidentifiedImageError, ValueError):
        traceback.print_exc(file=sys.stderr)
        return (left_result, right_result)

    return (
        PreviewResult(left_overlay_path, left_base.width, left_base.height),
        PreviewResult(right_overlay_path, right_base.width, right_base.height),
    )


def _diff_mask_results(
    left_result: PreviewResult,
    right_result: PreviewResult,
    mask_style: str,
    mask_threshold: str,
) -> tuple[PreviewResult, PreviewResult]:
    if not left_result.ok or not right_result.ok:
        return (left_result, right_result)
    if left_result.cache_path is None or right_result.cache_path is None:
        return (left_result, right_result)
    if mask_style not in MASK_STYLES:
        mask_style = MASK_STYLE_RED
    if mask_threshold not in MASK_THRESHOLDS:
        mask_threshold = MASK_THRESHOLD_MEDIUM

    left_mask_path = _diff_mask_cache_path(left_result, right_result, "left", mask_style, mask_threshold)
    right_mask_path = _diff_mask_cache_path(left_result, right_result, "right", mask_style, mask_threshold)
    if path_exists(left_mask_path) and path_exists(right_mask_path):
        return (
            PreviewResult(left_mask_path, left_result.width, left_result.height),
            PreviewResult(right_mask_path, right_result.width, right_result.height),
        )

    try:
        make_dirs(left_mask_path.parent)
        with Image.open(filesystem_path(left_result.cache_path)) as left_image:
            left_base = left_image.convert("RGB")
        with Image.open(filesystem_path(right_result.cache_path)) as right_image:
            right_base = right_image.convert("RGB")

        threshold_value = MASK_THRESHOLD_VALUES.get(mask_threshold, MASK_THRESHOLD_VALUES[MASK_THRESHOLD_MEDIUM])
        _save_diff_mask(left_base, right_base, left_mask_path, mask_style, threshold_value)
        _save_diff_mask(right_base, left_base, right_mask_path, mask_style, threshold_value)
    except (OSError, UnidentifiedImageError, ValueError):
        traceback.print_exc(file=sys.stderr)
        return (left_result, right_result)

    return (
        PreviewResult(left_mask_path, left_base.width, left_base.height),
        PreviewResult(right_mask_path, right_base.width, right_base.height),
    )


def _diff_cache_path(left_result: PreviewResult, right_result: PreviewResult, side: str) -> Path:
    key_source = "|".join(
        [
            "compare_diff_v1",
            side,
            _diff_cache_key_part(left_result),
            _diff_cache_key_part(right_result),
        ]
    )
    cache_key = hashlib.sha1(key_source.encode("utf-8")).hexdigest()
    return default_preview_cache_dir() / "compare_diff" / f"{cache_key}.bmp"


def _overlay_cache_path(left_result: PreviewResult, right_result: PreviewResult, side: str, alpha_percent: int) -> Path:
    key_source = "|".join(
        [
            "compare_overlay_v1",
            side,
            str(alpha_percent),
            _diff_cache_key_part(left_result),
            _diff_cache_key_part(right_result),
        ]
    )
    cache_key = hashlib.sha1(key_source.encode("utf-8")).hexdigest()
    return default_preview_cache_dir() / "compare_overlay" / f"{cache_key}.bmp"


def _diff_mask_cache_path(
    left_result: PreviewResult,
    right_result: PreviewResult,
    side: str,
    mask_style: str,
    mask_threshold: str,
) -> Path:
    key_source = "|".join(
        [
            "compare_mask_v1",
            side,
            mask_style,
            mask_threshold,
            _diff_cache_key_part(left_result),
            _diff_cache_key_part(right_result),
        ]
    )
    cache_key = hashlib.sha1(key_source.encode("utf-8")).hexdigest()
    return default_preview_cache_dir() / "compare_mask" / f"{cache_key}.bmp"


def _diff_cache_key_part(result: PreviewResult) -> str:
    if result.cache_path is None:
        return "none"
    try:
        stat = os.stat(filesystem_path(result.cache_path))
        stat_key = f"{stat.st_mtime_ns}:{stat.st_size}"
    except OSError:
        stat_key = "missing"
    return f"{display_path(result.cache_path)}:{stat_key}:{result.width}x{result.height}"


def _save_diff_overlay(base_image: Image.Image, other_image: Image.Image, cache_path: Path) -> None:
    comparison = other_image
    if comparison.size != base_image.size:
        comparison = comparison.resize(base_image.size, Image.Resampling.BILINEAR)

    diff = ImageChops.difference(base_image, comparison)
    mask = diff.convert("L").point(lambda value: 255 if value >= DIFF_HIGHLIGHT_THRESHOLD else 0)
    highlight = Image.new("RGB", base_image.size, (255, 48, 48))
    emphasized = Image.composite(highlight, base_image, mask)
    blended = Image.blend(base_image, emphasized, DIFF_HIGHLIGHT_BLEND)
    blended.save(filesystem_path(cache_path), format="BMP")


def _save_overlay_blend(base_image: Image.Image, overlay_image: Image.Image, cache_path: Path, alpha_percent: int) -> None:
    comparison = overlay_image
    if comparison.size != base_image.size:
        comparison = comparison.resize(base_image.size, Image.Resampling.BILINEAR)

    alpha = max(0.0, min(1.0, alpha_percent / 100.0))
    blended = Image.blend(base_image, comparison, alpha)
    blended.save(filesystem_path(cache_path), format="BMP")


def _save_diff_mask(
    base_image: Image.Image,
    other_image: Image.Image,
    cache_path: Path,
    mask_style: str,
    threshold_value: int,
) -> None:
    comparison = other_image
    if comparison.size != base_image.size:
        comparison = comparison.resize(base_image.size, Image.Resampling.BILINEAR)

    threshold = max(0, min(255, threshold_value))
    diff = ImageChops.difference(base_image, comparison)
    mask = diff.convert("L").point(lambda value: 255 if value >= threshold else 0)

    if mask_style == MASK_STYLE_GREEN:
        highlight = Image.new("RGB", base_image.size, (32, 220, 80))
        masked = Image.composite(highlight, base_image, mask)
    elif mask_style == MASK_STYLE_TRANSLUCENT:
        highlight = Image.new("RGB", base_image.size, (255, 232, 96))
        translucent = Image.blend(base_image, highlight, 0.45)
        masked = Image.composite(translucent, base_image, mask)
    else:
        highlight = Image.new("RGB", base_image.size, (255, 48, 48))
        masked = Image.composite(highlight, base_image, mask)

    masked.save(filesystem_path(cache_path), format="BMP")


def _register_compare_class() -> None:
    global _class_registered, _compare_proc_ref
    if _class_registered:
        return

    hinstance = kernel32.GetModuleHandleW(None)
    _compare_proc_ref = WNDPROC(_compare_proc)
    wndclass = WNDCLASSW(
        style=0,
        lpfnWndProc=_compare_proc_ref,
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


def _compare_proc(hwnd: int, message: int, w_param: int, l_param: int) -> int:
    view = _instances.get(int(hwnd))
    if view is not None:
        result = view.handle_message(hwnd, message, w_param, l_param)
        if result is not None:
            return result

    return int(user32.DefWindowProcW(hwnd, message, w_param, l_param))


def _image_detail_text(image_file: ImageFile) -> str:
    return f"画像サイズ: {_image_dimensions_text(image_file)} / ファイルサイズ: {_format_file_size(image_file.size)}"


def _image_info_text(image_file: ImageFile) -> str:
    return "\n".join(
        [
            f"ファイル名: {image_file.name}",
            f"画像サイズ: {_image_dimensions_text(image_file)}",
            f"ファイルサイズ: {_format_file_size(image_file.size)}",
            f"フルパス: {display_path(image_file.path)}",
        ]
    )


def _image_dimensions_text(image_file: ImageFile) -> str:
    try:
        with Image.open(filesystem_path(image_file.path)) as image:
            return f"{image.width} × {image.height}px"
    except (OSError, UnidentifiedImageError, ValueError):
        return "取得できません"


def _format_file_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    units = ["KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        value /= 1024
        if abs(value) < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
    return f"{size} B"

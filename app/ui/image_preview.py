from __future__ import annotations

import ctypes
from pathlib import Path

from ctypes import wintypes

from app.core.image_scanner import ImageFile
from app.core.preview_renderer import PreviewResult
from app.utils.long_path import filesystem_path

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]

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
user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.BeginPaint.restype = wintypes.HDC
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.DrawTextW.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p, wintypes.UINT]
user32.EndPaint.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.FillRect.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.HBRUSH]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short
user32.InvalidateRect.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.BOOL]
user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
user32.LoadCursorW.restype = wintypes.HANDLE
user32.LoadImageW.argtypes = [
    wintypes.HINSTANCE,
    wintypes.LPCWSTR,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.LoadImageW.restype = wintypes.HANDLE
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
user32.ReleaseCapture.argtypes = []
user32.ReleaseCapture.restype = wintypes.BOOL
user32.SetCapture.argtypes = [wintypes.HWND]
user32.SetCapture.restype = wintypes.HWND
user32.SetCursor.argtypes = [wintypes.HANDLE]
user32.SetCursor.restype = wintypes.HANDLE
user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND

gdi32.BitBlt.argtypes = [
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.DWORD,
]
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.COLORREF]
gdi32.CreatePen.restype = wintypes.HPEN
gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.GetStockObject.argtypes = [ctypes.c_int]
gdi32.GetStockObject.restype = ctypes.c_void_p
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.MoveToEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
gdi32.LineTo.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]

WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_PAINT = 0x000F
WM_ERASEBKGND = 0x0014
WM_SETCURSOR = 0x0020
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
WM_MOUSEWHEEL = 0x020A
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_DROPFILES = 0x0233

WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000
WS_TABSTOP = 0x00010000

CS_DBLCLKS = 0x0008
IMAGE_BITMAP = 0
LR_LOADFROMFILE = 0x0010
LR_CREATEDIBSECTION = 0x2000
SRCCOPY = 0x00CC0020
MK_LBUTTON = 0x0001
PS_SOLID = 0

DT_CENTER = 0x00000001
DT_SINGLELINE = 0x00000020
DT_VCENTER = 0x00000004
DT_NOPREFIX = 0x00000800

TRANSPARENT = 1
DEFAULT_GUI_FONT = 17
GUIDE_GRID_SPACING = 80
GUIDE_GRID_COLOR = 0x00D0D0D0
GUIDE_CENTER_COLOR = 0x000060FF
IDC_ARROW = 32512
IDC_SIZEALL = 32646
IDC_HAND = 32649
VK_CONTROL = 0x11
VK_ESCAPE = 0x1B
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_SPACE = 0x20
VK_SHIFT = 0x10
VK_MENU = 0x12
VK_C = 0x43
VK_F = 0x46
CLASS_NAME = "FastImageViewerImagePreview"


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]


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


_preview_proc_ref: WNDPROC | None = None
_preview_instances: dict[int, ImagePreview] = {}
_class_registered = False


class ImagePreview:
    def __init__(self) -> None:
        self.hwnd: int | None = None
        self.image_file: ImageFile | None = None
        self.result: PreviewResult | None = None
        self.on_activated = None
        self.on_files_dropped = None
        self.on_escape = None
        self.on_previous = None
        self.on_next = None
        self.on_parent_folder = None
        self.on_previous_folder = None
        self.on_next_folder = None
        self.on_space = None
        self.on_zoom_in = None
        self.on_zoom_out = None
        self.on_pan_changed = None
        self.on_context_menu = None
        self.on_copy_image_path = None
        self.on_copy_folder_path = None
        self._hbitmap: int | None = None
        self._loaded_path: Path | None = None
        self._pan_enabled = False
        self._pan_x = 0
        self._pan_y = 0
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_origin_x = 0
        self._drag_origin_y = 0
        self._guide_center_enabled = False
        self._guide_grid_enabled = False

    def create(self, parent_hwnd: int) -> int:
        _register_preview_class()
        hinstance = kernel32.GetModuleHandleW(None)
        hwnd = user32.CreateWindowExW(
            0,
            CLASS_NAME,
            "",
            WS_CHILD | WS_VISIBLE | WS_BORDER | WS_TABSTOP,
            0,
            0,
            0,
            0,
            parent_hwnd,
            None,
            hinstance,
            None,
        )
        if not hwnd:
            raise ctypes.WinError()
        self.hwnd = int(hwnd)
        shell32.DragAcceptFiles(self.hwnd, True)
        _preview_instances[self.hwnd] = self
        return self.hwnd

    def move(self, x: int, y: int, width: int, height: int) -> None:
        if not self.hwnd:
            return
        user32.MoveWindow(self.hwnd, x, y, width, height, True)

    def set_image(self, image_file: ImageFile | None) -> None:
        self.set_loading(image_file)

    def set_loading(self, image_file: ImageFile | None) -> None:
        self.image_file = image_file
        self.result = None
        self._reset_pan()
        self._clear_bitmap()
        self._set_current_cursor()
        self.invalidate()

    def set_result(self, image_file: ImageFile, result: PreviewResult) -> None:
        if self.image_file is None or self.image_file.path != image_file.path:
            return
        self.result = result
        self._load_bitmap(result.cache_path if result.ok else None)
        self._clamp_pan()
        self._set_current_cursor()
        self.invalidate()

    def set_pan_enabled(self, enabled: bool) -> None:
        if self._pan_enabled == enabled:
            return
        self._pan_enabled = enabled
        self._reset_pan()
        self._set_current_cursor()
        self.invalidate()

    def pan_offset(self) -> tuple[int, int]:
        return self._pan_x, self._pan_y

    def set_pan_offset(self, pan_x: int, pan_y: int) -> None:
        self._pan_x = pan_x
        self._pan_y = pan_y
        self._clamp_pan()
        self._set_current_cursor()
        self.invalidate()

    def pan_ratio(self) -> tuple[float, float]:
        max_x, max_y = self._pan_limits()
        ratio_x = self._pan_x / max_x if max_x else 0.0
        ratio_y = self._pan_y / max_y if max_y else 0.0
        return ratio_x, ratio_y

    def set_pan_ratio(self, ratio_x: float, ratio_y: float) -> None:
        max_x, max_y = self._pan_limits()
        self.set_pan_offset(
            round(max_x * _clamp_float(ratio_x, -1.0, 1.0)),
            round(max_y * _clamp_float(ratio_y, -1.0, 1.0)),
        )

    def set_guides(self, center: bool = False, grid: bool = False) -> None:
        center_enabled = bool(center)
        grid_enabled = bool(grid)
        if self._guide_center_enabled == center_enabled and self._guide_grid_enabled == grid_enabled:
            return
        self._guide_center_enabled = center_enabled
        self._guide_grid_enabled = grid_enabled
        self.invalidate()

    def preview_size(self) -> tuple[int, int]:
        if not self.hwnd:
            return (0, 0)
        client = self._client_rect()
        return (
            max(1, client.right - client.left - 24),
            max(1, client.bottom - client.top - 24),
        )

    def clear(self) -> None:
        self.image_file = None
        self.result = None
        self._reset_pan()
        self._clear_bitmap()
        self._set_current_cursor()
        self.invalidate()

    def invalidate(self) -> None:
        if self.hwnd:
            user32.InvalidateRect(self.hwnd, None, True)

    def destroy(self) -> None:
        self._clear_bitmap()
        if self.hwnd:
            shell32.DragAcceptFiles(self.hwnd, False)
            _preview_instances.pop(self.hwnd, None)
            self.hwnd = None

    def handle_message(self, hwnd: int, message: int, w_param: int, l_param: int) -> int | None:
        if message == WM_ERASEBKGND:
            return 1
        if message == WM_SETCURSOR:
            self._set_current_cursor()
            return 1
        if message == WM_SIZE:
            self._clamp_pan()
            self._set_current_cursor()
            self.invalidate()
            return 0
        if message == WM_PAINT:
            self._paint()
            return 0
        if message == WM_SYSKEYDOWN:
            if self._handle_folder_navigation_shortcut(int(w_param)):
                return 0
        if message == WM_KEYDOWN:
            key = int(w_param)
            if key == VK_ESCAPE:
                if self.on_escape is not None:
                    self.on_escape()
                return 0
            if self._handle_copy_shortcut(key):
                return 0
            if key == VK_LEFT:
                if self.on_previous is not None:
                    self.on_previous()
                return 0
            if key == VK_RIGHT:
                if self.on_next is not None:
                    self.on_next()
                return 0
            if key == VK_SPACE:
                if self.on_space is not None and self.on_space():
                    return 0
                if _shift_pressed():
                    if self.on_previous is not None:
                        self.on_previous()
                elif self.on_next is not None:
                    self.on_next()
                return 0
        if message == WM_LBUTTONDBLCLK:
            user32.SetFocus(self.hwnd)
            self._end_pan()
            if self._reset_pan_to_center():
                return 0
            if self.on_activated is not None:
                self.on_activated()
            return 0
        if message == WM_LBUTTONDOWN:
            user32.SetFocus(self.hwnd)
            if self._begin_pan(_signed_loword(int(l_param)), _signed_hiword(int(l_param))):
                return 0
        if message == WM_MOUSEMOVE:
            if self._dragging:
                if int(w_param) & MK_LBUTTON:
                    self._update_pan(_signed_loword(int(l_param)), _signed_hiword(int(l_param)))
                else:
                    self._end_pan()
                return 0
        if message == WM_LBUTTONUP:
            if self._dragging:
                self._end_pan()
                return 0
        if message == WM_RBUTTONUP:
            user32.SetFocus(self.hwnd)
            if self.on_context_menu is not None:
                self.on_context_menu(self.hwnd, _signed_loword(int(l_param)), _signed_hiword(int(l_param)))
            return 0
        if message == WM_MOUSEWHEEL:
            delta = _signed_hiword(int(w_param))
            if _ctrl_pressed():
                if delta > 0 and self.on_zoom_in is not None:
                    self.on_zoom_in()
                elif delta < 0 and self.on_zoom_out is not None:
                    self.on_zoom_out()
            elif delta > 0 and self.on_previous is not None:
                self.on_previous()
            elif delta < 0 and self.on_next is not None:
                self.on_next()
            return 0
        if message == WM_DROPFILES:
            if self.on_files_dropped is not None:
                self.on_files_dropped(int(w_param))
            return 0
        if message == WM_DESTROY:
            self.destroy()
            return 0
        return None

    def _handle_folder_navigation_shortcut(self, key: int) -> bool:
        if not _alt_pressed():
            return False
        if key == VK_UP and self.on_parent_folder is not None:
            self.on_parent_folder()
            return True
        if key == VK_LEFT and self.on_previous_folder is not None:
            self.on_previous_folder()
            return True
        if key == VK_RIGHT and self.on_next_folder is not None:
            self.on_next_folder()
            return True
        return False

    def _handle_copy_shortcut(self, key: int) -> bool:
        if not (_ctrl_pressed() and _shift_pressed()):
            return False
        if key == VK_C:
            if self.on_copy_image_path is not None:
                self.on_copy_image_path()
            return True
        if key == VK_F:
            if self.on_copy_folder_path is not None:
                self.on_copy_folder_path()
            return True
        return False

    def _paint(self) -> None:
        if not self.hwnd:
            return

        ps = PAINTSTRUCT()
        hdc = user32.BeginPaint(self.hwnd, ctypes.byref(ps))
        try:
            client = self._client_rect()
            background = _solid_brush(0xF8F8F8)
            user32.FillRect(hdc, ctypes.byref(client), background)
            gdi32.DeleteObject(background)
            gdi32.SetBkMode(hdc, TRANSPARENT)

            if self._hbitmap and self.result and self.result.ok:
                self._draw_bitmap(hdc, client)
                self._draw_guides(hdc, client)
            else:
                self._draw_message(hdc, client)
        finally:
            user32.EndPaint(self.hwnd, ctypes.byref(ps))

    def _draw_bitmap(self, hdc: int, client: RECT) -> None:
        assert self.result is not None
        width = self.result.width
        height = self.result.height
        x, y = self._bitmap_origin(client)
        dest_x, dest_y, src_x, src_y, blit_width, blit_height = _visible_blit_rect(
            x,
            y,
            width,
            height,
            client,
        )
        if blit_width <= 0 or blit_height <= 0:
            return

        memory_dc = gdi32.CreateCompatibleDC(hdc)
        old_bitmap = gdi32.SelectObject(memory_dc, self._hbitmap)
        gdi32.BitBlt(hdc, dest_x, dest_y, blit_width, blit_height, memory_dc, src_x, src_y, SRCCOPY)
        gdi32.SelectObject(memory_dc, old_bitmap)
        gdi32.DeleteDC(memory_dc)

    def _draw_guides(self, hdc: int, client: RECT) -> None:
        if not self._guide_center_enabled and not self._guide_grid_enabled:
            return
        if self._guide_grid_enabled:
            self._draw_grid_guide(hdc, client)
        if self._guide_center_enabled:
            self._draw_center_guide(hdc, client)

    def _draw_grid_guide(self, hdc: int, client: RECT) -> None:
        pen = gdi32.CreatePen(PS_SOLID, 1, GUIDE_GRID_COLOR)
        if not pen:
            return
        old_pen = gdi32.SelectObject(hdc, pen)
        try:
            center_x = client.left + _rect_width(client) // 2
            center_y = client.top + _rect_height(client) // 2
            for x in _guide_positions(center_x, client.left, client.right, GUIDE_GRID_SPACING):
                gdi32.MoveToEx(hdc, x, client.top, None)
                gdi32.LineTo(hdc, x, client.bottom)
            for y in _guide_positions(center_y, client.top, client.bottom, GUIDE_GRID_SPACING):
                gdi32.MoveToEx(hdc, client.left, y, None)
                gdi32.LineTo(hdc, client.right, y)
        finally:
            gdi32.SelectObject(hdc, old_pen)
            gdi32.DeleteObject(pen)

    def _draw_center_guide(self, hdc: int, client: RECT) -> None:
        pen = gdi32.CreatePen(PS_SOLID, 1, GUIDE_CENTER_COLOR)
        if not pen:
            return
        old_pen = gdi32.SelectObject(hdc, pen)
        try:
            center_x = client.left + _rect_width(client) // 2
            center_y = client.top + _rect_height(client) // 2
            gdi32.MoveToEx(hdc, center_x, client.top, None)
            gdi32.LineTo(hdc, center_x, client.bottom)
            gdi32.MoveToEx(hdc, client.left, center_y, None)
            gdi32.LineTo(hdc, client.right, center_y)
        finally:
            gdi32.SelectObject(hdc, old_pen)
            gdi32.DeleteObject(pen)

    def _begin_pan(self, x: int, y: int) -> bool:
        if not self._can_pan():
            return False
        self._dragging = True
        self._drag_start_x = x
        self._drag_start_y = y
        self._drag_origin_x = self._pan_x
        self._drag_origin_y = self._pan_y
        if self.hwnd:
            user32.SetCapture(self.hwnd)
        self._set_current_cursor()
        return True

    def _update_pan(self, x: int, y: int) -> None:
        if not self._dragging:
            return
        self._pan_x = self._drag_origin_x + x - self._drag_start_x
        self._pan_y = self._drag_origin_y + y - self._drag_start_y
        self._clamp_pan()
        self.invalidate()
        self._notify_pan_changed()

    def _end_pan(self) -> None:
        if not self._dragging:
            return
        self._dragging = False
        user32.ReleaseCapture()
        self._set_current_cursor()

    def _reset_pan(self) -> None:
        self._pan_x = 0
        self._pan_y = 0
        self._dragging = False

    def _reset_pan_to_center(self) -> bool:
        if not self._can_pan():
            return False
        if self._pan_x == 0 and self._pan_y == 0:
            return False
        self._reset_pan()
        self._set_current_cursor()
        self.invalidate()
        self._notify_pan_changed()
        return True

    def _can_pan(self) -> bool:
        if not self.hwnd or not self._pan_enabled or self.result is None or not self.result.ok:
            return False
        client = self._client_rect()
        return self.result.width > _rect_width(client) or self.result.height > _rect_height(client)

    def _cursor_id(self) -> int:
        if self._dragging:
            return IDC_SIZEALL
        if self._can_pan():
            return IDC_HAND
        return IDC_ARROW

    def _set_current_cursor(self) -> None:
        if not self.hwnd:
            return
        cursor = user32.LoadCursorW(None, ctypes.cast(ctypes.c_void_p(self._cursor_id()), wintypes.LPCWSTR))
        if cursor:
            user32.SetCursor(cursor)

    def _notify_pan_changed(self) -> None:
        if self.on_pan_changed is not None:
            self.on_pan_changed(self, self._pan_x, self._pan_y)

    def _clamp_pan(self) -> None:
        if self.result is None or not self.result.ok or not self.hwnd:
            return
        client = self._client_rect()
        self._pan_x, self._pan_y = _clamped_pan(
            self._pan_x,
            self._pan_y,
            self.result.width,
            self.result.height,
            client,
        )

    def _pan_limits(self) -> tuple[int, int]:
        if self.result is None or not self.result.ok or not self.hwnd:
            return 0, 0
        client = self._client_rect()
        return (
            _axis_pan_limit(self.result.width, _rect_width(client)),
            _axis_pan_limit(self.result.height, _rect_height(client)),
        )

    def _bitmap_origin(self, client: RECT) -> tuple[int, int]:
        assert self.result is not None
        centered_x = client.left + (_rect_width(client) - self.result.width) // 2
        centered_y = client.top + (_rect_height(client) - self.result.height) // 2
        if self._pan_enabled:
            self._clamp_pan()
            return centered_x + self._pan_x, centered_y + self._pan_y
        return centered_x, centered_y

    def _draw_message(self, hdc: int, client: RECT) -> None:
        font = gdi32.GetStockObject(DEFAULT_GUI_FONT)
        old_font = gdi32.SelectObject(hdc, font)
        gdi32.SetTextColor(hdc, 0x666666)
        if self.image_file is None:
            text = "画像を選択してください"
        elif self.result is None:
            text = "プレビュー読込中..."
        else:
            text = "プレビューできません"
        user32.DrawTextW(hdc, text, -1, ctypes.byref(client), DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        gdi32.SelectObject(hdc, old_font)

    def _load_bitmap(self, cache_path: Path | None) -> None:
        if cache_path is None:
            self._clear_bitmap()
            return
        if self._hbitmap and self._loaded_path == cache_path:
            return

        self._clear_bitmap()
        loaded = user32.LoadImageW(
            None,
            filesystem_path(cache_path),
            IMAGE_BITMAP,
            0,
            0,
            LR_LOADFROMFILE | LR_CREATEDIBSECTION,
        )
        if loaded:
            self._hbitmap = int(loaded)
            self._loaded_path = cache_path

    def _clear_bitmap(self) -> None:
        if self._hbitmap:
            gdi32.DeleteObject(self._hbitmap)
        self._hbitmap = None
        self._loaded_path = None

    def _client_rect(self) -> RECT:
        rect = RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        return rect


def _register_preview_class() -> None:
    global _class_registered, _preview_proc_ref
    if _class_registered:
        return

    hinstance = kernel32.GetModuleHandleW(None)
    _preview_proc_ref = WNDPROC(_preview_proc)
    wndclass = WNDCLASSW(
        style=CS_DBLCLKS,
        lpfnWndProc=_preview_proc_ref,
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


def _preview_proc(hwnd: int, message: int, w_param: int, l_param: int) -> int:
    preview = _preview_instances.get(int(hwnd))
    if preview is not None:
        result = preview.handle_message(hwnd, message, w_param, l_param)
        if result is not None:
            return result
    return user32.DefWindowProcW(hwnd, message, w_param, l_param)


def _solid_brush(color_ref: int) -> int:
    return int(gdi32.CreateSolidBrush(color_ref))


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


def _rect_width(rect: RECT) -> int:
    return max(0, int(rect.right - rect.left))


def _rect_height(rect: RECT) -> int:
    return max(0, int(rect.bottom - rect.top))


def _ctrl_pressed() -> bool:
    return bool(user32.GetKeyState(VK_CONTROL) & 0x8000)


def _shift_pressed() -> bool:
    return bool(user32.GetKeyState(VK_SHIFT) & 0x8000)


def _alt_pressed() -> bool:
    return bool(user32.GetKeyState(VK_MENU) & 0x8000)


def _clamped_pan(pan_x: int, pan_y: int, image_width: int, image_height: int, viewport: RECT) -> tuple[int, int]:
    return (
        _clamped_axis_pan(pan_x, image_width, _rect_width(viewport)),
        _clamped_axis_pan(pan_y, image_height, _rect_height(viewport)),
    )


def _clamped_axis_pan(pan: int, image_size: int, viewport_size: int) -> int:
    limit = _axis_pan_limit(image_size, viewport_size)
    if limit <= 0:
        return 0
    return max(-limit, min(limit, pan))


def _axis_pan_limit(image_size: int, viewport_size: int) -> int:
    if image_size <= viewport_size:
        return 0
    return (image_size - viewport_size) // 2


def _guide_positions(center: int, minimum: int, maximum: int, spacing: int) -> list[int]:
    if spacing <= 0 or maximum <= minimum:
        return []
    position = center % spacing
    if position < minimum:
        position += ((minimum - position + spacing - 1) // spacing) * spacing

    positions: list[int] = []
    while position < maximum:
        positions.append(position)
        position += spacing
    return positions


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _visible_blit_rect(
    image_x: int,
    image_y: int,
    image_width: int,
    image_height: int,
    viewport: RECT,
) -> tuple[int, int, int, int, int, int]:
    dest_x = max(int(viewport.left), image_x)
    dest_y = max(int(viewport.top), image_y)
    right = min(int(viewport.right), image_x + image_width)
    bottom = min(int(viewport.bottom), image_y + image_height)
    width = max(0, right - dest_x)
    height = max(0, bottom - dest_y)
    src_x = max(0, dest_x - image_x)
    src_y = max(0, dest_y - image_y)
    return dest_x, dest_y, src_x, src_y, width, height

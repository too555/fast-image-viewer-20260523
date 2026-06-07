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

user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.BeginPaint.restype = wintypes.HDC
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
user32.DrawTextW.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p, wintypes.UINT]
user32.EndPaint.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.FillRect.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.HBRUSH]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
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
user32.RegisterClassW.argtypes = [ctypes.c_void_p]
user32.RegisterClassW.restype = wintypes.ATOM
user32.ReleaseCapture.argtypes = []
user32.ReleaseCapture.restype = wintypes.BOOL
user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND
user32.SetCapture.argtypes = [wintypes.HWND]
user32.SetCapture.restype = wintypes.HWND
user32.SetCursor.argtypes = [wintypes.HANDLE]
user32.SetCursor.restype = wintypes.HANDLE
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p]
user32.SetTimer.restype = ctypes.c_size_t
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
user32.KillTimer.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UpdateWindow.argtypes = [wintypes.HWND]

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
gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.GetStockObject.argtypes = [ctypes.c_int]
gdi32.GetStockObject.restype = ctypes.c_void_p
gdi32.GetTextExtentPoint32W.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p]
gdi32.GetTextExtentPoint32W.restype = wintypes.BOOL
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]

WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WM_ERASEBKGND = 0x0014
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_TIMER = 0x0113
WM_SETCURSOR = 0x0020
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
WM_MOUSEWHEEL = 0x020A
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_DROPFILES = 0x0233

WS_POPUP = 0x80000000

CS_DBLCLKS = 0x0008
DT_CENTER = 0x00000001
DT_RIGHT = 0x00000002
DT_SINGLELINE = 0x00000020
DT_VCENTER = 0x00000004
DT_END_ELLIPSIS = 0x00008000
DT_NOPREFIX = 0x00000800
IMAGE_BITMAP = 0
LR_CREATEDIBSECTION = 0x2000
LR_LOADFROMFILE = 0x0010
SRCCOPY = 0x00CC0020
MK_LBUTTON = 0x0001
SW_HIDE = 0
SW_SHOW = 5
SWP_SHOWWINDOW = 0x0040
TRANSPARENT = 1
DEFAULT_GUI_FONT = 17
IDC_ARROW = 32512
IDC_SIZEALL = 32646
IDC_HAND = 32649
SM_CXSCREEN = 0
SM_CYSCREEN = 1
VK_ESCAPE = 0x1B
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_SPACE = 0x20
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_C = 0x43
VK_F = 0x46

CLASS_NAME = "FastImageViewerFullscreenPreview"
INFO_BAR_HEIGHT = 52
HINT_BAR_HEIGHT = 34
OVERLAY_PADDING = 18
FULLSCREEN_HINT = "\u2190 \u2192 / Space / \u30db\u30a4\u30fc\u30eb \u79fb\u52d5 / Ctrl+\u30db\u30a4\u30fc\u30eb \u500d\u7387 / \u30c0\u30d6\u30eb\u30af\u30ea\u30c3\u30af \u4e2d\u592e / Esc \u623b\u308b"
COPY_FEEDBACK_TIMER_ID = 1
COPY_FEEDBACK_DURATION_MS = 2500


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


class SIZE(ctypes.Structure):
    _fields_ = [
        ("cx", ctypes.c_long),
        ("cy", ctypes.c_long),
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


_fullscreen_proc_ref: WNDPROC | None = None
_fullscreen_instances: dict[int, FullscreenPreview] = {}
_class_registered = False


class FullscreenPreview:
    def __init__(self) -> None:
        self.hwnd: int | None = None
        self.image_file: ImageFile | None = None
        self.result: PreviewResult | None = None
        self.position_text = ""
        self.zoom_text = ""
        self.hint_text = FULLSCREEN_HINT
        self.feedback_text = ""
        self.visible = False
        self.on_close = None
        self.on_previous = None
        self.on_next = None
        self.on_parent_folder = None
        self.on_previous_folder = None
        self.on_next_folder = None
        self.on_files_dropped = None
        self.on_zoom_in = None
        self.on_zoom_out = None
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

    def create(self, parent_hwnd: int) -> int:
        _register_fullscreen_class()
        hinstance = kernel32.GetModuleHandleW(None)
        hwnd = user32.CreateWindowExW(
            0,
            CLASS_NAME,
            "",
            WS_POPUP,
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
        _fullscreen_instances[self.hwnd] = self
        return self.hwnd

    def show_loading(self, image_file: ImageFile, position_text: str = "", zoom_text: str = "") -> None:
        self._require_window()
        self.visible = True
        self.image_file = image_file
        self.position_text = position_text
        self.zoom_text = zoom_text
        self.result = None
        self._reset_pan()
        self._clear_bitmap()
        width, height = self._screen_size()
        user32.SetWindowPos(self.hwnd, wintypes.HWND(-1), 0, 0, width, height, SWP_SHOWWINDOW)
        user32.ShowWindow(self.hwnd, SW_SHOW)
        user32.SetForegroundWindow(self.hwnd)
        user32.SetFocus(self.hwnd)
        self._set_current_cursor()
        self.invalidate()
        user32.UpdateWindow(self.hwnd)

    def show_feedback(self, text: str, duration_ms: int = COPY_FEEDBACK_DURATION_MS) -> None:
        self.feedback_text = text
        if self.hwnd:
            user32.KillTimer(self.hwnd, COPY_FEEDBACK_TIMER_ID)
            user32.SetTimer(self.hwnd, COPY_FEEDBACK_TIMER_ID, duration_ms, None)
        self.invalidate()

    def clear_feedback(self) -> None:
        if not self.feedback_text:
            return
        self.feedback_text = ""
        if self.hwnd:
            user32.KillTimer(self.hwnd, COPY_FEEDBACK_TIMER_ID)
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

    def hide(self) -> None:
        if not self.hwnd:
            return
        self.visible = False
        self.image_file = None
        self.result = None
        self.position_text = ""
        self.zoom_text = ""
        self.clear_feedback()
        self._reset_pan()
        self._clear_bitmap()
        self._set_current_cursor()
        user32.ShowWindow(self.hwnd, SW_HIDE)

    def preview_size(self) -> tuple[int, int]:
        width, height = self._screen_size()
        return (width, max(1, height - INFO_BAR_HEIGHT - HINT_BAR_HEIGHT))

    def _screen_size(self) -> tuple[int, int]:
        width = max(1, user32.GetSystemMetrics(SM_CXSCREEN))
        height = max(1, user32.GetSystemMetrics(SM_CYSCREEN))
        return (width, height)

    def invalidate(self) -> None:
        if self.hwnd:
            user32.InvalidateRect(self.hwnd, None, True)

    def destroy(self) -> None:
        if self.hwnd:
            user32.KillTimer(self.hwnd, COPY_FEEDBACK_TIMER_ID)
        self._clear_bitmap()
        if self.hwnd:
            shell32.DragAcceptFiles(self.hwnd, False)
            _fullscreen_instances.pop(self.hwnd, None)
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None

    def handle_message(self, hwnd: int, message: int, w_param: int, l_param: int) -> int | None:
        if message == WM_ERASEBKGND:
            return 1
        if message == WM_TIMER:
            if int(w_param) == COPY_FEEDBACK_TIMER_ID:
                self.clear_feedback()
                return 0
        if message == WM_SETCURSOR:
            self._set_current_cursor()
            return 1
        if message == WM_SYSKEYDOWN:
            if self._handle_folder_navigation_shortcut(int(w_param)):
                return 0
        if message == WM_KEYDOWN:
            key = int(w_param)
            if self._handle_copy_shortcut(key):
                return 0
            if key == VK_ESCAPE:
                if self.on_close is not None:
                    self.on_close()
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
                if self.on_close is not None:
                    self.on_close()
                return 0
        if message == WM_MOUSEWHEEL:
            delta = _signed_hiword(int(w_param))
            if _ctrl_pressed():
                if delta > 0 and self.on_zoom_in is not None:
                    self.on_zoom_in()
                elif delta < 0 and self.on_zoom_out is not None:
                    self.on_zoom_out()
            elif delta > 0:
                if self.on_previous is not None:
                    self.on_previous()
            elif delta < 0 and self.on_next is not None:
                self.on_next()
            return 0
        if message == WM_LBUTTONDBLCLK:
            self._end_pan()
            self._reset_pan_to_center()
            return 0
        if message == WM_LBUTTONDOWN:
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
            if self.on_context_menu is not None:
                self.on_context_menu(self.hwnd, _signed_loword(int(l_param)), _signed_hiword(int(l_param)))
            return 0
        if message == WM_DROPFILES:
            if self.on_files_dropped is not None:
                self.on_files_dropped(int(w_param))
            return 0
        if message == WM_PAINT:
            self._paint()
            return 0
        if message == WM_DESTROY:
            self._clear_bitmap()
            _fullscreen_instances.pop(int(hwnd), None)
            self.hwnd = None
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
            background = _solid_brush(0x000000)
            user32.FillRect(hdc, ctypes.byref(client), background)
            gdi32.DeleteObject(background)
            gdi32.SetBkMode(hdc, TRANSPARENT)

            if self._hbitmap and self.result and self.result.ok:
                self._draw_bitmap(hdc, client)
            else:
                self._draw_message(hdc, client)
            self._draw_overlay(hdc, client)
        finally:
            user32.EndPaint(self.hwnd, ctypes.byref(ps))

    def _draw_bitmap(self, hdc: int, client: RECT) -> None:
        assert self.result is not None
        width = self.result.width
        height = self.result.height
        content_top = INFO_BAR_HEIGHT
        content_bottom = max(content_top + 1, client.bottom - HINT_BAR_HEIGHT)
        viewport = RECT(client.left, content_top, client.right, content_bottom)
        x, y = self._bitmap_origin(viewport)
        dest_x, dest_y, src_x, src_y, blit_width, blit_height = _visible_blit_rect(
            x,
            y,
            width,
            height,
            viewport,
        )
        if blit_width <= 0 or blit_height <= 0:
            return

        memory_dc = gdi32.CreateCompatibleDC(hdc)
        old_bitmap = gdi32.SelectObject(memory_dc, self._hbitmap)
        gdi32.BitBlt(hdc, dest_x, dest_y, blit_width, blit_height, memory_dc, src_x, src_y, SRCCOPY)
        gdi32.SelectObject(memory_dc, old_bitmap)
        gdi32.DeleteDC(memory_dc)

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
        return True

    def _can_pan(self) -> bool:
        if not self.hwnd or not self._pan_enabled or self.result is None or not self.result.ok:
            return False
        viewport = self._image_viewport()
        return self.result.width > _rect_width(viewport) or self.result.height > _rect_height(viewport)

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

    def _clamp_pan(self) -> None:
        if self.result is None or not self.result.ok or not self.hwnd:
            return
        viewport = self._image_viewport()
        self._pan_x, self._pan_y = _clamped_pan(
            self._pan_x,
            self._pan_y,
            self.result.width,
            self.result.height,
            viewport,
        )

    def _bitmap_origin(self, viewport: RECT) -> tuple[int, int]:
        assert self.result is not None
        centered_x = viewport.left + (_rect_width(viewport) - self.result.width) // 2
        centered_y = viewport.top + (_rect_height(viewport) - self.result.height) // 2
        if self._pan_enabled:
            self._clamp_pan()
            return centered_x + self._pan_x, centered_y + self._pan_y
        return centered_x, centered_y

    def _image_viewport(self) -> RECT:
        client = self._client_rect()
        content_top = client.top + INFO_BAR_HEIGHT
        content_bottom = max(content_top + 1, client.bottom - HINT_BAR_HEIGHT)
        return RECT(client.left, content_top, client.right, content_bottom)

    def _draw_message(self, hdc: int, client: RECT) -> None:
        font = gdi32.GetStockObject(DEFAULT_GUI_FONT)
        old_font = gdi32.SelectObject(hdc, font)
        gdi32.SetTextColor(hdc, 0xFFFFFF)
        if self.image_file is None:
            text = "\u753b\u50cf\u3092\u9078\u629e\u3057\u3066\u304f\u3060\u3055\u3044"
        elif self.result is None:
            text = "\u30d7\u30ec\u30d3\u30e5\u30fc\u8aad\u8fbc\u4e2d..."
        else:
            text = "\u30d7\u30ec\u30d3\u30e5\u30fc\u3067\u304d\u307e\u305b\u3093"
        content = RECT(client.left, client.top + INFO_BAR_HEIGHT, client.right, max(client.top + INFO_BAR_HEIGHT, client.bottom - HINT_BAR_HEIGHT))
        user32.DrawTextW(hdc, text, -1, ctypes.byref(content), DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        gdi32.SelectObject(hdc, old_font)

    def _draw_overlay(self, hdc: int, client: RECT) -> None:
        top_rect = RECT(client.left, client.top, client.right, client.top + INFO_BAR_HEIGHT)
        bottom_rect = RECT(client.left, max(client.top + INFO_BAR_HEIGHT, client.bottom - HINT_BAR_HEIGHT), client.right, client.bottom)
        brush = _solid_brush(0x181818)
        user32.FillRect(hdc, ctypes.byref(top_rect), brush)
        user32.FillRect(hdc, ctypes.byref(bottom_rect), brush)
        gdi32.DeleteObject(brush)

        font = gdi32.GetStockObject(DEFAULT_GUI_FONT)
        old_font = gdi32.SelectObject(hdc, font)
        gdi32.SetTextColor(hdc, 0xFFFFFF)

        file_name = self.image_file.name if self.image_file is not None else ""
        client_width = max(0, client.right - client.left)
        position_width = min(
            max(70, _text_width(hdc, self.position_text) + OVERLAY_PADDING),
            max(70, client_width // 3),
        )
        position_left = max(client.left + OVERLAY_PADDING, client.right - OVERLAY_PADDING - position_width)
        zoom_width = 0
        zoom_left = position_left
        if self.zoom_text:
            zoom_width = min(
                max(54, _text_width(hdc, self.zoom_text) + OVERLAY_PADDING),
                max(54, client_width // 3),
            )
            zoom_left = max(client.left + OVERLAY_PADDING, position_left - 10 - zoom_width)
        name_rect = RECT(
            client.left + OVERLAY_PADDING,
            client.top,
            max(client.left + OVERLAY_PADDING, (zoom_left if self.zoom_text else position_left) - 14),
            client.top + INFO_BAR_HEIGHT,
        )
        user32.DrawTextW(
            hdc,
            file_name,
            -1,
            ctypes.byref(name_rect),
            DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX,
        )

        position_rect = RECT(
            position_left,
            client.top,
            client.right - OVERLAY_PADDING,
            client.top + INFO_BAR_HEIGHT,
        )
        user32.DrawTextW(
            hdc,
            self.position_text,
            -1,
            ctypes.byref(position_rect),
            DT_RIGHT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX,
        )

        if self.zoom_text:
            zoom_rect = RECT(
                zoom_left,
                client.top,
                max(zoom_left, zoom_left + zoom_width),
                client.top + INFO_BAR_HEIGHT,
            )
            gdi32.SetTextColor(hdc, 0xD8D8D8)
            user32.DrawTextW(
                hdc,
                self.zoom_text,
                -1,
                ctypes.byref(zoom_rect),
                DT_RIGHT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX,
            )
            gdi32.SetTextColor(hdc, 0xFFFFFF)

        hint_rect = RECT(client.left + OVERLAY_PADDING, bottom_rect.top, client.right - OVERLAY_PADDING, bottom_rect.bottom)
        bottom_text = self.feedback_text or self.hint_text
        gdi32.SetTextColor(hdc, 0xFFFFFF if self.feedback_text else 0xD8D8D8)
        user32.DrawTextW(
            hdc,
            bottom_text,
            -1,
            ctypes.byref(hint_rect),
            DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX,
        )
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

    def _require_window(self) -> None:
        if not self.hwnd:
            raise RuntimeError("Fullscreen preview has not been created.")


def _register_fullscreen_class() -> None:
    global _class_registered, _fullscreen_proc_ref
    if _class_registered:
        return

    hinstance = kernel32.GetModuleHandleW(None)
    _fullscreen_proc_ref = WNDPROC(_fullscreen_proc)
    wndclass = WNDCLASSW(
        style=CS_DBLCLKS,
        lpfnWndProc=_fullscreen_proc_ref,
        cbClsExtra=0,
        cbWndExtra=0,
        hInstance=hinstance,
        hIcon=None,
        hCursor=user32.LoadCursorW(None, ctypes.cast(ctypes.c_void_p(IDC_ARROW), wintypes.LPCWSTR)),
        hbrBackground=wintypes.HBRUSH(4),
        lpszMenuName=None,
        lpszClassName=CLASS_NAME,
    )

    atom = user32.RegisterClassW(ctypes.byref(wndclass))
    if not atom:
        raise ctypes.WinError()
    _class_registered = True


def _fullscreen_proc(hwnd: int, message: int, w_param: int, l_param: int) -> int:
    preview = _fullscreen_instances.get(int(hwnd))
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


def _shift_pressed() -> bool:
    return bool(user32.GetKeyState(VK_SHIFT) & 0x8000)


def _ctrl_pressed() -> bool:
    return bool(user32.GetKeyState(VK_CONTROL) & 0x8000)


def _alt_pressed() -> bool:
    return bool(user32.GetKeyState(VK_MENU) & 0x8000)


def _rect_width(rect: RECT) -> int:
    return max(0, int(rect.right - rect.left))


def _rect_height(rect: RECT) -> int:
    return max(0, int(rect.bottom - rect.top))


def _clamped_pan(pan_x: int, pan_y: int, image_width: int, image_height: int, viewport: RECT) -> tuple[int, int]:
    return (
        _clamped_axis_pan(pan_x, image_width, _rect_width(viewport)),
        _clamped_axis_pan(pan_y, image_height, _rect_height(viewport)),
    )


def _clamped_axis_pan(pan: int, image_size: int, viewport_size: int) -> int:
    if image_size <= viewport_size:
        return 0
    limit = (image_size - viewport_size) // 2
    return max(-limit, min(limit, pan))


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


def _text_width(hdc: int, text: str) -> int:
    if not text:
        return 0
    size = SIZE()
    if not gdi32.GetTextExtentPoint32W(hdc, text, len(text), ctypes.byref(size)):
        return len(text) * 8
    return max(0, int(size.cx))

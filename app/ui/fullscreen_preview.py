from __future__ import annotations

import ctypes
from pathlib import Path

from ctypes import wintypes

from app.core.image_scanner import ImageFile
from app.core.preview_renderer import PreviewResult

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

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
user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
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
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]

WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WM_ERASEBKGND = 0x0014
WM_KEYDOWN = 0x0100

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
SW_HIDE = 0
SW_SHOW = 5
SWP_SHOWWINDOW = 0x0040
TRANSPARENT = 1
DEFAULT_GUI_FONT = 17
IDC_ARROW = 32512
SM_CXSCREEN = 0
SM_CYSCREEN = 1
VK_ESCAPE = 0x1B
VK_LEFT = 0x25
VK_RIGHT = 0x27

CLASS_NAME = "FastImageViewerFullscreenPreview"
INFO_BAR_HEIGHT = 52
HINT_BAR_HEIGHT = 34
OVERLAY_PADDING = 18
FULLSCREEN_HINT = "\u2190 \u2192 \u79fb\u52d5 / Esc \u623b\u308b"


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


_fullscreen_proc_ref: WNDPROC | None = None
_fullscreen_instances: dict[int, FullscreenPreview] = {}
_class_registered = False


class FullscreenPreview:
    def __init__(self) -> None:
        self.hwnd: int | None = None
        self.image_file: ImageFile | None = None
        self.result: PreviewResult | None = None
        self.position_text = ""
        self.hint_text = FULLSCREEN_HINT
        self.visible = False
        self.on_close = None
        self.on_previous = None
        self.on_next = None
        self._hbitmap: int | None = None
        self._loaded_path: Path | None = None

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
        _fullscreen_instances[self.hwnd] = self
        return self.hwnd

    def show_loading(self, image_file: ImageFile, position_text: str = "") -> None:
        self._require_window()
        self.visible = True
        self.image_file = image_file
        self.position_text = position_text
        self.result = None
        self._clear_bitmap()
        width, height = self._screen_size()
        user32.SetWindowPos(self.hwnd, wintypes.HWND(-1), 0, 0, width, height, SWP_SHOWWINDOW)
        user32.ShowWindow(self.hwnd, SW_SHOW)
        user32.SetForegroundWindow(self.hwnd)
        user32.SetFocus(self.hwnd)
        self.invalidate()
        user32.UpdateWindow(self.hwnd)

    def set_result(self, image_file: ImageFile, result: PreviewResult) -> None:
        if self.image_file is None or self.image_file.path != image_file.path:
            return
        self.result = result
        self._load_bitmap(result.cache_path if result.ok else None)
        self.invalidate()

    def hide(self) -> None:
        if not self.hwnd:
            return
        self.visible = False
        self.image_file = None
        self.result = None
        self.position_text = ""
        self._clear_bitmap()
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
        self._clear_bitmap()
        if self.hwnd:
            _fullscreen_instances.pop(self.hwnd, None)
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None

    def handle_message(self, hwnd: int, message: int, w_param: int, l_param: int) -> int | None:
        if message == WM_ERASEBKGND:
            return 1
        if message == WM_KEYDOWN:
            key = int(w_param)
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
        if message == WM_PAINT:
            self._paint()
            return 0
        if message == WM_DESTROY:
            self._clear_bitmap()
            _fullscreen_instances.pop(int(hwnd), None)
            self.hwnd = None
            return 0
        return None

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
        x = max(0, (client.right - client.left - width) // 2)
        y = max(content_top, content_top + (content_bottom - content_top - height) // 2)

        memory_dc = gdi32.CreateCompatibleDC(hdc)
        old_bitmap = gdi32.SelectObject(memory_dc, self._hbitmap)
        gdi32.BitBlt(hdc, x, y, width, height, memory_dc, 0, 0, SRCCOPY)
        gdi32.SelectObject(memory_dc, old_bitmap)
        gdi32.DeleteDC(memory_dc)

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
        name_rect = RECT(
            client.left + OVERLAY_PADDING,
            client.top,
            max(client.left + OVERLAY_PADDING, client.right - 140),
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
            max(client.left + OVERLAY_PADDING, client.right - 130),
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

        hint_rect = RECT(client.left + OVERLAY_PADDING, bottom_rect.top, client.right - OVERLAY_PADDING, bottom_rect.bottom)
        gdi32.SetTextColor(hdc, 0xD8D8D8)
        user32.DrawTextW(
            hdc,
            self.hint_text,
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
            str(cache_path),
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

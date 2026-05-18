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
WM_SIZE = 0x0005
WM_PAINT = 0x000F
WM_ERASEBKGND = 0x0014
WM_LBUTTONDBLCLK = 0x0203

WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000

CS_DBLCLKS = 0x0008
IMAGE_BITMAP = 0
LR_LOADFROMFILE = 0x0010
LR_CREATEDIBSECTION = 0x2000
SRCCOPY = 0x00CC0020

DT_CENTER = 0x00000001
DT_SINGLELINE = 0x00000020
DT_VCENTER = 0x00000004
DT_NOPREFIX = 0x00000800

TRANSPARENT = 1
DEFAULT_GUI_FONT = 17
IDC_ARROW = 32512
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
        self._hbitmap: int | None = None
        self._loaded_path: Path | None = None

    def create(self, parent_hwnd: int) -> int:
        _register_preview_class()
        hinstance = kernel32.GetModuleHandleW(None)
        hwnd = user32.CreateWindowExW(
            0,
            CLASS_NAME,
            "",
            WS_CHILD | WS_VISIBLE | WS_BORDER,
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
        self._clear_bitmap()
        self.invalidate()

    def set_result(self, image_file: ImageFile, result: PreviewResult) -> None:
        if self.image_file is None or self.image_file.path != image_file.path:
            return
        self.result = result
        self._load_bitmap(result.cache_path if result.ok else None)
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
        self._clear_bitmap()
        self.invalidate()

    def invalidate(self) -> None:
        if self.hwnd:
            user32.InvalidateRect(self.hwnd, None, True)

    def destroy(self) -> None:
        self._clear_bitmap()
        if self.hwnd:
            _preview_instances.pop(self.hwnd, None)
            self.hwnd = None

    def handle_message(self, hwnd: int, message: int, w_param: int, l_param: int) -> int | None:
        if message == WM_ERASEBKGND:
            return 1
        if message == WM_SIZE:
            self.invalidate()
            return 0
        if message == WM_PAINT:
            self._paint()
            return 0
        if message == WM_LBUTTONDBLCLK:
            if self.on_activated is not None:
                self.on_activated()
            return 0
        if message == WM_DESTROY:
            self.destroy()
            return 0
        return None

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
            else:
                self._draw_message(hdc, client)
        finally:
            user32.EndPaint(self.hwnd, ctypes.byref(ps))

    def _draw_bitmap(self, hdc: int, client: RECT) -> None:
        assert self.result is not None
        width = self.result.width
        height = self.result.height
        x = max(0, (client.right - client.left - width) // 2)
        y = max(0, (client.bottom - client.top - height) // 2)

        memory_dc = gdi32.CreateCompatibleDC(hdc)
        old_bitmap = gdi32.SelectObject(memory_dc, self._hbitmap)
        gdi32.BitBlt(hdc, x, y, width, height, memory_dc, 0, 0, SRCCOPY)
        gdi32.SelectObject(memory_dc, old_bitmap)
        gdi32.DeleteDC(memory_dc)

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

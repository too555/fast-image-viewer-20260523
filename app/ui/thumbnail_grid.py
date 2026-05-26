from __future__ import annotations

import ctypes
import time
from collections import OrderedDict
from ctypes import wintypes
from math import ceil
from pathlib import Path

from app.core.image_scanner import ImageFile
from app.core.thumbnail_cache import THUMBNAIL_SIZE
from app.utils.long_path import filesystem_path, path_exists

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
user32.SetScrollInfo.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p, wintypes.BOOL]
user32.SetScrollInfo.restype = ctypes.c_int
user32.GetScrollInfo.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
user32.GetScrollInfo.restype = wintypes.BOOL
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
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
gdi32.CreatePen.restype = wintypes.HGDIOBJ
gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.GetStockObject.argtypes = [ctypes.c_int]
gdi32.GetStockObject.restype = ctypes.c_void_p
gdi32.Rectangle.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]

WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_PAINT = 0x000F
WM_ERASEBKGND = 0x0014
WM_VSCROLL = 0x0115
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_MOUSEWHEEL = 0x020A
WM_DROPFILES = 0x0233

WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_VSCROLL = 0x00200000
WS_BORDER = 0x00800000
WS_TABSTOP = 0x00010000

SB_VERT = 1
SB_LINEUP = 0
SB_LINEDOWN = 1
SB_PAGEUP = 2
SB_PAGEDOWN = 3
SB_THUMBTRACK = 5
SB_TOP = 6
SB_BOTTOM = 7

SIF_RANGE = 0x0001
SIF_PAGE = 0x0002
SIF_POS = 0x0004
SIF_TRACKPOS = 0x0010
SIF_ALL = SIF_RANGE | SIF_PAGE | SIF_POS | SIF_TRACKPOS

CS_DBLCLKS = 0x0008

IMAGE_BITMAP = 0
LR_LOADFROMFILE = 0x0010
LR_CREATEDIBSECTION = 0x2000
SRCCOPY = 0x00CC0020

DT_CENTER = 0x00000001
DT_WORDBREAK = 0x00000010
DT_SINGLELINE = 0x00000020
DT_VCENTER = 0x00000004
DT_END_ELLIPSIS = 0x00008000
DT_NOPREFIX = 0x00000800

TRANSPARENT = 1
DEFAULT_GUI_FONT = 17
NULL_BRUSH = 5
PS_SOLID = 0
IDC_ARROW = 32512
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

CELL_PADDING = 14
NAME_HEIGHT = 38
MAX_BITMAP_CACHE = 128
PREFETCH_EXTRA_ROWS = 4
BITMAP_CACHE_EXTRA_ROWS = 4
CLASS_NAME = "FastImageViewerThumbnailGrid"


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


class SCROLLINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("fMask", wintypes.UINT),
        ("nMin", ctypes.c_int),
        ("nMax", ctypes.c_int),
        ("nPage", wintypes.UINT),
        ("nPos", ctypes.c_int),
        ("nTrackPos", ctypes.c_int),
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


_grid_proc_ref: WNDPROC | None = None
_grid_instances: dict[int, ThumbnailGrid] = {}
_class_registered = False


class ThumbnailGrid:
    def __init__(self) -> None:
        self.hwnd: int | None = None
        self.items: list[ImageFile] = []
        self.thumbnails: dict[int, Path] = {}
        self.failed_indexes: set[int] = set()
        self.selected_index: int | None = None
        self.on_selection_changed = None
        self.on_item_activated = None
        self.on_files_dropped = None
        self.on_visible_range_changed = None
        self.on_context_menu = None
        self.on_copy_image_path = None
        self.on_copy_folder_path = None
        self.on_previous = None
        self.on_next = None
        self.on_parent_folder = None
        self.on_previous_folder = None
        self.on_next_folder = None
        self.on_scroll_started = None
        self.on_paint_completed = None
        self.thumbnail_size = THUMBNAIL_SIZE
        self.scroll_y = 0
        self._bitmap_cache: OrderedDict[Path, int] = OrderedDict()

    def create(self, parent_hwnd: int) -> int:
        _register_grid_class()
        hinstance = kernel32.GetModuleHandleW(None)
        hwnd = user32.CreateWindowExW(
            0,
            CLASS_NAME,
            "",
            WS_CHILD | WS_VISIBLE | WS_BORDER | WS_VSCROLL | WS_TABSTOP,
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
        _grid_instances[self.hwnd] = self
        return self.hwnd

    def move(self, x: int, y: int, width: int, height: int) -> None:
        if not self.hwnd:
            return
        user32.MoveWindow(self.hwnd, x, y, width, height, True)
        self._update_scrollbar()
        self._notify_visible_range_changed()

    def set_items(self, items: list[ImageFile]) -> None:
        self.items = items
        self.thumbnails.clear()
        self.failed_indexes.clear()
        self.selected_index = None
        self.scroll_y = 0
        self._clear_bitmap_cache()
        self._update_scrollbar()
        self._notify_visible_range_changed()
        self.invalidate()

    def set_thumbnail_size(self, thumbnail_size: int) -> None:
        if thumbnail_size <= 0:
            raise ValueError("サムネイルサイズは正の値である必要があります")
        if thumbnail_size == self.thumbnail_size:
            return

        self.thumbnail_size = thumbnail_size
        self.thumbnails.clear()
        self.failed_indexes.clear()
        self._clear_bitmap_cache()
        if self.hwnd:
            if self.selected_index is not None and self.selected_index >= len(self.items):
                self.selected_index = None
            if self.selected_index is not None and self.items:
                self._ensure_index_visible(self.selected_index)
            else:
                self.scroll_y = max(0, min(self.scroll_y, self._max_scroll()))
            self._update_scrollbar()
            self._notify_visible_range_changed()
        self.invalidate()

    def set_thumbnail(self, index: int, cache_path: Path | None, failed: bool = False) -> bool:
        if index < 0 or index >= len(self.items):
            return False

        old_cache_path = self.thumbnails.get(index)
        old_failed = index in self.failed_indexes
        if cache_path is not None:
            self.thumbnails[index] = cache_path
            self.failed_indexes.discard(index)
        elif failed:
            self.thumbnails.pop(index, None)
            self.failed_indexes.add(index)
        else:
            return False

        if old_cache_path == self.thumbnails.get(index) and old_failed == (index in self.failed_indexes):
            return False

        self._invalidate_item(index)
        return True

    def invalidate(self) -> None:
        if self.hwnd:
            user32.InvalidateRect(self.hwnd, None, True)

    def _invalidate_item(self, index: int) -> None:
        if not self.hwnd:
            return
        if not self._is_index_near_visible(index, extra_rows=1):
            return
        rect = self._item_rect(index)
        if rect is None:
            return
        user32.InvalidateRect(self.hwnd, ctypes.byref(rect), False)

    def destroy(self) -> None:
        self._clear_bitmap_cache()
        if self.hwnd:
            shell32.DragAcceptFiles(self.hwnd, False)
            _grid_instances.pop(self.hwnd, None)
            self.hwnd = None

    def select_relative(self, delta: int) -> bool:
        if not self.items:
            return False
        if self.selected_index is None:
            new_index = 0
        else:
            new_index = max(0, min(len(self.items) - 1, self.selected_index + delta))
        return self.select_index(new_index)

    def select_page(self, direction: int) -> bool:
        if direction == 0:
            return False
        delta = self._page_item_count()
        if direction < 0:
            delta *= -1
        return self.select_relative(delta)

    def select_first(self) -> bool:
        if not self.items:
            return False
        return self.select_index(0)

    def select_last(self) -> bool:
        if not self.items:
            return False
        return self.select_index(len(self.items) - 1)

    def select_index(self, index: int) -> bool:
        if index < 0 or index >= len(self.items):
            return False
        previous_index = self.selected_index
        previous_scroll_y = self.scroll_y
        changed = previous_index != index
        self.selected_index = index
        self._ensure_index_visible(index)
        if self.scroll_y == previous_scroll_y:
            if previous_index is not None and previous_index != index:
                self._invalidate_item(previous_index)
            if changed:
                self._invalidate_item(index)
        if changed and self.on_selection_changed is not None:
            self.on_selection_changed(index, self.items[index])
        return changed

    def handle_message(self, hwnd: int, message: int, w_param: int, l_param: int) -> int | None:
        if message == WM_ERASEBKGND:
            return 1
        if message == WM_SIZE:
            self._update_scrollbar()
            self._notify_visible_range_changed()
            self.invalidate()
            return 0
        if message == WM_VSCROLL:
            self._handle_vscroll(int(w_param) & 0xFFFF)
            return 0
        if message == WM_SYSKEYDOWN:
            if self._handle_folder_navigation_shortcut(int(w_param)):
                return 0
        if message == WM_KEYDOWN:
            if self._handle_copy_shortcut(int(w_param)):
                return 0
            if int(w_param) == VK_LEFT:
                self.select_relative(-1)
                return 0
            if int(w_param) == VK_RIGHT:
                self.select_relative(1)
                return 0
            if int(w_param) == VK_HOME:
                self.select_first()
                return 0
            if int(w_param) == VK_END:
                self.select_last()
                return 0
            if int(w_param) == VK_PRIOR:
                self.select_page(-1)
                return 0
            if int(w_param) == VK_NEXT:
                self.select_page(1)
                return 0
            if int(w_param) == VK_RETURN:
                self._activate_selected()
                return 0
            if int(w_param) == VK_SPACE:
                self._navigate_by_input(-1 if _shift_pressed() else 1)
                return 0
        if message == WM_LBUTTONDOWN:
            user32.SetFocus(self.hwnd)
            self._handle_click(_signed_loword(int(l_param)), _signed_hiword(int(l_param)))
            return 0
        if message == WM_LBUTTONDBLCLK:
            user32.SetFocus(self.hwnd)
            self._handle_double_click(_signed_loword(int(l_param)), _signed_hiword(int(l_param)))
            return 0
        if message == WM_RBUTTONUP:
            user32.SetFocus(self.hwnd)
            self._handle_context_menu(_signed_loword(int(l_param)), _signed_hiword(int(l_param)))
            return 0
        if message == WM_MOUSEWHEEL:
            delta = _signed_hiword(int(w_param))
            if delta > 0:
                self._navigate_by_input(-1)
            elif delta < 0:
                self._navigate_by_input(1)
            return 0
        if message == WM_DROPFILES:
            if self.on_files_dropped is not None:
                self.on_files_dropped(int(w_param))
            return 0
        if message == WM_PAINT:
            self._paint()
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

    def _paint(self) -> None:
        if not self.hwnd:
            return

        paint_started_at = time.perf_counter()
        ps = PAINTSTRUCT()
        hdc = user32.BeginPaint(self.hwnd, ctypes.byref(ps))
        try:
            client = self._client_rect()
            paint_rect = ps.rcPaint
            background = _solid_brush(0xF4F4F4)
            user32.FillRect(hdc, ctypes.byref(paint_rect), background)
            gdi32.DeleteObject(background)
            gdi32.SetBkMode(hdc, TRANSPARENT)
            font = gdi32.GetStockObject(DEFAULT_GUI_FONT)
            old_font = gdi32.SelectObject(hdc, font)

            if not self.items:
                self._draw_empty_state(hdc, client)
            else:
                self._draw_items(hdc, client, paint_rect)

            gdi32.SelectObject(hdc, old_font)
        finally:
            user32.EndPaint(self.hwnd, ctypes.byref(ps))
        if self.on_paint_completed is not None:
            start, end = self.visible_index_range()
            self.on_paint_completed((time.perf_counter() - paint_started_at) * 1000.0, max(0, end - start))

    def _draw_empty_state(self, hdc: int, client: RECT) -> None:
        text_rect = RECT(0, 0, client.right - client.left, client.bottom - client.top)
        gdi32.SetTextColor(hdc, 0x666666)
        user32.DrawTextW(hdc, "画像が見つかりません", -1, ctypes.byref(text_rect), DT_CENTER | DT_VCENTER | DT_SINGLELINE)

    def _draw_items(self, hdc: int, client: RECT, paint_rect: RECT) -> None:
        width = max(1, client.right - client.left)
        height = max(1, client.bottom - client.top)
        columns = self._column_count(width)
        cell_width = self._cell_width()
        cell_height = self._cell_height()
        first_row = max(0, self.scroll_y // cell_height)
        last_row = min(self._row_count(columns), ceil((self.scroll_y + height) / cell_height) + 1)

        for row in range(first_row, last_row):
            for column in range(columns):
                index = row * columns + column
                if index >= len(self.items):
                    break
                x = column * cell_width + CELL_PADDING
                y = row * cell_height - self.scroll_y + CELL_PADDING
                item_rect = self._item_rect_at(x, y)
                if not _rects_intersect(item_rect, paint_rect):
                    continue
                self._draw_item(hdc, index, x, y)
        self._trim_bitmap_cache_to_visible()

    def _draw_item(self, hdc: int, index: int, x: int, y: int) -> None:
        thumbnail_size = self.thumbnail_size
        cell_width = self._cell_width()
        cell_height = self._cell_height()
        thumb_left = x + (cell_width - CELL_PADDING * 2 - thumbnail_size) // 2
        thumb_top = y
        box_left = thumb_left - 4
        box_top = thumb_top - 4
        box_right = thumb_left + thumbnail_size + 4
        box_bottom = thumb_top + thumbnail_size + 4

        cell_brush = _solid_brush(0xFFFFFF)
        rect = RECT(x - 4, y - 8, x + cell_width - CELL_PADDING * 2 + 4, y + cell_height - CELL_PADDING)
        user32.FillRect(hdc, ctypes.byref(rect), cell_brush)
        gdi32.DeleteObject(cell_brush)
        if index == self.selected_index:
            self._draw_selection(hdc, rect)
        gdi32.Rectangle(hdc, box_left, box_top, box_right, box_bottom)

        cache_path = self.thumbnails.get(index)
        if cache_path is not None and path_exists(cache_path):
            self._draw_bitmap(hdc, cache_path, thumb_left, thumb_top)
        else:
            label = "失敗" if index in self.failed_indexes else "読込中"
            self._draw_placeholder(hdc, label, thumb_left, thumb_top)

        name_top = thumb_top + thumbnail_size + 10
        name_rect = RECT(x, name_top, x + cell_width - CELL_PADDING * 2, name_top + NAME_HEIGHT)
        gdi32.SetTextColor(hdc, 0x222222)
        user32.DrawTextW(
            hdc,
            self.items[index].name,
            -1,
            ctypes.byref(name_rect),
            DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX,
        )

    def _draw_bitmap(self, hdc: int, cache_path: Path, x: int, y: int) -> None:
        hbitmap = self._bitmap_for(cache_path)
        if not hbitmap:
            self._draw_placeholder(hdc, "失敗", x, y)
            return

        memory_dc = gdi32.CreateCompatibleDC(hdc)
        old_bitmap = gdi32.SelectObject(memory_dc, hbitmap)
        gdi32.BitBlt(hdc, x, y, self.thumbnail_size, self.thumbnail_size, memory_dc, 0, 0, SRCCOPY)
        gdi32.SelectObject(memory_dc, old_bitmap)
        gdi32.DeleteDC(memory_dc)

    def _draw_placeholder(self, hdc: int, label: str, x: int, y: int) -> None:
        rect = RECT(x, y, x + self.thumbnail_size, y + self.thumbnail_size)
        brush = _solid_brush(0xEAEAEA)
        user32.FillRect(hdc, ctypes.byref(rect), brush)
        gdi32.DeleteObject(brush)
        gdi32.SetTextColor(hdc, 0x777777)
        user32.DrawTextW(hdc, label, -1, ctypes.byref(rect), DT_CENTER | DT_VCENTER | DT_SINGLELINE)

    def _draw_selection(self, hdc: int, rect: RECT) -> None:
        pen = gdi32.CreatePen(PS_SOLID, 3, 0xD77800)
        old_pen = gdi32.SelectObject(hdc, pen)
        old_brush = gdi32.SelectObject(hdc, gdi32.GetStockObject(NULL_BRUSH))
        gdi32.Rectangle(hdc, rect.left + 1, rect.top + 1, rect.right - 1, rect.bottom - 1)
        gdi32.SelectObject(hdc, old_brush)
        gdi32.SelectObject(hdc, old_pen)
        gdi32.DeleteObject(pen)

    def _bitmap_for(self, cache_path: Path) -> int | None:
        hbitmap = self._bitmap_cache.get(cache_path)
        if hbitmap:
            self._bitmap_cache.move_to_end(cache_path)
            return hbitmap

        loaded = user32.LoadImageW(
            None,
            filesystem_path(cache_path),
            IMAGE_BITMAP,
            self.thumbnail_size,
            self.thumbnail_size,
            LR_LOADFROMFILE | LR_CREATEDIBSECTION,
        )
        if not loaded:
            return None

        self._bitmap_cache[cache_path] = int(loaded)
        self._trim_bitmap_cache_to_limit()
        return int(loaded)

    def _clear_bitmap_cache(self) -> None:
        for hbitmap in self._bitmap_cache.values():
            gdi32.DeleteObject(hbitmap)
        self._bitmap_cache.clear()

    def _trim_bitmap_cache_to_visible(self, extra_rows: int = BITMAP_CACHE_EXTRA_ROWS) -> None:
        if not self._bitmap_cache:
            return
        if not self.items:
            self._clear_bitmap_cache()
            return

        start, end = self.visible_index_range(extra_rows=extra_rows)
        keep_paths = {
            cache_path
            for index in range(start, end)
            if (cache_path := self.thumbnails.get(index)) is not None
        }
        if self.selected_index is not None:
            selected_cache_path = self.thumbnails.get(self.selected_index)
            if selected_cache_path is not None:
                keep_paths.add(selected_cache_path)

        for cache_path in list(self._bitmap_cache.keys()):
            if cache_path in keep_paths:
                continue
            hbitmap = self._bitmap_cache.pop(cache_path)
            gdi32.DeleteObject(hbitmap)
        self._trim_bitmap_cache_to_limit()

    def _trim_bitmap_cache_to_limit(self) -> None:
        limit = self._bitmap_cache_limit()
        while len(self._bitmap_cache) > limit:
            _, old_hbitmap = self._bitmap_cache.popitem(last=False)
            gdi32.DeleteObject(old_hbitmap)

    def _handle_vscroll(self, request: int) -> None:
        if request == SB_LINEUP:
            self._set_scroll(self.scroll_y - 40)
        elif request == SB_LINEDOWN:
            self._set_scroll(self.scroll_y + 40)
        elif request == SB_PAGEUP:
            self._set_scroll(self.scroll_y - self._client_height())
        elif request == SB_PAGEDOWN:
            self._set_scroll(self.scroll_y + self._client_height())
        elif request == SB_THUMBTRACK:
            info = SCROLLINFO(
                cbSize=ctypes.sizeof(SCROLLINFO),
                fMask=SIF_TRACKPOS,
                nMin=0,
                nMax=0,
                nPage=0,
                nPos=0,
                nTrackPos=0,
            )
            if user32.GetScrollInfo(self.hwnd, SB_VERT, ctypes.byref(info)):
                self._set_scroll(info.nTrackPos)
        elif request == SB_TOP:
            self._set_scroll(0)
        elif request == SB_BOTTOM:
            self._set_scroll(self._max_scroll())

    def _handle_click(self, x: int, y: int) -> None:
        index = self._index_at_point(x, y)
        if index is None:
            return

        self.select_index(index)

    def _handle_double_click(self, x: int, y: int) -> None:
        index = self._index_at_point(x, y)
        if index is None:
            return

        self.select_index(index)
        self._activate_selected()

    def _handle_context_menu(self, x: int, y: int) -> None:
        if self.on_context_menu is None:
            return
        index = self._index_at_point(x, y)
        image_file = self.items[index] if index is not None else None
        self.on_context_menu(self.hwnd, x, y, image_file)

    def _index_at_point(self, x: int, y: int) -> int | None:
        width = self._client_width()
        columns = self._column_count(width)
        content_y = y + self.scroll_y
        if x < 0 or content_y < 0:
            return None

        column = x // self._cell_width()
        row = content_y // self._cell_height()
        if column >= columns:
            return None

        index = row * columns + column
        if index < 0 or index >= len(self.items):
            return None

        return index

    def _activate_selected(self) -> None:
        if self.selected_index is None or self.selected_index >= len(self.items):
            return
        if self.on_item_activated is not None:
            self.on_item_activated(self.selected_index, self.items[self.selected_index])

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

    def _navigate_by_input(self, delta: int) -> None:
        if delta < 0 and self.on_previous is not None:
            self.on_previous()
            return
        if delta > 0 and self.on_next is not None:
            self.on_next()
            return
        self.select_relative(delta)

    def _item_rect(self, index: int) -> RECT | None:
        if index < 0 or index >= len(self.items):
            return None
        columns = self._column_count(self._client_width())
        row = index // columns
        column = index % columns
        x = column * self._cell_width() + CELL_PADDING
        y = row * self._cell_height() - self.scroll_y + CELL_PADDING
        return self._item_rect_at(x, y)

    def _item_rect_at(self, x: int, y: int) -> RECT:
        cell_width = self._cell_width()
        cell_height = self._cell_height()
        return RECT(
            x - 4,
            y - 8,
            x + cell_width - CELL_PADDING * 2 + 4,
            y + cell_height - CELL_PADDING,
        )

    def _ensure_index_visible(self, index: int) -> None:
        columns = self._column_count(self._client_width())
        row = index // columns
        item_top = row * self._cell_height()
        item_bottom = item_top + self._cell_height()
        if item_top < self.scroll_y:
            self._set_scroll(item_top)
        elif item_bottom > self.scroll_y + self._client_height():
            self._set_scroll(item_bottom - self._client_height())

    def _set_scroll(self, value: int) -> None:
        new_scroll = max(0, min(value, self._max_scroll()))
        if new_scroll == self.scroll_y:
            return
        if self.on_scroll_started is not None:
            self.on_scroll_started()
        self.scroll_y = new_scroll
        self._update_scrollbar()
        self._notify_visible_range_changed()
        self._trim_bitmap_cache_to_visible()
        self.invalidate()

    def _update_scrollbar(self) -> None:
        if not self.hwnd:
            return
        height = self._client_height()
        content_height = self._content_height()
        self.scroll_y = max(0, min(self.scroll_y, self._max_scroll()))
        info = SCROLLINFO(
            cbSize=ctypes.sizeof(SCROLLINFO),
            fMask=SIF_RANGE | SIF_PAGE | SIF_POS,
            nMin=0,
            nMax=max(0, content_height - 1),
            nPage=max(1, height),
            nPos=self.scroll_y,
            nTrackPos=0,
        )
        user32.SetScrollInfo(self.hwnd, SB_VERT, ctypes.byref(info), True)

    def _content_height(self) -> int:
        width = max(1, self._client_width())
        return self._row_count(self._column_count(width)) * self._cell_height()

    def _max_scroll(self) -> int:
        return max(0, self._content_height() - self._client_height())

    def _row_count(self, columns: int) -> int:
        if not self.items:
            return 1
        return ceil(len(self.items) / columns)

    def _column_count(self, width: int) -> int:
        return max(1, width // self._cell_width())

    def _page_item_count(self) -> int:
        visible_rows = max(1, self._client_height() // self._cell_height())
        columns = self._column_count(self._client_width())
        return max(1, visible_rows * columns)

    def visible_index_range(self, extra_rows: int = 0) -> tuple[int, int]:
        if not self.items:
            return (0, 0)

        columns = self._column_count(self._client_width())
        cell_height = self._cell_height()
        first_row = max(0, self.scroll_y // cell_height - max(0, extra_rows))
        last_row = min(
            self._row_count(columns),
            ceil((self.scroll_y + self._client_height()) / cell_height) + max(0, extra_rows),
        )
        start = min(len(self.items), first_row * columns)
        end = min(len(self.items), max(start, last_row * columns))
        return (start, end)

    def _is_index_near_visible(self, index: int, extra_rows: int = 0) -> bool:
        start, end = self.visible_index_range(extra_rows=extra_rows)
        return start <= index < end

    def _cell_width(self) -> int:
        return self.thumbnail_size + CELL_PADDING * 2 + 12

    def _cell_height(self) -> int:
        return self.thumbnail_size + CELL_PADDING + NAME_HEIGHT + 22

    def _bitmap_cache_limit(self) -> int:
        if self.thumbnail_size >= 256:
            base_limit = 48
        elif self.thumbnail_size <= 64:
            base_limit = 192
        else:
            base_limit = MAX_BITMAP_CACHE

        start, end = self.visible_index_range(extra_rows=BITMAP_CACHE_EXTRA_ROWS)
        visible_limit = max(1, end - start)
        return max(24, min(base_limit, visible_limit))

    def _client_rect(self) -> RECT:
        rect = RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        return rect

    def _client_width(self) -> int:
        rect = self._client_rect()
        return max(1, rect.right - rect.left)

    def _client_height(self) -> int:
        rect = self._client_rect()
        return max(1, rect.bottom - rect.top)

    def _notify_visible_range_changed(self) -> None:
        if self.on_visible_range_changed is not None:
            start, end = self.visible_index_range(extra_rows=PREFETCH_EXTRA_ROWS)
            self.on_visible_range_changed(start, end)


def _register_grid_class() -> None:
    global _class_registered, _grid_proc_ref
    if _class_registered:
        return

    hinstance = kernel32.GetModuleHandleW(None)
    _grid_proc_ref = WNDPROC(_grid_proc)
    wndclass = WNDCLASSW(
        style=CS_DBLCLKS,
        lpfnWndProc=_grid_proc_ref,
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


def _grid_proc(hwnd: int, message: int, w_param: int, l_param: int) -> int:
    grid = _grid_instances.get(int(hwnd))
    if grid is not None:
        result = grid.handle_message(hwnd, message, w_param, l_param)
        if result is not None:
            return result
    return user32.DefWindowProcW(hwnd, message, w_param, l_param)


def _solid_brush(color_ref: int) -> int:
    return int(gdi32.CreateSolidBrush(color_ref))


def _rects_intersect(first: RECT, second: RECT) -> bool:
    return (
        first.left < second.right
        and first.right > second.left
        and first.top < second.bottom
        and first.bottom > second.top
    )


def _signed_hiword(value: int) -> int:
    hiword = (value >> 16) & 0xFFFF
    if hiword >= 0x8000:
        hiword -= 0x10000
    return hiword


def _signed_loword(value: int) -> int:
    loword = value & 0xFFFF
    if loword >= 0x8000:
        loword -= 0x10000
    return loword


def _shift_pressed() -> bool:
    return bool(user32.GetKeyState(VK_SHIFT) & 0x8000)


def _ctrl_pressed() -> bool:
    return bool(user32.GetKeyState(VK_CONTROL) & 0x8000)


def _alt_pressed() -> bool:
    return bool(user32.GetKeyState(VK_MENU) & 0x8000)

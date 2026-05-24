from __future__ import annotations

import ctypes
from ctypes import wintypes


if not hasattr(ctypes, "windll"):
    raise RuntimeError("このUIは現在Windowsのみ対応しています。")


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

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


WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_COMMAND = 0x0111
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

ES_MULTILINE = 0x0004
ES_AUTOVSCROLL = 0x0040
ES_READONLY = 0x0800
EM_SETSEL = 0x00B1

GWLP_WNDPROC = -4
DEFAULT_GUI_FONT = 17
IDC_ARROW = 32512
SW_SHOW = 5

CLASS_NAME = "FastImageViewerOperationGuideDialog"
TEXT_CONTROL_ID = 4001
CLOSE_BUTTON_ID = 4002

_dialog_proc_ref: WNDPROC | None = None
_class_registered = False
_instances: dict[int, "OperationGuideDialog"] = {}


class OperationGuideDialog:
    def __init__(self) -> None:
        self.hwnd: int | None = None
        self.text_hwnd: int | None = None
        self.close_button: int | None = None
        self._child_proc_ref: WNDPROC | None = None
        self._child_old_procs: dict[int, int] = {}

    def show(self, owner: int | None, title: str, text: str) -> None:
        if self.hwnd:
            user32.SetForegroundWindow(self.hwnd)
            if self.text_hwnd:
                user32.SetFocus(self.text_hwnd)
            return

        _register_dialog_class()
        hinstance = kernel32.GetModuleHandleW(None)
        hwnd = user32.CreateWindowExW(
            0,
            CLASS_NAME,
            title,
            WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_MINIMIZEBOX | WS_VISIBLE,
            120,
            120,
            620,
            460,
            owner,
            None,
            hinstance,
            None,
        )
        if not hwnd:
            raise ctypes.WinError()

        self.hwnd = int(hwnd)
        _instances[self.hwnd] = self
        self._create_controls(text)
        self._layout()
        user32.ShowWindow(self.hwnd, SW_SHOW)
        user32.UpdateWindow(self.hwnd)
        if self.text_hwnd:
            user32.SetFocus(self.text_hwnd)

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

        if message == WM_COMMAND:
            control_id = int(w_param) & 0xFFFF
            notification = (int(w_param) >> 16) & 0xFFFF
            if control_id == CLOSE_BUTTON_ID and notification == BN_CLICKED:
                self.destroy()
                return 0

        if message == WM_CLOSE:
            self.destroy()
            return 0

        if message == WM_DESTROY:
            self._restore_child_procs()
            _instances.pop(int(hwnd), None)
            if self.hwnd == int(hwnd):
                self.hwnd = None
            self.text_hwnd = None
            self.close_button = None
            return 0

        return None

    def _create_controls(self, text: str) -> None:
        if not self.hwnd:
            return
        hinstance = kernel32.GetModuleHandleW(None)
        font = gdi32.GetStockObject(DEFAULT_GUI_FONT)
        self.text_hwnd = int(
            user32.CreateWindowExW(
                0,
                "EDIT",
                text.replace("\n", "\r\n"),
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
        if not self.text_hwnd:
            raise ctypes.WinError()

        self.close_button = int(
            user32.CreateWindowExW(
                0,
                "BUTTON",
                "閉じる",
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
        if not self.close_button:
            raise ctypes.WinError()

        user32.SendMessageW(self.text_hwnd, WM_SETFONT, font, True)
        user32.SendMessageW(self.close_button, WM_SETFONT, font, True)
        user32.SendMessageW(self.text_hwnd, EM_SETSEL, 0, 0)
        self._subclass_child(self.text_hwnd)
        self._subclass_child(self.close_button)

    def _layout(self) -> None:
        if not self.hwnd or not self.text_hwnd or not self.close_button:
            return
        rect = RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        width = max(1, rect.right - rect.left)
        height = max(1, rect.bottom - rect.top)
        margin = 12
        button_width = 96
        button_height = 30
        gap = 10
        user32.MoveWindow(
            self.text_hwnd,
            margin,
            margin,
            max(1, width - margin * 2),
            max(1, height - margin * 2 - button_height - gap),
            True,
        )
        user32.MoveWindow(
            self.close_button,
            max(margin, width - margin - button_width),
            max(margin, height - margin - button_height),
            button_width,
            button_height,
            True,
        )

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

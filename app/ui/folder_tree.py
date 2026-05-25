from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path

from app.utils.long_path import display_path, filesystem_path, path_is_dir

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
comctl32 = ctypes.windll.comctl32

kernel32.GetLogicalDrives.argtypes = []
kernel32.GetLogicalDrives.restype = wintypes.DWORD
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
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.MoveWindow.argtypes = [
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.BOOL,
]
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t

WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000
WS_TABSTOP = 0x00010000
WS_VSCROLL = 0x00200000
WS_EX_CLIENTEDGE = 0x00000200

TVS_HASBUTTONS = 0x0001
TVS_HASLINES = 0x0002
TVS_LINESATROOT = 0x0004
TVS_SHOWSELALWAYS = 0x0020
TVS_DISABLEDRAGDROP = 0x0010
TVS_FULLROWSELECT = 0x1000

TV_FIRST = 0x1100
TVM_INSERTITEMW = TV_FIRST + 50
TVM_DELETEITEM = TV_FIRST + 1
TVM_GETNEXTITEM = TV_FIRST + 10
TVM_SETITEMW = TV_FIRST + 63

TVGN_NEXT = 1
TVGN_CHILD = 4

TVIF_TEXT = 0x0001
TVIF_CHILDREN = 0x0040

TVN_FIRST = -400
TVN_SELCHANGEDW = TVN_FIRST - 51
TVN_ITEMEXPANDINGW = TVN_FIRST - 54

ICC_TREEVIEW_CLASSES = 0x00000002
TREEVIEW_CLASS = "SysTreeView32"
LOADING_LABEL = "読み込み中..."
FILE_ATTRIBUTE_HIDDEN = 0x00000002
FILE_ATTRIBUTE_SYSTEM = 0x00000004
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400

_UINT_PTR_MASK = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1
TVI_ROOT = ctypes.c_void_p((-0x10000) & _UINT_PTR_MASK)
TVI_LAST = ctypes.c_void_p((-0x0FFFE) & _UINT_PTR_MASK)


class INITCOMMONCONTROLSEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("dwICC", wintypes.DWORD),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


class NMHDR(ctypes.Structure):
    _fields_ = [
        ("hwndFrom", wintypes.HWND),
        ("idFrom", ctypes.c_size_t),
        ("code", ctypes.c_int),
    ]


class TVITEMW(ctypes.Structure):
    _fields_ = [
        ("mask", wintypes.UINT),
        ("hItem", ctypes.c_void_p),
        ("state", wintypes.UINT),
        ("stateMask", wintypes.UINT),
        ("pszText", wintypes.LPWSTR),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("iSelectedImage", ctypes.c_int),
        ("cChildren", ctypes.c_int),
        ("lParam", wintypes.LPARAM),
    ]


class TVINSERTSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hParent", ctypes.c_void_p),
        ("hInsertAfter", ctypes.c_void_p),
        ("item", TVITEMW),
    ]


class NMTREEVIEWW(ctypes.Structure):
    _fields_ = [
        ("hdr", NMHDR),
        ("action", wintypes.UINT),
        ("itemOld", TVITEMW),
        ("itemNew", TVITEMW),
        ("ptDrag", POINT),
    ]


class FolderTree:
    def __init__(self) -> None:
        self.hwnd: int | None = None
        self.on_folder_selected = None
        self._item_paths: dict[int, Path] = {}
        self._loaded_items: set[int] = set()

    def create(self, parent_hwnd: int) -> int:
        self._init_common_controls()
        hinstance = kernel32.GetModuleHandleW(None)
        hwnd = user32.CreateWindowExW(
            WS_EX_CLIENTEDGE,
            TREEVIEW_CLASS,
            "",
            WS_CHILD
            | WS_VISIBLE
            | WS_BORDER
            | WS_TABSTOP
            | WS_VSCROLL
            | TVS_HASBUTTONS
            | TVS_HASLINES
            | TVS_LINESATROOT
            | TVS_SHOWSELALWAYS
            | TVS_DISABLEDRAGDROP
            | TVS_FULLROWSELECT,
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
        self._populate_roots()
        return self.hwnd

    def move(self, x: int, y: int, width: int, height: int) -> None:
        if self.hwnd:
            user32.MoveWindow(self.hwnd, x, y, width, height, True)

    def destroy(self) -> None:
        self._item_paths.clear()
        self._loaded_items.clear()
        if self.hwnd:
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None

    def handle_notify(self, l_param: int) -> bool:
        if not self.hwnd or not l_param:
            return False
        header = ctypes.cast(l_param, ctypes.POINTER(NMHDR)).contents
        if int(header.hwndFrom or 0) != self.hwnd:
            return False

        if header.code == TVN_ITEMEXPANDINGW:
            notification = ctypes.cast(l_param, ctypes.POINTER(NMTREEVIEWW)).contents
            item = _handle_to_int(notification.itemNew.hItem)
            if item:
                self._ensure_loaded(item)
            return True

        if header.code == TVN_SELCHANGEDW:
            notification = ctypes.cast(l_param, ctypes.POINTER(NMTREEVIEWW)).contents
            item = _handle_to_int(notification.itemNew.hItem)
            folder = self._item_paths.get(item)
            if folder is not None and self.on_folder_selected is not None:
                self.on_folder_selected(folder)
            return True

        return False

    def _populate_roots(self) -> None:
        if not self.hwnd:
            return
        for label, folder in _initial_tree_roots():
            self._add_path_item(0, label, folder, assume_children=True)

    def _ensure_loaded(self, item: int) -> None:
        if item in self._loaded_items:
            return
        folder = self._item_paths.get(item)
        if folder is None:
            return

        children = _child_folders(folder)
        self._delete_children(item)
        for child in children:
            self._add_path_item(item, _folder_label(child), child, assume_children=True)
        self._set_item_children(item, 1 if children else 0)
        self._loaded_items.add(item)

    def _add_path_item(self, parent: int, label: str, folder: Path, assume_children: bool) -> int:
        has_children = assume_children or _has_child_folder(folder)
        item = self._insert_item(parent, label, has_children=has_children)
        if item:
            self._item_paths[item] = display_path(folder)
            if has_children:
                self._insert_item(item, LOADING_LABEL, has_children=False)
        return item

    def _insert_item(self, parent: int, label: str, has_children: bool) -> int:
        if not self.hwnd:
            return 0
        text = ctypes.create_unicode_buffer(label)
        item = TVITEMW(
            mask=TVIF_TEXT | TVIF_CHILDREN,
            hItem=None,
            state=0,
            stateMask=0,
            pszText=ctypes.cast(text, wintypes.LPWSTR),
            cchTextMax=len(label) + 1,
            iImage=0,
            iSelectedImage=0,
            cChildren=1 if has_children else 0,
            lParam=0,
        )
        insert = TVINSERTSTRUCTW(
            hParent=ctypes.c_void_p(parent) if parent else TVI_ROOT,
            hInsertAfter=TVI_LAST,
            item=item,
        )
        result = user32.SendMessageW(self.hwnd, TVM_INSERTITEMW, 0, ctypes.addressof(insert))
        return int(result or 0)

    def _delete_children(self, item: int) -> None:
        if not self.hwnd:
            return
        child = int(user32.SendMessageW(self.hwnd, TVM_GETNEXTITEM, TVGN_CHILD, item) or 0)
        while child:
            next_child = int(user32.SendMessageW(self.hwnd, TVM_GETNEXTITEM, TVGN_NEXT, child) or 0)
            self._item_paths.pop(child, None)
            self._loaded_items.discard(child)
            user32.SendMessageW(self.hwnd, TVM_DELETEITEM, 0, child)
            child = next_child

    def _set_item_children(self, item: int, child_count: int) -> None:
        if not self.hwnd:
            return
        tv_item = TVITEMW(
            mask=TVIF_CHILDREN,
            hItem=ctypes.c_void_p(item),
            state=0,
            stateMask=0,
            pszText=None,
            cchTextMax=0,
            iImage=0,
            iSelectedImage=0,
            cChildren=child_count,
            lParam=0,
        )
        user32.SendMessageW(self.hwnd, TVM_SETITEMW, 0, ctypes.addressof(tv_item))

    def _init_common_controls(self) -> None:
        init = INITCOMMONCONTROLSEX(ctypes.sizeof(INITCOMMONCONTROLSEX), ICC_TREEVIEW_CLASSES)
        comctl32.InitCommonControlsEx(ctypes.byref(init))


def _initial_tree_roots() -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    user_profile = Path(os.environ.get("USERPROFILE") or str(Path.home()))
    candidates = [
        ("\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", user_profile / "Desktop"),
        ("\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8", user_profile / "Documents"),
        ("\u30d4\u30af\u30c1\u30e3", user_profile / "Pictures"),
        ("\u30c0\u30a6\u30f3\u30ed\u30fc\u30c9", user_profile / "Downloads"),
    ]
    for label, folder in candidates:
        if _safe_is_dir(folder):
            roots.append((label, display_path(folder)))

    for index, folder in enumerate(_onedrive_roots()):
        label = "OneDrive" if index == 0 else _folder_label(folder)
        roots.append((label, folder))

    for drive in _drive_roots():
        roots.append((_folder_label(drive), drive))

    unique: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for label, folder in roots:
        key = str(folder).casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append((label, folder))
    return unique


def _onedrive_roots() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value))
    user_profile = Path(os.environ.get("USERPROFILE") or str(Path.home()))
    candidates.append(user_profile / "OneDrive")

    roots: list[Path] = []
    seen: set[str] = set()
    for folder in candidates:
        if not _safe_is_dir(folder):
            continue
        display = display_path(folder)
        key = str(display).casefold()
        if key in seen:
            continue
        seen.add(key)
        roots.append(display)
    return roots


def _drive_roots() -> list[Path]:
    mask = int(kernel32.GetLogicalDrives() or 0)
    drives: list[Path] = []
    for index in range(26):
        if mask & (1 << index):
            drives.append(Path(f"{chr(ord('A') + index)}:\\"))
    return drives


def _child_folders(folder: Path) -> list[Path]:
    children: list[Path] = []
    try:
        with os.scandir(filesystem_path(folder)) as entries:
            for entry in entries:
                try:
                    if _should_show_folder_entry(entry):
                        children.append(display_path(Path(entry.path)))
                except OSError:
                    continue
    except OSError:
        return []
    children.sort(key=lambda path: (_folder_label(path).casefold(), str(path).casefold()))
    return children


def _has_child_folder(folder: Path) -> bool:
    try:
        with os.scandir(filesystem_path(folder)) as entries:
            for entry in entries:
                try:
                    if _should_show_folder_entry(entry):
                        return True
                except OSError:
                    continue
    except OSError:
        return False
    return False


def _should_show_folder_entry(entry: os.DirEntry[str]) -> bool:
    name = entry.name
    name_key = name.casefold()
    if name_key in _excluded_folder_names():
        return False
    if name.startswith("."):
        return False
    if not entry.is_dir(follow_symlinks=False):
        return False
    try:
        attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
    except OSError:
        return False
    if attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        return False
    if attributes & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM):
        return False
    return True


def _excluded_folder_names() -> set[str]:
    return {
        "appdata",
        "application data",
        "cookies",
        "local settings",
        "my music",
        "my pictures",
        "my videos",
        "nethood",
        "printhood",
        "recent",
        "sendto",
        "start menu",
        "templates",
        ".git",
        ".venv",
        "__pycache__",
    }


def _safe_is_dir(folder: Path) -> bool:
    try:
        return path_is_dir(folder)
    except OSError:
        return False


def _folder_label(folder: Path) -> str:
    folder = display_path(folder)
    if folder.drive and folder.parent == folder:
        return f"{folder.drive}\\"
    return folder.name or folder.drive or folder.anchor or str(folder)


def _handle_to_int(handle: object) -> int:
    if handle is None:
        return 0
    try:
        return int(handle)
    except (TypeError, ValueError):
        value = getattr(handle, "value", None)
        return int(value or 0)
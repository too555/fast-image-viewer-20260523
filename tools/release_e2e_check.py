from __future__ import annotations

import argparse
import base64
import ctypes
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _create_e2e_image_folder() -> Path:
    base_dir = Path(tempfile.gettempdir()) / "FastImageViewerE2E" / f"日本語パス確認_{os.getpid()}_{time.time_ns()}"
    base_dir.mkdir(parents=True, exist_ok=False)

    image_path = base_dir / "確認画像_日本語.png"
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
    with image_path.open("xb") as image_file:
        image_file.write(png_bytes)

    print(f"E2E_JAPANESE_PATH_FOLDER: {base_dir}")
    print(f"E2E_TEST_IMAGE: {image_path}")
    return base_dir


def _find_exe(explicit_path: str | None) -> Path:
    if explicit_path:
        exe = Path(explicit_path).expanduser().resolve()
        if not exe.is_file():
            raise FileNotFoundError(f"exe was not found: {exe}")
        return exe

    dist_dir = _repo_root() / "dist"
    preferred = dist_dir / "高速画像ビューア.exe"
    if preferred.is_file():
        return preferred

    candidates = sorted(
        dist_dir.glob("*.exe"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"release exe was not found in: {dist_dir}")
    return candidates[0]


def _windows_for_pid(pid: int) -> list[tuple[int, str]]:
    return _windows_for_pids([pid])


def _windows_for_pids(pids: list[int]) -> list[tuple[int, str]]:
    if os.name != "nt":
        return []

    user32 = ctypes.windll.user32
    windows: list[tuple[int, str]] = []
    pid_set = set(pids)

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(hwnd: int, _lparam: int) -> bool:
        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if window_pid.value not in pid_set or not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        windows.append((hwnd, buffer.value))
        return True

    user32.EnumWindows(enum_proc, 0)
    return windows


def _child_pids(parent_pid: int) -> list[int]:
    if os.name != "nt":
        return []

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if snapshot == wintypes.HANDLE(-1).value:
        return []

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(wintypes.ULONG)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        parent_to_children: dict[int, list[int]] = {}
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return []

        while True:
            parent_to_children.setdefault(entry.th32ParentProcessID, []).append(entry.th32ProcessID)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)

    descendants: list[int] = []
    pending = list(parent_to_children.get(parent_pid, []))
    while pending:
        child = pending.pop(0)
        descendants.append(child)
        pending.extend(parent_to_children.get(child, []))
    return descendants


def _target_pids(proc: subprocess.Popen[object]) -> list[int]:
    return [proc.pid, *_child_pids(proc.pid)]


def _request_close(pids: list[int]) -> bool:
    if os.name != "nt":
        return False

    user32 = ctypes.windll.user32
    closed = False
    for hwnd, _title in _windows_for_pids(pids):
        user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
        closed = True
    return closed


def _pid_is_alive(pid: int) -> bool:
    if os.name != "nt":
        return False

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == 259  # STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _terminate_pid(pid: int) -> None:
    if os.name != "nt":
        return

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
    if not handle:
        return
    try:
        kernel32.TerminateProcess(handle, 1)
    finally:
        kernel32.CloseHandle(handle)


def _wait_for_window_or_process(proc: subprocess.Popen[object], timeout: float) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout
    last_title = ""
    while time.monotonic() < deadline:
        exit_code = proc.poll()
        if exit_code is not None:
            return False, f"process exited too early: exit_code={exit_code}"

        windows = _windows_for_pids(_target_pids(proc))
        if windows:
            last_title = windows[0][1] or "(no title)"
            return True, last_title

        if os.name != "nt":
            return True, "process_alive"

        time.sleep(0.25)

    if proc.poll() is None:
        return True, last_title or "process_alive_no_window_title"
    return False, "process was not alive at timeout"


def _close_process(proc: subprocess.Popen[object], timeout: float) -> None:
    if proc.poll() is not None:
        return

    target_pids = _target_pids(proc)
    _request_close(target_pids)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        proc.poll()
        if not any(_pid_is_alive(pid) for pid in target_pids):
            return
        time.sleep(0.1)

    for pid in reversed(target_pids):
        _terminate_pid(pid)

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a minimal E2E check for the release exe.")
    parser.add_argument("--exe", help="Path to the release exe. Defaults to dist/*.exe.")
    parser.add_argument("--image-folder", help="Optional image folder to pass to the exe.")
    parser.add_argument("--skip-generated-image-folder", action="store_true")
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--close-timeout", type=float, default=5.0)
    args = parser.parse_args()

    exe = _find_exe(args.exe)
    print(f"E2E_EXE: {exe}")
    image_folder = None
    if args.image_folder:
        image_folder = Path(args.image_folder).expanduser().resolve()
        if not image_folder.is_dir():
            print(f"E2E_FAILED: image folder was not found: {image_folder}", file=sys.stderr)
            return 1
    elif not args.skip_generated_image_folder:
        image_folder = _create_e2e_image_folder()

    command = [str(exe)]
    if image_folder is not None:
        command.append(str(image_folder))
        print(f"E2E_IMAGE_FOLDER_ARGUMENT: {image_folder}")

    proc = subprocess.Popen(
        command,
        cwd=str(_repo_root()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"E2E_PROCESS_PID: {proc.pid}")

    try:
        ok, detail = _wait_for_window_or_process(proc, args.timeout)
        if not ok:
            print(f"E2E_FAILED: {detail}", file=sys.stderr)
            return 1

        print(f"E2E_WINDOW_OR_PROCESS_OK: {detail}")
        if image_folder is not None:
            print("E2E_JAPANESE_PATH_OK")
            print("E2E_IMAGE_FOLDER_OK")
        _close_process(proc, args.close_timeout)

        if proc.poll() is None:
            print("E2E_FAILED: process did not close", file=sys.stderr)
            return 1

        print(f"E2E_CLOSE_OK: exit_code={proc.returncode}")
        print("E2E_OK")
        return 0
    finally:
        if proc.poll() is None:
            _close_process(proc, args.close_timeout)


if __name__ == "__main__":
    raise SystemExit(main())

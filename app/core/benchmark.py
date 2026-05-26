from __future__ import annotations

import ctypes
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.utils.long_path import filesystem_path, make_dirs

BENCHMARK_ENV_VAR = "FAST_IMAGE_VIEWER_BENCHMARK"
BENCHMARK_LOG_ENV_VAR = "FAST_IMAGE_VIEWER_BENCHMARK_LOG"
THUMBNAIL_PROGRESS_LOG_INTERVAL = 500


def is_benchmark_enabled(value: str | None = None) -> bool:
    raw_value = os.environ.get(BENCHMARK_ENV_VAR) if value is None else value
    if raw_value is None:
        return False
    return raw_value.strip().casefold() not in {"", "0", "false", "no", "off"}


def default_benchmark_log_path() -> Path:
    custom_path = os.environ.get(BENCHMARK_LOG_ENV_VAR)
    if custom_path:
        return Path(custom_path)
    base_dir = os.environ.get("LOCALAPPDATA")
    if base_dir:
        return Path(base_dir) / "FastImageViewer" / "benchmark.log"
    return Path.home() / ".fast_image_viewer" / "benchmark.log"


@dataclass(frozen=True, slots=True)
class BenchmarkSnapshot:
    folder_load_ms: float | None
    first_thumbnail_ms: float | None
    first_paint_ms: float | None
    scroll_response_ms: float | None
    thumbnail_count: int
    cache_hits: int
    cache_misses: int
    memory_bytes: int | None


class BenchmarkRecorder:
    def __init__(self, enabled: bool | None = None, log_path: Path | None = None) -> None:
        self.enabled = is_benchmark_enabled() if enabled is None else enabled
        self.log_path = log_path or default_benchmark_log_path()
        self.folder: Path | None = None
        self.folder_load_ms: float | None = None
        self.first_thumbnail_ms: float | None = None
        self.first_paint_ms: float | None = None
        self.scroll_response_ms: float | None = None
        self.thumbnail_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self._folder_start: float | None = None
        self._scroll_start: float | None = None

    def start_folder_load(self, folder: Path) -> None:
        if not self.enabled:
            return
        self.folder = folder
        self.folder_load_ms = None
        self.first_thumbnail_ms = None
        self.first_paint_ms = None
        self.scroll_response_ms = None
        self.thumbnail_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self._folder_start = time.perf_counter()
        self._scroll_start = None
        self._log("folder_load_start", folder=str(folder))

    def record_folder_loaded(self, image_count: int) -> None:
        if not self.enabled or self._folder_start is None:
            return
        self.folder_load_ms = _elapsed_ms(self._folder_start)
        self._log("folder_load_done", image_count=image_count, folder_load_ms=f"{self.folder_load_ms:.1f}")

    def record_thumbnail_result(self, cache_hit: bool, done: int, total: int) -> None:
        if not self.enabled:
            return
        self.thumbnail_count += 1
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        if self.first_thumbnail_ms is None and self._folder_start is not None:
            self.first_thumbnail_ms = _elapsed_ms(self._folder_start)
            self._log(
                "first_thumbnail_done",
                done=done,
                total=total,
                cache_hit=cache_hit,
                first_thumbnail_ms=f"{self.first_thumbnail_ms:.1f}",
            )
        if total and (done == total or done % THUMBNAIL_PROGRESS_LOG_INTERVAL == 0):
            self._log(
                "thumbnail_progress",
                done=done,
                total=total,
                cache_hits=self.cache_hits,
                cache_misses=self.cache_misses,
            )

    def start_scroll(self) -> None:
        if self.enabled:
            self._scroll_start = time.perf_counter()

    def record_paint(self, paint_ms: float, visible_count: int) -> None:
        if not self.enabled:
            return
        if self.first_paint_ms is None and self._folder_start is not None:
            self.first_paint_ms = _elapsed_ms(self._folder_start)
            self._log(
                "first_paint_done",
                first_paint_ms=f"{self.first_paint_ms:.1f}",
                paint_ms=f"{paint_ms:.1f}",
                visible_count=visible_count,
            )
        if self._scroll_start is not None:
            self.scroll_response_ms = _elapsed_ms(self._scroll_start)
            self._scroll_start = None
            self._log(
                "scroll_paint_done",
                scroll_response_ms=f"{self.scroll_response_ms:.1f}",
                paint_ms=f"{paint_ms:.1f}",
                visible_count=visible_count,
            )

    def record_error(self, event: str, message: str) -> None:
        if self.enabled:
            self._log(event, error=message)

    def snapshot(self) -> BenchmarkSnapshot:
        return BenchmarkSnapshot(
            folder_load_ms=self.folder_load_ms,
            first_thumbnail_ms=self.first_thumbnail_ms,
            first_paint_ms=self.first_paint_ms,
            scroll_response_ms=self.scroll_response_ms,
            thumbnail_count=self.thumbnail_count,
            cache_hits=self.cache_hits,
            cache_misses=self.cache_misses,
            memory_bytes=current_memory_bytes(),
        )

    def status_text(self) -> str:
        if not self.enabled:
            return ""
        snapshot = self.snapshot()
        parts: list[str] = []
        if snapshot.folder_load_ms is not None:
            parts.append(f"読込 {snapshot.folder_load_ms:.0f}ms")
        if snapshot.first_thumbnail_ms is not None:
            parts.append(f"初サムネ {snapshot.first_thumbnail_ms:.0f}ms")
        if snapshot.first_paint_ms is not None:
            parts.append(f"初描画 {snapshot.first_paint_ms:.0f}ms")
        if snapshot.scroll_response_ms is not None:
            parts.append(f"スクロール {snapshot.scroll_response_ms:.0f}ms")
        if snapshot.thumbnail_count:
            parts.append(f"Hit {snapshot.cache_hits}/{snapshot.thumbnail_count}")
        if snapshot.memory_bytes is not None:
            parts.append(f"Mem {_format_bytes(snapshot.memory_bytes)}")
        if not parts:
            parts.append("ベンチマーク待機中")
        return "BM " + " / ".join(parts)

    def _log(self, event: str, **fields: object) -> None:
        memory_bytes = current_memory_bytes()
        if memory_bytes is not None:
            fields.setdefault("memory_bytes", memory_bytes)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        details = " ".join(f"{key}={_quote_log_value(value)}" for key, value in fields.items())
        line = f"{timestamp} {event}"
        if details:
            line += f" {details}"
        line += "\n"
        try:
            make_dirs(self.log_path.parent)
            with open(filesystem_path(self.log_path), "a", encoding="utf-8") as log_file:
                log_file.write(line)
        except OSError:
            pass


def current_memory_bytes() -> int | None:
    if not hasattr(ctypes, "windll"):
        return None
    try:
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
            ctypes.c_ulong,
        ]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        process_handle = kernel32.GetCurrentProcess()
        ok = psapi.GetProcessMemoryInfo(
            process_handle,
            ctypes.byref(counters),
            counters.cb,
        )
        if not ok:
            return None
        return int(counters.WorkingSetSize)
    except (AttributeError, OSError, ValueError):
        return None


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


def _format_bytes(size_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)}{unit}"
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{size_bytes}B"


def _quote_log_value(value: object) -> str:
    text = str(value).replace('"', '\\"')
    if any(character.isspace() for character in text):
        return f'"{text}"'
    return text

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.preview_renderer import default_preview_cache_dir
from app.core.thumbnail_cache import default_cache_dir
from app.utils.long_path import display_path, filesystem_path, make_dirs, path_exists

CACHE_FILE_SUFFIX = ".bmp"
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


@dataclass(frozen=True, slots=True)
class CacheStats:
    thumbnails_bytes: int = 0
    previews_bytes: int = 0
    thumbnails_files: int = 0
    previews_files: int = 0

    @property
    def total_bytes(self) -> int:
        return self.thumbnails_bytes + self.previews_bytes

    @property
    def total_files(self) -> int:
        return self.thumbnails_files + self.previews_files


@dataclass(frozen=True, slots=True)
class CacheCleanupResult:
    before_bytes: int
    after_bytes: int
    deleted_files: int
    deleted_bytes: int
    failed_files: int = 0


@dataclass(frozen=True, slots=True)
class _CacheFile:
    path: Path
    size: int
    mtime: float
    kind: str


def cache_stats(
    thumbnail_dir: Path | None = None,
    preview_dir: Path | None = None,
) -> CacheStats:
    thumbnail_files = _list_cache_files(_cache_root(thumbnail_dir, "thumbnails"), "thumbnails")
    preview_files = _list_cache_files(_cache_root(preview_dir, "previews"), "previews")
    return CacheStats(
        thumbnails_bytes=sum(cache_file.size for cache_file in thumbnail_files),
        previews_bytes=sum(cache_file.size for cache_file in preview_files),
        thumbnails_files=len(thumbnail_files),
        previews_files=len(preview_files),
    )


def cleanup_cache(
    limit_bytes: int,
    thumbnail_dir: Path | None = None,
    preview_dir: Path | None = None,
) -> CacheCleanupResult:
    limit_bytes = max(0, int(limit_bytes))
    thumbnail_root = _cache_root(thumbnail_dir, "thumbnails")
    preview_root = _cache_root(preview_dir, "previews")
    files = [
        *_list_cache_files(preview_root, "previews"),
        *_list_cache_files(thumbnail_root, "thumbnails"),
    ]
    before_bytes = sum(cache_file.size for cache_file in files)
    if before_bytes <= limit_bytes:
        return CacheCleanupResult(before_bytes, before_bytes, 0, 0)

    total_bytes = before_bytes
    deleted_files = 0
    deleted_bytes = 0
    failed_files = 0
    files.sort(key=lambda cache_file: (_cache_delete_priority(cache_file.kind), cache_file.mtime, str(cache_file.path)))

    for cache_file in files:
        if total_bytes <= limit_bytes:
            break
        if _delete_cache_file(cache_file.path):
            total_bytes -= cache_file.size
            deleted_files += 1
            deleted_bytes += cache_file.size
        else:
            failed_files += 1

    return CacheCleanupResult(before_bytes, max(0, total_bytes), deleted_files, deleted_bytes, failed_files)


def clear_cache(
    thumbnail_dir: Path | None = None,
    preview_dir: Path | None = None,
) -> CacheCleanupResult:
    thumbnail_root = _cache_root(thumbnail_dir, "thumbnails")
    preview_root = _cache_root(preview_dir, "previews")
    files = [
        *_list_cache_files(preview_root, "previews"),
        *_list_cache_files(thumbnail_root, "thumbnails"),
    ]
    before_bytes = sum(cache_file.size for cache_file in files)
    deleted_files = 0
    deleted_bytes = 0
    failed_files = 0

    for cache_file in files:
        if _delete_cache_file(cache_file.path):
            deleted_files += 1
            deleted_bytes += cache_file.size
        else:
            failed_files += 1

    return CacheCleanupResult(before_bytes, max(0, before_bytes - deleted_bytes), deleted_files, deleted_bytes, failed_files)


def _cache_root(root: Path | None, expected_name: str) -> Path:
    cache_root = display_path(root or (default_cache_dir() if expected_name == "thumbnails" else default_preview_cache_dir()))
    if cache_root.name.casefold() != expected_name:
        raise ValueError(f"Unexpected cache root: {cache_root}")
    make_dirs(cache_root)
    return cache_root


def _list_cache_files(root: Path, kind: str) -> list[_CacheFile]:
    if not path_exists(root):
        return []

    files: list[_CacheFile] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(filesystem_path(current)) as entries:
                for entry in entries:
                    if _is_reparse_point(entry):
                        continue
                    entry_path = display_path(entry.path)
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry_path)
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            continue
                        if entry_path.suffix.casefold() != CACHE_FILE_SUFFIX:
                            continue
                        stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    files.append(_CacheFile(path=entry_path, size=max(0, int(stat.st_size)), mtime=stat.st_mtime, kind=kind))
        except OSError:
            continue
    return files


def _is_reparse_point(entry: os.DirEntry[str]) -> bool:
    try:
        if entry.is_symlink():
            return True
        attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
    except OSError:
        return True
    return bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)


def _delete_cache_file(path: Path) -> bool:
    try:
        if display_path(path).suffix.casefold() != CACHE_FILE_SUFFIX:
            return False
        os.remove(filesystem_path(path))
    except OSError:
        return False
    return True


def _cache_delete_priority(kind: str) -> int:
    return 0 if kind == "previews" else 1

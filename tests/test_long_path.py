from __future__ import annotations

import os
import unittest
from pathlib import Path

from app.utils.long_path import display_path, filesystem_path, strip_extended_prefix


class LongPathTest(unittest.TestCase):
    def test_strip_extended_drive_prefix(self) -> None:
        self.assertEqual(strip_extended_prefix("\\\\?\\C:\\images\\photo.jpg"), "C:\\images\\photo.jpg")

    def test_strip_extended_unc_prefix(self) -> None:
        self.assertEqual(
            strip_extended_prefix("\\\\?\\UNC\\server\\share\\photo.jpg"),
            "\\\\server\\share\\photo.jpg",
        )

    def test_display_path_removes_windows_extended_prefix(self) -> None:
        self.assertEqual(display_path("\\\\?\\C:\\images\\photo.jpg"), Path("C:/images/photo.jpg"))

    def test_filesystem_path_adds_windows_extended_prefix(self) -> None:
        if os.name != "nt":
            self.assertEqual(filesystem_path("/tmp/photo.jpg"), "/tmp/photo.jpg")
            return

        result = filesystem_path("C:/images/photo.jpg")

        self.assertEqual(result, "\\\\?\\C:\\images\\photo.jpg")


if __name__ == "__main__":
    unittest.main()

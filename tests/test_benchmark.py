from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core.benchmark import BenchmarkRecorder, is_benchmark_enabled


class BenchmarkRecorderTest(unittest.TestCase):
    def test_benchmark_env_flag(self) -> None:
        self.assertTrue(is_benchmark_enabled("1"))
        self.assertTrue(is_benchmark_enabled("true"))
        self.assertFalse(is_benchmark_enabled("0"))
        self.assertFalse(is_benchmark_enabled("off"))

    def test_records_metrics_and_writes_log_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "benchmark.log"
            recorder = BenchmarkRecorder(enabled=True, log_path=log_path)

            recorder.start_folder_load(Path("C:/images"))
            recorder.record_folder_loaded(10000)
            recorder.record_thumbnail_result(cache_hit=True, done=1, total=10000)
            recorder.start_scroll()
            recorder.record_paint(paint_ms=12.5, visible_count=40)

            snapshot = recorder.snapshot()
            status_text = recorder.status_text()

            self.assertIsNotNone(snapshot.folder_load_ms)
            self.assertIsNotNone(snapshot.first_thumbnail_ms)
            self.assertIsNotNone(snapshot.first_paint_ms)
            self.assertIsNotNone(snapshot.scroll_response_ms)
            self.assertEqual(snapshot.cache_hits, 1)
            self.assertIn("BM", status_text)
            self.assertTrue(log_path.exists())
            self.assertIn("folder_load_done", log_path.read_text(encoding="utf-8"))

    def test_disabled_recorder_does_not_write_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "benchmark.log"
            recorder = BenchmarkRecorder(enabled=False, log_path=log_path)

            recorder.start_folder_load(Path("C:/images"))
            recorder.record_folder_loaded(1)

            self.assertEqual(recorder.status_text(), "")
            self.assertFalse(log_path.exists())

    def test_main_window_uses_environment_flag(self) -> None:
        with mock.patch.dict("os.environ", {"FAST_IMAGE_VIEWER_BENCHMARK": "1"}):
            recorder = BenchmarkRecorder()

        self.assertTrue(recorder.enabled)


if __name__ == "__main__":
    unittest.main()

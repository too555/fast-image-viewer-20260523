from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from PIL import Image

from app.core.image_scanner import ImageFile
from app.core.preview_renderer import (
    PREVIEW_MODE_FIT_HEIGHT,
    PREVIEW_MODE_ORIGINAL,
    PREVIEW_MODE_SCALE_200,
    PreviewResult,
)
from app.ui import compare_view
from app.ui.image_preview import ImagePreview, VK_ESCAPE, VK_SPACE, WM_KEYDOWN


def _image_file(path: Path, index: int) -> ImageFile:
    return ImageFile(
        path=path,
        name=path.name,
        suffix=path.suffix.lower(),
        size=100 + index,
        mtime=float(index),
    )


class FakePreview:
    def __init__(self) -> None:
        self.image_file: ImageFile | None = None
        self.result: PreviewResult | None = None
        self.pan_enabled = False
        self.guides: list[tuple[bool, bool]] = []
        self.pan_ratios: list[tuple[float, float]] = []
        self._pan_ratio = (0.0, 0.0)

    def set_pan_enabled(self, enabled: bool) -> None:
        self.pan_enabled = enabled

    def set_guides(self, center: bool = False, grid: bool = False) -> None:
        self.guides.append((center, grid))

    def set_loading(self, image_file: ImageFile) -> None:
        self.image_file = image_file

    def set_result(self, image_file: ImageFile, result: PreviewResult) -> None:
        self.image_file = image_file
        self.result = result

    def preview_size(self) -> tuple[int, int]:
        return (320, 240)

    def pan_ratio(self) -> tuple[float, float]:
        return self._pan_ratio

    def set_pan_ratio(self, ratio_x: float, ratio_y: float) -> None:
        self._pan_ratio = (ratio_x, ratio_y)
        self.pan_ratios.append((ratio_x, ratio_y))


class CompareViewTest(unittest.TestCase):
    def test_escape_key_closes_compare_view(self) -> None:
        view = compare_view.CompareView()
        calls: list[bool] = []
        view.destroy = lambda: calls.append(True)  # type: ignore[method-assign]

        self.assertEqual(view.handle_message(0, compare_view.WM_KEYDOWN, compare_view.VK_ESCAPE, 0), 0)
        self.assertEqual(calls, [True])

    def test_escape_key_inside_preview_can_close_compare_view(self) -> None:
        preview = ImagePreview()
        calls: list[bool] = []
        preview.on_escape = lambda: calls.append(True)

        self.assertEqual(preview.handle_message(0, WM_KEYDOWN, VK_ESCAPE, 0), 0)
        self.assertEqual(calls, [True])

    def test_sync_zoom_renders_both_images_with_same_display_mode(self) -> None:
        original_render_preview = compare_view.render_preview
        first = _image_file(Path("C:/images/a.jpg"), 1)
        second = _image_file(Path("C:/images/b.jpg"), 2)
        render_calls: list[tuple[ImageFile, int, int, str]] = []

        def fake_render_preview(image_file: ImageFile, width: int, height: int, *args: object, **kwargs: object) -> PreviewResult:
            render_calls.append((image_file, width, height, kwargs["display_mode"]))
            return PreviewResult(Path(f"C:/cache/{image_file.name}.bmp"), 640, 480)

        try:
            compare_view.render_preview = fake_render_preview  # type: ignore[assignment]
            view = compare_view.CompareView()
            view.left_preview = FakePreview()  # type: ignore[assignment]
            view.right_preview = FakePreview()  # type: ignore[assignment]
            view._left_image = first
            view._right_image = second
            view._display_mode = PREVIEW_MODE_ORIGINAL

            view._zoom_in()
        finally:
            compare_view.render_preview = original_render_preview  # type: ignore[assignment]

        self.assertEqual(view._display_mode, PREVIEW_MODE_SCALE_200)
        self.assertEqual(
            render_calls,
            [
                (first, 320, 240, PREVIEW_MODE_SCALE_200),
                (second, 320, 240, PREVIEW_MODE_SCALE_200),
            ],
        )
        self.assertTrue(view.left_preview.pan_enabled)  # type: ignore[attr-defined]
        self.assertTrue(view.right_preview.pan_enabled)  # type: ignore[attr-defined]

    def test_fit_height_disables_compare_panning(self) -> None:
        original_render_preview = compare_view.render_preview
        first = _image_file(Path("C:/images/a.jpg"), 1)
        second = _image_file(Path("C:/images/b.jpg"), 2)

        def fake_render_preview(image_file: ImageFile, width: int, height: int, *args: object, **kwargs: object) -> PreviewResult:
            return PreviewResult(Path(f"C:/cache/{image_file.name}.bmp"), 320, 240)

        try:
            compare_view.render_preview = fake_render_preview  # type: ignore[assignment]
            view = compare_view.CompareView()
            view.left_preview = FakePreview()  # type: ignore[assignment]
            view.right_preview = FakePreview()  # type: ignore[assignment]
            view._left_image = first
            view._right_image = second
            view._display_mode = PREVIEW_MODE_FIT_HEIGHT
            view._left_display_mode = PREVIEW_MODE_FIT_HEIGHT
            view._right_display_mode = PREVIEW_MODE_FIT_HEIGHT

            view._render_current_pair(reset_pan=True)
        finally:
            compare_view.render_preview = original_render_preview  # type: ignore[assignment]

        self.assertFalse(view.left_preview.pan_enabled)  # type: ignore[attr-defined]
        self.assertFalse(view.right_preview.pan_enabled)  # type: ignore[attr-defined]

    def test_pan_changed_syncs_to_opposite_preview_by_ratio(self) -> None:
        view = compare_view.CompareView()
        view.left_preview = FakePreview()  # type: ignore[assignment]
        view.right_preview = FakePreview()  # type: ignore[assignment]
        view.left_preview._pan_ratio = (0.5, -0.25)  # type: ignore[attr-defined]

        view._sync_pan_from(view.left_preview, 120, -80)

        self.assertEqual(view.right_preview.pan_ratios[-1], (0.5, -0.25))  # type: ignore[attr-defined]

    def test_info_label_shows_sync_state_and_zoom(self) -> None:
        view = compare_view.CompareView()
        captured: dict[int, str] = {}
        view.info_label = 101
        view._set_label = lambda hwnd, text: captured.__setitem__(hwnd, text) if hwnd else None  # type: ignore[method-assign]
        view._display_mode = PREVIEW_MODE_SCALE_200
        view._left_display_mode = PREVIEW_MODE_SCALE_200
        view._right_display_mode = PREVIEW_MODE_SCALE_200

        view._update_info_label()

        self.assertIn("通常表示", captured[101])
        self.assertIn("同期ON", captured[101])
        self.assertIn("左: 200%", captured[101])
        self.assertIn("右: 200%", captured[101])

    def test_view_mode_cycle_reaches_diff_and_rerenders_pair(self) -> None:
        original_render_preview = compare_view.render_preview
        original_diff_results = compare_view._diff_emphasized_results
        first = _image_file(Path("C:/images/a.jpg"), 1)
        second = _image_file(Path("C:/images/b.jpg"), 2)
        captured: dict[int, str] = {}
        render_calls: list[ImageFile] = []

        def fake_render_preview(image_file: ImageFile, width: int, height: int, *args: object, **kwargs: object) -> PreviewResult:
            render_calls.append(image_file)
            return PreviewResult(Path(f"C:/cache/{image_file.name}.bmp"), 640, 480)

        def fake_diff_results(left_result: PreviewResult, right_result: PreviewResult) -> tuple[PreviewResult, PreviewResult]:
            return (
                PreviewResult(Path("C:/diff/left.bmp"), left_result.width, left_result.height),
                PreviewResult(Path("C:/diff/right.bmp"), right_result.width, right_result.height),
            )

        try:
            compare_view.render_preview = fake_render_preview  # type: ignore[assignment]
            compare_view._diff_emphasized_results = fake_diff_results  # type: ignore[assignment]
            view = compare_view.CompareView()
            view.left_preview = FakePreview()  # type: ignore[assignment]
            view.right_preview = FakePreview()  # type: ignore[assignment]
            view.view_mode_button = 103
            view.info_label = 104
            view._set_label = lambda hwnd, text: captured.__setitem__(hwnd, text) if hwnd else None  # type: ignore[method-assign]
            view._left_image = first
            view._right_image = second

            self.assertTrue(view._cycle_view_mode())
        finally:
            compare_view.render_preview = original_render_preview  # type: ignore[assignment]
            compare_view._diff_emphasized_results = original_diff_results  # type: ignore[assignment]

        self.assertTrue(view._diff_enabled)
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_DIFF)
        self.assertEqual(captured[103], "表示: 差分")
        self.assertIn("差分強調表示", captured[104])
        self.assertEqual(render_calls, [first, second])
        self.assertEqual(view.left_preview.result.cache_path, Path("C:/diff/left.bmp"))  # type: ignore[union-attr]
        self.assertEqual(view.right_preview.result.cache_path, Path("C:/diff/right.bmp"))  # type: ignore[union-attr]

    def test_view_mode_cycle_reaches_alternate_and_back_to_normal(self) -> None:
        view = compare_view.CompareView()
        render_modes: list[str] = []
        view._render_current_pair = lambda reset_pan=False: render_modes.append(view._view_mode)  # type: ignore[method-assign]
        view._start_alternate_timer = lambda: render_modes.append("timer-start")  # type: ignore[method-assign]
        view._stop_alternate_timer = lambda: render_modes.append("timer-stop")  # type: ignore[method-assign]

        self.assertTrue(view._cycle_view_mode())
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_DIFF)

        self.assertTrue(view._cycle_view_mode())
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_ALTERNATE)
        self.assertFalse(view._alternate_phase)

        self.assertTrue(view._cycle_view_mode())
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_OVERLAY)

        self.assertTrue(view._cycle_view_mode())
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_MASK)

        self.assertTrue(view._cycle_view_mode())
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_NORMAL)
        self.assertFalse(view._alternate_phase)
        self.assertIn("timer-start", render_modes)
        self.assertIn("timer-stop", render_modes)

    def test_view_mode_cycle_reaches_overlay_and_back_to_normal(self) -> None:
        view = compare_view.CompareView()
        render_modes: list[str] = []
        view._render_current_pair = lambda reset_pan=False: render_modes.append(view._view_mode)  # type: ignore[method-assign]
        view._start_alternate_timer = lambda: render_modes.append("timer-start")  # type: ignore[method-assign]
        view._stop_alternate_timer = lambda: render_modes.append("timer-stop")  # type: ignore[method-assign]

        self.assertTrue(view._cycle_view_mode())
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_DIFF)

        self.assertTrue(view._cycle_view_mode())
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_ALTERNATE)

        self.assertTrue(view._cycle_view_mode())
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_OVERLAY)
        self.assertFalse(view._diff_enabled)

        self.assertTrue(view._cycle_view_mode())
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_MASK)
        self.assertFalse(view._diff_enabled)

        self.assertTrue(view._cycle_view_mode())
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_NORMAL)
        self.assertIn("timer-start", render_modes)
        self.assertIn("timer-stop", render_modes)

    def test_overlay_ratio_cycles_and_rerenders_only_in_overlay_mode(self) -> None:
        view = compare_view.CompareView()
        render_ratios: list[int] = []
        info_updates: list[int] = []
        view._render_current_pair = lambda reset_pan=False: render_ratios.append(view._overlay_alpha_percent)  # type: ignore[method-assign]
        view._update_info_label = lambda: info_updates.append(view._overlay_alpha_percent)  # type: ignore[method-assign]
        view._view_mode = compare_view.COMPARE_VIEW_MODE_OVERLAY

        self.assertTrue(view._cycle_overlay_ratio())
        self.assertEqual(view._overlay_alpha_percent, 75)
        self.assertTrue(view._cycle_overlay_ratio())
        self.assertEqual(view._overlay_alpha_percent, 25)
        self.assertEqual(render_ratios, [75, 25])

        view._view_mode = compare_view.COMPARE_VIEW_MODE_NORMAL
        self.assertTrue(view._cycle_overlay_ratio())
        self.assertEqual(view._overlay_alpha_percent, 50)
        self.assertEqual(render_ratios, [75, 25])
        self.assertEqual(info_updates, [50])

    def test_mask_style_cycles_and_rerenders_only_in_mask_mode(self) -> None:
        view = compare_view.CompareView()
        render_styles: list[str] = []
        info_updates: list[str] = []
        view._render_current_pair = lambda reset_pan=False: render_styles.append(view._mask_style)  # type: ignore[method-assign]
        view._update_info_label = lambda: info_updates.append(view._mask_style)  # type: ignore[method-assign]
        view._view_mode = compare_view.COMPARE_VIEW_MODE_MASK

        self.assertTrue(view._cycle_mask_style())
        self.assertEqual(view._mask_style, compare_view.MASK_STYLE_GREEN)
        self.assertTrue(view._cycle_mask_style())
        self.assertEqual(view._mask_style, compare_view.MASK_STYLE_TRANSLUCENT)
        self.assertTrue(view._cycle_mask_style())
        self.assertEqual(view._mask_style, compare_view.MASK_STYLE_RED)
        self.assertEqual(
            render_styles,
            [
                compare_view.MASK_STYLE_GREEN,
                compare_view.MASK_STYLE_TRANSLUCENT,
                compare_view.MASK_STYLE_RED,
            ],
        )

        view._view_mode = compare_view.COMPARE_VIEW_MODE_NORMAL
        self.assertTrue(view._cycle_mask_style())
        self.assertEqual(view._mask_style, compare_view.MASK_STYLE_GREEN)
        self.assertEqual(len(render_styles), 3)
        self.assertEqual(info_updates, [compare_view.MASK_STYLE_GREEN])

    def test_mask_threshold_cycles_and_rerenders_only_in_mask_mode(self) -> None:
        view = compare_view.CompareView()
        render_thresholds: list[str] = []
        info_updates: list[str] = []
        view._render_current_pair = lambda reset_pan=False: render_thresholds.append(view._mask_threshold)  # type: ignore[method-assign]
        view._update_info_label = lambda: info_updates.append(view._mask_threshold)  # type: ignore[method-assign]
        view._view_mode = compare_view.COMPARE_VIEW_MODE_MASK

        self.assertTrue(view._cycle_mask_threshold())
        self.assertEqual(view._mask_threshold, compare_view.MASK_THRESHOLD_STRONG)
        self.assertTrue(view._cycle_mask_threshold())
        self.assertEqual(view._mask_threshold, compare_view.MASK_THRESHOLD_WEAK)
        self.assertTrue(view._cycle_mask_threshold())
        self.assertEqual(view._mask_threshold, compare_view.MASK_THRESHOLD_MEDIUM)
        self.assertEqual(
            render_thresholds,
            [
                compare_view.MASK_THRESHOLD_STRONG,
                compare_view.MASK_THRESHOLD_WEAK,
                compare_view.MASK_THRESHOLD_MEDIUM,
            ],
        )

        view._view_mode = compare_view.COMPARE_VIEW_MODE_NORMAL
        self.assertTrue(view._cycle_mask_threshold())
        self.assertEqual(view._mask_threshold, compare_view.MASK_THRESHOLD_STRONG)
        self.assertEqual(len(render_thresholds), 3)
        self.assertEqual(info_updates, [compare_view.MASK_THRESHOLD_STRONG])

    def test_guide_mode_cycles_through_center_grid_both_and_off(self) -> None:
        view = compare_view.CompareView()
        view.left_preview = FakePreview()  # type: ignore[assignment]
        view.right_preview = FakePreview()  # type: ignore[assignment]
        info_updates: list[str] = []
        view._update_info_label = lambda: info_updates.append(view._guide_mode)  # type: ignore[method-assign]

        self.assertTrue(view._cycle_guide_mode())
        self.assertEqual(view._guide_mode, compare_view.COMPARE_GUIDE_MODE_CENTER)
        self.assertEqual(view.left_preview.guides[-1], (True, False))  # type: ignore[attr-defined]
        self.assertEqual(view.right_preview.guides[-1], (True, False))  # type: ignore[attr-defined]

        self.assertTrue(view._cycle_guide_mode())
        self.assertEqual(view._guide_mode, compare_view.COMPARE_GUIDE_MODE_GRID)
        self.assertEqual(view.left_preview.guides[-1], (False, True))  # type: ignore[attr-defined]

        self.assertTrue(view._cycle_guide_mode())
        self.assertEqual(view._guide_mode, compare_view.COMPARE_GUIDE_MODE_BOTH)
        self.assertEqual(view.left_preview.guides[-1], (True, True))  # type: ignore[attr-defined]

        self.assertTrue(view._cycle_guide_mode())
        self.assertEqual(view._guide_mode, compare_view.COMPARE_GUIDE_MODE_OFF)
        self.assertEqual(view.left_preview.guides[-1], (False, False))  # type: ignore[attr-defined]
        self.assertEqual(info_updates, [
            compare_view.COMPARE_GUIDE_MODE_CENTER,
            compare_view.COMPARE_GUIDE_MODE_GRID,
            compare_view.COMPARE_GUIDE_MODE_BOTH,
            compare_view.COMPARE_GUIDE_MODE_OFF,
        ])

    def test_compare_show_resets_guides_to_off(self) -> None:
        first = _image_file(Path("C:/images/a.jpg"), 1)
        second = _image_file(Path("C:/images/b.jpg"), 2)
        view = compare_view.CompareView()
        view.left_preview = FakePreview()  # type: ignore[assignment]
        view.right_preview = FakePreview()  # type: ignore[assignment]
        view.hwnd = 100
        view._create = lambda owner: None  # type: ignore[method-assign]
        view._layout = lambda: None  # type: ignore[method-assign]
        view._render_current_pair = lambda reset_pan=False: None  # type: ignore[method-assign]
        view._set_label = lambda hwnd, text: None  # type: ignore[method-assign]
        view._guide_mode = compare_view.COMPARE_GUIDE_MODE_BOTH

        view.show(None, first, second)

        self.assertEqual(view._guide_mode, compare_view.COMPARE_GUIDE_MODE_OFF)
        self.assertEqual(view.left_preview.guides[-1], (False, False))  # type: ignore[attr-defined]
        self.assertEqual(view.right_preview.guides[-1], (False, False))  # type: ignore[attr-defined]

    def test_diff_and_overlay_view_modes_are_exclusive(self) -> None:
        view = compare_view.CompareView()
        view._render_current_pair = lambda reset_pan=False: None  # type: ignore[method-assign]

        self.assertTrue(view._set_view_mode(compare_view.COMPARE_VIEW_MODE_DIFF))
        self.assertTrue(view._diff_enabled)

        self.assertTrue(view._set_view_mode(compare_view.COMPARE_VIEW_MODE_OVERLAY))
        self.assertEqual(view._view_mode, compare_view.COMPARE_VIEW_MODE_OVERLAY)
        self.assertFalse(view._diff_enabled)

    def test_alternate_timer_swaps_displayed_images_without_swapping_data(self) -> None:
        original_render_preview = compare_view.render_preview
        first = _image_file(Path("C:/images/a.jpg"), 1)
        second = _image_file(Path("C:/images/b.jpg"), 2)
        render_calls: list[ImageFile] = []

        def fake_render_preview(image_file: ImageFile, width: int, height: int, *args: object, **kwargs: object) -> PreviewResult:
            render_calls.append(image_file)
            return PreviewResult(Path(f"C:/cache/{image_file.name}.bmp"), 640, 480)

        try:
            compare_view.render_preview = fake_render_preview  # type: ignore[assignment]
            view = compare_view.CompareView()
            view.left_preview = FakePreview()  # type: ignore[assignment]
            view.right_preview = FakePreview()  # type: ignore[assignment]
            view._left_image = first
            view._right_image = second
            view._view_mode = compare_view.COMPARE_VIEW_MODE_ALTERNATE
            view._alternate_phase = False
            view._update_info_label = lambda: None  # type: ignore[method-assign]
            view._update_image_info_labels = lambda: None  # type: ignore[method-assign]

            self.assertTrue(view._advance_alternate_phase())
        finally:
            compare_view.render_preview = original_render_preview  # type: ignore[assignment]

        self.assertTrue(view._alternate_phase)
        self.assertIs(view._left_image, first)
        self.assertIs(view._right_image, second)
        self.assertEqual(render_calls, [second, first])
        self.assertIs(view.left_preview.image_file, second)  # type: ignore[attr-defined]
        self.assertIs(view.right_preview.image_file, first)  # type: ignore[attr-defined]

    def test_layout_mode_cycle_reaches_top_bottom_center_and_back(self) -> None:
        view = compare_view.CompareView()
        render_modes: list[str] = []
        view._layout = lambda: render_modes.append(f"layout:{view._layout_mode}")  # type: ignore[method-assign]
        view._render_current_pair = lambda reset_pan=False: render_modes.append(view._layout_mode)  # type: ignore[method-assign]

        self.assertTrue(view._cycle_layout_mode())
        self.assertEqual(view._layout_mode, compare_view.COMPARE_LAYOUT_TOP_BOTTOM)

        self.assertTrue(view._cycle_layout_mode())
        self.assertEqual(view._layout_mode, compare_view.COMPARE_LAYOUT_CENTER)

        self.assertTrue(view._cycle_layout_mode())
        self.assertEqual(view._layout_mode, compare_view.COMPARE_LAYOUT_SIDE_BY_SIDE)
        self.assertEqual(view._center_side, "left")
        self.assertIn(compare_view.COMPARE_LAYOUT_TOP_BOTTOM, render_modes)
        self.assertIn(compare_view.COMPARE_LAYOUT_CENTER, render_modes)
        self.assertIn(compare_view.COMPARE_LAYOUT_SIDE_BY_SIDE, render_modes)

    def test_center_layout_keys_switch_active_image(self) -> None:
        original_render_preview = compare_view.render_preview
        first = _image_file(Path("C:/images/a.jpg"), 1)
        second = _image_file(Path("C:/images/b.jpg"), 2)
        render_calls: list[ImageFile] = []

        def fake_render_preview(image_file: ImageFile, width: int, height: int, *args: object, **kwargs: object) -> PreviewResult:
            render_calls.append(image_file)
            return PreviewResult(Path(f"C:/cache/{image_file.name}.bmp"), 640, 480)

        try:
            compare_view.render_preview = fake_render_preview  # type: ignore[assignment]
            view = compare_view.CompareView()
            view.left_preview = FakePreview()  # type: ignore[assignment]
            view.right_preview = FakePreview()  # type: ignore[assignment]
            view._left_image = first
            view._right_image = second
            view._layout_mode = compare_view.COMPARE_LAYOUT_CENTER
            view._center_side = "left"
            view._update_info_label = lambda: None  # type: ignore[method-assign]
            view._update_image_info_labels = lambda: None  # type: ignore[method-assign]

            self.assertTrue(view._handle_center_key(compare_view.VK_RIGHT))
            self.assertEqual(view._center_side, "right")
            self.assertIs(view.left_preview.image_file, second)  # type: ignore[attr-defined]

            self.assertTrue(view._handle_center_key(compare_view.VK_SPACE))
            self.assertEqual(view._center_side, "left")
            self.assertIs(view.left_preview.image_file, first)  # type: ignore[attr-defined]

            self.assertTrue(view._handle_center_key(compare_view.VK_LEFT))
            self.assertEqual(view._center_side, "left")
        finally:
            compare_view.render_preview = original_render_preview  # type: ignore[assignment]

        self.assertEqual(render_calls[:4], [second, first, first, second])

    def test_center_layout_does_not_handle_center_keys_outside_center(self) -> None:
        view = compare_view.CompareView()
        view._layout_mode = compare_view.COMPARE_LAYOUT_SIDE_BY_SIDE

        self.assertFalse(view._handle_center_key(compare_view.VK_SPACE))

    def test_preview_navigation_callbacks_route_center_layout_keys(self) -> None:
        view = compare_view.CompareView()
        calls: list[int] = []
        view._handle_center_key = lambda key: calls.append(key) or True  # type: ignore[method-assign]

        view.left_preview.on_previous = lambda: view._handle_center_key(compare_view.VK_LEFT)
        view.left_preview.on_next = lambda: view._handle_center_key(compare_view.VK_RIGHT)
        view.left_preview.on_space = lambda: calls.append(compare_view.VK_SPACE) or True
        view.right_preview.on_previous = lambda: view._handle_center_key(compare_view.VK_LEFT)
        view.right_preview.on_next = lambda: view._handle_center_key(compare_view.VK_RIGHT)
        view.right_preview.on_space = lambda: calls.append(compare_view.VK_SPACE) or True

        view.left_preview.on_previous()
        view.left_preview.on_next()
        self.assertTrue(view.left_preview.on_space())
        view.right_preview.on_previous()
        view.right_preview.on_next()
        self.assertTrue(view.right_preview.on_space())

        self.assertEqual(
            calls,
            [
                compare_view.VK_LEFT,
                compare_view.VK_RIGHT,
                compare_view.VK_SPACE,
                compare_view.VK_LEFT,
                compare_view.VK_RIGHT,
                compare_view.VK_SPACE,
            ],
        )

    def test_preview_space_callback_can_override_default_next_navigation(self) -> None:
        preview = ImagePreview()
        calls: list[str] = []
        preview.on_space = lambda: calls.append("space") or True
        preview.on_next = lambda: calls.append("next")

        self.assertEqual(preview.handle_message(0, WM_KEYDOWN, VK_SPACE, 0), 0)
        self.assertEqual(calls, ["space"])

    def test_diff_emphasis_creates_highlighted_preview_files(self) -> None:
        original_cache_dir = compare_view.default_preview_cache_dir
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            left_path = temp_dir / "left.bmp"
            right_path = temp_dir / "right.bmp"
            Image.new("RGB", (8, 8), (255, 255, 255)).save(left_path)
            right_image = Image.new("RGB", (8, 8), (255, 255, 255))
            right_image.putpixel((4, 4), (0, 0, 0))
            right_image.save(right_path)
            left_result = PreviewResult(left_path, 8, 8)
            right_result = PreviewResult(right_path, 8, 8)

            try:
                compare_view.default_preview_cache_dir = lambda: temp_dir / "cache"  # type: ignore[assignment]
                diff_left, diff_right = compare_view._diff_emphasized_results(left_result, right_result)
            finally:
                compare_view.default_preview_cache_dir = original_cache_dir  # type: ignore[assignment]

            self.assertTrue(diff_left.ok)
            self.assertTrue(diff_right.ok)
            self.assertNotEqual(diff_left.cache_path, left_path)
            self.assertNotEqual(diff_right.cache_path, right_path)
            self.assertTrue(diff_left.cache_path and diff_left.cache_path.exists())
            self.assertTrue(diff_right.cache_path and diff_right.cache_path.exists())
            with Image.open(diff_left.cache_path) as highlighted:
                red, green, blue = highlighted.convert("RGB").getpixel((4, 4))

        self.assertGreater(red, green)
        self.assertGreater(red, blue)

    def test_diff_mask_creates_colored_preview_files_for_each_style(self) -> None:
        original_cache_dir = compare_view.default_preview_cache_dir
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            left_path = temp_dir / "left.bmp"
            right_path = temp_dir / "right.bmp"
            Image.new("RGB", (8, 8), (0, 0, 0)).save(left_path)
            right_image = Image.new("RGB", (8, 8), (0, 0, 0))
            right_image.putpixel((3, 3), (255, 255, 255))
            right_image.save(right_path)
            left_result = PreviewResult(left_path, 8, 8)
            right_result = PreviewResult(right_path, 8, 8)

            try:
                compare_view.default_preview_cache_dir = lambda: temp_dir / "cache"  # type: ignore[assignment]
                red_mask, _ = compare_view._diff_mask_results(
                    left_result,
                    right_result,
                    compare_view.MASK_STYLE_RED,
                    compare_view.MASK_THRESHOLD_MEDIUM,
                )
                green_mask, _ = compare_view._diff_mask_results(
                    left_result,
                    right_result,
                    compare_view.MASK_STYLE_GREEN,
                    compare_view.MASK_THRESHOLD_MEDIUM,
                )
                translucent_mask, _ = compare_view._diff_mask_results(
                    left_result,
                    right_result,
                    compare_view.MASK_STYLE_TRANSLUCENT,
                    compare_view.MASK_THRESHOLD_MEDIUM,
                )
            finally:
                compare_view.default_preview_cache_dir = original_cache_dir  # type: ignore[assignment]

            self.assertTrue(red_mask.cache_path and red_mask.cache_path.exists())
            self.assertTrue(green_mask.cache_path and green_mask.cache_path.exists())
            self.assertTrue(translucent_mask.cache_path and translucent_mask.cache_path.exists())
            with Image.open(red_mask.cache_path) as image:
                red_pixel = image.convert("RGB").getpixel((3, 3))
            with Image.open(green_mask.cache_path) as image:
                green_pixel = image.convert("RGB").getpixel((3, 3))
            with Image.open(translucent_mask.cache_path) as image:
                translucent_pixel = image.convert("RGB").getpixel((3, 3))

        self.assertGreater(red_pixel[0], red_pixel[1])
        self.assertGreater(green_pixel[1], green_pixel[0])
        self.assertNotEqual(translucent_pixel, (0, 0, 0))
        self.assertNotEqual(red_mask.cache_path, green_mask.cache_path)
        self.assertNotEqual(green_mask.cache_path, translucent_mask.cache_path)

    def test_diff_mask_threshold_controls_detected_area(self) -> None:
        original_cache_dir = compare_view.default_preview_cache_dir
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            left_path = temp_dir / "left.bmp"
            right_path = temp_dir / "right.bmp"
            Image.new("RGB", (4, 4), (0, 0, 0)).save(left_path)
            right_image = Image.new("RGB", (4, 4), (0, 0, 0))
            right_image.putpixel((1, 1), (30, 30, 30))
            right_image.save(right_path)
            left_result = PreviewResult(left_path, 4, 4)
            right_result = PreviewResult(right_path, 4, 4)

            try:
                compare_view.default_preview_cache_dir = lambda: temp_dir / "cache"  # type: ignore[assignment]
                weak_mask, _ = compare_view._diff_mask_results(
                    left_result,
                    right_result,
                    compare_view.MASK_STYLE_RED,
                    compare_view.MASK_THRESHOLD_WEAK,
                )
                strong_mask, _ = compare_view._diff_mask_results(
                    left_result,
                    right_result,
                    compare_view.MASK_STYLE_RED,
                    compare_view.MASK_THRESHOLD_STRONG,
                )
            finally:
                compare_view.default_preview_cache_dir = original_cache_dir  # type: ignore[assignment]

            with Image.open(weak_mask.cache_path) as image:
                weak_pixel = image.convert("RGB").getpixel((1, 1))
            with Image.open(strong_mask.cache_path) as image:
                strong_pixel = image.convert("RGB").getpixel((1, 1))

        self.assertEqual(weak_pixel, (0, 0, 0))
        self.assertGreater(strong_pixel[0], strong_pixel[1])

    def test_overlay_blend_creates_preview_files_for_each_ratio(self) -> None:
        original_cache_dir = compare_view.default_preview_cache_dir
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            left_path = temp_dir / "left.bmp"
            right_path = temp_dir / "right.bmp"
            Image.new("RGB", (4, 4), (0, 0, 0)).save(left_path)
            Image.new("RGB", (4, 4), (200, 200, 200)).save(right_path)
            left_result = PreviewResult(left_path, 4, 4)
            right_result = PreviewResult(right_path, 4, 4)

            try:
                compare_view.default_preview_cache_dir = lambda: temp_dir / "cache"  # type: ignore[assignment]
                blended_25, _ = compare_view._overlay_blended_results(left_result, right_result, 25)
                blended_50, _ = compare_view._overlay_blended_results(left_result, right_result, 50)
                blended_75, _ = compare_view._overlay_blended_results(left_result, right_result, 75)
            finally:
                compare_view.default_preview_cache_dir = original_cache_dir  # type: ignore[assignment]

            self.assertTrue(blended_25.ok)
            self.assertTrue(blended_50.ok)
            self.assertTrue(blended_75.ok)
            self.assertNotEqual(blended_25.cache_path, left_path)
            self.assertNotEqual(blended_25.cache_path, blended_50.cache_path)
            with Image.open(blended_25.cache_path) as image_25:
                pixel_25 = image_25.convert("RGB").getpixel((0, 0))[0]
            with Image.open(blended_50.cache_path) as image_50:
                pixel_50 = image_50.convert("RGB").getpixel((0, 0))[0]
            with Image.open(blended_75.cache_path) as image_75:
                pixel_75 = image_75.convert("RGB").getpixel((0, 0))[0]

        self.assertLess(pixel_25, pixel_50)
        self.assertLess(pixel_50, pixel_75)

    def test_overlay_blend_invalid_ratio_falls_back_to_half(self) -> None:
        original_cache_dir = compare_view.default_preview_cache_dir
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            left_path = temp_dir / "left.bmp"
            right_path = temp_dir / "right.bmp"
            Image.new("RGB", (4, 4), (0, 0, 0)).save(left_path)
            Image.new("RGB", (4, 4), (200, 200, 200)).save(right_path)
            left_result = PreviewResult(left_path, 4, 4)
            right_result = PreviewResult(right_path, 4, 4)

            try:
                compare_view.default_preview_cache_dir = lambda: temp_dir / "cache"  # type: ignore[assignment]
                fallback, _ = compare_view._overlay_blended_results(left_result, right_result, 99)
            finally:
                compare_view.default_preview_cache_dir = original_cache_dir  # type: ignore[assignment]

            with Image.open(fallback.cache_path) as image:
                pixel = image.convert("RGB").getpixel((0, 0))[0]

        self.assertEqual(pixel, 100)

    def test_sync_off_zoom_updates_only_source_side(self) -> None:
        original_render_preview = compare_view.render_preview
        first = _image_file(Path("C:/images/a.jpg"), 1)
        second = _image_file(Path("C:/images/b.jpg"), 2)
        render_calls: list[tuple[ImageFile, str]] = []

        def fake_render_preview(image_file: ImageFile, width: int, height: int, *args: object, **kwargs: object) -> PreviewResult:
            render_calls.append((image_file, kwargs["display_mode"]))
            return PreviewResult(Path(f"C:/cache/{image_file.name}.bmp"), 640, 480)

        try:
            compare_view.render_preview = fake_render_preview  # type: ignore[assignment]
            view = compare_view.CompareView()
            view.left_preview = FakePreview()  # type: ignore[assignment]
            view.right_preview = FakePreview()  # type: ignore[assignment]
            view._left_image = first
            view._right_image = second
            view._sync_enabled = False
            view._left_display_mode = PREVIEW_MODE_ORIGINAL
            view._right_display_mode = PREVIEW_MODE_ORIGINAL

            view._zoom_in("left")
        finally:
            compare_view.render_preview = original_render_preview  # type: ignore[assignment]

        self.assertEqual(view._left_display_mode, PREVIEW_MODE_SCALE_200)
        self.assertEqual(view._right_display_mode, PREVIEW_MODE_ORIGINAL)
        self.assertEqual(render_calls, [(first, PREVIEW_MODE_SCALE_200)])

    def test_sync_off_pan_does_not_update_opposite_preview(self) -> None:
        view = compare_view.CompareView()
        view.left_preview = FakePreview()  # type: ignore[assignment]
        view.right_preview = FakePreview()  # type: ignore[assignment]
        view.left_preview._pan_ratio = (0.5, -0.25)  # type: ignore[attr-defined]
        view._sync_enabled = False

        view._sync_pan_from(view.left_preview, 120, -80)

        self.assertEqual(view.right_preview.pan_ratios, [])  # type: ignore[attr-defined]

    def test_toggle_sync_button_switches_label_and_syncs_modes(self) -> None:
        view = compare_view.CompareView()
        captured: dict[int, str] = {}
        view.sync_toggle_button = 102
        view._set_label = lambda hwnd, text: captured.__setitem__(hwnd, text) if hwnd else None  # type: ignore[method-assign]
        view._render_current_pair = lambda reset_pan=False: None  # type: ignore[method-assign]
        view._sync_enabled = False
        view._left_display_mode = PREVIEW_MODE_SCALE_200
        view._right_display_mode = PREVIEW_MODE_ORIGINAL

        self.assertTrue(view._toggle_sync_enabled())

        self.assertTrue(view._sync_enabled)
        self.assertEqual(view._right_display_mode, PREVIEW_MODE_SCALE_200)
        self.assertEqual(captured[102], "同期ON")

    def test_swap_sides_exchanges_images_info_modes_and_pan(self) -> None:
        original_render_preview = compare_view.render_preview
        with tempfile.TemporaryDirectory() as temp:
            left_path = Path(temp) / "left.jpg"
            right_path = Path(temp) / "right.jpg"
            Image.new("RGB", (320, 240), (20, 40, 60)).save(left_path)
            Image.new("RGB", (640, 480), (60, 40, 20)).save(right_path)
            left_image = ImageFile(left_path, left_path.name, left_path.suffix, 1024, 1.0)
            right_image = ImageFile(right_path, right_path.name, right_path.suffix, 1536, 2.0)
            render_calls: list[tuple[ImageFile, str]] = []

            def fake_render_preview(image_file: ImageFile, width: int, height: int, *args: object, **kwargs: object) -> PreviewResult:
                render_calls.append((image_file, kwargs["display_mode"]))
                return PreviewResult(Path(f"C:/cache/{image_file.name}.bmp"), 640, 480)

            try:
                compare_view.render_preview = fake_render_preview  # type: ignore[assignment]
                view = compare_view.CompareView()
                captured: dict[int, str] = {}
                view.left_label = 101
                view.left_detail_label = 102
                view.right_label = 103
                view.right_detail_label = 104
                view.info_label = 105
                view.left_preview = FakePreview()  # type: ignore[assignment]
                view.right_preview = FakePreview()  # type: ignore[assignment]
                view.left_preview._pan_ratio = (0.25, 0.1)  # type: ignore[attr-defined]
                view.right_preview._pan_ratio = (-0.5, -0.2)  # type: ignore[attr-defined]
                view._left_image = left_image
                view._right_image = right_image
                view._left_display_mode = PREVIEW_MODE_SCALE_200
                view._right_display_mode = PREVIEW_MODE_ORIGINAL
                view._sync_enabled = False
                view._set_label = lambda hwnd, text: captured.__setitem__(hwnd, text) if hwnd else None  # type: ignore[method-assign]

                self.assertTrue(view._swap_sides())
            finally:
                compare_view.render_preview = original_render_preview  # type: ignore[assignment]

        self.assertIs(view._left_image, right_image)
        self.assertIs(view._right_image, left_image)
        self.assertEqual(view._left_display_mode, PREVIEW_MODE_ORIGINAL)
        self.assertEqual(view._right_display_mode, PREVIEW_MODE_SCALE_200)
        self.assertFalse(view._sync_enabled)
        self.assertEqual(captured[101], "左: right.jpg")
        self.assertIn("640 × 480px", captured[102])
        self.assertEqual(captured[103], "右: left.jpg")
        self.assertIn("320 × 240px", captured[104])
        self.assertEqual(view.left_preview.pan_ratios[-1], (-0.5, -0.2))  # type: ignore[attr-defined]
        self.assertEqual(view.right_preview.pan_ratios[-1], (0.25, 0.1))  # type: ignore[attr-defined]
        self.assertEqual(
            render_calls,
            [
                (right_image, PREVIEW_MODE_ORIGINAL),
                (left_image, PREVIEW_MODE_SCALE_200),
            ],
        )

    def test_swap_sides_without_images_is_safe(self) -> None:
        view = compare_view.CompareView()

        self.assertFalse(view._swap_sides())

    def test_copy_left_and_right_image_paths(self) -> None:
        left = _image_file(Path("C:/images/left.jpg"), 1)
        right = _image_file(Path("C:/images/right.jpg"), 2)
        view = compare_view.CompareView()
        copied: list[str] = []
        messages: list[str] = []
        view._left_image = left
        view._right_image = right
        view._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
        view._show_temporary_message = lambda message, duration_ms=0: messages.append(message)  # type: ignore[method-assign]

        self.assertTrue(view._copy_left_image_path())
        self.assertTrue(view._copy_right_image_path())

        self.assertEqual(copied, [str(left.path), str(right.path)])
        self.assertEqual(messages, ["左画像パスをコピーしました", "右画像パスをコピーしました"])

    def test_copy_paths_follow_swapped_sides(self) -> None:
        original_render_preview = compare_view.render_preview
        left = _image_file(Path("C:/images/left.jpg"), 1)
        right = _image_file(Path("C:/images/right.jpg"), 2)
        copied: list[str] = []

        def fake_render_preview(image_file: ImageFile, width: int, height: int, *args: object, **kwargs: object) -> PreviewResult:
            return PreviewResult(Path(f"C:/cache/{image_file.name}.bmp"), 640, 480)

        try:
            compare_view.render_preview = fake_render_preview  # type: ignore[assignment]
            view = compare_view.CompareView()
            view.left_preview = FakePreview()  # type: ignore[assignment]
            view.right_preview = FakePreview()  # type: ignore[assignment]
            view._left_image = left
            view._right_image = right
            view._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
            view._show_temporary_message = lambda message, duration_ms=0: None  # type: ignore[method-assign]
            view._update_image_info_labels = lambda: None  # type: ignore[method-assign]

            self.assertTrue(view._swap_sides())
            self.assertTrue(view._copy_left_image_path())
            self.assertTrue(view._copy_right_image_path())
        finally:
            compare_view.render_preview = original_render_preview  # type: ignore[assignment]

        self.assertEqual(copied, [str(right.path), str(left.path)])

    def test_copy_image_path_without_target_is_safe(self) -> None:
        view = compare_view.CompareView()
        messages: list[str] = []
        view._show_temporary_message = lambda message, duration_ms=0: messages.append(message)  # type: ignore[method-assign]

        self.assertFalse(view._copy_left_image_path())

        self.assertEqual(messages, ["左画像パスをコピーする画像がありません"])

    def test_copy_message_timer_restores_compare_info(self) -> None:
        view = compare_view.CompareView()
        captured: dict[int, str] = {}
        restored: list[bool] = []
        view.info_label = 101
        view._set_label = lambda hwnd, text: captured.__setitem__(hwnd, text) if hwnd else None  # type: ignore[method-assign]
        view._update_info_label = lambda: restored.append(True)  # type: ignore[method-assign]

        view._show_temporary_message("左画像パスをコピーしました")

        self.assertEqual(captured[101], "左画像パスをコピーしました")
        self.assertEqual(view.handle_message(0, compare_view.WM_TIMER, compare_view.COPY_MESSAGE_TIMER_ID, 0), 0)
        self.assertEqual(restored, [True])

    def test_image_info_text_includes_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            image_path = Path(temp) / "info.jpg"
            Image.new("RGB", (320, 240), (20, 40, 60)).save(image_path)
            image_file = ImageFile(image_path, image_path.name, image_path.suffix, 2048, 1.0)

            info_text = compare_view._image_info_text(image_file)

        self.assertIn("ファイル名: info.jpg", info_text)
        self.assertIn("画像サイズ: 320 × 240px", info_text)
        self.assertIn("ファイルサイズ: 2.0 KB", info_text)
        self.assertIn(f"フルパス: {image_path}", info_text)

    def test_copy_left_and_right_image_info(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            left_path = Path(temp) / "left_info.jpg"
            right_path = Path(temp) / "right_info.jpg"
            Image.new("RGB", (320, 240), (20, 40, 60)).save(left_path)
            Image.new("RGB", (640, 480), (60, 40, 20)).save(right_path)
            left = ImageFile(left_path, left_path.name, left_path.suffix, 2048, 1.0)
            right = ImageFile(right_path, right_path.name, right_path.suffix, 4096, 2.0)
            view = compare_view.CompareView()
            copied: list[str] = []
            messages: list[str] = []
            view._left_image = left
            view._right_image = right
            view._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
            view._show_temporary_message = lambda message, duration_ms=0: messages.append(message)  # type: ignore[method-assign]

            self.assertTrue(view._copy_left_image_info())
            self.assertTrue(view._copy_right_image_info())

        self.assertIn("ファイル名: left_info.jpg", copied[0])
        self.assertIn("画像サイズ: 320 × 240px", copied[0])
        self.assertIn("ファイルサイズ: 2.0 KB", copied[0])
        self.assertIn(f"フルパス: {left_path}", copied[0])
        self.assertIn("ファイル名: right_info.jpg", copied[1])
        self.assertIn("画像サイズ: 640 × 480px", copied[1])
        self.assertIn("ファイルサイズ: 4.0 KB", copied[1])
        self.assertIn(f"フルパス: {right_path}", copied[1])
        self.assertEqual(messages, ["左画像情報をコピーしました", "右画像情報をコピーしました"])

    def test_copy_info_follows_swapped_sides(self) -> None:
        original_render_preview = compare_view.render_preview
        with tempfile.TemporaryDirectory() as temp:
            left_path = Path(temp) / "left_info.jpg"
            right_path = Path(temp) / "right_info.jpg"
            Image.new("RGB", (320, 240), (20, 40, 60)).save(left_path)
            Image.new("RGB", (640, 480), (60, 40, 20)).save(right_path)
            left = ImageFile(left_path, left_path.name, left_path.suffix, 2048, 1.0)
            right = ImageFile(right_path, right_path.name, right_path.suffix, 4096, 2.0)
            copied: list[str] = []

            def fake_render_preview(image_file: ImageFile, width: int, height: int, *args: object, **kwargs: object) -> PreviewResult:
                return PreviewResult(Path(f"C:/cache/{image_file.name}.bmp"), 640, 480)

            try:
                compare_view.render_preview = fake_render_preview  # type: ignore[assignment]
                view = compare_view.CompareView()
                view.left_preview = FakePreview()  # type: ignore[assignment]
                view.right_preview = FakePreview()  # type: ignore[assignment]
                view._left_image = left
                view._right_image = right
                view._copy_text_to_clipboard = lambda text: copied.append(text)  # type: ignore[method-assign]
                view._show_temporary_message = lambda message, duration_ms=0: None  # type: ignore[method-assign]
                view._update_image_info_labels = lambda: None  # type: ignore[method-assign]

                self.assertTrue(view._swap_sides())
                self.assertTrue(view._copy_left_image_info())
                self.assertTrue(view._copy_right_image_info())
            finally:
                compare_view.render_preview = original_render_preview  # type: ignore[assignment]

        self.assertIn("ファイル名: right_info.jpg", copied[0])
        self.assertIn(f"フルパス: {right_path}", copied[0])
        self.assertIn("ファイル名: left_info.jpg", copied[1])
        self.assertIn(f"フルパス: {left_path}", copied[1])

    def test_copy_image_info_without_target_is_safe(self) -> None:
        view = compare_view.CompareView()
        messages: list[str] = []
        view._show_temporary_message = lambda message, duration_ms=0: messages.append(message)  # type: ignore[method-assign]

        self.assertFalse(view._copy_left_image_info())

        self.assertEqual(messages, ["左画像情報をコピーする画像がありません"])

    def test_preview_context_menu_routes_to_image_info_copy(self) -> None:
        view = compare_view.CompareView()
        calls: list[str] = []
        view._show_info_context_menu = lambda side, x, y, owner_hwnd=None: compare_view.CONTEXT_COPY_IMAGE_INFO_ID  # type: ignore[method-assign]
        view._copy_image_info = lambda side: calls.append(side) or True  # type: ignore[method-assign]

        view._handle_preview_context_menu("left", None, 10, 20)
        view._handle_preview_context_menu("right", None, 10, 20)

        self.assertEqual(calls, ["left", "right"])

    def test_image_detail_text_shows_dimensions_and_file_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            image_path = Path(temp) / "detail.jpg"
            Image.new("RGB", (320, 240), (20, 40, 60)).save(image_path)
            image_file = _image_file(image_path, 1)
            image_file = ImageFile(image_path, image_path.name, image_path.suffix, 2048, image_file.mtime)

            detail_text = compare_view._image_detail_text(image_file)

        self.assertIn("画像サイズ: 320 × 240px", detail_text)
        self.assertIn("ファイルサイズ: 2.0 KB", detail_text)

    def test_update_image_info_labels_sets_left_and_right_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            left_path = Path(temp) / "left.jpg"
            right_path = Path(temp) / "right.jpg"
            Image.new("RGB", (320, 240), (20, 40, 60)).save(left_path)
            Image.new("RGB", (640, 480), (60, 40, 20)).save(right_path)
            left_image = ImageFile(left_path, left_path.name, left_path.suffix, 1024, 1.0)
            right_image = ImageFile(right_path, right_path.name, right_path.suffix, 1536, 2.0)
            view = compare_view.CompareView()
            captured: dict[int, str] = {}
            view.left_label = 101
            view.left_detail_label = 102
            view.right_label = 103
            view.right_detail_label = 104
            view._left_image = left_image
            view._right_image = right_image
            view._set_label = lambda hwnd, text: captured.__setitem__(hwnd, text) if hwnd else None  # type: ignore[method-assign]

            view._update_image_info_labels()

        self.assertEqual(captured[101], "左: left.jpg")
        self.assertIn("320 × 240px", captured[102])
        self.assertEqual(captured[103], "右: right.jpg")
        self.assertIn("640 × 480px", captured[104])

    def test_center_reset_sets_both_compare_panes_to_center(self) -> None:
        view = compare_view.CompareView()
        view.left_preview = FakePreview()  # type: ignore[assignment]
        view.right_preview = FakePreview()  # type: ignore[assignment]
        view.left_preview._pan_ratio = (0.5, 0.5)  # type: ignore[attr-defined]
        view.right_preview._pan_ratio = (-0.5, -0.5)  # type: ignore[attr-defined]
        view._update_info_label = lambda: None  # type: ignore[method-assign]

        self.assertTrue(view._reset_center())

        self.assertEqual(view.left_preview.pan_ratios[-1], (0.0, 0.0))  # type: ignore[attr-defined]
        self.assertEqual(view.right_preview.pan_ratios[-1], (0.0, 0.0))  # type: ignore[attr-defined]

    def test_center_reset_button_routes_to_handler(self) -> None:
        view = compare_view.CompareView()
        calls: list[bool] = []
        view._reset_center = lambda: calls.append(True) or True  # type: ignore[method-assign]

        w_param = compare_view.CENTER_RESET_BUTTON_ID | (compare_view.BN_CLICKED << 16)

        self.assertEqual(view.handle_message(0, compare_view.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [True])

    def test_sync_toggle_button_routes_to_handler(self) -> None:
        view = compare_view.CompareView()
        calls: list[bool] = []
        view._toggle_sync_enabled = lambda: calls.append(True) or True  # type: ignore[method-assign]

        w_param = compare_view.SYNC_TOGGLE_BUTTON_ID | (compare_view.BN_CLICKED << 16)

        self.assertEqual(view.handle_message(0, compare_view.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [True])

    def test_swap_button_routes_to_handler(self) -> None:
        view = compare_view.CompareView()
        calls: list[bool] = []
        view._swap_sides = lambda: calls.append(True) or True  # type: ignore[method-assign]

        w_param = compare_view.SWAP_BUTTON_ID | (compare_view.BN_CLICKED << 16)

        self.assertEqual(view.handle_message(0, compare_view.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [True])

    def test_view_mode_button_routes_to_handler(self) -> None:
        view = compare_view.CompareView()
        calls: list[bool] = []
        view._cycle_view_mode = lambda: calls.append(True) or True  # type: ignore[method-assign]

        w_param = compare_view.VIEW_MODE_BUTTON_ID | (compare_view.BN_CLICKED << 16)

        self.assertEqual(view.handle_message(0, compare_view.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [True])

    def test_layout_mode_button_routes_to_handler(self) -> None:
        view = compare_view.CompareView()
        calls: list[bool] = []
        view._cycle_layout_mode = lambda: calls.append(True) or True  # type: ignore[method-assign]

        w_param = compare_view.LAYOUT_MODE_BUTTON_ID | (compare_view.BN_CLICKED << 16)

        self.assertEqual(view.handle_message(0, compare_view.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [True])

    def test_overlay_ratio_button_routes_to_handler(self) -> None:
        view = compare_view.CompareView()
        calls: list[bool] = []
        view._cycle_overlay_ratio = lambda: calls.append(True) or True  # type: ignore[method-assign]

        w_param = compare_view.OVERLAY_RATIO_BUTTON_ID | (compare_view.BN_CLICKED << 16)

        self.assertEqual(view.handle_message(0, compare_view.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [True])

    def test_guide_mode_button_routes_to_handler(self) -> None:
        view = compare_view.CompareView()
        calls: list[bool] = []
        view._cycle_guide_mode = lambda: calls.append(True) or True  # type: ignore[method-assign]

        w_param = compare_view.GUIDE_MODE_BUTTON_ID | (compare_view.BN_CLICKED << 16)

        self.assertEqual(view.handle_message(0, compare_view.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [True])

    def test_mask_style_button_routes_to_handler(self) -> None:
        view = compare_view.CompareView()
        calls: list[bool] = []
        view._cycle_mask_style = lambda: calls.append(True) or True  # type: ignore[method-assign]

        w_param = compare_view.MASK_STYLE_BUTTON_ID | (compare_view.BN_CLICKED << 16)

        self.assertEqual(view.handle_message(0, compare_view.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [True])

    def test_mask_threshold_button_routes_to_handler(self) -> None:
        view = compare_view.CompareView()
        calls: list[bool] = []
        view._cycle_mask_threshold = lambda: calls.append(True) or True  # type: ignore[method-assign]

        w_param = compare_view.MASK_THRESHOLD_BUTTON_ID | (compare_view.BN_CLICKED << 16)

        self.assertEqual(view.handle_message(0, compare_view.WM_COMMAND, w_param, 0), 0)
        self.assertEqual(calls, [True])

    def test_copy_buttons_route_to_handlers(self) -> None:
        view = compare_view.CompareView()
        calls: list[str] = []
        view._copy_left_image_path = lambda: calls.append("left") or True  # type: ignore[method-assign]
        view._copy_right_image_path = lambda: calls.append("right") or True  # type: ignore[method-assign]

        left_w_param = compare_view.LEFT_COPY_PATH_BUTTON_ID | (compare_view.BN_CLICKED << 16)
        right_w_param = compare_view.RIGHT_COPY_PATH_BUTTON_ID | (compare_view.BN_CLICKED << 16)

        self.assertEqual(view.handle_message(0, compare_view.WM_COMMAND, left_w_param, 0), 0)
        self.assertEqual(view.handle_message(0, compare_view.WM_COMMAND, right_w_param, 0), 0)
        self.assertEqual(calls, ["left", "right"])


if __name__ == "__main__":
    unittest.main()

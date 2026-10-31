# common/utils/screenshot_comparator.py
"""
截图比对工具（视觉回归）

只依赖 Pillow + numpy：
1. 按像素统计差异比例，允许传入 max_diff_pixel_ratio 作为容差
2. 单像素允许微小色差（pixel_threshold），滤掉 GPU 渲染 / 抗锯齿噪声
3. 支持矩形忽略区域，用于遮掉 Canvas 上的动态弹窗
4. 生成差异图（差异像素标红、基准图压暗），便于在 Allure 里定位问题
"""
import io
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np
from PIL import Image


# 忽略区域：(x, y, width, height)，坐标基于截图左上角
IgnoreRegion = Tuple[int, int, int, int]


@dataclass
class ScreenshotDiffResult:
    """一次截图比对的结果"""

    passed: bool
    diff_ratio: float
    diff_pixels: int
    total_pixels: int
    diff_image: Optional[bytes] = None

    @property
    def diff_percent(self) -> float:
        return self.diff_ratio * 100


def compare_screenshots(
    actual: bytes,
    baseline: bytes,
    max_diff_pixel_ratio: float = 0.02,
    pixel_threshold: int = 24,
    ignore_regions: Iterable[IgnoreRegion] = (),
) -> ScreenshotDiffResult:
    """
    比较两张 PNG 截图。

    Args:
        actual: 本次截图（PNG bytes）
        baseline: 基准图（PNG bytes）
        max_diff_pixel_ratio: 允许的差异像素比例，0.02 表示 2%
        pixel_threshold: 单像素单通道允许的最大差值（0-255），用于吸收渲染噪声
        ignore_regions: 不参与比对的矩形区域

    Returns:
        ScreenshotDiffResult

    Raises:
        ValueError: 两张截图尺寸不一致
    """
    actual_img = Image.open(io.BytesIO(actual)).convert("RGB")
    baseline_img = Image.open(io.BytesIO(baseline)).convert("RGB")

    if actual_img.size != baseline_img.size:
        raise ValueError(
            f"截图尺寸不一致: actual={actual_img.size}, baseline={baseline_img.size}"
        )

    width, height = baseline_img.size
    actual_arr = np.asarray(actual_img, dtype=np.int16)
    baseline_arr = np.asarray(baseline_img, dtype=np.int16)

    # 任一通道差值超过阈值才算“有差异”
    diff_mask = np.max(np.abs(actual_arr - baseline_arr), axis=2) > pixel_threshold
    _apply_ignore_regions(diff_mask, ignore_regions, width, height)

    diff_pixels = int(diff_mask.sum())
    total_pixels = width * height
    diff_ratio = diff_pixels / total_pixels if total_pixels else 0.0

    return ScreenshotDiffResult(
        passed=diff_ratio <= max_diff_pixel_ratio,
        diff_ratio=diff_ratio,
        diff_pixels=diff_pixels,
        total_pixels=total_pixels,
        diff_image=_render_diff_image(baseline_img, diff_mask) if diff_pixels else None,
    )


def _apply_ignore_regions(
    diff_mask: np.ndarray,
    ignore_regions: Iterable[IgnoreRegion],
    width: int,
    height: int,
):
    """把忽略区域内的差异抹掉（原地修改）"""
    for x, y, region_width, region_height in ignore_regions or ():
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2 = min(width, int(x + region_width))
        y2 = min(height, int(y + region_height))
        if x2 > x1 and y2 > y1:
            diff_mask[y1:y2, x1:x2] = False


def _render_diff_image(baseline_img: Image.Image, diff_mask: np.ndarray) -> bytes:
    """生成差异图：基准图压暗做底，差异像素标红"""
    base = baseline_img.convert("L").point(lambda value: int(value * 0.35)).convert("RGB")
    diff_arr = np.asarray(base).copy()
    diff_arr[diff_mask] = (255, 0, 0)

    buffer = io.BytesIO()
    Image.fromarray(diff_arr).save(buffer, format="PNG")
    return buffer.getvalue()

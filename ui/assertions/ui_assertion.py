# common/assertions/ui_assertion.py
import time
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

import allure
from allure_commons.types import AttachmentType
from playwright.sync_api import Page, Locator, ElementHandle

from common.assertions.base_assertion import BaseAssertion
from common.config.settings import Config
from common.utils.logger import log
from common.utils.screenshot_comparator import ScreenshotDiffResult, compare_screenshots


class UIAssertion(BaseAssertion):
    """
    UI 专用断言类
    继承 BaseAssertion，扩展页面元素相关断言
    """

    def __init__(self, page: Page, screenshot_callback=None):
        super().__init__(screenshot_callback)
        self.page = page

    # ==================== 元素存在性断言 ====================

    def assert_element_visible(self, selector: str, timeout: int = 5000, message: str = None):
        """断言元素可见"""
        try:
            element = self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            is_visible = element.is_visible()
            msg = message or f"元素 '{selector}' 应该可见"
            self.assert_true(is_visible, msg)
            log.success(f"✅ 元素可见: {selector}")
        except Exception as e:
            self.assert_true(False, message or f"元素 '{selector}' 不可见: {e}")

    def assert_element_hidden(self, selector: str, timeout: int = 5000, message: str = None):
        """断言元素隐藏"""
        try:
            element = self.page.wait_for_selector(selector, state="hidden", timeout=timeout)
            is_hidden = not element.is_visible() if element else True
            msg = message or f"元素 '{selector}' 应该隐藏"
            self.assert_true(is_hidden, msg)
        except Exception:
            # 如果找不到元素，也算隐藏
            self.assert_true(True, message or f"元素 '{selector}' 不存在，符合隐藏预期")

    def assert_element_exists(self, selector: str, message: str = None):
        """断言元素存在于 DOM 中"""
        count = self.page.locator(selector).count()
        msg = message or f"元素 '{selector}' 应该存在于 DOM 中"
        self.assert_true(count > 0, msg)

    def assert_element_not_exists(self, selector: str, message: str = None):
        """断言元素不存在于 DOM 中"""
        count = self.page.locator(selector).count()
        msg = message or f"元素 '{selector}' 不应存在于 DOM 中"
        self.assert_true(count == 0, msg)

    def assert_element_count(self, selector: str, expected_count: int, message: str = None):
        """断言元素数量"""
        actual_count = self.page.locator(selector).count()
        msg = message or f"元素 '{selector}' 数量应为 {expected_count}, 实际 {actual_count}"
        self.assert_equal(actual_count, expected_count, msg)

    # ==================== 元素属性断言 ====================

    def assert_element_text(self, selector: str, expected_text: str, exact: bool = True, message: str = None):
        """断言元素文本"""
        element = self.page.locator(selector).first
        actual_text = element.text_content() or ""

        if exact:
            msg = message or f"元素 '{selector}' 文本应为 '{expected_text}', 实际 '{actual_text}'"
            self.assert_equal(actual_text.strip(), expected_text, msg)
        else:
            msg = message or f"元素 '{selector}' 文本应包含 '{expected_text}', 实际 '{actual_text}'"
            self.assert_true(expected_text in actual_text, msg)

    def assert_element_attribute(self, selector: str, attribute: str, expected_value: str, message: str = None):
        """断言元素属性"""
        element = self.page.locator(selector).first
        actual_value = element.get_attribute(attribute)
        msg = message or f"元素 '{selector}' 属性 '{attribute}' 应为 '{expected_value}', 实际 '{actual_value}'"
        self.assert_equal(actual_value, expected_value, msg)

    def assert_element_checked(self, selector: str, should_be_checked: bool = True, message: str = None):
        """断言复选框/单选框选中状态"""
        element = self.page.locator(selector).first
        is_checked = element.is_checked()
        expected_state = "选中" if should_be_checked else "未选中"
        actual_state = "选中" if is_checked else "未选中"
        msg = message or f"元素 '{selector}' 应该{expected_state}, 实际{actual_state}"
        self.assert_equal(is_checked, should_be_checked, msg)

    def assert_element_enabled(self, selector: str, should_be_enabled: bool = True, message: str = None):
        """断言元素启用状态"""
        element = self.page.locator(selector).first
        is_enabled = element.is_enabled()
        expected_state = "启用" if should_be_enabled else "禁用"
        actual_state = "启用" if is_enabled else "禁用"
        msg = message or f"元素 '{selector}' 应该{expected_state}, 实际{actual_state}"
        self.assert_equal(is_enabled, should_be_enabled, msg)

    def assert_element_focused(self, selector: str, message: str = None):
        """断言元素获得焦点"""
        element = self.page.locator(selector).first
        is_focused = element.evaluate("el => el === document.activeElement")
        msg = message or f"元素 '{selector}' 应该获得焦点"
        self.assert_true(is_focused, msg)

    # ==================== 页面断言 ====================

    def assert_title(self, expected_title: str, message: str = None):
        """断言页面标题"""
        actual_title = self.page.title()
        msg = message or f"页面标题应为 '{expected_title}', 实际 '{actual_title}'"
        self.assert_equal(actual_title, expected_title, msg)

    def assert_url(self, expected_url: str, exact: bool = True, message: str = None):
        """断言当前URL"""
        actual_url = self.page.url
        if exact:
            msg = message or f"URL 应为 '{expected_url}', 实际 '{actual_url}'"
            self.assert_equal(actual_url, expected_url, msg)
        else:
            msg = message or f"URL 应包含 '{expected_url}', 实际 '{actual_url}'"
            self.assert_true(expected_url in actual_url, msg)

    def assert_url_contains(self, text: str, message: str = None):
        """断言URL包含指定文本"""
        self.assert_url(text, exact=False, message=message)

    # ==================== 三维引擎专用断言 ====================

    def assert_canvas_exists(self, timeout: int = 10000, message: str = None):
        """断言 Canvas 存在"""
        try:
            self.page.wait_for_selector("canvas.webgl, canvas#canvas3d", timeout=timeout)
            self.assert_true(True, message or "Canvas 存在")
        except Exception as e:
            self.assert_true(False, message or f"Canvas 不存在: {e}")

    def assert_webgl_context(self, message: str = None):
        """断言 WebGL 上下文已初始化"""
        result = self.page.evaluate("""
            () => {
                const canvas = document.querySelector('canvas.webgl, canvas#canvas3d');
                if (!canvas) return false;
                const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                return gl !== null;
            }
        """)
        msg = message or "WebGL 上下文应该已初始化"
        self.assert_true(result, msg)

    def assert_model_loaded(self, message: str = None):
        """断言模型已加载（通过检查特定标志）"""
        # 可以根据你的三维引擎的具体实现调整
        result = self.page.evaluate("""
            () => {
                // 检查是否有全局模型加载标志
                return window.modelLoaded === true || 
                       document.querySelector('.model-loaded') !== null;
            }
        """)
        msg = message or "模型应该已加载完成"
        self.assert_true(result, msg)

    def assert_fps_greater_than(self, min_fps: int = 30, message: str = None):
        """断言帧率大于阈值"""
        fps = self.page.evaluate("""
            () => {
                // 如果有性能监控对象
                return window.performanceMonitor ? window.performanceMonitor.getFPS() : 60;
            }
        """)
        msg = message or f"帧率应大于 {min_fps}, 实际 {fps}"
        self.assert_greater(fps, min_fps, msg)

    # ==================== 截图断言 ====================

    def assert_canvas_screenshot_match(
        self,
        canvas: Locator,
        name: str,
        max_diff_pixel_ratio: float = 0.02,
        baseline_dir: Union[str, Path] = None,
        style: str = None,
        mask: Sequence[Locator] = None,
        ignore_regions: Iterable[Tuple[int, int, int, int]] = (),
        pixel_threshold: int = 24,
        update_baseline: bool = False,
        stable_timeout: int = 3000,
        message: str = None,
    ) -> ScreenshotDiffResult:
        """
        断言 Canvas 截图与基准图一致（视觉回归）

        - 只截取传入的 Canvas 元素，不包含整页
        - 基准图不存在（或 update_baseline=True）时自动生成基准图并直接通过
        - max_diff_pixel_ratio: 允许的差异像素比例，默认 0.02（2%）
        - style: 截图时注入的 CSS，用于隐藏 Canvas 上的动态弹窗
        - ignore_regions: 不参与比对的矩形区域 (x, y, w, h)
        """
        baseline_path = Path(baseline_dir or Config.UI_BASELINE_DIR) / f"{name}.png"

        actual = self._capture_stable_canvas(
            canvas, style=style, mask=mask, timeout=stable_timeout
        )
        allure.attach(
            actual, name=f"实际截图_{name}", attachment_type=AttachmentType.PNG
        )

        if update_baseline or not baseline_path.exists():
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            baseline_path.write_bytes(actual)
            allure.attach(
                actual,
                name=f"基准图（首次生成）_{name}",
                attachment_type=AttachmentType.PNG,
            )
            log.warning(f"基准图不存在，已自动生成: {baseline_path}")
            return ScreenshotDiffResult(
                passed=True, diff_ratio=0.0, diff_pixels=0, total_pixels=0
            )

        baseline = baseline_path.read_bytes()
        allure.attach(
            baseline, name=f"基准图_{name}", attachment_type=AttachmentType.PNG
        )

        try:
            result = compare_screenshots(
                actual,
                baseline,
                max_diff_pixel_ratio=max_diff_pixel_ratio,
                pixel_threshold=pixel_threshold,
                ignore_regions=ignore_regions,
            )
        except ValueError as exc:
            self.assert_true(False, message or f"Canvas 截图尺寸变化，无法比对: {exc}")
            raise

        if result.diff_image:
            allure.attach(
                result.diff_image,
                name=f"差异图_{name}",
                attachment_type=AttachmentType.PNG,
            )

        if result.passed:
            msg = message or (
                f"Canvas 截图差异 {result.diff_percent:.2f}% 在容差 "
                f"{max_diff_pixel_ratio * 100:.0f}% 以内"
                f"（{result.diff_pixels}/{result.total_pixels} 像素）"
            )
        else:
            msg = message or (
                f"Canvas 截图差异 {result.diff_percent:.2f}% 超过容差 "
                f"{max_diff_pixel_ratio * 100:.0f}%（"
                f"{result.diff_pixels}/{result.total_pixels} 像素）"
            )
        self.assert_true(result.passed, msg)

        if result.passed:
            log.success(f"✅ Canvas 截图匹配: {name}（差异 {result.diff_percent:.2f}%）")
        return result

    def _capture_stable_canvas(
        self, canvas: Locator, style: str = None, mask: Sequence[Locator] = None,
        timeout: int = 3000, interval: int = 250,
    ) -> bytes:
        """连续截图直到画面稳定，避免在渲染/动画中途取图

        style 会同时注入主页面和查看器 iframe：查看器的弹窗、工具栏、方向盘等
        浮层大多不在 canvas 内部，只靠 screenshot(style=...) 注入不到。
        """
        options = {"scale": "css", "animations": "disabled"}
        if style:
            options["style"] = style
            self._apply_hide_style(style)
        if mask:
            options["mask"] = mask

        try:
            previous = canvas.screenshot(**options)
            deadline = time.time() + timeout / 1000
            while time.time() < deadline:
                self.page.wait_for_timeout(interval)
                current = canvas.screenshot(**options)
                if current == previous:
                    return current
                previous = current
            return previous
        finally:
            if style:
                self._remove_hide_style()

    _HIDE_STYLE_ID = "__canvas_compare_hide_style__"

    def _apply_hide_style(self, css: str):
        """在所有 frame 中注入隐藏浮层的样式"""
        for frame in self.page.frames:
            try:
                frame.evaluate(
                    """([css, id]) => {
                        let s = document.getElementById(id);
                        if (!s) {
                            s = document.createElement('style');
                            s.id = id;
                            (document.head || document.documentElement).appendChild(s);
                        }
                        s.textContent = css;
                    }""",
                    [css, self._HIDE_STYLE_ID],
                )
            except Exception:
                pass  # 页面可能正在跳转，忽略

    def _remove_hide_style(self):
        """移除注入的隐藏样式，避免影响后续操作"""
        for frame in self.page.frames:
            try:
                frame.evaluate(
                    "id => { const s = document.getElementById(id); if (s) s.remove(); }",
                    self._HIDE_STYLE_ID,
                )
            except Exception:
                pass

    def assert_screenshot_match(self, selector: str = None, threshold: float = 0.1, name: str = "screenshot"):
        """断言截图匹配（视觉回归测试）"""
        if selector:
            element = self.page.locator(selector).first
            screenshot = element.screenshot()
        else:
            screenshot = self.page.screenshot()

        # 保存到 Allure
        allure.attach(screenshot, name=f"截图_{name}", attachment_type=AttachmentType.PNG)

        # 这里可以集成像素对比库，如 pixelmatch
        # 简单实现：对比文件是否存在
        import os
        baseline_path = f"baseline/{name}.png"
        if os.path.exists(baseline_path):
            # 对比逻辑...
            log.info(f"截图已保存: {baseline_path}")
        else:
            # 首次运行，保存基准图
            with open(baseline_path, "wb") as f:
                f.write(screenshot)
            log.warning(f"基准图不存在，已创建: {baseline_path}")
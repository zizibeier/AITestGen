# tests/test_canvas.py
import allure
from allure_commons.types import AttachmentType

from ui.tests.ui_base_test import BaseDesignTest


@allure.feature("Canvas操作")
class TestCanvasOperations(BaseDesignTest):
    """Canvas 操作测试类"""

    @allure.story("Canvas信息")
    def test_get_canvas_info(self):
        """测试获取Canvas信息"""
        self.log_info("开始测试获取Canvas信息")

        canvas_info = self.design.get_canvas_info()

        self.assert_not_none(canvas_info, "获取Canvas信息失败")
        self.assert_true(canvas_info['width'] > 0, "Canvas宽度异常")
        self.assert_true(canvas_info['height'] > 0, "Canvas高度异常")

        allure.attach(
            f"""
            Canvas信息:
            - 位置: ({canvas_info['x']:.2f}, {canvas_info['y']:.2f})
            - 尺寸: {canvas_info['width']:.2f} x {canvas_info['height']:.2f}
            - 中心点: ({canvas_info['center_x']:.2f}, {canvas_info['center_y']:.2f})
            """,
            name="Canvas信息",
            attachment_type=AttachmentType.TEXT
        )

        self.log_success(f"Canvas尺寸: {canvas_info['width']:.2f} x {canvas_info['height']:.2f}")

    @allure.story("Canvas截图")
    def test_canvas_screenshot(self):
        """测试Canvas截图功能"""
        self.log_info("开始测试Canvas截图功能")

        screenshot = self.design.canvas.screenshot()

        self.assert_not_none(screenshot, "Canvas截图失败")
        allure.attach(screenshot, name="Canvas截图", attachment_type=AttachmentType.PNG)

        self.log_success("Canvas截图成功")

    @allure.story("Canvas可见性")
    def test_canvas_visibility(self):
        """测试Canvas可见性"""
        self.log_info("开始测试Canvas可见性")

        is_visible = self.design.canvas.is_ready()

        self.assert_true(is_visible, "Canvas不可见")
        self.log_success("Canvas可见")

    @allure.story("Canvas点击")
    def test_click_canvas(self):
        """测试点击Canvas"""
        self.log_info("开始测试点击Canvas")

        canvas_info = self.design.get_canvas_info()
        center_x = canvas_info['center_x']
        center_y = canvas_info['center_y']

        result = self.design.canvas.click_at(center_x, center_y)

        self.assert_true(result, "点击Canvas失败")
        self.take_screenshot("点击Canvas后")
        self.log_success("点击Canvas成功")
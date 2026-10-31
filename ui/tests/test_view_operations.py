# tests/test_view_operations.py
import allure
from ui.tests.ui_base_test import UIBaseTest
from common.utils.performance_monitor import PerformanceContext

@allure.feature("视图操作")
@allure.severity(allure.severity_level.CRITICAL)
class TestViewOperations(UIBaseTest):
    """视图操作测试"""

    def setup_method(self):
        """每个测试方法前置"""
        super().setup_method()

        # self.dynamic.set_feature("三维引擎")


    @allure.story("旋转视图")
    def test_rotate_view(self):
        """测试旋转视图"""
        self.step.log_step("开始测试旋转视图")
        self._reset_view_to_default()

        result,duration = self.measure_time(self.ctx.view.rotate,100,50)
        self.perf.add("模型旋转", duration, threshold=500)
        self.log_info(f"旋转操作耗时: {duration:.2f}ms")
        self.assert_true(result, "旋转操作应该成功")
        self.assert_performance(duration, 500, "旋转视图")
        self.assert_true(result, "旋转操作失败")

        # 视觉回归：旋转后的 3D 画面应与基准图一致（允许 2% 像素差异）
        self.assert_canvas_screenshot(
            "view_operations/rotate", max_diff_pixel_ratio=0.02
        )


    @allure.story("缩放视图")
    def test_zoom_view(self):
        """测试缩放视图"""
        self.step.log_step("开始测试缩放视图")
        self._reset_view_to_default()

        result = self.ctx.view.zoom(200)

        self.assert_true(result, "缩放操作失败")
        self.take_canvas_screenshot("缩放后视图")
        self.assert_canvas_screenshot(
            "view_operations/zoom", max_diff_pixel_ratio=0.02
        )
        self.log_info("缩放测试通过")

    @allure.story("平移视图")
    def test_pan_view(self):
        """测试平移视图"""
        self.step.log_step("开始测试平移视图")
        self._reset_view_to_default()

        result = self.ctx.view.pan(100, 100)

        self.assert_true(result, "平移操作失败")
        self.take_screenshot("平移后视图")
        self.assert_canvas_screenshot(
            "view_operations/pan", max_diff_pixel_ratio=0.02
        )
        self.log_info("平移测试通过")

    @allure.story("重置视图")
    def test_reset_view(self):
        """测试重置视图"""
        self.step.log_step("开始测试重置视图")
        self._reset_view_to_default()

        # 先旋转
        self.step.log_step("开始旋转")
        self.ctx.view.rotate(100, 50)
        self.wait(0.5)

        # 再重置
        self.step.log_step("再重置")
        result = self.ctx.view.reset()

        self.assert_true(result, "重置操作失败")
        self.take_screenshot("重置后视图")
        self.assert_canvas_screenshot(
            "view_operations/reset", max_diff_pixel_ratio=0.02
        )
        self.log_info("重置测试通过")

    @allure.story("连续操作")
    def test_continuous_operations(self):
        """测试连续操作"""
        self.step.log_step("开始测试连续操作")
        self._reset_view_to_default()

        operations = [
            ("旋转", lambda: self.ctx.view.rotate(50, 30)),
            ("放大", lambda: self.ctx.view.zoom(100)),
            ("平移", lambda: self.ctx.view.pan(50, 50)),
            ("缩小", lambda: self.ctx.view.zoom(-100)),
            ("回到原点", lambda: self.ctx.view.reset()),
        ]

        for op_name, op_func in operations:
            with self.step.log_step(f"执行{op_name}操作"):
                result = op_func()
                self.assert_true(result, f"{op_name}操作失败")
                self.wait(0.3)
        self.take_screenshot("连续操作最终视图")
        self.assert_canvas_screenshot(
            "view_operations/continuous", max_diff_pixel_ratio=0.02
        )
        self.log_info("连续操作测试通过")

    def _reset_view_to_default(self):
        """回到默认视角，保证每个用例的截图基准有确定的起始状态"""
        self.assert_true(
            self.ctx.base.wait_for_toolbar("回到原点", timeout=30000),
            "查看器工具栏未出现，无法重置视图",
        )
        self.assert_true(self.ctx.view.reset(), "初始重置视图失败")
        self.wait(1.0)

    def wait(self, seconds: float = 0.5):
        """等待"""
        import time
        time.sleep(seconds)


import pytest
import os

if __name__ == '__main__':
    # 1. 运行测试，生成 allure 原始数据
    exit_code = pytest.main([
        __file__,
        "-v",
        "-s",
        "--alluredir=allure-results",
        "--clean-alluredir"
    ])

    # ============================
    # 2. 关键：用 Python 自带方式生成 HTML 报告（不会报错！）
    # ============================
    try:
        print("\n正在生成 Allure 报告...")
        os.system("cmd /c allure generate allure-results -o allure-report --clean")

        print("✅ 报告生成成功：allure-report/index.html")
    except Exception as e:
        print("⚠️ 报告生成失败，但测试已完成")
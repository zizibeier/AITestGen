# tests/test_measurement.py
import allure
from ui.tests.ui_base_test import BaseDesignTest


@allure.feature("测量工具")
class TestMeasurement(BaseDesignTest):
    """测量工具测试类"""

    @allure.story("激活测量工具")
    def test_activate_measurement(self):
        """测试激活测量工具"""
        self.log_info("开始测试激活测量工具")

        # 切换到主页面
        self.design.ensure_in_main()

        # 激活测量工具
        result, duration = self.measure_time(self.design.toolbar.click_tool, "测量")

        self.assert_true(result, "激活测量工具失败")
        self.assert_performance(duration, 1000)

        # 验证激活状态
        is_active = self.design.toolbar.is_tool_active("测量")
        self.assert_true(is_active, "测量工具未激活")

        self.take_screenshot("测量工具激活状态")
        self.log_success("测量工具激活成功")

        # 切换回 iframe
        self.design.ensure_in_iframe()

    @allure.story("测量距离")
    def test_measure_distance(self):
        """测试测量距离功能"""
        self.log_info("开始测试测量距离")

        # 激活测量工具
        self.design.ensure_in_main()
        self.design.toolbar.click_tool("测量")

        # 切换回 iframe 进行测量
        self.design.ensure_in_iframe()

        # 测量距离
        distance = self.design.measure.measure_distance(100, 100, 200, 200)

        self.assert_not_none(distance, "测量失败，未获取到距离")
        self.assert_true(distance > 0, f"测量距离异常: {distance}mm")

        allure.attach(
            f"测量距离: {distance}mm",
            name="测量结果",
            attachment_type=AttachmentType.TEXT
        )

        self.take_screenshot("测量结果")
        self.log_success(f"测量成功，距离: {distance}mm")

        # 清理
        self.design.ensure_in_main()
        self.design.measure.clear()
        self.design.ensure_in_iframe()

    @allure.story("测量距离")
    def test_measure_horizontal_line(self):
        """测试测量水平线"""
        self.log_info("开始测试测量水平线")

        self.design.ensure_in_main()
        self.design.toolbar.click_tool("测量")
        self.design.ensure_in_iframe()

        # 测量水平线
        distance = self.design.measure.measure_distance(100, 200, 300, 200)

        self.assert_not_none(distance, "水平线测量失败")
        self.assert_true(distance > 0, f"水平线测量距离异常: {distance}mm")

        allure.attach(f"水平线距离: {distance}mm", name="测量结果", attachment_type=AttachmentType.TEXT)
        self.log_success(f"水平线测量成功，距离: {distance}mm")

        self.design.ensure_in_main()
        self.design.measure.clear()
        self.design.ensure_in_iframe()

    @allure.story("测量距离")
    def test_measure_vertical_line(self):
        """测试测量垂直线"""
        self.log_info("开始测试测量垂直线")

        self.design.ensure_in_main()
        self.design.toolbar.click_tool("测量")
        self.design.ensure_in_iframe()

        # 测量垂直线
        distance = self.design.measure.measure_distance(200, 100, 200, 300)

        self.assert_not_none(distance, "垂直线测量失败")
        self.assert_true(distance > 0, f"垂直线测量距离异常: {distance}mm")

        allure.attach(f"垂直线距离: {distance}mm", name="测量结果", attachment_type=AttachmentType.TEXT)
        self.log_success(f"垂直线测量成功，距离: {distance}mm")

        self.design.ensure_in_main()
        self.design.measure.clear()
        self.design.ensure_in_iframe()

    @allure.story("多次测量")
    def test_multiple_measurements(self):
        """测试多次测量"""
        self.log_info("开始测试多次测量")

        self.design.ensure_in_main()
        self.design.toolbar.click_tool("测量")

        measurements = [
            ((100, 100), (200, 200), "对角线1"),
            ((150, 150), (250, 250), "对角线2"),
            ((200, 200), (300, 300), "对角线3"),
        ]

        results = []
        for start, end, desc in measurements:
            with allure.step(f"执行{desc}"):
                self.design.ensure_in_iframe()
                distance = self.design.measure.measure_distance(start[0], start[1], end[0], end[1])
                self.assert_not_none(distance, f"{desc}失败")
                results.append(distance)
                self.log_info(f"{desc}距离: {distance}mm")

        # 获取所有测量结果
        self.design.ensure_in_main()
        all_measurements = self.design.measure.get_all_measurements()

        allure.attach(
            f"测量结果列表:\n" + "\n".join([f"- {r}" for r in results]),
            name="所有测量距离",
            attachment_type=AttachmentType.TEXT
        )

        # 清除所有测量
        self.design.measure.clear()

        self.log_success(f"成功完成 {len(measurements)} 次测量")
        self.design.ensure_in_iframe()

    @allure.story("清除测量")
    def test_clear_measurements(self):
        """测试清除测量功能"""
        self.log_info("开始测试清除测量功能")

        self.design.ensure_in_main()
        self.design.toolbar.click_tool("测量")

        # 创建一个测量
        self.design.ensure_in_iframe()
        self.design.measure.measure_distance(100, 100, 200, 200)

        # 获取测量结果
        self.design.ensure_in_main()
        before_clear = self.design.measure.get_all_measurements()
        self.log_info(f"清除前测量数量: {len(before_clear)}")

        # 清除测量
        result = self.design.measure.clear()
        self.assert_true(result, "清除测量失败")

        # 验证清除结果
        after_clear = self.design.measure.get_all_measurements()
        self.log_info(f"清除后测量数量: {len(after_clear)}")

        self.take_screenshot("清除测量后")
        self.log_success("清除测量成功")

        self.design.ensure_in_iframe()
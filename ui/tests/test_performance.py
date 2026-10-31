# tests/test_performance.py
import allure
from ui.tests.ui_base_test import BaseDesignTest


@allure.feature("性能测试")
class TestPerformance(BaseDesignTest):
    """性能测试类"""

    @allure.story("视图操作性能")
    def test_view_operations_performance(self):
        """测试视图操作性能"""
        self.log_info("开始测试视图操作性能")

        operations = [
            ("旋转", lambda: self.design.view.rotate(50, 50)),
            ("缩放", lambda: self.design.view.zoom(100)),
            ("平移", lambda: self.design.view.pan(50, 50)),
            ("重置", lambda: self.design.view.reset()),
        ]

        performance_data = []

        for op_name, op_func in operations:
            with allure.step(f"测量{op_name}操作性能"):
                _, duration = self.measure_time(op_func)
                performance_data.append({
                    "operation": op_name,
                    "duration_ms": duration
                })
                self.log_info(f"{op_name}耗时: {duration:.2f}ms")
                self.assert_performance(duration, 500)
                self.wait_for_animation()

        # 生成性能报告
        report = "\n".join([
            f"{data['operation']}: {data['duration_ms']:.2f}ms"
            for data in performance_data
        ])

        allure.attach(report, name="性能测试报告", attachment_type=AttachmentType.TEXT)
        self.log_success("所有性能测试通过")

    @allure.story("连续操作性能")
    def test_continuous_operations_performance(self):
        """测试连续操作性能"""
        self.log_info("开始测试连续操作性能")

        durations = []

        for i in range(10):
            _, duration = self.measure_time(self.design.view.zoom, 50)
            durations.append(duration)
            self.wait_for_animation()

        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)

        allure.attach(
            f"""
            连续操作性能统计:
            - 平均耗时: {avg_duration:.2f}ms
            - 最大耗时: {max_duration:.2f}ms
            - 最小耗时: {min_duration:.2f}ms
            - 操作次数: {len(durations)}
            """,
            name="连续操作性能报告",
            attachment_type=AttachmentType.TEXT
        )

        self.assert_true(avg_duration < 300, f"平均耗时过高: {avg_duration:.2f}ms")
        self.log_success(f"连续操作平均耗时: {avg_duration:.2f}ms")
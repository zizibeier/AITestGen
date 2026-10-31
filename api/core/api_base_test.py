# api/tests/base_test.py
"""
API测试基类
"""
import allure
from typing import Optional, Any, Callable
from common.base_test import BaseTest
from common.utils.performance_monitor import PerformanceMonitor
from common.utils.logger import log
from api.core.api_context import APIContext
from api.assertions.api_assertion import APIAssertion


class APIBaseTest(BaseTest):

    """
    API 测试基类

    提供断言、性能监控等能力
    测试用例可以选择继承，也可以直接使用 fixture
    """

    # 类级别变量
    api_context: Optional[APIContext] = None



    def setup_method(self):
        """每个测试方法前置"""
        super().setup_method()

        # 替换为 API 断言器
        self.assertion = APIAssertion(
            screenshot_callback=self._on_assert_fail_screenshot
        )

        # 初始化性能监控
        self.perf = PerformanceMonitor(self._get_test_name())

        # 提供便捷别名
        self.api_assert = self.assertion

        log.info(f"开始 API 测试: {self._get_test_name()}")

    def teardown_method(self):
        """每个测试方法后置"""
        if hasattr(self, 'perf') and self.perf.metrics:
            self.perf.attach_to_allure()

        super().teardown_method()
        log.info(f"结束 API 测试: {self._get_test_name()}")




    # ==================== 重写父类方法 ====================

    def _on_assert_fail_screenshot(self):
        """API 断言失败时的处理"""
        if self.api_context:
            last_request = self.api_context.get_last_request()
            last_response = self.api_context.get_last_response()

            if last_request:
                import json
                allure.attach(
                    json.dumps(last_request, indent=2, ensure_ascii=False),
                    name="失败时请求信息",
                    attachment_type=allure.attachment_type.JSON
                )
            if last_response:
                allure.attach(
                    f"状态码: {last_response.status_code}\n\n响应体:\n{last_response.text[:2000]}",
                    name="失败时响应信息",
                    attachment_type=allure.attachment_type.TEXT
                )

    # ==================== API 便捷方法 ====================

    @property
    def api(self):
        """获取 API 上下文"""
        return self.api_context

    def clear_api_history(self):
        """清空 API 请求历史"""
        if self.api_context:
            self.api_context.clear_history()

    def get_last_response(self):
        """获取最后一次响应"""
        if self.api_context:
            return self.api_context.get_last_response()
        return None

    def get_last_request(self):
        """获取最后一次请求"""
        if self.api_context:
            return self.api_context.get_last_request()
        return None

    def ensure_token(self):
        """确保 Token 有效"""
        if self.api_context:
            return self.api_context.ensure_token()
        return None

    # ==================== 断言便捷方法 ====================

    def assert_status(self, response, expected_code: int, message: str = None):
        """断言 HTTP 状态码"""
        self.api_assert.assert_status_code(response, expected_code, message)

    def assert_json_path(self, response, path: str, expected, message: str = None):
        """断言 JSON 路径"""
        self.api_assert.assert_json_path(response, path, expected, message)

    def assert_business_success(self, response, code_field: str = "code", success_code: int = 200):
        """断言业务成功（Forface API 使用 code=200 表示成功）"""
        self.api_assert.assert_business_code(response, success_code, code_field)

    def assert_ai_response(self, response, expected: str, context: str = "",
                           message: str = None, **kwargs) -> bool:
        """
        用大模型判断 HTTP 响应是否满足自然语言预期

        示例：
            self.assert_ai_response(
                response,
                "code 为 200，data.fileId 非空，且 data.status 为 success",
            )

        :param response: requests.Response
        :param expected: 自然语言预期
        :param context: 额外上下文（如请求参数）
        :param message: 自定义失败信息前缀
        :param kwargs: 透传 AIAssertion.judge
        """
        try:
            actual = response.json()
        except ValueError:
            actual = response.text

        headers = getattr(response, "headers", {}) or {}
        http_context = (
            f"HTTP 状态码: {getattr(response, 'status_code', 'N/A')}\n"
            f"Content-Type: {headers.get('Content-Type', '')}"
        )
        if context:
            http_context = f"{context}\n{http_context}"

        return self.assert_ai(
            expected, actual, context=http_context, message=message, **kwargs
        )

    # ==================== 性能监控 ====================

    def measure_time(self, func: Callable, *args, **kwargs) -> tuple:
        """测量函数执行时间"""
        return self.perf.measure(func, *args, **kwargs)

    def assert_performance(self, duration: float, threshold: float = 500, operation: str = "操作"):
        """断言性能在阈值内"""
        self.perf.add(operation, duration, threshold=threshold)

        is_pass = duration <= threshold
        self.assert_true(is_pass, f"{operation} 耗时 {duration:.2f}ms 超过阈值 {threshold}ms")

        if is_pass:
            self.log_success(f"✅ {operation} 耗时 {duration:.2f}ms")
        else:
            self.log_error(f"❌ {operation} 耗时 {duration:.2f}ms 超过阈值 {threshold}ms")

        return is_pass
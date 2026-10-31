# common/api_base_test.py
"""
测试基类 - 只做组合和代理，不重复实现断言逻辑
"""

import time
import functools
from typing import Optional, Any, Callable, Dict, List
from datetime import datetime

import allure
from allure_commons.types import AttachmentType

from common.utils.logger import log
from common.config.settings import Config
from common.assertions.base_assertion import BaseAssertion


class BaseTest:
    """
    测试基类

    职责：
    1. 管理测试生命周期
    2. 组合断言类（委托给断言类）
    3. 提供日志、性能、数据管理等公共能力
    """

    # ==================== 类级别变量 ====================
    _test_session_start: Optional[float] = None
    _test_session_name: str = ""

    # ==================== 生命周期方法 ====================

    @classmethod
    def setup_class(cls):
        """测试类级别前置"""
        cls._test_session_start = time.time()
        cls._test_session_name = cls.__name__

        log.section(f"🚀 测试套件开始: {cls._test_session_name}")

        # 类级别的数据存储
        cls._class_test_data: Dict[str, Any] = {}
        cls._failures: int = 0
        cls._skips: int = 0

    @classmethod
    def teardown_class(cls):
        """测试类级别后置"""
        if cls._test_session_start:
            duration = (time.time() - cls._test_session_start) * 1000
            log.section(f"🏁 测试套件结束: {cls._test_session_name} 耗时: {duration:.2f}ms")

    def setup_method(self):
        """每个测试方法前置"""
        # 初始化测试数据
        self._test_name = self._get_test_name()
        self._start_time = time.time()
        self.test_data: Dict[str, Any] = {}

        # 初始化断言器（传入截图回调）
        self.assertion = BaseAssertion(
            screenshot_callback=self._on_assert_fail_screenshot
        )

        # 初始化步骤记录
        self._steps: List[Dict] = []

        log.info("=" * 60)
        log.info(f"📝 开始测试: {self._test_name}")

        # Allure 信息
        allure.dynamic.title(self._get_test_title())
        if self._get_test_docstring():
            allure.dynamic.description(self._get_test_docstring())

    def teardown_method(self):
        """每个测试方法后置"""
        duration = (time.time() - self._start_time) * 1000 if self._start_time else 0

        # 记录测试结果
        self._record_test_result()

        log.info(f"✅ 结束测试: {self._test_name} 耗时: {duration:.2f}ms")
        log.info("=" * 60)

    # ==================== 私有方法 ====================

    def _get_test_name(self) -> str:
        """获取测试方法名"""
        if hasattr(self, '_testMethodName'):
            return self._testMethodName
        import inspect
        frame = inspect.currentframe()
        while frame:
            if frame.f_code.co_name.startswith('test_'):
                return frame.f_code.co_name
            frame = frame.f_back
        return "unknown_test"

    def _get_test_title(self) -> str:
        """获取测试标题"""
        test_func = getattr(self, self._test_name, None)
        if test_func and test_func.__doc__:
            first_line = test_func.__doc__.strip().split('\n')[0]
            if first_line:
                return first_line
        return self._test_name.replace('_', ' ').title()

    def _get_test_docstring(self) -> str:
        """获取测试文档"""
        test_func = getattr(self, self._test_name, None)
        return test_func.__doc__ if test_func else None

    def _record_test_result(self):
        """记录测试结果到 Allure"""
        duration = (time.time() - self._start_time) * 1000 if self._start_time else 0

        allure.attach(
            f"测试方法: {self._test_name}\n执行耗时: {duration:.2f}ms",
            name="测试执行信息",
            attachment_type=AttachmentType.TEXT
        )

    def _add_step(self, message: str, level: str):
        """添加步骤记录"""
        self._steps.append({
            "index": len(self._steps) + 1,
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "name": message,
            "status": level
        })

    # ==================== 断言方法（代理给 assertion） ====================

    # 硬断言
    def assert_true(self, condition: bool, message: str = "断言失败") -> bool:
        return self.assertion.assert_true(condition, message)

    def assert_false(self, condition: bool, message: str = "断言失败") -> bool:
        return self.assertion.assert_false(condition, message)

    def assert_equal(self, actual: Any, expected: Any, message: str = None) -> bool:
        return self.assertion.assert_equal(actual, expected, message)

    def assert_not_equal(self, actual: Any, expected: Any, message: str = None) -> bool:
        return self.assertion.assert_not_equal(actual, expected, message)

    def assert_is_none(self, value: Any, message: str = "值应为 None") -> bool:
        return self.assertion.assert_is_none(value, message)

    def assert_is_not_none(self, value: Any, message: str = "值不应为 None") -> bool:
        return self.assertion.assert_is_not_none(value, message)

    def assert_in(self, item: Any, container, message: str = None) -> bool:
        return self.assertion.assert_in(item, container, message)

    def assert_not_in(self, item: Any, container, message: str = None) -> bool:
        return self.assertion.assert_not_in(item, container, message)

    def assert_is_instance(self, obj: Any, expected_type: type, message: str = None) -> bool:
        return self.assertion.assert_is_instance(obj, expected_type, message)

    def assert_greater(self, value: Any, threshold: Any, message: str = None) -> bool:
        return self.assertion.assert_greater(value, threshold, message)

    def assert_greater_equal(self, value: Any, threshold: Any, message: str = None) -> bool:
        return self.assertion.assert_greater_equal(value, threshold, message)

    def assert_less(self, value: Any, threshold: Any, message: str = None) -> bool:
        return self.assertion.assert_less(value, threshold, message)

    def assert_less_equal(self, value: Any, threshold: Any, message: str = None) -> bool:
        return self.assertion.assert_less_equal(value, threshold, message)

    def assert_between(self, value: Any, min_val: Any, max_val: Any, message: str = None) -> bool:
        return self.assertion.assert_between(value, min_val, max_val, message)

    def assert_contains(self, text: str, substring: str, message: str = None) -> bool:
        return self.assertion.assert_contains(text, substring, message)

    def assert_not_contains(self, text: str, substring: str, message: str = None) -> bool:
        return self.assertion.assert_not_contains(text, substring, message)

    def assert_starts_with(self, text: str, prefix: str, message: str = None) -> bool:
        return self.assertion.assert_starts_with(text, prefix, message)

    def assert_ends_with(self, text: str, suffix: str, message: str = None) -> bool:
        return self.assertion.assert_ends_with(text, suffix, message)

    def assert_regex_match(self, text: str, pattern: str, message: str = None) -> bool:
        return self.assertion.assert_regex_match(text, pattern, message)

    def assert_empty(self, container, message: str = None) -> bool:
        return self.assertion.assert_empty(container, message)

    def assert_not_empty(self, container, message: str = None) -> bool:
        return self.assertion.assert_not_empty(container, message)

    # 软断言
    def soft_assert_true(self, condition: bool, message: str = "断言失败"):
        self.assertion.soft_assert_true(condition, message)

    def soft_assert_equal(self, actual: Any, expected: Any, message: str = None):
        self.assertion.soft_assert_equal(actual, expected, message)

    def soft_assert_in(self, item: Any, container, message: str = None):
        self.assertion.soft_assert_in(item, container, message)

    def soft_assert_greater(self, value: Any, threshold: Any, message: str = None):
        self.assertion.soft_assert_greater(value, threshold, message)

    def soft_assert_less(self, value: Any, threshold: Any, message: str = None):
        self.assertion.soft_assert_less(value, threshold, message)

    # AI 断言
    def assert_ai(self, expected: str, actual: Any, context: str = "",
                  message: str = None, **kwargs) -> bool:
        """用大模型判断 actual 是否满足自然语言预期（硬断言）"""
        return self.assertion.assert_ai(expected, actual, context, message, **kwargs)

    def soft_assert_ai(self, expected: str, actual: Any, context: str = "",
                       message: str = None, **kwargs) -> bool:
        """软 AI 断言：失败只记录，由 assert_all() 统一抛出"""
        return self.assertion.soft_assert_ai(expected, actual, context, message, **kwargs)

    def assert_all(self):
        """断言所有软断言都通过"""
        self.assertion.assert_all()

    def has_soft_assert_failures(self) -> bool:
        return self.assertion.has_soft_assert_failures()

    def clear_soft_assertions(self):
        self.assertion.clear_soft_assertions()

    # ==================== 断言回调 ====================

    def _on_assert_fail_screenshot(self):
        """
        断言失败时的截图回调

        子类可以重写此方法实现具体截图逻辑
        """
        pass

    # ==================== 日志方法 ====================

    def log_info(self, message: str):
        log.info(message)
        self._add_step(message, "info")

    def log_success(self, message: str):
        log.success(message)
        self._add_step(message, "success")

    def log_error(self, message: str):
        log.error(message)
        self._add_step(message, "error")

    def log_warning(self, message: str):
        log.warning(message)
        self._add_step(message, "warning")

    def log_step(self, message: str):
        log.step(message)
        self._add_step(message, "step")
        allure.step(message)

    def log_debug(self, message: str):
        log.debug(message)

    # ==================== 性能监控 ====================

    def measure_time(self, func: Callable, *args, **kwargs) -> tuple:
        """测量函数执行时间"""
        start = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        return result, duration

    def assert_performance(self, duration: float, threshold: float = 500, operation: str = "操作") -> bool:
        """断言性能在阈值内"""
        is_pass = duration <= threshold
        message = f"{operation} 耗时 {duration:.2f}ms"

        if is_pass:
            self.log_success(f"✅ {message} (阈值: {threshold}ms)")
        else:
            self.log_error(f"❌ {message} 超过阈值 {threshold}ms")

        allure.attach(
            f"操作: {operation}\n耗时: {duration:.2f}ms\n阈值: {threshold}ms",
            name="性能数据",
            attachment_type=AttachmentType.TEXT
        )

        return self.assert_true(is_pass, f"{operation} 性能不达标")

    # ==================== 数据管理 ====================

    def set_test_data(self, key: str, value: Any):
        self.test_data[key] = value
        self.log_debug(f"设置测试数据: {key} = {value}")

    def get_test_data(self, key: str, default: Any = None) -> Any:
        return self.test_data.get(key, default)

    def has_test_data(self, key: str) -> bool:
        return key in self.test_data

    def clear_test_data(self):
        self.test_data.clear()

    def set_class_data(self, key: str, value: Any):
        self.__class__._class_test_data[key] = value

    def get_class_data(self, key: str, default: Any = None) -> Any:
        return self.__class__._class_test_data.get(key, default)

    # ==================== 重试机制 ====================

    def retry(self, func: Callable, max_retries: int = 3, delay: float = 1,
              backoff: float = 2, exceptions: tuple = (Exception,)) -> Any:
        """重试执行函数"""
        current_delay = delay

        for attempt in range(max_retries):
            try:
                return func()
            except exceptions as e:
                if attempt == max_retries - 1:
                    raise
                self.log_warning(f"第 {attempt + 1} 次失败: {e}, {current_delay}秒后重试")
                time.sleep(current_delay)
                current_delay *= backoff
        return None

    def retry_assert(self, condition_func: Callable, max_retries: int = 3,
                     delay: float = 0.5, message: str = "条件未满足") -> bool:
        """重试断言条件"""
        for attempt in range(max_retries):
            try:
                if condition_func():
                    return True
            except Exception:
                pass

            if attempt < max_retries - 1:
                time.sleep(delay)

        return self.assert_true(False, f"{message} (重试 {max_retries} 次后失败)")

    # ==================== 等待方法 ====================

    def wait(self, seconds: float = 0.5):
        time.sleep(seconds)

    def wait_until(self, condition_func: Callable, timeout: float = 30,
                   interval: float = 0.5, message: str = "等待超时") -> bool:
        """等待条件满足"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if condition_func():
                    return True
            except Exception:
                pass
            time.sleep(interval)

        return self.assert_true(False, f"{message} ({timeout}秒)")

    # ==================== Allure 标记 ====================

    def add_tag(self, tag: str):
        allure.dynamic.tag(tag)

    def set_priority(self, priority: str):
        priority_map = {
            "critical": allure.severity_level.CRITICAL,
            "high": allure.severity_level.HIGH,
            "normal": allure.severity_level.NORMAL,
            "low": allure.severity_level.LOW
        }
        if priority in priority_map:
            allure.dynamic.severity(priority_map[priority])

    def set_feature(self, feature: str):
        allure.dynamic.feature(feature)

    def set_story(self, story: str):
        allure.dynamic.story(story)

    # ==================== 装饰器 ====================

    @staticmethod
    def retry_decorator(max_retries: int = 3, delay: float = 1):
        """重试装饰器"""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return func(self, *args, **kwargs)
                    except AssertionError as e:
                        if attempt == max_retries - 1:
                            raise
                        self.log_warning(f"第 {attempt + 1} 次失败: {e}")
                        time.sleep(delay)
                return None

            return wrapper

        return decorator
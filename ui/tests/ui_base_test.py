# tests/api_base_test.py
"""
UI测试基类
继承 BaseTest，只添加 UI 特有的功能
"""

import allure
import time
from typing import Optional, Any, Callable
from allure_commons.types import AttachmentType
from playwright.sync_api import sync_playwright, Browser, BrowserContext

from common.base_test import BaseTest
from ui.assertions.ui_assertion import UIAssertion
from ui.context.ui_context import UIContext
from common.config.settings import Config
from common.utils.logger import log
from common.utils.allure_helper import UIAllureHelper,StepHelper,AllureDynamicHelper
from common.utils.performance_monitor import PerformanceMonitor, PerformanceContext

class UIBaseTest(BaseTest):
    """
    UI测试基类

    继承 BaseTest，只添加 UI 特有的功能：
    1. 替换断言器为 UIAssertion
    2. 添加 UI 特有断言方法（代理给 UIAssertion）
    3. 添加 UI 特有操作方法（截图、元素操作等）
    4. 管理浏览器生命周期
    """

    # 类级别变量，整个测试会话共享
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None
    _playwright = None

    # ==================== 类级别生命周期 ====================

    @classmethod
    def setup_class(cls):
        """测试类级别前置 - 只执行一次"""
        super().setup_class()

        log.section("UI测试会话开始")
        cls._init_browser()
        cls._init_context()

    @classmethod
    def teardown_class(cls):
        """测试类级别后置 - 只执行一次"""

        # 1. 先清理 context（关闭页面）
        cls._cleanup_context()

        # 2. 再关闭浏览器
        cls._close_browser()

        # 3. 最后调用父类
        super().teardown_class()

        log.section("UI测试会话结束")

    # ==================== 方法级别生命周期 ====================

    def setup_method(self):
        """每个测试方法前置 - 每个用例执行前"""
        # 调用父类（会初始化 assertion 和 test_data）
        super().setup_method()

        # 替换为 UI 断言器（传入 page 和截图回调）
        self.assertion = UIAssertion(
            page=self.page,
            screenshot_callback=self._on_assert_fail_screenshot
        )
        # 初始化 Allure 辅助类
        self.ui_allure = UIAllureHelper()
        self.step = StepHelper()
        self.dynamic = AllureDynamicHelper()
        # 初始化性能监控器
        self.perf = PerformanceMonitor(self._get_test_name())
        # 提供便捷别名
        self.ui = self.assertion

        log.info(f"开始测试: {self._get_test_name()}")

    def teardown_method(self):
        """每个测试方法后置 - 每个用例执行后"""
        # 自动附加性能数据到 Allure
        if hasattr(self, 'perf') and self.perf.metrics:
            self.perf.attach_to_allure()

        super().teardown_method()
        log.info(f"结束测试: {self._get_test_name()}, 耗时: {self._get_test_duration():.2f}ms")

    # ==================== 浏览器管理（私有方法） ====================

    @classmethod
    def _init_browser(cls):
        """初始化浏览器（类级别）"""
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch(
            headless=Config.HEADLESS,
            slow_mo=Config.SLOW_MO,
            args=[
                '--start-maximized',
                '--kiosk',
                '--disable-infobars'
            ]
        )
        log.info("✅ 浏览器启动成功")

    @classmethod
    def _close_browser(cls):
        """关闭浏览器（类级别）"""
        try:
            if cls._context:
                cls._context.close()
                cls._context = None

            if cls._browser:
                cls._browser.close()
                cls._browser = None

            if cls._playwright:
                cls._playwright.stop()
                cls._playwright = None

            log.info("✅ 浏览器已关闭")
        except Exception as e:
            log.warning(f"关闭浏览器时出错: {e}")


    # 无头模式下默认窗口很小，查看器会退化成移动端布局（`.fc-mobile-tool-btn-box`），
    # 与桌面端选择器对不上，也会让 Canvas 尺寸不稳定，这里固定为桌面分辨率。
    DESKTOP_VIEWPORT = {"width": 1920, "height": 1080}

    @classmethod
    def _init_context(cls):
        """初始化测试上下文"""
        if Config.HEADLESS:
            browser_version = cls._browser.version  # 如 145.0.7632.6
            major = browser_version.split(".")[0]
            user_agent = (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{major}.0.0.0 Safari/537.36"
            )
            cls._context = cls._browser.new_context(
                viewport=cls.DESKTOP_VIEWPORT,
                user_agent=user_agent,
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
        else:
            cls._context = cls._browser.new_context(no_viewport=True)

        cls.page = cls._context.new_page()

        cls.ctx = UIContext(cls.page)
        cls.ctx.navigate()

        if Config.AUTO_LOGIN:
            cls.ctx.login()


        if Config.AUTO_UPLOAD_MODEL:
            if not cls.ctx.upload_model():
                raise RuntimeError(
                    "模型上传失败，UI 用例无法继续；请检查网络、匿名预览额度或登录状态"
                )
            if not cls.ctx.wait_for_model_load():
                raise RuntimeError("模型加载超时，UI 用例无法继续")

        log.info("✅ UI测试上下文初始化完成")

    @classmethod
    def _cleanup_context(cls):
        """清理测试上下文"""
        try:
            if hasattr(cls, 'ctx') and cls.ctx:
                cls.ctx.cleanup()
                cls.ctx = None

            if hasattr(cls, 'page') and cls.page:
                cls.page.close()
                cls.page = None

            # 注意：不要在这里关闭 _context，让 _close_browser 统一处理
            # 或者安全地关闭
            if cls._context:
                try:
                    cls._context.close()
                except Exception as e:
                    log.warning(f"关闭 context 时出错: {e}")
                finally:
                    cls._context = None

            log.info("✅ UI测试上下文已清理")
        except Exception as e:
            log.warning(f"清理上下文时出错: {e}")


    # ==================== 重写父类方法 ====================

    def _on_assert_fail_screenshot(self):
        """断言失败时的截图回调"""
        self.take_failure_screenshot()

    def _get_test_name(self) -> str:
        """获取当前测试名称"""
        import inspect
        frame = inspect.currentframe()
        while frame:
            if frame.f_code.co_name.startswith('test_'):
                return frame.f_code.co_name
            frame = frame.f_back

        if hasattr(self, '_testMethodName'):
            return self._testMethodName
        return 'unknown_test'

    def _get_test_duration(self) -> float:
        """获取测试耗时（毫秒）"""
        if hasattr(self, '_start_time') and self._start_time:
            return (time.time() - self._start_time) * 1000
        return 0

    def _record_test_result(self):
        """记录测试结果"""
        duration = self._get_test_duration()

        allure.attach(
            f"测试方法: {self._get_test_name()}\n测试耗时: {duration:.2f}ms",
            name="测试性能",
            attachment_type=AttachmentType.TEXT
        )

        if hasattr(self, '_assert_errors') and self._assert_errors:
            allure.attach(
                "\n".join(self._assert_errors),
                name="断言错误",
                attachment_type=AttachmentType.TEXT
            )

    # ==================== UI 特有断言方法（代理给 UIAssertion） ====================

    # 元素存在性断言
    def assert_element_visible(self, selector: str, timeout: int = 5000, message: str = None):
        """断言元素可见"""
        self.ui.assert_element_visible(selector, timeout, message)

    def assert_element_hidden(self, selector: str, timeout: int = 5000, message: str = None):
        """断言元素隐藏"""
        self.ui.assert_element_hidden(selector, timeout, message)

    def assert_element_exists(self, selector: str, message: str = None):
        """断言元素存在于 DOM 中"""
        self.ui.assert_element_exists(selector, message)

    def assert_element_not_exists(self, selector: str, message: str = None):
        """断言元素不存在于 DOM 中"""
        self.ui.assert_element_not_exists(selector, message)

    def assert_element_count(self, selector: str, expected_count: int, message: str = None):
        """断言元素数量"""
        self.ui.assert_element_count(selector, expected_count, message)

    # 元素属性断言
    def assert_element_text(self, selector: str, expected_text: str, exact: bool = True, message: str = None):
        """断言元素文本"""
        self.ui.assert_element_text(selector, expected_text, exact, message)

    def assert_element_attribute(self, selector: str, attribute: str, expected_value: str, message: str = None):
        """断言元素属性"""
        self.ui.assert_element_attribute(selector, attribute, expected_value, message)

    def assert_element_checked(self, selector: str, should_be_checked: bool = True, message: str = None):
        """断言复选框/单选框选中状态"""
        self.ui.assert_element_checked(selector, should_be_checked, message)

    def assert_element_enabled(self, selector: str, should_be_enabled: bool = True, message: str = None):
        """断言元素启用状态"""
        self.ui.assert_element_enabled(selector, should_be_enabled, message)

    # 页面断言
    def assert_title(self, expected_title: str, message: str = None):
        """断言页面标题"""
        self.ui.assert_title(expected_title, message)

    def assert_url(self, expected_url: str, exact: bool = True, message: str = None):
        """断言当前URL"""
        self.ui.assert_url(expected_url, exact, message)

    def assert_url_contains(self, text: str, message: str = None):
        """断言URL包含指定文本"""
        self.ui.assert_url_contains(text, message)

    # 三维引擎专用断言
    def assert_canvas_exists(self, timeout: int = 10000, message: str = None):
        """断言 Canvas 存在"""
        self.ui.assert_canvas_exists(timeout, message)

    def assert_webgl_context(self, message: str = None):
        """断言 WebGL 上下文已初始化"""
        self.ui.assert_webgl_context(message)

    def assert_model_loaded(self, message: str = None):
        """断言模型已加载"""
        self.ui.assert_model_loaded(message)

    def assert_fps_greater_than(self, min_fps: int = 30, message: str = None):
        """断言帧率大于阈值"""
        self.ui.assert_fps_greater_than(min_fps, message)

    # 软断言版本（UI特有）
    def soft_assert_element_visible(self, selector: str, timeout: int = 5000, message: str = None):
        """软断言 - 元素可见"""
        self.ui.soft_assert_element_visible(selector, timeout, message)

    def soft_assert_element_text(self, selector: str, expected_text: str, exact: bool = True, message: str = None):
        """软断言 - 元素文本"""
        self.ui.soft_assert_element_text(selector, expected_text, exact, message)

    # ==================== UI 特有操作方法 ====================

    def take_failure_screenshot(self, name: str = "failure"):
        """失败时截图"""
        try:
            screenshot = self.page.screenshot()
            allure.attach(
                screenshot,
                name=f"失败截图_{self._get_test_name()}",
                attachment_type=AttachmentType.PNG
            )
            log.info("📸 失败截图已保存")
        except Exception as e:
            log.error(f"截图失败: {e}")

    def take_screenshot(self, name: str = "screenshot"):
        """主动截图"""
        screenshot = self.page.screenshot()
        allure.attach(screenshot, name=name, attachment_type=AttachmentType.PNG)
        log.info(f"📸 截图已保存: {name}")
        return screenshot

    def take_canvas_screenshot(self, name: str = "canvas_screenshot"):
        """截取 Canvas 截图"""
        try:
            canvas = self.ctx.base.get_canvas()
            screenshot = canvas.screenshot()
            allure.attach(screenshot, name=name, attachment_type=AttachmentType.PNG)
            log.info(f"🎨 Canvas截图已保存: {name}")
            return screenshot
        except Exception as e:
            self.log_error(f"Canvas 截图失败: {e}")
            return None

    def assert_canvas_screenshot(self, name: str, max_diff_pixel_ratio: float = 0.02,
                                 ignore_regions=(), update_baseline: bool = False,
                                 message: str = None):
        """断言 Canvas 渲染结果与基准图一致

        - 只截取 Canvas 元素，不包含整页
        - 截图时自动隐藏弹窗/提示/加载态等动态浮层
        - 基准图不存在时自动生成（首次运行）
        - max_diff_pixel_ratio 默认 0.02，即允许 2% 的像素差异
        """
        canvas = self.ctx.base.get_canvas()
        if canvas.count() == 0:
            self.assert_true(False, message or "Canvas 不存在，无法进行截图比对")
            return None

        return self.ui.assert_canvas_screenshot_match(
            canvas,
            name,
            max_diff_pixel_ratio=max_diff_pixel_ratio,
            style=self.ctx.base.get_canvas_overlay_style(),
            ignore_regions=ignore_regions,
            update_baseline=update_baseline,
            message=message,
        )

    # ==================== 元素操作便捷方法 ====================

    def click(self, selector: str):
        """点击元素"""
        self.ctx.click(selector)

    def fill(self, selector: str, text: str):
        """填写输入框"""
        self.ctx.fill(selector, text)

    def get_text(self, selector: str) -> str:
        """获取元素文本"""
        return self.ctx.get_text(selector)

    # ==================== 业务操作便捷方法 ====================

    def login(self, username: str = None, password: str = None):
        """登录"""
        return self.ctx.login(username, password)

    def logout(self):
        """登出"""
        return self.ctx.logout()

    def upload_model(self, file_path: str = None) -> bool:
        """上传模型"""
        return self.ctx.upload_model(file_path)

    def wait_for_model_load(self, timeout: int = None) -> bool:
        """等待模型加载"""
        return self.ctx.wait_for_model_load(timeout)

    def navigate_to(self, url: str = None):
        """导航到指定URL"""
        return self.ctx.navigate(url)


    # ==================== 性能监控 ====================

    def measure_time(self, func: Callable, *args, **kwargs) -> tuple:
        """测量函数执行时间"""
        return self.perf.measure(func, *args, **kwargs)

    def add_performance_metric(self, name: str, value: float, unit: str = "ms", threshold: float = None):
        """添加性能指标"""
        self.perf.add(name, value, unit, threshold)

    def assert_performance(self, duration: float, threshold: float = 500, operation: str = "操作"):
        """断言性能在阈值内"""
        # 记录到性能监控器
        self.perf.add(operation, duration, threshold=threshold)

        # 断言
        is_pass = duration <= threshold
        self.assert_true(is_pass, f"{operation} 耗时 {duration:.2f}ms 超过阈值 {threshold}ms")

        if is_pass:
            self.log_success(f"✅ {operation} 耗时 {duration:.2f}ms")
        else:
            self.log_error(f"❌ {operation} 耗时 {duration:.2f}ms 超过阈值 {threshold}ms")

        return is_pass




    # ==================== 等待方法 ====================

    def wait_for_element(self, selector: str, timeout: int = 10000):
        """等待元素出现"""
        return self.page.wait_for_selector(selector, timeout=timeout)
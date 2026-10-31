# context/api_context.py
import os.path
from pathlib import Path

import allure
from common.context.base_context import BaseContext
from playwright.sync_api import Page
from ui.pages.base_page import BasePage
from ui.methods.view_methods import ViewMethods
from ui.methods.measure_methods import MeasurementMethods
from ui.methods.toolbar_methods import ToolbarMethods
from ui.methods.base_methods import BaseMethods
from common.config.settings import Config
from common.utils.logger import log
import time


class UIContext(BaseContext):
    """
    统一上下文
    职责：环境管理、登录、开关、数据
    """

    def __init__(self, page: Page):
        # 调用父类初始化
        super().__init__()
        self.page = page
        self.base_page = BasePage(page)
        # 加载主页面定位器
        self.base_page.load_locators("main_page_locators.yaml")
        # 初始化基础方法（传入 self，让 BaseMethods 能访问 Context）
        self.base = BaseMethods(self)
        # 初始化业务方法（传入 self）
        self.view = ViewMethods(self)
        self.measure = MeasurementMethods(self)
        self.toolbar = ToolbarMethods(self)

        # 环境配置
        self.env = Config.ENV
        self.base_url = Config.BASE_URL

        # 登录状态
        self._is_logged_in = False

        # 模型加载状态
        self._model_loaded = False


    # ==================== 实现 BaseContext 抽象方法 ====================
    def setup(self):
        """初始化UI上下文"""
        self.logger.info("🚀 初始化UI上下文")
        # 可以在这里做一些初始化工作
        # 比如：设置默认超时、清除缓存等
        self.page.set_default_timeout(Config.UI_TIMEOUT)
        self.logger.info("✅ UI上下文初始化完成")
        return self

    def teardown(self):
        """清理UI上下文"""
        self.logger.info("🧹 清理UI上下文")
        self.cleanup()  # 调用你现有的cleanup方法
        self.logger.info("✅ UI上下文清理完成")
        return self

    def get_session(self):
        """获取会话对象 - UI返回page"""
        return self.page

    def navigate(self, url: str = None):
        """导航到页面（实现BaseContext的抽象方法）"""
        if url is None:
            url = self.base_url
        self.page.goto(url)
        self.logger.info(f"✅ 页面导航成功: {url}")
        return self
    # ==================== 环境管理 ====================

    def set_env(self, env: str):
        """设置环境"""
        self.env = env
        if env == "test":
            self.base_url = Config.TEST_URL
        elif env == "prod":
            self.base_url = Config.PROD_URL
        elif env == "ci":
            self.base_url = Config.CI_URL
        return self

    def get_env(self) -> str:
        """获取当前环境"""
        return self.env

    # ==================== 登录管理 ====================

    def login(self, username: str = None, password: str = None):
        """登录"""
        if username is None:
            username = Config.DEFAULT_USERNAME
        if password is None:
            password = Config.DEFAULT_PASSWORD

        self.page.goto(f"{self.base_url}/login")
        self.base_page.fill(selector="input[name='username']", text=username)
        self.base_page.fill(selector="input[name='password']", text=password)
        self.base_page.click(selector="button[type='submit']")
        time.sleep(2)

        self._is_logged_in = True
        print(f"✅ 登录成功: {username}")
        return self

    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self._is_logged_in

    def logout(self):
        """登出"""
        self.page.goto(f"{self.base_url}/logout")
        self._is_logged_in = False
        print("✅ 已登出")
        return self


    # ==================== 模型上传和加载（使用 base 方法） ====================

    def upload_model(self, file_path: str = None) -> bool:
        """上传模型并等待跳转到查看页"""
        if file_path is None:
            file_path = Config.TEST_MODEL_PATH

        try:
            # 使用 base_page 的定位器方法
            file_input = self.base_page.get_element('main_page', 'file_input')
            if file_input.count() == 0:
                log.error("❌ 未找到上传控件")
                return False

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            self.logger.info(f"正在上传模型: {Path(file_path).name}")

            # 首页 React 应用挂载完成后 <input> 的 onChange 才会生效，
            # 刚导航完立刻 set_input_files 会被静默丢弃（页面一直停在首页）。
            try:
                self.page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                self.logger.warning("⚠️ 等待页面网络空闲超时，继续尝试上传")
            self.page.wait_for_timeout(1000)

            file_input.set_input_files(file_path)

            # 页面选中文件后会立即发起转换，并把 <input> 重新渲染（files 会变回 0），
            # 所以不能用 files.length 判断成败，以是否进入 /viewer 页面为准。
            deadline = time.time() + Config.MODEL_LOAD_TIMEOUT / 1000
            while time.time() < deadline:
                current = self.page.url
                if "/viewer" in current and "modelId=" in current:
                    log.info(f"✅ 模型上传成功，已进入查看页: {current}")
                    allure.attach(self.page.screenshot(), name="上传后状态",
                                  attachment_type=allure.attachment_type.PNG)
                    return True
                if "passport.jlc.com" in current:
                    raise RuntimeError(
                        "站点跳转到了登录页（匿名预览额度可能已用尽），"
                        f"请登录或更换出口 IP 后重试: {current}"
                    )
                self.page.wait_for_timeout(500)

            raise RuntimeError(f"上传后未能进入查看页，当前 URL: {self.page.url}")

        except Exception as e:
            log.error(f"❌ 模型上传失败: {e}")
            # 失败时也截图
            try:
                allure.attach(self.base_page.page.screenshot(), name="上传失败状态",
                              attachment_type=allure.attachment_type.PNG)
            except:
                pass
            return False
    def wait_for_model_load(self, timeout: int = None) -> bool:
        """等待模型加载完成"""
        if timeout is None:
            timeout = Config.MODEL_LOAD_TIMEOUT

        try:
            # 1. 等待加载进度条消失
            loading = self.base_page.get_element('main_page', 'model_loading')
            if loading.count() > 0:
                loading.wait_for(state="detached", timeout=timeout)
                print("✅ 加载进度条消失")

            # 2. 等待查看器工具栏出现（Canvas 出现得更早，工具栏出现才说明模型渲染完成）
            if not self.base.wait_for_toolbar("回到原点", timeout=timeout):
                raise RuntimeError("查看器工具栏未出现，模型可能未加载完成")

            # 3. 切换到 iframe（使用 base 方法）
            self.base.switch_to_iframe()

            # 4. 等待 Canvas 出现（使用 base 方法）
            self.base.wait_for_canvas(timeout)
            self.logger.info("✅ Canvas 可见，模型加载完成")

            self._model_loaded = True
            return True

        except Exception as e:
            self.logger.error(f"❌ 模型加载超时: {e}")
            return False

    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._model_loaded

    # ==================== 开关管理 ====================

    def set_feature_switch(self, feature: str, enabled: bool):
        """设置功能开关"""
        self.page.evaluate(f"""
            localStorage.setItem('feature_{feature}', '{enabled}');
        """)
        log.info(f"✅ 功能开关 {feature}: {enabled}")
        return self

    def get_feature_switch(self, feature: str) -> bool:
        """获取功能开关状态"""
        result = self.page.evaluate(f"""
            localStorage.getItem('feature_{feature}');
        """)
        return result == 'true'

    # ==================== 代理 BasePage 方法（便捷方法） ====================

    def click(self, *args, **kwargs):
        return self.base_page.click(*args, **kwargs)

    def fill(self, *args, **kwargs):
        return self.base_page.fill(*args, **kwargs)

    def get_text(self, *args, **kwargs):
        return self.base_page.get_text(*args, **kwargs)

    def screenshot(self, *args, **kwargs):
        return self.base_page.screenshot(*args, **kwargs)

    # ==================== 清理 ====================

    def cleanup(self):
        """清理环境"""
        self.base.switch_to_main()
        self.clear_data()  # 使用父类的方法
        self.logger.info("✅ 环境清理完成")
        return self
    #====================等待=======================
    def wait_for(self, condition, timeout: int = None):
        """
        等待条件满足

        Args:
            condition: 可以是选择器字符串，也可以是返回bool的函数
            timeout: 超时时间（毫秒）
        """
        if timeout is None:
            timeout = Config.UI_TIMEOUT

        if isinstance(condition, str):
            # 如果是字符串，当作选择器处理
            self.logger.debug(f"等待元素出现: {condition}")
            return self.page.wait_for_selector(condition, timeout=timeout)
        elif callable(condition):
            # 如果是函数，轮询执行直到返回True
            start_time = time.time()
            timeout_sec = timeout / 1000
            while time.time() - start_time < timeout_sec:
                try:
                    if condition():
                        return True
                except Exception as e:
                    self.logger.debug(f"条件检查异常: {e}")
                time.sleep(0.1)
            raise TimeoutError(f"等待条件超时 ({timeout}ms)")
        else:
            raise ValueError(f"不支持的condition类型: {type(condition)}")
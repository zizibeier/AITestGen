# utils/logger.py
import logging
import allure
from datetime import datetime
from common.config.settings import Config


class TestLogger:
    """统一日志工具 - 同时输出到控制台、文件、Allure报告"""

    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_logger()
        return cls._instance

    def _setup_logger(self):
        """设置日志器"""
        # 创建日志目录
        log_dir = Config.LOG_DIR
        log_dir.mkdir(exist_ok=True)

        # 日志文件名
        log_file = log_dir / f"test_{datetime.now().strftime('%Y%m%d')}.log"

        # 创建 logger
        self._logger = logging.getLogger("TestLogger")
        self._logger.setLevel(logging.INFO)

        # 避免重复添加 handler
        if self._logger.handlers:
            return

        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)

        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

    def info(self, message: str, allure_attach: bool = True):
        """记录信息日志"""
        self._logger.info(message)
        if allure_attach:
            allure.attach(message, name="📝 日志信息", attachment_type=allure.attachment_type.TEXT)

    def success(self, message: str, allure_attach: bool = True):
        """记录成功日志"""
        msg = f"✅ {message}"
        self._logger.info(msg)
        if allure_attach:
            allure.attach(msg, name="✅ 成功", attachment_type=allure.attachment_type.TEXT)

    def error(self, message: str, allure_attach: bool = True):
        """记录错误日志"""
        msg = f"❌ {message}"
        self._logger.error(msg)
        if allure_attach:
            allure.attach(msg, name="❌ 错误", attachment_type=allure.attachment_type.TEXT)

    def warning(self, message: str, allure_attach: bool = True):
        """记录警告日志"""
        msg = f"⚠️ {message}"
        self._logger.warning(msg)
        if allure_attach:
            allure.attach(msg, name="⚠️ 警告", attachment_type=allure.attachment_type.TEXT)

    def debug(self, message: str, allure_attach: bool = False):
        """记录调试日志"""
        msg = f"🔍 {message}"
        self._logger.debug(msg)
        if allure_attach:
            allure.attach(msg, name="🔍 调试", attachment_type=allure.attachment_type.TEXT)

    def step(self, message: str, allure_attach: bool = True):
        """记录步骤日志"""
        msg = f"▶ {message}"
        self._logger.info(msg)
        if allure_attach:
            allure.attach(msg, name="📌 步骤", attachment_type=allure.attachment_type.TEXT)

    def section(self, title: str):
        """记录章节分隔"""
        separator = "=" * 60
        self._logger.info(separator)
        self._logger.info(f"  {title}")
        self._logger.info(separator)
        allure.attach(f"\n{separator}\n  {title}\n{separator}",
                      name="📑 章节",
                      attachment_type=allure.attachment_type.TEXT)

    def attach_screenshot(self, screenshot_bytes, name: str = "截图"):
        """附加截图到报告"""
        allure.attach(screenshot_bytes, name=name, attachment_type=allure.attachment_type.PNG)

    def attach_text(self, text: str, name: str = "文本信息"):
        """附加文本到报告"""
        allure.attach(text, name=name, attachment_type=allure.attachment_type.TEXT)

    def attach_json(self, data: dict, name: str = "JSON数据"):
        """附加JSON到报告"""
        import json
        allure.attach(json.dumps(data, indent=2, ensure_ascii=False),
                      name=name,
                      attachment_type=allure.attachment_type.JSON)


# 全局日志实例
log = TestLogger()
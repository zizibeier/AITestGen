# config/settings.py
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent

# 本地开发从仓库根目录的 .env 读取配置；
# override=False 保证 CI / 容器注入的环境变量优先级更高。
load_dotenv(PROJECT_ROOT / ".env", override=False)

class Config:
    #============UI==========
    # 浏览器配置
    HEADLESS = True
    SLOW_MO = 300

    # 视口配置
    VIEWPORT_WIDTH = 1920
    VIEWPORT_HEIGHT = 1080
    # AI 断言配置（兼容 OpenAI Chat Completions 协议）
    AI_ASSERT_API_KEY = os.getenv("AI_ASSERT_API_KEY") or os.getenv("CEREBRAS_API_KEY", "")
    AI_ASSERT_BASE_URL = os.getenv("AI_ASSERT_BASE_URL", "")
    AI_ASSERT_MODEL = os.getenv("AI_ASSERT_MODEL", "")
    AI_ASSERT_TIMEOUT = float(os.getenv("AI_ASSERT_TIMEOUT", "30"))
    AI_ASSERT_MAX_CHARS = int(os.getenv("AI_ASSERT_MAX_CHARS", "12000"))

    # 截图配置
    SCREENSHOT_ON_EACH_TEST = True  # 每个用例后是否截图
    # 登录配置
    AUTO_LOGIN = False
    DEFAULT_USERNAME = os.getenv("UI_USERNAME", "")
    DEFAULT_PASSWORD = os.getenv("UI_PASSWORD", "")

    CI_URL = "https://3d-viewer.jlc.com/"
    PROD_URL = "https://3d-viewer.jlc.com/"
    TEST_URL = "https://test-3d-viewer.jlc.com/"
    ENV = None
    BASE_URL = "https://3d-viewer.jlc.com/"

    # 获取当前文件所在目录
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 模型上传拼接路径（自动适配 Windows/Linux）
    TEST_MODEL_PATH = os.path.join(BASE_DIR, "files", "气垫.STEP")

    # 视觉回归基准图目录
    UI_BASELINE_DIR = Path(BASE_DIR) / "ui" / "baselines"
    # 模型配置
    AUTO_NAVIGATE_TO_DESIGNER = False
    AUTO_UPLOAD_MODEL = True

    # 超时设置
    DEFAULT_TIMEOUT = 30000  # 30秒
    MODEL_LOAD_TIMEOUT = 60000  # 60秒
    UI_TIMEOUT= 60000
    # 截图设置
    SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots"

    LOG_DIR = Path(__file__).parent.parent / "logs"


    # 报告设置
    REPORT_DIR = Path(__file__).parent.parent / "reports"

    @classmethod
    def ensure_dirs(cls):
        """确保目录存在"""
        cls.SCREENSHOT_DIR.mkdir(exist_ok=True)
        cls.REPORT_DIR.mkdir(exist_ok=True)

    #================API=================
    API_BASE_URL="https://api.forface3d.com"
    APP_ID = os.getenv("API_APP_ID", "")
    APP_SECRET = os.getenv("API_APP_SECRET", "")
    TOKEN_URL='/forface/external/oauth/getAccessToken'

    # 是否自动获取 Token
    API_AUTO_LOGIN = os.getenv("API_AUTO_LOGIN", "True").lower() == "true"

    # API 超时时间
    API_TIMEOUT = 30
    API_MAX_RETRIES = 3
    # ========== Webhook 配置 ==========
    WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")
    WEBHOOK_KEY = os.getenv("WEBHOOK_KEY", "")
    WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "180"))
    # ========== Builder ==========
    # Web 前端内部接口（Token/Cookie），禁止在接口代码中使用 UI 的 web_url
    BUILDER_BASE_URL = os.getenv("BUILDER_BASE_URL", "https://prod.forface3d.com")
    # 对外 OpenAPI（AppID/Secret -> Bearer）
    BUILDER_OPEN_BASE_URL = os.getenv("BUILDER_OPEN_BASE_URL", API_BASE_URL)
    # Web 端 Token / Cookie 只从环境变量注入，不写死
    BUILDER_WEB_TOKEN = os.getenv("BUILDER_WEB_TOKEN", "")
    BUILDER_WEB_COOKIE = os.getenv("BUILDER_WEB_COOKIE", "")
    # autoRequestModel 所需业务标识
    BUILDER_USER_ID = os.getenv("BUILDER_USER_ID", "")
    BUILDER_WEBHOOK_KEY = os.getenv("BUILDER_WEBHOOK_KEY", "")
    # 在线用例使用的模型信息（未配置则跳过）
    BUILDER_TEST_MODEL_KEY = os.getenv("BUILDER_TEST_MODEL_KEY", "")
    BUILDER_TEST_MODEL_NAME = os.getenv("BUILDER_TEST_MODEL_NAME", "")
    # 下载目录
    BUILDER_DOWNLOAD_DIR = Path(os.getenv("BUILDER_DOWNLOAD_DIR", str(Path(BASE_DIR) / "downloads")))

    # ========== 文件路径 ==========

    # 测试文件目录
    TEST_FILES_DIR = Path(__file__).parent.parent.parent / "files"

    @classmethod
    def get_test_file_path(cls, filename: str) -> str:
        """获取测试文件路径"""
        return str(cls.TEST_FILES_DIR / filename)
# 环境配置
class TestConfig(Config):
    """测试环境配置"""
    HEADLESS = False
    SLOW_MO = 100  # 慢动作延迟(ms)


class CIConfig(Config):
    """CI环境配置"""
    HEADLESS = True
    SLOW_MO = 0


# config/settings.py 添加邮件配置

# ==================== 邮件配置 ====================
class EmailConfig:
    """邮件配置（从环境变量 / .env 读取，QQ 邮箱使用授权码而不是登录密码）"""
    SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.qq.com")
    SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "465"))

    SENDER = os.getenv("EMAIL_SENDER", "")
    PASSWORD = os.getenv("EMAIL_PASSWORD", "")

    # 收件人列表，支持英文逗号分隔多个地址
    RECIPIENTS = [
        item.strip()
        for item in os.getenv("EMAIL_RECIPIENTS", "").split(",")
        if item.strip()
    ]

    # 邮件主题前缀
    SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[测试]")
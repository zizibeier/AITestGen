# conftest.py
"""
pytest 全局配置文件
"""

import pytest
import allure

from common.config.settings import Config
from common.utils.logger import log
from common.utils.data_utils.data_loader import TestDataLoader
from api.core.api_context import APIContext


# ==================== 命令行参数 ====================

def pytest_addoption(parser):
    """添加命令行参数"""
    parser.addoption(
        "--env",
        action="store",
        default="test",
        choices=["dev", "test", "staging", "prod"],
        help="设置测试环境"
    )
    parser.addoption(
        "--api-timeout",
        action="store",
        default=30,
        type=int,
        help="API 超时时间（秒）"
    )
    parser.addoption(
        "--api-auto-login",
        action="store_true",
        default=True,
        help="是否自动登录获取 Token"
    )


def pytest_configure(config):
    """pytest 启动时的配置"""
    # 获取命令行参数
    env = config.getoption("--env")
    api_timeout = config.getoption("--api-timeout")
    api_auto_login = config.getoption("--api-auto-login")

    # 更新配置
    Config.ENV = env
    Config.API_TIMEOUT = api_timeout
    Config.API_AUTO_LOGIN = api_auto_login

    # 加载测试数据
    TestDataLoader.load()

    # 设置 Allure 环境信息
    allure.dynamic.environment(
        environment=env,
        api_base_url=Config.API_BASE_URL,
        api_timeout=str(api_timeout),
        auto_login=str(api_auto_login)
    )

    log.info(f"测试环境: {env}")
    log.info(f"API 地址: {Config.API_BASE_URL}")
    log.info(f"API 超时: {api_timeout}秒")


# ==================== Session 级别 fixtures ====================

@pytest.fixture(scope="session")
def api_context():
    """
    Session 级别的 API 上下文
    整个测试会话共享一个 API 客户端
    """
    ctx = APIContext(Config.API_BASE_URL)
    ctx.setup()

    # 鉴权由 APIContext / AuthManager 自动处理：首次请求时自动换取并附加 Bearer Token。
    # 这里只做启动预检，不手动持有、不手动下发 Token。
    if Config.API_AUTO_LOGIN:
        try:
            ctx.ensure_token()
            log.info("✅ API 自动认证成功")
        except Exception as e:
            log.warning(f"API 自动认证失败: {e}")

    yield ctx

    ctx.teardown()
    log.info("✅ API 上下文已关闭")


@pytest.fixture(scope="session")
def api_client(api_context):
    """API 客户端别名"""
    return api_context



@pytest.fixture
def api(api_context):
    """API 上下文别名"""
    return api_context

@pytest.fixture
def endpoints(api):
    """
    所有 endpoint 的工厂

    使用方式：
        endpoints.user.login(...)
    """
    from api.endpoints import (
        AnalysisEndpoints,
        BaiduEndpoints,
        BuilderOpenEndpoints,
        BuilderWebEndpoints,
    )

    class Endpoints:
        def __init__(self, ctx):
            self._analysis = AnalysisEndpoints(ctx)
            self._baidu = BaiduEndpoints(ctx)
            self._builder_open = BuilderOpenEndpoints(ctx)
            self._builder_web = BuilderWebEndpoints(ctx)

        @property
        def analysis(self):
            return self._analysis

        @property
        def baidu(self):
            return self._baidu

        @property
        def builder_open(self):
            return self._builder_open

        @property
        def builder_web(self):
            return self._builder_web



    return Endpoints(api)



# ==================== 测试数据 fixtures ====================

@pytest.fixture
def test_data():
    """测试数据 fixture"""
    return TestDataLoader.get_all()


@pytest.fixture
def admin_user():
    """管理员用户数据"""
    return TestDataLoader.get("users.admin", {})


@pytest.fixture
def normal_user():
    """普通用户数据"""
    return TestDataLoader.get("users.normal_user", {})


@pytest.fixture
def invalid_user():
    """无效用户数据"""
    return TestDataLoader.get("users.invalid_user", {})


@pytest.fixture
def login_cases():
    """登录测试用例"""
    return TestDataLoader.get_test_cases("login_test_cases")


@pytest.fixture
def model_cases():
    """模型测试用例"""
    return TestDataLoader.get_test_cases("model_upload_cases")


# ==================== 钩子函数 ====================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """测试失败时记录信息"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        # 获取 api_context fixture
        api_ctx = None

        # 从 fixture 中获取
        if hasattr(item, "_fixtureinfo"):
            for fixture in item._fixtureinfo.name2fixturedefs.get("api_context", []):
                if hasattr(fixture, "cached_result"):
                    api_ctx = fixture.cached_result[0]
                    break

        # 从测试实例中获取
        if not api_ctx and hasattr(item, "instance"):
            api_ctx = getattr(item.instance, "api", None)

        if api_ctx:
            last_response = api_ctx.get_last_response()
            if last_response:
                allure.attach(
                    f"状态码: {last_response.status_code}\n\n响应体:\n{last_response.text[:2000]}",
                    name="失败时响应信息",
                    attachment_type=allure.attachment_type.TEXT
                )

            last_request = api_ctx._last_request
            if last_request:
                allure.attach(
                    f"请求: {last_request.get('method')} {last_request.get('url')}",
                    name="失败时请求信息",
                    attachment_type=allure.attachment_type.TEXT
                )


def pytest_collection_modifyitems(items):
    """修改测试用例标记"""
    # 凭据缺失时跳过在线用例，保证无 .env 的 CI / 新环境仍可完成收集
    missing_api_credentials = not (Config.APP_ID and Config.APP_SECRET)
    missing_webhook = not Config.WEBHOOK_BASE_URL
    skip_live_api = pytest.mark.skip(
        reason="未配置 API_APP_ID / API_APP_SECRET，跳过在线接口用例"
    )
    skip_webhook = pytest.mark.skip(
        reason="未配置 WEBHOOK_BASE_URL，跳过 Webhook 回调用例"
    )

    for item in items:
        # 根据目录自动添加标记
        if "api/tests" in str(item.fspath):
            item.add_marker(pytest.mark.api)
        elif "ui/tests" in str(item.fspath):
            item.add_marker(pytest.mark.ui)

        # 根据文件名添加标记
        if "test_user" in str(item.fspath):
            item.add_marker(pytest.mark.user)
        elif "test_model" in str(item.fspath):
            item.add_marker(pytest.mark.model)

        # 依赖 APIContext 的用例都需要 AppID / Secret 换取 Token
        if missing_api_credentials and "api_context" in getattr(item, "fixturenames", ()):
            item.add_marker(skip_live_api)
        # Webhook 用例还需要可访问的回调地址
        elif missing_webhook and (
            "webhook" in item.name.lower() or item.get_closest_marker("webhook")
        ):
            item.add_marker(skip_webhook)


# ==================== 自定义 markers ====================

def pytest_configure(config):
    """注册自定义 markers"""
    config.addinivalue_line("markers", "api: API 接口测试")
    config.addinivalue_line("markers", "ui: UI 界面测试")
    config.addinivalue_line("markers", "user: 用户相关测试")
    config.addinivalue_line("markers", "model: 模型相关测试")
    config.addinivalue_line("markers", "smoke: 冒烟测试")
    config.addinivalue_line("markers", "regression: 回归测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "webhook: 回调测试")
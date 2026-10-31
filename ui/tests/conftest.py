# tests/conftest.py（使用 BaseTest 时）
import pytest


def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption("--env", action="store", default="test", help="环境: test/ci/prod")
    parser.addoption("--headed", action="store_true", default=False, help="有头模式")


@pytest.fixture(scope="session")
def browser_context_args(request):
    """浏览器参数"""
    return {
        "headless": not request.config.getoption("--headed"),
        "slow_mo": 300
    }
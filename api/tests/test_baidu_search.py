# api/tests/test_baidu_search.py
"""
百度网页搜索真实接口测试

接口：GET https://www.baidu.com/s?wd=<关键词>（定义见 docs/api_specs/baidu_search.json）
断言：用 self.assert_ai_response 让大模型判断返回页面是否包含搜索关键词。

不使用任何 Mock：请求、AI 判定都走真实服务。
未配置 AI_ASSERT_API_KEY / CEREBRAS_API_KEY 时整个文件自动跳过。
"""
import allure
import pytest

from api.core.api_base_test import APIBaseTest
from common.assertions.ai_assertion import AIAssertion


pytestmark = pytest.mark.skipif(
    not AIAssertion.is_configured(),
    reason="未配置 AI_ASSERT_API_KEY / CEREBRAS_API_KEY",
)

KEYWORD = "自动化测试"


@allure.epic("百度搜索")
@allure.feature("网页搜索")
class TestBaiduSearch(APIBaseTest):
    """百度搜索接口"""

    @pytest.fixture(autouse=True)
    def setup_endpoints(self, api_context, endpoints):
        # api_context 供断言失败附件与 get_last_response() 使用
        self.api_context = api_context
        self.baidu = endpoints.baidu

    @allure.story("关键词搜索")
    @pytest.mark.smoke
    def test_search_result_contains_keyword(self):
        """搜索关键词，AI 断言返回结果包含该关键词"""
        allure.dynamic.title(f"百度搜索「{KEYWORD}」返回结果包含关键词")
        allure.dynamic.description(f"""
        ### 测试用例详情
        - 接口: GET https://www.baidu.com/s?wd={KEYWORD}
        - 预期: HTTP 200，返回的搜索页面包含关键词「{KEYWORD}」
        - 断言方式: self.assert_ai_response 语义断言
        """)

        with allure.step(f"发起搜索：{KEYWORD}"):
            response = self.baidu.search(KEYWORD)
            self.assert_status(response, 200, "百度搜索 HTTP 状态码为 200")
            allure.attach(
                response.text[:4000],
                name="搜索响应（前 4000 字符）",
                attachment_type=allure.attachment_type.HTML
            )

        with allure.step("AI 断言：返回结果包含关键词"):
            self.assert_ai_response(
                response,
                f"返回的是百度搜索结果页面，且页面中包含了搜索关键词「{KEYWORD}」"
                f"（例如出现在页面标题或搜索框中）",
                context=f"请求 GET /s?wd={KEYWORD}，响应类型为 text/html"
            )

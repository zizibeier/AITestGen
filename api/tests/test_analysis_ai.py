# api/tests/test_analysis_ai.py
"""
真实业务流的 AI 语义断言用例

流程：上传模型 → 轮询查询解析记录 → 用大模型判断响应是否表示“文件解析成功”
不使用任何 Mock：上传、查询、AI 判定全部走真实接口。

鉴权由 APIContext / AuthManager 自动完成，用例里不出现 Token、Authorization 或 requests。
所有接口调用都经 endpoints.analysis 封装。

未配置 AI_ASSERT_API_KEY / CEREBRAS_API_KEY 时整个文件自动跳过。
用例数据来自 api/data/analysis_test_data.yaml 的 standard 分组。
"""
import json

import allure
import pytest

from api.core.api_base_test import APIBaseTest
from api.data.analysis_test_data import get_cases_by_group
from common.assertions.ai_assertion import AIAssertion
from common.config.settings import Config


pytestmark = pytest.mark.skipif(
    not AIAssertion.is_configured(),
    reason="未配置 AI_ASSERT_API_KEY / CEREBRAS_API_KEY",
)


def get_case_display_name(case) -> str:
    """获取用例显示名称"""
    if case.extra_info and case.extra_info != "":
        return f"{case.name} - {case.extra_info}"
    return case.name


@allure.epic("CNC平台")
@allure.feature("零件解析")
class TestAnalysisAIAssertion(APIBaseTest):
    """用真实解析记录做 AI 语义断言"""

    @pytest.fixture(autouse=True)
    def setup_endpoints(self, api_context, endpoints):
        # api_context 供 APIBaseTest 的断言失败附件与 get_last_response() 使用
        self.api_context = api_context
        self.analysis = endpoints.analysis

    @allure.story("AI 语义断言")
    @pytest.mark.slow
    @pytest.mark.parametrize("case", get_cases_by_group("standard"), ids=get_case_display_name)
    def test_upload_and_ai_assert_parse_success(self, case):
        """上传后查询解析记录，用大模型断言文件解析成功"""
        allure.dynamic.title(f"【{case.name}】AI 断言：文件解析成功")
        allure.dynamic.description(f"""
        ### 测试用例详情
        - 用例名称: {case.name}
        - 文件名: {case.file_name}
        - 预览格式: {case.preview_type}
        - 业务服务: {case.need_business_service}
        - 轻量化: {case.need_stl_light_weight}
        - 使用缓存: {case.use_cache}
        - 扩展信息: {case.extra_info or '无'}
        """)

        with allure.step("上传模型文件"):
            upload = self.analysis.analysis_upload_file(
                file_path=Config.get_test_file_path(case.file_name),
                **case.to_api_params()
            )
            file_id = upload.get("file_id")
            allure.attach(
                json.dumps(upload.get("response"), ensure_ascii=False, indent=2)[:4000],
                name="上传响应",
                attachment_type=allure.attachment_type.JSON
            )
            self.assert_is_not_none(
                file_id, f"上传未返回 file_id: {upload.get('response')}"
            )

        with allure.step("轮询查询解析记录"):
            record = self.analysis.wait_for_record(
                file_id,
                timeout=float(case.query_timeout),
                interval=float(case.query_interval)
            )
            allure.attach(
                json.dumps(record, ensure_ascii=False, indent=2)[:4000],
                name="解析记录",
                attachment_type=allure.attachment_type.JSON
            )
            self.assert_is_not_none(
                record.get("data"), f"未查询到解析记录: {record.get('msg')}"
            )

        with allure.step("AI 语义断言：文件解析成功"):
            # 最近一次真实 HTTP 响应即 findByFileId 返回的解析记录
            response = self.api_context.get_last_response()
            self.assert_ai_response(
                response,
                "校验文件解析成功",
                context=f"上传返回的 file_id={file_id}，以下为按该 file_id 查询到的解析记录"
            )

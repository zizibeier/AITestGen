# api/tests/test_analysis_query.py
"""
零件解析记录查询用例

流程：上传模型 → 用返回的 file_id 轮询查询解析记录 → 校验记录归属与文件元信息
用例数据来自 api/data/analysis_test_data.yaml 的 query 分组
"""
import json
import os

import allure
import pytest

from api.core.api_base_test import APIBaseTest
from api.data.analysis_test_data import get_cases_by_group
from common.config.settings import Config


def get_case_display_name(case) -> str:
    """获取用例显示名称"""
    if case.extra_info and case.extra_info != "":
        return f"{case.name} - {case.extra_info}"
    return case.name


@allure.epic("CNC平台")
@allure.feature("零件解析")
class TestAnalysisQuery(APIBaseTest):
    """解析记录查询"""

    @pytest.fixture(autouse=True)
    def setup_endpoints(self, api_context, endpoints):
        # api_context 供 APIBaseTest 的断言失败附件使用
        self.api_context = api_context
        self.analysis = endpoints.analysis

    @allure.story("解析记录查询")
    @pytest.mark.parametrize("case", get_cases_by_group("query"), ids=get_case_display_name)
    def test_query_uploaded_file_record(self, case):
        """上传后能按 file_id 查询到解析记录，且文件元信息与上传文件一致"""
        allure.dynamic.title(f"【{case.name}】解析记录查询")
        allure.dynamic.description(f"""
        ### 测试用例详情
        - 用例名称: {case.name}
        - 文件名: {case.file_name}
        - 使用缓存: {case.use_cache}
        - 业务服务: {case.need_business_service}
        - 轻量化: {case.need_stl_light_weight}
        - 查询超时: {case.query_timeout}s / 间隔: {case.query_interval}s
        """)

        file_path = Config.get_test_file_path(case.file_name)
        expected_name = os.path.basename(case.file_name)
        expected_type = os.path.splitext(expected_name)[1].lstrip(".").lower()

        with allure.step("上传模型文件"):
            upload = self.analysis.analysis_upload_file(
                file_path=file_path,
                **case.to_api_params()
            )
            file_id = upload.get("file_id")
            allure.attach(
                f"file_id: {file_id}\nfile_name: {upload.get('file_name')}",
                name="上传结果",
                attachment_type=allure.attachment_type.TEXT
            )
            self.assert_is_not_none(
                file_id, f"上传未返回 file_id: {upload.get('response')}"
            )

        with allure.step(f"轮询查询解析记录（超时 {case.query_timeout}s）"):
            result = self.analysis.wait_for_record(
                file_id,
                timeout=float(case.query_timeout),
                interval=float(case.query_interval)
            )
            allure.attach(
                json.dumps(result, ensure_ascii=False, indent=2)[:4000],
                name="查询响应",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("校验解析记录"):
            self.assert_equal(
                str(result.get("code")), "00000",
                f"查询失败: {result.get('msg')}"
            )
            self.assert_true(
                result.get("success") is True,
                f"查询失败: {result.get('msg')}"
            )

            data = result.get("data") or {}
            self.assert_is_not_none(result.get("data"), "查询结果 data 为空")
            self.assert_equal(
                str(data.get("id")), str(file_id),
                "查询记录的 id 与上传返回的 file_id 不一致"
            )
            self.assert_equal(
                data.get("fileName"), expected_name,
                "查询记录的 fileName 与上传文件不一致"
            )
            self.assert_equal(
                str(data.get("fileType", "")).lower(), expected_type,
                "查询记录的 fileType 与上传文件扩展名不一致"
            )
            self.assert_true(bool(data.get("status")), "查询记录的 status 为空")
            self.assert_greater(
                int(data.get("fileSize") or 0), 0,
                "查询记录的 fileSize 应大于 0"
            )

    @allure.story("解析记录查询")
    @allure.title("查询不存在的 file_id 返回数据不存在")
    def test_query_unknown_file_id(self):
        """不存在的 file_id 应返回业务码 000012 且 data 为空"""
        result = self.analysis.get_status_by_id("0")

        self.assert_equal(
            str(result.get("code")), "000012",
            f"不存在的 file_id 应返回 000012，实际: {result.get('code')} {result.get('msg')}"
        )
        self.assert_true(result.get("success") is False, "查询失败时 success 应为 false")
        self.assert_is_none(result.get("data"), "数据不存在时 data 应为空")

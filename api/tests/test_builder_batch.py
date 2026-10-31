# api/tests/test_builder_batch.py
"""Builder 批量对比链路演示。

串联：
    BuilderWeb/OpenEndpoints -> json_comparator -> excel_helper -> excel_reporter

离线用例不访问网络；在线用例需要环境变量：
    BUILDER_WEB_TOKEN                      Web 内部接口
    BUILDER_USER_ID / BUILDER_WEBHOOK_KEY  autoRequestModel
    BUILDER_TEST_MODEL_KEY                 在线建模使用的模型编码
"""

import json
from pathlib import Path

import allure
import pytest
from openpyxl import Workbook, load_workbook

from api.core.api_base_test import APIBaseTest
from common.config.settings import Config
from common.utils.excel_helper import (
    read_and_prepare_data,
    read_batch_comparison_data,
    save_results,
)
from common.utils.excel_reporter import BatchParameterComparison
from common.utils.json_comparator import ParameterComparison


# ==================== 测试数据构造 ====================

def make_dataset(
    value="10",
    origin_value=None,
    equation="",
    name="长度",
    interface_name="Length",
    interface_full_name="Length",
    model_interface_id="10001",
    sub_params=None,
):
    component = {
        "name": name,
        "model_key": "MK001",
        "interfaceName": interface_name,
        "interfaceFullName": interface_full_name,
        "model_interface_id": model_interface_id,
        "driveType": "dimension",
        "value": value,
        "origin_value": value if origin_value is None else origin_value,
        "equationDesc": equation,
    }
    if sub_params:
        component["params"] = [{"step": sub_params}]
    return {"params": [{"step": [component]}]}


def make_sub_param(value, name="宽度", interface_name="Width", model_interface_id="20001"):
    return {
        "name": name,
        "interfaceName": interface_name,
        "interfaceFullName": f"Length/{name}",
        "model_interface_id": model_interface_id,
        "driveType": "dimension",
        "value": value,
        "origin_value": value,
        "equationDesc": "",
    }


COMPARE_CASES = [
    pytest.param(
        {
            "modelname": "未变化",
            "old": make_dataset("10"),
            "new": make_dataset("10"),
            "target": "长度",
            "has_changes": False,
            "status": "未变化",
            "value_changed": "否",
        },
        id="unchanged",
    ),
    pytest.param(
        {
            "modelname": "值变化",
            "old": make_dataset("10"),
            "new": make_dataset("12"),
            "target": "长度",
            "has_changes": True,
            "status": "修改",
            "value_changed": "是",
        },
        id="value-changed",
    ),
    pytest.param(
        {
            "modelname": "数值等价",
            "old": make_dataset("2.00"),
            "new": make_dataset("2"),
            "target": "长度",
            "has_changes": False,
            "status": "未变化",
            "value_changed": "否",
        },
        id="numeric-equivalent",
    ),
    pytest.param(
        {
            "modelname": "新增组件",
            "old": {"params": []},
            "new": make_dataset("10"),
            "target": "长度",
            "has_changes": True,
            "status": "新增",
            "value_changed": "是",
        },
        id="component-added",
    ),
    pytest.param(
        {
            "modelname": "删除组件",
            "old": make_dataset("10"),
            "new": {"params": []},
            "target": "长度",
            "has_changes": True,
            "status": "删除",
            "value_changed": "是",
        },
        id="component-removed",
    ),
    pytest.param(
        {
            "modelname": "子参数变化",
            "old": make_dataset("10", sub_params=[make_sub_param("5")]),
            "new": make_dataset("10", sub_params=[make_sub_param("6")]),
            "target": "宽度",
            "has_changes": True,
            "status": "修改",
            "value_changed": "是",
        },
        id="sub-param-changed",
    ),
]


@allure.epic("Builder")
@allure.feature("批量参数对比")
class TestBuilderBatch(APIBaseTest):
    """Builder 批量对比与报表链路。"""

    # ==================== 离线用例 ====================

    @allure.story("参数对比")
    @pytest.mark.parametrize("case", COMPARE_CASES)
    def test_parameter_comparison(self, case):
        """不同变更类型应得到正确的状态与值变更标记"""
        comparator = ParameterComparison()

        with allure.step(f"对比数据集: {case['modelname']}"):
            result = comparator.compare_datasets(
                case["old"],
                case["new"],
                modelname=case["modelname"],
            )

        self.assert_true(result["total_results"] >= 1, "对比结果不应为空")
        self.assert_equal(
            result["has_changes"],
            case["has_changes"],
            f"{case['modelname']}: has_changes 不符合预期",
        )

        target = next(
            (
                item
                for item in result["all_comparison_results"]
                if item["名称"] == case["target"]
            ),
            None,
        )
        self.assert_is_not_none(target, f"未找到参数: {case['target']}")
        self.assert_equal(target["状态"], case["status"])
        self.assert_equal(target["值变更"], case["value_changed"])

    @allure.story("批量报表")
    def test_batch_comparison_report(self, tmp_path):
        """Excel -> 对比 -> 染色报表 的完整链路"""
        source = tmp_path / "batch_source.xlsx"
        old_data = make_dataset("10")
        new_data = make_dataset("12")

        with allure.step("构造批量对比源文件"):
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.append(
                ["modelname", "model_fullname", "model_key", "old_data", "new_data", "attr_info"]
            )
            worksheet.append(
                [
                    "垫块",
                    "垫块-完整名称",
                    "MK001",
                    json.dumps(old_data, ensure_ascii=False),
                    json.dumps(new_data, ensure_ascii=False),
                    json.dumps([{"name": "长度", "value": "12"}], ensure_ascii=False),
                ]
            )
            worksheet.append(
                [
                    "底板",
                    "底板-完整名称",
                    "MK002",
                    json.dumps(old_data, ensure_ascii=False),
                    json.dumps(old_data, ensure_ascii=False),
                    None,
                ]
            )
            workbook.save(source)

        with allure.step("读取批量对比数据"):
            batch_data = read_batch_comparison_data(str(source))

        self.assert_equal(len(batch_data), 2)
        self.assert_equal(batch_data[0]["modelname"], "垫块")
        self.assert_equal(batch_data[0]["attr_info"][0]["name"], "长度")

        with allure.step("生成批量对比报表"):
            report_path = BatchParameterComparison(
                output_dir=str(tmp_path / "report"),
                no_change_display_count=1,
            ).generate_batch_report(batch_data)

        self.assert_true(Path(report_path).exists(), "批量报表未生成")

        report_workbook = load_workbook(report_path, read_only=True)
        try:
            sheet_names = report_workbook.sheetnames
            self.assert_in("汇总", sheet_names)
            self.assert_in("有变化模型对比", sheet_names)
            self.assert_in("无变化模型汇总", sheet_names)
            self.assert_in("无变化模型详情", sheet_names)
        finally:
            report_workbook.close()

    @allure.story("Excel 合并")
    def test_read_and_save_results(self, tmp_path):
        """read_and_prepare_data / save_results 应保留行号并合并结果列"""
        source = tmp_path / "builder_rows.xlsx"

        with allure.step("构造建模测试数据"):
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.append(["modelKey", "attr_info", "modelname"])
            worksheet.append(["MK001", '[{"name": "长度", "value": "10"}]', "垫块"])
            worksheet.append(["MK002", None, "底板"])
            workbook.save(source)

        with allure.step("读取数据并补充行号"):
            rows = read_and_prepare_data(str(source))

        self.assert_equal(len(rows), 2)
        self.assert_equal(rows[0]["_row_id"], 2)
        self.assert_equal(rows[1]["_row_id"], 3)
        self.assert_is_none(rows[1]["attr_info"])

        with allure.step("保存合并报告"):
            output_path = save_results(
                str(source),
                [
                    {
                        "_row_id": 2,
                        "状态": "成功",
                        "mqMsg": "msg-1",
                        "modelKey": "MK001",
                    }
                ],
                str(tmp_path / "out"),
                timestamp_str="20260101_000000",
            )

        self.assert_true(Path(output_path).exists(), "合并报告未生成")

        merged_workbook = load_workbook(output_path, read_only=True)
        try:
            merged_sheet = merged_workbook["完整报告"]
            headers = [cell.value for cell in merged_sheet[1]]
            self.assert_in("状态", headers)
            self.assert_in("mqMsg", headers)
            self.assert_in("modelKey_测试", headers)

            status_column = headers.index("状态") + 1
            self.assert_equal(merged_sheet.cell(row=2, column=status_column).value, "成功")
        finally:
            merged_workbook.close()

    # ==================== 在线用例（无环境变量自动跳过） ====================

    @allure.story("Web 内部接口")
    @pytest.mark.skipif(
        not Config.BUILDER_WEB_TOKEN,
        reason="未设置 BUILDER_WEB_TOKEN，跳过 Builder Web 接口用例",
    )
    def test_query_my_models(self, api_context, endpoints):
        """Web 端模型列表接口应返回分页结构"""
        self.api_context = api_context
        with allure.step("查询我的模型（第一页）"):
            data = endpoints.builder_web.query_my_models(page_size=5)

        self.assert_is_instance(data, dict)
        self.assert_in("total", data)
        self.assert_in("modelVoList", data)
        self.assert_is_instance(data["modelVoList"], list)
        self.assert_true(data["total"] >= 0)

        if data["modelVoList"]:
            first_model = data["modelVoList"][0]
            self.assert_in("id", first_model)
            self.assert_in("name", first_model)

    @allure.story("对外 OpenAPI")
    @pytest.mark.skipif(
        not (
            Config.BUILDER_USER_ID
            and Config.BUILDER_WEBHOOK_KEY
            and Config.BUILDER_TEST_MODEL_KEY
        ),
        reason="未配置 BUILDER_USER_ID / BUILDER_WEBHOOK_KEY / BUILDER_TEST_MODEL_KEY",
    )
    def test_auto_request_model(self, api_context, endpoints):
        """autoRequestModel 应返回 mqMsg"""
        self.api_context = api_context
        with allure.step("发送自动建模请求"):
            body = endpoints.builder_open.auto_request_model(
                model_key=Config.BUILDER_TEST_MODEL_KEY,
                model_name=Config.BUILDER_TEST_MODEL_NAME
                or Config.BUILDER_TEST_MODEL_KEY,
                attr_info=[{"name": "长度", "value": "10"}],
            )

        self.assert_in("code", body)
        mq_msg = endpoints.builder_open.extract_mq_msg(body)
        self.assert_is_not_none(mq_msg, "建模响应中没有 data.mqMsg")

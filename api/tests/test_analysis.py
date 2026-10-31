# api/tests/test_cnc_endpoints.py
"""
CNC Endpoints 测试用例
"""
import os

import pytest
import allure
from common.config.settings import Config
from common.utils.webhook_utils.webhook_listener import WebhookListener
from api.data.analysis_test_data import get_all_cases,get_cases_by_group


def get_case_display_name(case) -> str:
    """获取用例显示名称"""
    # 如果有额外信息，显示更详细
    if case.extra_info and case.extra_info != "":
        return f"{case.name} - {case.extra_info}"
    return case.name

@allure.epic("CNC平台")
@allure.feature("零件解析")
class TestAnalysisEndpoints:
    @pytest.fixture(autouse=True)
    def setup(self, endpoints):
        self.analysis = endpoints.analysis
        self.webhook = WebhookListener(Config.WEBHOOK_BASE_URL)
        self.webhook.reset()

    # ==================== 方式1：运行所有用例 ====================

    @allure.story("全量测试")
    @pytest.mark.parametrize("case", get_all_cases(),ids=get_case_display_name)
    def test_all_cases(self, endpoints, case):
        """运行所有测试用例"""
        allure.dynamic.title(f"【{case.name}】测试")
        # 添加参数显示
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

        file_path = Config.get_test_file_path(case.file_name)

        # 处理预期异常
        if case.expect_exception:
            with pytest.raises(Exception):
                endpoints.analysis.analysis_upload_file(
                    file_path=file_path,
                    **case.to_api_params()
                )
            return

        # 正常上传
        result = endpoints.analysis.analysis_upload_file(
            file_path=file_path,
            **case.to_api_params()
        )

        assert result is not None
        assert result.get('file_id') is not None

    # ==================== 方式2：按分组运行 ====================

    @allure.story("标准功能测试")
    @pytest.mark.parametrize("case", get_cases_by_group("standard"), ids=get_case_display_name)
    def test_standard_cases(self, endpoints, case):
        """运行标准测试用例"""
        allure.dynamic.title(f"【{case.name}】测试")
        # 添加参数显示
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
        file_path = Config.get_test_file_path(case.file_name)

        # 处理预期异常
        if case.expect_exception:
            with pytest.raises(Exception):
                endpoints.analysis.analysis_upload_file(
                    file_path=file_path,
                    **case.to_api_params()
                )
            return

        # 正常上传
        result = endpoints.analysis.analysis_upload_file(
            file_path=file_path,
            **case.to_api_params()
        )

        assert result is not None
        assert result.get('file_id') is not None

    @allure.story("边界值测试")
    @pytest.mark.parametrize("case", get_cases_by_group("boundary"), ids=get_case_display_name)
    def test_boundary_cases(self, endpoints, case):
        """运行边界值测试用例"""
        allure.dynamic.title(f"【{case.name}】测试")
        # 添加参数显示
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
        file_path = Config.get_test_file_path(case.file_name)

        # 处理预期异常
        if case.expect_exception:
            with pytest.raises(Exception):
                endpoints.analysis.analysis_upload_file(
                    file_path=file_path,
                    **case.to_api_params()
                )
            return

        # 正常上传
        result = endpoints.analysis.analysis_upload_file(
            file_path=file_path,
            **case.to_api_params()
        )

        assert result is not None
        assert result.get('file_id') is not None

    @allure.story("参数组合测试")
    @pytest.mark.parametrize("case", get_cases_by_group("combination"), ids=get_case_display_name)
    def test_combination_cases(self, endpoints, case):
        """运行参数组合测试用例"""
        allure.dynamic.title(f"【{case.name}】测试")
        # 添加参数显示
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
        file_path = Config.get_test_file_path(case.file_name)

        # 处理预期异常
        if case.expect_exception:
            with pytest.raises(Exception):
                endpoints.analysis.analysis_upload_file(
                    file_path=file_path,
                    **case.to_api_params()
                )
            return

        # 正常上传
        result = endpoints.analysis.analysis_upload_file(
            file_path=file_path,
            **case.to_api_params()
        )

        assert result is not None
        assert result.get('file_id') is not None

    @allure.story("回归测试")
    @pytest.mark.parametrize("case", get_cases_by_group("regression"), ids=get_case_display_name)
    def test_regression_cases(self, endpoints, case):
        """运行回归测试用例"""
        allure.dynamic.title(f"【{case.name}】测试")
        # 添加参数显示
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
        file_path = Config.get_test_file_path(case.file_name)

        # 处理预期异常
        if case.expect_exception:
            with pytest.raises(Exception):
                endpoints.analysis.analysis_upload_file(
                    file_path=file_path,
                    **case.to_api_params()
                )
            return

        # 正常上传
        result = endpoints.analysis.analysis_upload_file(
            file_path=file_path,
            **case.to_api_params()
        )

        assert result is not None
        assert result.get('file_id') is not None

    @allure.story("异常测试")
    @pytest.mark.parametrize("case", get_cases_by_group("negative"), ids=get_case_display_name)
    def test_negative_cases(self, endpoints, case):
        """运行异常测试用例"""
        allure.dynamic.title(f"【{case.name}】测试")
        # 添加参数显示
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
        file_path = Config.get_test_file_path(case.file_name)

        # 处理预期异常
        if case.expect_exception:
            with pytest.raises(Exception):
                endpoints.analysis.analysis_upload_file(
                    file_path=file_path,
                    **case.to_api_params()
                )
            return

        # 正常上传
        result = endpoints.analysis.analysis_upload_file(
            file_path=file_path,
            **case.to_api_params()
        )

        assert result is not None
        assert result.get('file_id') is not None

    # ==================== 方式3：同时运行多个分组 ====================

    @allure.story("冒烟测试")
    @pytest.mark.smoke
    @pytest.mark.parametrize("case", get_cases_by_group("standard", "boundary"), ids=get_case_display_name)
    def test_smoke_cases(self, endpoints, case):
        """冒烟测试（标准+边界）"""
        allure.dynamic.title(f"【{case.name}】测试")
        # 添加参数显示
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
        file_path = Config.get_test_file_path(case.file_name)

        # 处理预期异常
        if case.expect_exception:
            with pytest.raises(Exception):
                endpoints.analysis.analysis_upload_file(
                    file_path=file_path,
                    **case.to_api_params()
                )
            return

        # 正常上传
        result = endpoints.analysis.analysis_upload_file(
            file_path=file_path,
            **case.to_api_params()
        )

        assert result is not None
        assert result.get('file_id') is not None


    # @allure.title("测试：零件解析文件上传")  # 添加 title
    # @allure.story("文件上传")
    # @pytest.mark.api
    # @pytest.mark.smoke
    # def test_analysis_upload_file(self):
    #     """测试：零件解析文件上传"""
    #     file_path = Config.get_test_file_path("配重块.stp")
    #     print(f"Epic: {getattr(self, 'epic', 'None')}")
    #
    #     result = self.analysis.analysis_upload_file(
    #         file_path=file_path,
    #         webhook_key=Config.WEBHOOK_KEY,
    #         previewType=1,
    #         needBusinessService=1,
    #         needStlLightWeight=1,
    #         params="21)71",
    #         extraInfo="21)71过"
    #     )
    #
    #     assert result['file_id'] is not None
    #     print(f"上传成功: {result['file_id']}")
    #

    @allure.title("测试：零件解析文件链接上传")  # 添加 title
    @allure.story("文件上传")
    @pytest.mark.api
    @pytest.mark.smoke
    def test_analysis_upload_file(self):
        """测试：零件解析文件链接上传"""
        filepath = "https://jlc-prod-forface-public.oss-cn-shenzhen.aliyuncs.com/1692809352278180161?fType=step"
        filename="面板.stp"
        filetype="stp"
        print(f"Epic: {getattr(self, 'epic', 'None')}")

        result = self.analysis.analysis_upload_filepath(
            filepath=filepath,
            filename=filename,
            filetype=filetype,
            webhook_key=Config.WEBHOOK_KEY,
            previewType=1,
            needBusinessService=1,
            needStlLightWeight=1,
            params="21)71",
            extraInfo="21)71过"
        )

        assert result['file_id'] is not None
        print(f"上传成功: {result['file_id']}")
    @allure.title("测试：上传不存在的文件")
    @allure.story("异常测试")
    @pytest.mark.api
    def test_upload_file_not_found(self):
        """测试：文件不存在"""
        with pytest.raises(FileNotFoundError):
            self.analysis.analysis_upload_file(file_path="test_files/不存在.stp")


    @allure.title("测试：webhook回调：验证存在analysis.part.finished")
    @allure.story("回调监听")
    @pytest.mark.api
    @pytest.mark.webhook
    @pytest.mark.slow
    def test_upload_with_webhook_wait(self, endpoints, api_context):
        """
        测试：上传并等待回调
        """
        webhook = WebhookListener(Config.WEBHOOK_BASE_URL)
        webhook.reset()

        with allure.step("上传文件"):
            result = endpoints.analysis.analysis_upload_file(
                file_path=Config.get_test_file_path("面板-1.stp"),
                webhook_key=Config.WEBHOOK_KEY
            )
            file_id = result['file_id']
            allure.attach(f"file_id: {file_id}", "上传结果", allure.attachment_type.TEXT)

        with allure.step("等待 Webhook 回调"):
            # 解包元组：record 是 WebhookRecord 对象，compare_result 是比较结果
            records,compare_results= webhook.wait_for_id(
                file_id=file_id,
                timeout=Config.WEBHOOK_TIMEOUT
            )
        with allure.step("验证回调结果"):
            # 验证至少收到一个回调
            assert len(records) > 0, "未收到任何回调"
            allure.attach(f"共收到 {len(records)} 个回调事件", "回调统计", allure.attachment_type.TEXT)

            # 查找特定事件（例如解析完成事件）
            target_event = "analysis.part.finished"
            finished_record = None
            finished_result = None

            for i, record in enumerate(records):
                allure.attach(
                    f"事件 {i + 1}: {record.event_id}",
                    "收到的事件",
                    allure.attachment_type.TEXT
                )

                if record.event_id == target_event:
                    finished_record = record
                    finished_result = compare_results[i] if i < len(compare_results) else None
                    break


            # 验证解析完成事件存在
            assert finished_record is not None, f"未收到 {target_event} 事件"
            assert finished_record.file_id == file_id

            # 测试代码中
            if finished_result:
                # 显示结构变化
                allure.attach(
                    WebhookListener.format_differences(finished_result),
                    "结构变化分析",
                    allure.attachment_type.TEXT
                )

                # 获取简要摘要
                summary = WebhookListener.get_summary(finished_result)
                if summary['has_change']:
                    print(f"结构变化: 缺失{summary['missing_count']}个, 新增{summary['added_count']}个")

                    # 如果是缺失关键字段，测试失败
                    if summary['missing_count'] > 0:
                        pytest.fail(f"数据结构缺失 {summary['missing_count']} 个必需字段")
            # 获取解析结果数据
            data = finished_record.payload.get('data', {})
            if data:
                allure.attach(
                    f"文件名: {data.get('fileName')}\n"
                    f"状态: {data.get('status')}\n"
                    f"分类: {data.get('classifyName', 'N/A')}\n"
                    f"消息: {data.get('message', 'N/A')}",
                    "解析结果",
                    allure.attachment_type.TEXT
                )




if __name__ == '__main__':

    # 报告目录
    allure_results_dir = "allure-results"
    allure_report_dir = "allure-report"

    # 清空旧报告
    if os.path.exists(allure_results_dir):
        import shutil

        shutil.rmtree(allure_results_dir)
        print(f"已清空: {allure_results_dir}")

    # 运行测试并生成 Allure 结果
    print("=" * 50)
    print("开始运行测试...")
    print("=" * 50)

    exit_code = pytest.main([
        __file__,  # 当前文件
        "-v",  # 详细输出
        "-s",  # 显示 print
        "--tb=short",  # 简化错误信息
        f"--alluredir={allure_results_dir}",  # 生成 Allure 结果
        "--clean-alluredir",
        "--allure-no-capture"  # 添加这个
        # 清空旧结果
    ])

    print("=" * 50)
    print(f"测试完成，退出码: {exit_code}")
    print("=" * 50)

    # 生成 Allure 报告
    if exit_code == 0 or exit_code == 1:  # 测试完成（无论通过还是失败）
        print("\n正在生成 Allure 报告...")
        os.system(f"allure generate {allure_results_dir} -o {allure_report_dir} --clean")

        # 打开报告
        report_path = os.path.abspath(f"{allure_report_dir}/index.html")
        print(f"\n报告已生成: {report_path}")


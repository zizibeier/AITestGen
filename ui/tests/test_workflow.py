# tests/test_workflow.py
import allure
from ui.tests.ui_base_test import BaseDesignTest


@allure.feature("完整工作流")
class TestWorkflow(BaseDesignTest):
    """完整工作流测试类"""

    @allure.story("视图操作+测量")
    def test_full_workflow(self):
        """测试完整工作流程"""
        self.log_info("开始测试完整工作流程")

        try:
            # 1. 旋转视图
            with allure.step("旋转视图"):
                self.design.view.rotate(100, 0)
                self.wait_for_animation()
                self.log_success("旋转视图完成")

            # 2. 缩放视图
            with allure.step("缩放视图"):
                self.design.view.zoom(200)
                self.wait_for_animation()
                self.log_success("缩放视图完成")

            # 3. 平移视图
            with allure.step("平移视图"):
                self.design.view.pan(50, 50)
                self.wait_for_animation()
                self.log_success("平移视图完成")

            # 4. 测量
            with allure.step("激活测量工具"):
                self.design.ensure_in_main()
                self.design.toolbar.click_tool("测量")
                self.log_success("测量工具激活")

            with allure.step("进行测量"):
                self.design.ensure_in_iframe()
                distance = self.design.measure.measure_distance(150, 150, 350, 350)
                self.assert_not_none(distance, "测量失败")
                allure.attach(f"测量距离: {distance}mm", name="测量结果", attachment_type=AttachmentType.TEXT)
                self.log_success(f"测量完成，距离: {distance}mm")

            # 5. 重置视图
            with allure.step("重置视图"):
                self.design.view.reset()
                self.wait_for_animation()
                self.log_success("视图重置完成")

            # 6. 截图
            with allure.step("截图保存"):
                self.take_screenshot("完整工作流最终截图")
                self.log_success("截图保存成功")

            self.log_success("✅ 完整工作流程测试通过")

        finally:
            self.design.ensure_in_iframe()

    @allure.story("视图操作+批注")
    def test_view_with_annotation(self):
        """测试视图操作与批注组合"""
        self.log_info("开始测试视图操作与批注组合")

        # 旋转视图
        self.design.view.rotate(90, 0)
        self.take_screenshot("旋转后视图")

        # 缩放视图
        self.design.view.zoom(150)
        self.take_screenshot("缩放后视图")

        # 重置
        self.design.view.reset()
        self.take_screenshot("重置后视图")

        self.log_success("视图操作与批注组合测试通过")
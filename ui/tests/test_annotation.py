# tests/test_annotation.py
import pytest
import time
import allure


@allure.feature("批注功能")
class TestAnnotation:
    """批注功能测试类 - 使用独立模型，避免批注污染"""

    @allure.story("添加批注")
    @allure.title("测试添加批注功能")
    def test_add_annotation(self, fresh_uploaded_model):
        """测试：添加批注 - 使用独立模型"""
        annotation = fresh_uploaded_model.annotation

        with allure.step("添加批注: '测试批注内容'"):
            result = annotation.add_annotation("测试批注内容")
            assert result, "添加批注失败"
            time.sleep(1)

        with allure.step("验证批注已添加"):
            count = annotation.get_annotation_count()
            assert count > 0, "批注未添加成功"

    @allure.story("删除批注")
    @allure.title("测试删除批注功能")
    def test_delete_annotation(self, fresh_uploaded_model):
        """测试：删除批注 - 使用独立模型"""
        annotation = fresh_uploaded_model.annotation

        with allure.step("添加待删除的批注"):
            annotation.add_annotation("待删除批注")
            time.sleep(1)

        with allure.step("删除批注"):
            result = annotation.delete_annotation(0)
            assert result, "删除批注失败"
            time.sleep(1)

        with allure.step("验证批注已删除"):
            count = annotation.get_annotation_count()
            assert count == 0, "批注未删除成功"
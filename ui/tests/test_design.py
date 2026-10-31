# tests/test_design_operations.py
import pytest
import allure


class TestViewOperations:
    """视图操作测试类"""

    @allure.feature("视图操作")
    @allure.story("旋转视图")
    def test_rotate_view(self, uploaded_model):
        """
        测试旋转视图功能
        uploaded_model 是 ModelViewerPage 实例（已初始化）
        """
        # 创建 DesignPage 实例（传入已初始化的 ModelViewerPage）
        design = DesignPage(uploaded_model)

        # 使用 DesignPage 的方法
        result = design.view.rotate(100, 50)
        assert result, "旋转操作失败"

    @allure.feature("视图操作")
    @allure.story("缩放视图")
    def test_zoom_view(self, uploaded_model):
        design = DesignPage(uploaded_model)

        result = design.view.zoom(200)
        assert result, "放大操作失败"

        result = design.view.zoom(-200)
        assert result, "缩小操作失败"

    @allure.feature("视图操作")
    @allure.story("重置视图")
    def test_reset_view(self, uploaded_model):
        design = DesignPage(uploaded_model)

        # 先旋转
        design.view.rotate(100, 50)

        # 再重置
        result = design.view.reset(debug=True)
        assert result, "重置视图失败"

if __name__ == "__main__":

    import pytest
    import subprocess
    import os
    import sys

    # 运行测试
    exit_code = pytest.main([
        __file__,
        "-v",
        "-s",
        "--alluredir=allure-results",
        "--clean-alluredir"
    ])

    print(f"\n测试完成，退出码: {exit_code}")
    print(f"Allure 数据已生成: {os.path.abspath('allure-results')}")

    # 尝试打开报告
    try:
        # 使用 allure serve 启动服务
        subprocess.Popen(["allure", "serve", "allure-results"], shell=True)
        print("✅ 正在启动 Allure 服务...")
        print("浏览器将自动打开，如果没有请访问 http://localhost:8080")
    except FileNotFoundError:
        print("\n❌ 未找到 allure 命令")
        print("请安装 Allure:")
        print("  1. 下载: https://github.com/allure-framework/allure2/releases")
        print("  2. 解压并添加到 PATH")
        print("  3. 或使用: pip install allure-pytest")
        print("\n临时查看报告:")
        print("  allure serve allure-results")
    except Exception as e:
        print(f"启动报告失败: {e}")
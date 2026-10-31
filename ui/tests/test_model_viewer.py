# tests/test_model_viewer.py
from common.config.settings import Config


class TestModelViewer:
    """3D模型查看器测试用例"""

    def test_upload_and_load_model(self, model_viewer):
        """测试：上传并加载模型"""
        # 上传模型
        model_viewer.upload_model(Config.TEST_MODEL_PATH)

        # 等待模型加载
        result = model_viewer.wait_for_model_load()
        assert result, "模型加载超时"

        # 验证模型已加载
        assert model_viewer.is_model_loaded(), "模型未加载成功"

    def test_add_annotation_on_point(self, uploaded_model):
        """测试：在点上添加批注"""
        iframe = uploaded_model.iframe_methods

        # 在模型上选中一个点并添加批注
        # 坐标需要根据实际模型位置调整
        result = iframe.add_annotation_on_point(
            x=500,  # 屏幕坐标X
            y=400,  # 屏幕坐标Y
            text="这是一个点批注"
        )
        assert result, "点在批注添加失败"

        # 验证批注已添加
        point_annotations = iframe.get_point_annotations()
        assert len(point_annotations) > 0, "点批注未找到"

    def test_add_annotation_on_line(self, uploaded_model):
        """测试：在线上添加批注"""
        iframe = uploaded_model.iframe_methods

        # 在模型上选中一条线并添加批注
        result = iframe.add_annotation_on_line(
            x1=450, y1=380,  # 起点坐标
            x2=550, y2=420,  # 终点坐标
            text="这是一个线批注"
        )
        assert result, "线批注添加失败"

        # 验证批注已添加
        line_annotations = iframe.get_line_annotations()
        assert len(line_annotations) > 0, "线批注未找到"

    def test_add_annotation_on_face(self, uploaded_model):
        """测试：在面上添加批注"""
        iframe = uploaded_model.iframe_methods

        # 在模型上选中一个面并添加批注
        result = iframe.add_annotation_on_face(
            x=500,  # 屏幕坐标X
            y=400,  # 屏幕坐标Y
            text="这是一个面批注"
        )
        assert result, "面批注添加失败"

        # 验证批注已添加
        face_annotations = iframe.get_face_annotations()
        assert len(face_annotations) > 0, "面批注未找到"

    def test_add_annotation_on_selection(self, uploaded_model):
        """测试：在当前选中的元素上添加批注"""
        iframe = uploaded_model.iframe_methods

        # 先选中一个点
        iframe.select_point(500, 400)

        # 在当前选中的点上添加批注
        result = iframe.add_annotation_on_current_selection("选中的点批注")
        assert result, "在选中元素上添加批注失败"

    def test_add_multiple_annotations(self, uploaded_model):
        """测试：添加多个不同类型的批注"""
        iframe = uploaded_model.iframe_methods

        # 添加点批注
        result1 = iframe.add_annotation_on_point(500, 400, "点批注1")
        assert result1, "点批注1添加失败"

        # 添加线批注
        result2 = iframe.add_annotation_on_line(450, 380, 550, 420, "线批注1")
        assert result2, "线批注1添加失败"

        # 添加面批注
        result3 = iframe.add_annotation_on_face(500, 400, "面批注1")
        assert result3, "面批注1添加失败"

        # 验证所有批注
        point_count = len(iframe.get_point_annotations())
        line_count = len(iframe.get_line_annotations())
        face_count = len(iframe.get_face_annotations())

        assert point_count > 0, "点批注未找到"
        assert line_count > 0, "线批注未找到"
        assert face_count > 0, "面批注未找到"

        print(f"点批注数量: {point_count}")
        print(f"线批注数量: {line_count}")
        print(f"面批注数量: {face_count}")

    def test_delete_annotation_by_type(self, uploaded_model):
        """测试：按类型删除批注"""
        iframe = uploaded_model.iframe_methods

        # 添加一些批注
        iframe.add_annotation_on_point(500, 400, "待删除点批注")
        iframe.add_annotation_on_face(500, 400, "待删除面批注")

        # 删除所有点批注
        result = iframe.delete_annotations_by_type('point')
        assert result, "按类型删除批注失败"

        # 验证点批注已删除，面批注还在
        point_count = len(iframe.get_point_annotations())
        face_count = len(iframe.get_face_annotations())

        assert point_count == 0, "点批注未删除"
        assert face_count > 0, "面批注被误删"

    def test_hide_annotations(self, uploaded_model):
        """测试：隐藏批注"""
        iframe = uploaded_model.iframe_methods

        # 添加批注
        iframe.add_annotation("测试批注1")
        iframe.add_annotation("测试批注2")

        # 隐藏所有批注
        result = iframe.hide_all_annotations()
        assert result, "隐藏批注失败"

    def test_select_color(self, uploaded_model):
        """测试：选择颜色"""
        iframe = uploaded_model.iframe_methods

        # 选择预设颜色
        result = iframe.select_preset_color(0)
        assert result, "选择预设颜色失败"

        # 选择自定义颜色
        result = iframe.select_color("#FF0000")
        assert result, "选择自定义颜色失败"

    def test_search_structure_tree(self, uploaded_model):
        """测试：结构树搜索"""
        iframe = uploaded_model.iframe_methods

        result = iframe.search_in_tree("测试")
        assert result, "结构树搜索失败"

    def test_get_model_info(self, uploaded_model):
        """测试：获取模型信息"""
        iframe = uploaded_model.iframe_methods

        model_name = iframe.get_model_name()
        volume = iframe.get_model_volume()
        surface_area = iframe.get_model_surface_area()

        assert model_name is not None, "模型名称为空"
        assert volume is not None, "体积为空"
        assert surface_area is not None, "表面积为空"

        print(f"模型名称: {model_name}")
        print(f"体积: {volume}")
        print(f"表面积: {surface_area}")

    def test_sectioning_operations(self, uploaded_model):
        """测试：剖切操作"""
        iframe = uploaded_model.iframe_methods

        # 切换隐藏切面
        result = iframe.toggle_hide_section()
        assert result, "切换隐藏切面失败"

        # 切换反向剖切
        result = iframe.toggle_reverse_section()
        assert result, "切换反向剖切失败"

        # 重置剖切
        result = iframe.reset_sectioning()
        assert result, "重置剖切失败"

    def test_right_click_menu(self, uploaded_model):
        """测试：右键菜单"""
        iframe = uploaded_model.iframe_methods

        # 打开右键菜单
        result = iframe.open_right_menu()
        assert result, "打开右键菜单失败"

        # 选择子菜单项
        result = iframe.select_submenu_item('transparent')
        assert result, "选择子菜单失败"

        # 恢复显示
        result = iframe.select_submenu_item('hide')
        assert result, "恢复显示失败"

    def test_rotate_view(self, uploaded_model):
        """测试：旋转视图"""
        iframe = uploaded_model.iframe_methods

        result = iframe.rotate_view(100, 50)
        assert result, "旋转视图失败"

    def test_multiple_annotations(self, uploaded_model):
        """测试：多个批注操作"""
        iframe = uploaded_model.iframe_methods

        # 添加多个批注
        annotations = ["批注1", "批注2", "批注3"]
        for text in annotations:
            result = iframe.add_annotation(text)
            assert result, f"添加{text}失败"

        # 验证批注数量
        count = iframe.get_annotation_count()
        assert count == len(annotations), f"期望{len(annotations)}个批注，实际{count}个"

        # 删除所有批注
        result = iframe.delete_all_annotations()
        assert result, "删除所有批注失败"

        # 验证批注已清空
        count = iframe.get_annotation_count()
        assert count == 0, "批注未清空"

    def test_annotation_persistence(self, uploaded_model):
        """测试：批注持久化"""
        iframe = uploaded_model.iframe_methods

        # 添加批注
        annotation_text = "持久化测试批注"
        iframe.add_annotation(annotation_text)

        # 刷新页面
        uploaded_model.refresh_page()
        uploaded_model.wait_for_model_load()

        # 重新获取iframe方法
        new_iframe = uploaded_model.iframe_methods

        # 验证批注仍然存在
        count = new_iframe.get_annotation_count()
        assert count > 0, "批注未持久化保存"

    def test_screenshot(self, uploaded_model):
        """测试：截图功能"""
        # 截图
        screenshot_path = uploaded_model.take_screenshot("test_model")

        # 验证文件存在
        import os
        assert os.path.exists(screenshot_path), "截图文件未创建"


class TestModelViewerSmoke:
    """冒烟测试"""

    def test_page_load(self, model_viewer):
        """测试：页面加载"""
        assert model_viewer.get_page_title() is not None, "页面加载失败"

    def test_upload_flow(self, model_viewer):
        """测试：上传流程"""
        # 上传模型
        model_viewer.upload_model(Config.TEST_MODEL_PATH)

        # 等待加载
        result = model_viewer.wait_for_model_load()
        assert result, "模型加载失败"

    def test_basic_operations(self, uploaded_model):
        """测试：基本操作"""
        iframe = uploaded_model.iframe_methods

        # 测试右键菜单
        assert iframe.open_right_menu(), "右键菜单打开失败"

        # 测试旋转
        assert iframe.rotate_view(50, 30), "旋转失败"

        # 测试获取信息
        assert iframe.get_model_name() is not None, "获取模型信息失败"
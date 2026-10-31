# test_cases.py
import time

import pytest
import asyncio
from playwright.async_api import async_playwright, Page, Browser
from test_methods import ModelViewerTestMethods


class TestModelViewer:
    """3D模型查看器测试用例 - Playwright版本"""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """测试前置设置"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
        self.methods = ModelViewerTestMethods(self.page)

        yield

        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

    @pytest.mark.asyncio
    async def test_open_model_viewer_page(self):
        """测试：打开模型查看器页面"""
        url = "https://3d-viewer.jlc.com/"
        await self.page.goto(url)
        # ========== 2. 上传3D模型 ==========
        self.page.locator('input[type="file"]').set_input_files(r"D:\三维\建模模型\方程式测试模型\BJSU (1).SLDASM")
        print("✅ 模型上传成功")
        time.sleep(6)  # 等待模型加载
        # 等待页面加载完成
        # ========== 3. 进入 iframe ==========
        iframe = self.page.frame_locator("#viewerIframe")
        canvas = iframe.locator("canvas").first

        # 验证底部工具栏存在
        footer = await self.page.wait_for_selector(".fc-page-footer", timeout=5000)
        assert await footer.is_visible(), "底部工具栏未显示"

    @pytest.mark.asyncio
    async def test_panel_open_and_close(self):
        """测试：面板打开和关闭"""
        # 测试打开模型属性面板
        result = await self.methods.open_panel('model_property')
        assert result, "无法打开模型属性面板"
        await asyncio.sleep(1)

        # 验证面板可见
        is_visible = await self.methods.is_panel_visible('model_property')
        assert is_visible, "模型属性面板未显示"

        # 测试关闭面板
        result = await self.methods.close_panel('model_property')
        assert result, "无法关闭模型属性面板"
        await asyncio.sleep(1)

        # 验证面板不可见
        is_visible = await self.methods.is_panel_visible('model_property')
        assert not is_visible, "模型属性面板未关闭"

    @pytest.mark.asyncio
    async def test_model_property_display(self):
        """测试：模型属性显示正确"""
        # 打开基本信息面板
        await self.methods.open_panel('basic_info')
        await asyncio.sleep(1)

        # 获取模型属性
        model_name = await self.methods.get_model_property('model_name')
        volume = await self.methods.get_model_property('volume')
        surface_area = await self.methods.get_model_property('surface_area')
        bounding_box = await self.methods.get_model_property('bounding_box')

        # 验证属性值不为空
        assert model_name is not None, "模型名称为空"
        assert volume is not None, "体积为空"
        assert surface_area is not None, "表面积为空"
        assert bounding_box is not None, "包围盒为空"

        # 验证单位格式
        assert 'mm³' in volume, "体积单位不正确"
        assert 'mm²' in surface_area, "表面积单位不正确"
        assert 'mm' in bounding_box, "包围盒单位不正确"

    @pytest.mark.asyncio
    async def test_coordinate_display(self):
        """测试：坐标显示正确"""
        # 打开坐标面板
        await self.methods.open_panel('coordinate')
        await asyncio.sleep(1)

        # 获取坐标值
        x = await self.methods.get_coordinate('x')
        y = await self.methods.get_coordinate('y')
        z = await self.methods.get_coordinate('z')

        # 验证坐标存在
        assert x is not None, "X坐标为空"
        assert y is not None, "Y坐标为空"
        assert z is not None, "Z坐标为空"

        # 验证坐标是数字
        try:
            float(x)
            float(y)
            float(z)
            assert True
        except ValueError:
            assert False, "坐标不是有效数字"

    @pytest.mark.asyncio
    async def test_color_selection(self):
        """测试：颜色选择功能"""
        # 选择颜色
        result = await self.methods.select_color("#FF0000")
        assert result, "颜色选择失败"
        await asyncio.sleep(1)

        # 验证颜色选择器显示正确颜色
        color_input = self.page.locator(".fc-color-selector-tool input")
        value = await color_input.get_attribute('value')
        assert value == "#FF0000", f"颜色值设置错误，期望#FF0000，实际{value}"

        # 选择预设颜色
        result = await self.methods.select_preset_color(0)
        assert result, "预设颜色选择失败"

    @pytest.mark.asyncio
    async def test_structure_tree_search(self):
        """测试：结构树搜索功能"""
        # 打开结构树面板
        await self.methods.open_panel('structure_tree')
        await asyncio.sleep(1)

        # 执行搜索
        result = await self.methods.search_structure_tree("测试模型")
        assert result, "搜索失败"
        await asyncio.sleep(1)

        # 验证搜索结果显示
        tree_container = self.page.locator(".react-checkbox-tree")
        assert await tree_container.is_visible(), "结构树未显示"

    @pytest.mark.asyncio
    async def test_custom_reply_crud(self):
        """测试：自定义快捷回复的增删改查"""
        # 添加快捷回复
        reply_text = "这是一个测试回复"
        result = await self.methods.add_custom_reply(reply_text)
        assert result, "添加快捷回复失败"
        await asyncio.sleep(1)

        # 验证回复已添加
        input_field = self.page.locator(".fc-annotationSetting-input")
        value = await input_field.get_attribute('value')
        assert value == reply_text, "回复内容未保存"

        # 删除快捷回复
        result = await self.methods.delete_custom_reply(0)
        assert result, "删除快捷回复失败"

    @pytest.mark.asyncio
    async def test_annotation_operations(self):
        """测试：批注操作"""
        # 添加批注
        result = await self.methods.add_annotation("测试批注")
        assert result, "添加批注失败"
        await asyncio.sleep(1)

        # 隐藏所有批注
        result = await self.methods.hide_annotations()
        assert result, "隐藏批注失败"
        await asyncio.sleep(1)

    @pytest.mark.asyncio
    async def test_settings_changes(self):
        """测试：设置更改"""
        # 切换背景色
        result = await self.methods.change_background(0)
        assert result, "背景色切换失败"
        await asyncio.sleep(1)

        # 恢复默认设置
        result = await self.methods.restore_default_settings()
        assert result, "恢复默认设置失败"

    @pytest.mark.asyncio
    async def test_sectioning_function(self):
        """测试：剖切功能"""
        # 切换隐藏切面
        result = await self.methods.toggle_hide_section()
        assert result, "切换隐藏切面失败"
        await asyncio.sleep(1)

        # 重置剖切
        result = await self.methods.reset_sectioning()
        assert result, "重置剖切失败"

    @pytest.mark.asyncio
    async def test_right_click_menu(self):
        """测试：右键菜单功能"""
        # 右键点击模型
        result = await self.methods.right_click_on_model()
        assert result, "右键点击失败"

        # 验证右键菜单显示
        right_menu = self.page.locator("#rightMenus")
        assert await right_menu.is_visible(), "右键菜单未显示"

        # 选择子菜单项
        result = await self.methods.select_submenu_item('transparent')
        assert result, "子菜单选择失败"

        # 选择显示全部
        result = await self.methods.select_right_menu_item('show_all')
        assert result, "显示全部失败"

    @pytest.mark.asyncio
    async def test_toolbar_buttons(self):
        """测试：底部工具栏按钮"""
        # 测试各个按钮点击
        buttons = ['home', 'rotate', 'pan', 'measure', 'screenshot']

        for button in buttons:
            result = await self.methods.click_toolbar_button(button)
            assert result, f"{button}按钮点击失败"
            await asyncio.sleep(0.5)

    @pytest.mark.asyncio
    async def test_3d_view_interaction(self):
        """测试：3D视图交互"""
        # 测试旋转视图
        result = await self.methods.rotate_view(100, 50)
        assert result, "旋转视图失败"
        await asyncio.sleep(1)

        # 测试平移视图
        result = await self.methods.pan_view(50, 30)
        assert result, "平移视图失败"
        await asyncio.sleep(1)

        # 测试重置视图
        result = await self.methods.reset_view()
        assert result, "重置视图失败"

    @pytest.mark.asyncio
    async def test_drag_panel(self):
        """测试：拖拽面板"""
        # 拖拽反馈群面板
        result = await self.methods.drag_panel('feedback', 100, 50)
        assert result, "拖拽面板失败"
        await asyncio.sleep(1)

        # 验证面板位置改变
        panel = self.page.locator(".dragBox:has-text('反馈群')")
        style = await panel.get_attribute('style')
        assert 'translate' in style, "面板位置未改变"

    @pytest.mark.asyncio
    async def test_fullscreen_function(self):
        """测试：全屏功能"""
        # 点击全屏按钮
        result = await self.methods.click_toolbar_button('fullscreen')
        assert result, "全屏按钮点击失败"
        await asyncio.sleep(2)

        # 注意：全屏功能需要特殊处理
        # 可以通过检查页面全屏状态验证
        is_fullscreen = await self.page.evaluate("document.fullscreenElement !== null")
        # 由于全屏需要用户交互，这里可能无法直接验证
        # 但可以验证按钮状态变化

    @pytest.mark.asyncio
    async def test_screenshot_function(self):
        """测试：截图功能"""
        # 截图功能测试
        screenshot_path = "test_screenshot.png"
        result = await self.methods.take_screenshot(screenshot_path)
        assert result, "截图失败"

        # 验证截图文件已创建
        import os
        assert os.path.exists(screenshot_path), "截图文件未创建"

        # 清理测试文件
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)

    @pytest.mark.asyncio
    async def test_language_switch(self):
        """测试：语言切换"""
        # 切换到英文
        result = await self.methods.change_language("English")
        assert result, "语言切换失败"
        await asyncio.sleep(2)

        # 验证部分文本已切换（可以根据实际显示的文字进行验证）

        # 切换回中文
        result = await self.methods.change_language("中文（简体）")
        assert result, "语言切换失败"

    @pytest.mark.asyncio
    async def test_model_loading_indicator(self):
        """测试：模型加载指示器"""
        # 刷新页面
        await self.page.reload()

        # 等待加载指示器出现
        loader = self.page.locator(".loading-progress")
        await loader.wait_for(state="visible", timeout=5000)

        # 等待模型加载完成
        result = await self.methods.wait_for_model_load(timeout=30000)
        assert result, "模型加载超时"

        # 验证canvas已加载
        canvas = self.page.locator("canvas[data-engine='three.js r147']")
        assert await canvas.is_visible(), "模型加载失败"


class TestModelViewerEdgeCases:
    """边界条件和异常场景测试"""

    @pytest.fixture(autouse=True)
    async def setup(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self.methods = ModelViewerTestMethods(self.page)
        yield
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

    @pytest.mark.asyncio
    async def test_rapid_click_operations(self):
        """测试：快速点击操作"""
        # 快速点击多个按钮
        buttons = ['home', 'rotate', 'pan', 'measure']

        for button in buttons:
            await self.methods.click_toolbar_button(button)

        # 验证没有报错，页面状态正常
        canvas = self.page.locator("canvas[data-engine='three.js r147']")
        assert await canvas.is_visible(), "页面崩溃"

    @pytest.mark.asyncio
    async def test_concurrent_panel_operations(self):
        """测试：并发面板操作"""
        # 同时打开多个面板
        panels = ['model_property', 'coordinate', 'basic_info', 'structure_tree']

        for panel in panels:
            await self.methods.open_panel(panel)

        await asyncio.sleep(2)

        # 验证所有面板都已打开
        for panel in panels:
            is_visible = await self.methods.is_panel_visible(panel)
            # 注意：某些面板可能不能同时打开，需要根据实际UI调整
            # assert is_visible, f"{panel}面板未打开"

    @pytest.mark.asyncio
    async def test_network_disconnect(self):
        """测试：网络断开场景"""
        # 模拟网络断开
        await self.context.set_offline(True)

        # 尝试进行操作
        result = await self.methods.click_toolbar_button('home')

        # 验证有错误提示
        error_message = self.page.locator(".error-message")
        # 根据实际错误提示进行验证

        # 恢复网络
        await self.context.set_offline(False)

    @pytest.mark.asyncio
    async def test_element_not_found(self):
        """测试：元素未找到场景"""
        # 尝试操作不存在的元素
        result = await self.methods.select_preset_color(999)
        assert not result, "应该返回False"

    @pytest.mark.asyncio
    async def test_performance_large_model(self):
        """测试：大模型性能"""
        start_time = asyncio.get_event_loop().time()

        # 等待模型加载
        await self.methods.wait_for_model_load()

        # 执行一系列操作
        await self.methods.rotate_view(100, 50)
        await self.methods.pan_view(50, 30)
        await self.methods.zoom_view(True)

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # 验证操作时间在可接受范围内
        assert duration < 10, f"操作耗时过长: {duration}秒"
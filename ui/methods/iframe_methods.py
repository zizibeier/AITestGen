# methods/iframe_methods.py
from typing import Optional
from ui.methods.base_methods import BaseMethods
import time


class IFrameMethods(BaseMethods):
    """iframe内的操作方法 - 只包含iframe内的元素操作"""

    def __init__(self, context):
        super().__init__(context)
        self.page = context.page
        # self._locators = self._load_locators("iframe_locators.yaml")
        self.iframe = None

    def switch_to_iframe(self):
        """切换到iframe"""
        self.iframe = self.page.frame_locator("#viewerIframe")
        return self.iframe

    # ========== 3D视图操作方法 ==========

    def get_canvas(self):
        """获取canvas元素"""
        if not self.iframe:
            self.switch_to_iframe()
        return self.iframe.locator(self._get_locator('viewer_3d', 'canvas')).first

    def right_click_on_model(self, x_offset: int = 0, y_offset: int = 0) -> bool:
        """在模型上右键点击"""
        canvas = self.get_canvas()
        if canvas and canvas.count() > 0:
            box = canvas.bounding_box()
            if box:
                x = box['x'] + box['width'] / 2 + x_offset
                y = box['y'] + box['height'] / 2 + y_offset
                self.page.mouse.click(x, y, button='right')
                time.sleep(0.5)
                return True
        return False




    def rotate_view(self, x_offset: int, y_offset: int) -> bool:
        """旋转视图"""
        canvas = self.get_canvas()
        if canvas and canvas.count() > 0:
            box = canvas.bounding_box()
            if box:
                center_x = box['x'] + box['width'] / 2
                center_y = box['y'] + box['height'] / 2

                self.page.mouse.move(center_x, center_y)
                self.page.mouse.down()
                self.page.mouse.move(center_x + x_offset, center_y + y_offset)
                self.page.mouse.up()
                time.sleep(0.5)
                return True
        return False

    # ========== 模型选中方法 ==========

    def click_on_model(self, x: int, y: int) -> bool:
        """点击模型上的指定位置"""
        canvas = self.get_canvas()
        if canvas and canvas.count() > 0:
            box = canvas.bounding_box()
            if box:
                click_x = box['x'] + x
                click_y = box['y'] + y
                self.page.mouse.click(click_x, click_y)
                time.sleep(0.3)
                return True
        return False

    def select_point(self, x: int, y: int) -> bool:
        """选中模型上的点"""
        canvas = self.get_canvas()
        if canvas and canvas.count() > 0:
            box = canvas.bounding_box()
            if box:
                # 点击目标位置
                click_x = box['x'] + x
                click_y = box['y'] + y
                self.page.mouse.click(click_x, click_y)
                time.sleep(0.3)

                # 验证点是否被选中
                selected_point = self._get_element('model_selection', 'selected_point')
                if selected_point.count() > 0 and selected_point.is_visible():
                    print("✅ 点已选中")
                    return True
        return False

    def select_line(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """选中模型上的线（拖拽选择）"""
        canvas = self.get_canvas()
        if canvas and canvas.count() > 0:
            box = canvas.bounding_box()
            if box:
                start_x = box['x'] + x1
                start_y = box['y'] + y1
                end_x = box['x'] + x2
                end_y = box['y'] + y2

                # 拖拽选择线
                self.page.mouse.move(start_x, start_y)
                self.page.mouse.down()
                self.page.mouse.move(end_x, end_y)
                self.page.mouse.up()
                time.sleep(0.5)

                # 验证线是否被选中
                selected_line = self._get_element('model_selection', 'selected_line')
                if selected_line.count() > 0 and selected_line.is_visible():
                    print("✅ 线已选中")
                    return True
        return False

    def select_face(self, x: int, y: int) -> bool:
        """选中模型上的面"""
        canvas = self.get_canvas()
        if canvas and canvas.count() > 0:
            box = canvas.bounding_box()
            if box:
                # 点击目标面
                click_x = box['x'] + x
                click_y = box['y'] + y
                self.page.mouse.click(click_x, click_y)
                time.sleep(0.3)

                # 验证面是否被选中
                selected_face = self._get_element('model_selection', 'selected_face')
                if selected_face.count() > 0 and selected_face.is_visible():
                    print("✅ 面已选中")
                    return True
        return False

    def get_selected_element_type(self) -> Optional[str]:
        """获取当前选中的元素类型"""
        if self._get_element('model_selection', 'selected_point').is_visible():
            return 'point'
        elif self._get_element('model_selection', 'selected_line').is_visible():
            return 'line'
        elif self._get_element('model_selection', 'selected_face').is_visible():
            return 'face'
        return None

    def clear_selection(self) -> bool:
        """清除选中状态"""
        canvas = self.get_canvas()
        if canvas and canvas.count() > 0:
            # 点击空白区域清除选中
            box = canvas.bounding_box()
            if box:
                # 点击canvas边缘空白处
                self.page.mouse.click(box['x'] + 10, box['y'] + 10)
                time.sleep(0.2)
                return True
        return False

    # # ========== 右键菜单操作方法 ==========
    #
    # def open_right_menu(self) -> bool:
    #     """打开右键菜单"""
    #     return self.right_click_on_model()
    #
    # def select_menu_item(self, item_name: str) -> bool:
    #     """选择右键菜单项"""
    #     item_map = {
    #         'add_annotation': ('right_menu', 'menu_items', 'add_annotation'),
    #         'hide': ('right_menu', 'menu_items', 'hide'),
    #         'show_all': ('right_menu', 'menu_items', 'show_all'),
    #         'hide_annotation': ('right_menu', 'menu_items', 'hide_annotation'),
    #         'single_restore': ('right_menu', 'menu_items', 'single_restore'),
    #         'all_restore': ('right_menu', 'menu_items', 'all_restore')
    #     }
    #
    #     if item_name in item_map:
    #         element = self._get_element(*item_map[item_name])
    #         if element.count() > 0:
    #             element.click()
    #             time.sleep(0.5)
    #             return True
    #     return False
    #
    # def select_submenu_item(self, item_name: str) -> bool:
    #     """选择子菜单项"""
    #     submenu_map = {
    #         'hide': ('right_menu', 'submenu', 'hide'),
    #         'transparent': ('right_menu', 'submenu', 'transparent'),
    #         'transparent_other': ('right_menu', 'submenu', 'transparent_other'),
    #         'hide_other': ('right_menu', 'submenu', 'hide_other'),
    #         'show_all': ('right_menu', 'submenu', 'show_all')
    #     }
    #
    #     if item_name in submenu_map:
    #         element = self._get_element(*submenu_map[item_name])
    #         if element.count() > 0:
    #             element.click()
    #             time.sleep(0.5)
    #             return True
    #     return False

    # ========== 右键菜单方法（支持不同元素） ==========

    def open_right_menu_on_selection(self, element_type: str = None) -> bool:
        """在选中的元素上打开右键菜单"""
        canvas = self.get_canvas()
        if canvas and canvas.count() > 0:
            box = canvas.bounding_box()
            if box:
                # 根据元素类型确定点击位置
                if element_type == 'point':
                    # 点击选中点的位置
                    point = self._get_element('model_selection', 'selected_point')
                    if point.count() > 0:
                        point_box = point.bounding_box()
                        if point_box:
                            x = point_box['x'] + point_box['width'] / 2
                            y = point_box['y'] + point_box['height'] / 2
                            self.page.mouse.click(x, y, button='right')
                            time.sleep(0.5)
                            return True
                else:
                    # 默认在canvas中心右键
                    x = box['x'] + box['width'] / 2
                    y = box['y'] + box['height'] / 2
                    self.page.mouse.click(x, y, button='right')
                    time.sleep(0.5)
                    return True
        return False

    def select_menu_item(self, item_name: str) -> bool:
        """选择右键菜单项"""
        item_map = {
            'add_annotation': ('right_menu', 'menu_items', 'add_annotation'),
            'add_annotation_on_point': ('right_menu', 'menu_items', 'add_annotation_on_point'),
            'add_annotation_on_line': ('right_menu', 'menu_items', 'add_annotation_on_line'),
            'add_annotation_on_face': ('right_menu', 'menu_items', 'add_annotation_on_face'),
            'hide': ('right_menu', 'menu_items', 'hide'),
            'show_all': ('right_menu', 'menu_items', 'show_all'),
            'hide_annotation': ('right_menu', 'menu_items', 'hide_annotation'),
            'single_restore': ('right_menu', 'menu_items', 'single_restore'),
            'all_restore': ('right_menu', 'menu_items', 'all_restore')
        }

        if item_name in item_map:
            element = self._get_element(*item_map[item_name])
            if element.count() > 0:
                element.click()
                time.sleep(0.5)
                return True
        return False

    # ========== 批注方法（支持点/线/面） ==========

    def add_annotation_on_point(self, x: int, y: int, text: str) -> bool:
        """在指定点上添加批注"""
        # 1. 选中点
        if not self.select_point(x, y):
            print("❌ 点选中失败")
            return False

        # 2. 右键打开菜单
        if not self.open_right_menu_on_selection('point'):
            print("❌ 右键菜单打开失败")
            return False

        # 3. 选择添加批注（点）
        if not self.select_menu_item('add_annotation_on_point'):
            # 如果没有专门的点的批注选项，使用通用批注
            if not self.select_menu_item('add_annotation'):
                print("❌ 添加批注选项选择失败")
                return False

        # 4. 输入批注内容
        time.sleep(0.5)
        annotation_input = self._get_element('annotation_panel', 'annotation_input')
        if annotation_input.count() > 0:
            annotation_input.fill(text)
            time.sleep(0.5)

            # 5. 保存批注
            save_btn = self._get_element('annotation_panel', 'save_btn')
            if save_btn.count() > 0:
                save_btn.click()
                time.sleep(0.5)
                print(f"✅ 点批注添加成功: {text}")
                return True

        return False

    def add_annotation_on_line(self, x1: int, y1: int, x2: int, y2: int, text: str) -> bool:
        """在指定线上添加批注"""
        # 1. 选中线
        if not self.select_line(x1, y1, x2, y2):
            print("❌ 线选中失败")
            return False

        # 2. 右键打开菜单
        if not self.open_right_menu_on_selection('line'):
            print("❌ 右键菜单打开失败")
            return False

        # 3. 选择添加批注（线）
        if not self.select_menu_item('add_annotation_on_line'):
            # 如果没有专门的线的批注选项，使用通用批注
            if not self.select_menu_item('add_annotation'):
                print("❌ 添加批注选项选择失败")
                return False

        # 4. 输入批注内容
        time.sleep(0.5)
        annotation_input = self._get_element('annotation_panel', 'annotation_input')
        if annotation_input.count() > 0:
            annotation_input.fill(text)
            time.sleep(0.5)

            # 5. 保存批注
            save_btn = self._get_element('annotation_panel', 'save_btn')
            if save_btn.count() > 0:
                save_btn.click()
                time.sleep(0.5)
                print(f"✅ 线批注添加成功: {text}")
                return True

        return False

    def add_annotation_on_face(self, x: int, y: int, text: str) -> bool:
        """在指定面上添加批注"""
        # 1. 选中面
        if not self.select_face(x, y):
            print("❌ 面选中失败")
            return False

        # 2. 右键打开菜单
        if not self.open_right_menu_on_selection('face'):
            print("❌ 右键菜单打开失败")
            return False

        # 3. 选择添加批注（面）
        if not self.select_menu_item('add_annotation_on_face'):
            # 如果没有专门的面的批注选项，使用通用批注
            if not self.select_menu_item('add_annotation'):
                print("❌ 添加批注选项选择失败")
                return False

        # 4. 输入批注内容
        time.sleep(0.5)
        annotation_input = self._get_element('annotation_panel', 'annotation_input')
        if annotation_input.count() > 0:
            annotation_input.fill(text)
            time.sleep(0.5)

            # 5. 保存批注
            save_btn = self._get_element('annotation_panel', 'save_btn')
            if save_btn.count() > 0:
                save_btn.click()
                time.sleep(0.5)
                print(f"✅ 面批注添加成功: {text}")
                return True

        return False

    def add_annotation_generic(self, x: int, y: int, text: str) -> bool:
        """通用批注添加（自动识别点击位置的元素类型）"""
        # 1. 点击模型上的位置
        canvas = self.get_canvas()
        if canvas and canvas.count() > 0:
            box = canvas.bounding_box()
            if box:
                click_x = box['x'] + x
                click_y = box['y'] + y
                self.page.mouse.click(click_x, click_y, button='right')
                time.sleep(0.5)

                # 2. 选择添加批注
                if not self.select_menu_item('add_annotation'):
                    print("❌ 添加批注选项选择失败")
                    return False

                # 3. 输入批注内容
                time.sleep(0.5)
                annotation_input = self._get_element('annotation_panel', 'annotation_input')
                if annotation_input.count() > 0:
                    annotation_input.fill(text)
                    time.sleep(0.5)

                    # 4. 保存批注
                    save_btn = self._get_element('annotation_panel', 'save_btn')
                    if save_btn.count() > 0:
                        save_btn.click()
                        time.sleep(0.5)
                        print(f"✅ 批注添加成功: {text}")
                        return True

        return False

    def add_annotation_by_coordinates(self, coordinates: dict, text: str) -> bool:
        """通过三维坐标添加批注"""
        # coordinates: {'x': 100, 'y': 200, 'z': 300}
        # 将3D坐标转换为2D屏幕坐标（需要根据实际API实现）
        # 这里简化处理，假设有坐标转换方法
        screen_x = coordinates.get('screen_x', 500)
        screen_y = coordinates.get('screen_y', 400)
        return self.add_annotation_generic(screen_x, screen_y, text)

    def add_annotation_on_current_selection(self, text: str) -> bool:
        """在当前选中的元素上添加批注"""
        element_type = self.get_selected_element_type()

        if element_type == 'point':
            # 在选中的点上右键
            point = self._get_element('model_selection', 'selected_point')
            if point.count() > 0:
                point_box = point.bounding_box()
                if point_box:
                    x = point_box['x'] + point_box['width'] / 2
                    y = point_box['y'] + point_box['height'] / 2
                    self.page.mouse.click(x, y, button='right')
                    time.sleep(0.5)

                    if self.select_menu_item('add_annotation_on_point'):
                        return self._input_annotation_text(text)

        elif element_type == 'line':
            # 在选中的线上右键
            line = self._get_element('model_selection', 'selected_line')
            if line.count() > 0:
                line_box = line.bounding_box()
                if line_box:
                    x = line_box['x'] + line_box['width'] / 2
                    y = line_box['y'] + line_box['height'] / 2
                    self.page.mouse.click(x, y, button='right')
                    time.sleep(0.5)

                    if self.select_menu_item('add_annotation_on_line'):
                        return self._input_annotation_text(text)

        elif element_type == 'face':
            # 在选中的面上右键
            face = self._get_element('model_selection', 'selected_face')
            if face.count() > 0:
                face_box = face.bounding_box()
                if face_box:
                    x = face_box['x'] + face_box['width'] / 2
                    y = face_box['y'] + face_box['height'] / 2
                    self.page.mouse.click(x, y, button='right')
                    time.sleep(0.5)

                    if self.select_menu_item('add_annotation_on_face'):
                        return self._input_annotation_text(text)

        return False

    def _input_annotation_text(self, text: str) -> bool:
        """输入批注文本"""
        annotation_input = self._get_element('annotation_panel', 'annotation_input')
        if annotation_input.count() > 0:
            annotation_input.fill(text)
            time.sleep(0.5)

            save_btn = self._get_element('annotation_panel', 'save_btn')
            if save_btn.count() > 0:
                save_btn.click()
                time.sleep(0.5)
                print(f"✅ 批注添加成功: {text}")
                return True
        return False

    def get_annotations_by_type(self, element_type: str) -> list:
        """获取指定类型的批注列表"""
        annotations = []
        annotation_items = self._get_element('annotation_panel', 'annotation_items')
        count = annotation_items.count()

        for i in range(count):
            item = annotation_items.nth(i)
            # 根据元素类型筛选批注
            if element_type in item.get_attribute('class', ''):
                text = item.text_content()
                annotations.append(text)

        return annotations

    def get_point_annotations(self) -> list:
        """获取点批注列表"""
        return self.get_annotations_by_type('point')

    def get_line_annotations(self) -> list:
        """获取线批注列表"""
        return self.get_annotations_by_type('line')

    def get_face_annotations(self) -> list:
        """获取面批注列表"""
        return self.get_annotations_by_type('face')

    def delete_annotations_by_type(self, element_type: str) -> bool:
        """按类型删除批注"""
        self.open_annotation_panel()
        time.sleep(0.5)

        annotation_items = self._get_element('annotation_panel', 'annotation_items')
        count = annotation_items.count()

        deleted = 0
        for i in range(count):
            item = annotation_items.nth(i)
            # 检查元素类型
            if element_type in item.get_attribute('class', ''):
                # 右键点击该批注
                box = item.bounding_box()
                if box:
                    self.page.mouse.click(
                        box['x'] + box['width'] / 2,
                        box['y'] + box['height'] / 2,
                        button='right'
                    )
                    time.sleep(0.3)

                    # 点击删除
                    delete_btn = self.page.locator("button:has-text('删除')").first
                    if delete_btn.count() > 0:
                        delete_btn.click()
                        time.sleep(0.3)

                        # 确认删除
                        confirm_ok = self._get_element('annotation_panel', 'confirm_ok')
                        if confirm_ok.count() > 0:
                            confirm_ok.click()
                            time.sleep(0.3)
                            deleted += 1

        print(f"✅ 已删除 {deleted} 个{element_type}批注")
        return deleted > 0
    # ========== 颜色操作方法 ==========

    def open_color_panel(self) -> bool:
        """打开颜色选择面板"""
        color_btn = self._get_element('footer_toolbar', 'buttons', 'color')
        if color_btn.count() > 0:
            color_btn.click()
            time.sleep(0.5)
            return True
        return False

    def select_color(self, color_hex: str) -> bool:
        """选择颜色"""
        self.open_color_panel()
        time.sleep(0.5)

        color_input = self._get_element('color_panel', 'color_input')
        if color_input.count() > 0:
            color_input.fill(color_hex)
            confirm_btn = self._get_element('color_panel', 'confirm_btn')
            if confirm_btn.count() > 0:
                confirm_btn.click()
                time.sleep(0.5)
                return True
        return False

    def select_preset_color(self, index: int) -> bool:
        """选择预设颜色"""
        self.open_color_panel()
        time.sleep(0.5)

        presets = self._get_element('color_panel', 'color_presets')
        if presets.count() > index:
            presets.nth(index).click()
            time.sleep(0.5)
            return True
        return False

    # ========== 结构树操作方法 ==========

    def open_structure_tree(self) -> bool:
        """打开结构树面板"""
        tree_btn = self._get_element('footer_toolbar', 'buttons', 'structure_tree')
        if tree_btn.count() > 0:
            tree_btn.click()
            time.sleep(0.5)
            return True
        return False

    def search_in_tree(self, keyword: str) -> bool:
        """在结构树中搜索"""
        self.open_structure_tree()
        time.sleep(0.5)

        search_input = self._get_element('structure_tree_panel', 'search_input')
        if search_input.count() > 0:
            search_input.fill(keyword)
            search_btn = self._get_element('structure_tree_panel', 'search_btn')
            if search_btn.count() > 0:
                search_btn.click()
                time.sleep(0.5)
                return True
        return False

    def toggle_tree_node(self, node_name: str) -> bool:
        """切换树节点"""
        tree_items = self._get_element('structure_tree_panel', 'tree_items')
        count = tree_items.count()

        for i in range(count):
            item = tree_items.nth(i)
            text = item.text_content()
            if node_name in text:
                checkbox = item.locator(self._get_locator('structure_tree_panel', 'checkbox'))
                if checkbox.count() > 0:
                    checkbox.click()
                    return True
        return False

    # ========== 基本信息操作方法 ==========

    def open_basic_info_panel(self) -> bool:
        """打开基本信息面板"""
        info_btn = self._get_element('footer_toolbar', 'buttons', 'info')
        if info_btn.count() > 0:
            info_btn.click()
            time.sleep(0.5)
            return True
        return False

    def get_model_name(self) -> str:
        """获取模型名称"""
        self.open_basic_info_panel()
        time.sleep(0.5)
        element = self._get_element('basic_info_panel', 'model_name')
        return element.text_content() if element.count() > 0 else ""

    def get_model_volume(self) -> str:
        """获取模型体积"""
        self.open_basic_info_panel()
        time.sleep(0.5)
        element = self._get_element('basic_info_panel', 'volume')
        return element.text_content() if element.count() > 0 else ""

    def get_model_surface_area(self) -> str:
        """获取模型表面积"""
        self.open_basic_info_panel()
        time.sleep(0.5)
        element = self._get_element('basic_info_panel', 'surface_area')
        return element.text_content() if element.count() > 0 else ""

    # ========== 剖切操作方法 ==========

    def open_sectioning_panel(self) -> bool:
        """打开剖切面板"""
        section_btn = self._get_element('footer_toolbar', 'buttons', 'sectioning')
        if section_btn.count() > 0:
            section_btn.click()
            time.sleep(0.5)
            return True
        return False

    def toggle_hide_section(self) -> bool:
        """切换隐藏切面"""
        self.open_sectioning_panel()
        time.sleep(0.5)

        switch = self._get_element('sectioning_panel', 'hide_section_switch')
        if switch.count() > 0:
            switch.click()
            time.sleep(0.5)
            return True
        return False

    def toggle_reverse_section(self) -> bool:
        """切换反向剖切"""
        self.open_sectioning_panel()
        time.sleep(0.5)

        switch = self._get_element('sectioning_panel', 'reverse_section_switch')
        if switch.count() > 0:
            switch.click()
            time.sleep(0.5)
            return True
        return False

    def reset_sectioning(self) -> bool:
        """重置剖切"""
        self.open_sectioning_panel()
        time.sleep(0.5)

        reset_btn = self._get_element('sectioning_panel', 'reset_btn')
        if reset_btn.count() > 0:
            reset_btn.click()
            time.sleep(0.5)
            return True
        return False
# methods/annotation_methods.py
from ui.methods.base_methods import BaseMethods
import time


class AnnotationMethods(BaseMethods):
    """批注操作方法类"""

    def __init__(self, page):
        super().__init__(page)

    def open_right_menu(self, x: int = None, y: int = None) -> bool:
        """打开右键菜单"""
        canvas = self.get_canvas()
        box = canvas.bounding_box()
        if box:
            click_x = x if x else box['x'] + box['width'] / 2
            click_y = y if y else box['y'] + box['height'] / 2
            self.page.mouse.click(click_x, click_y, button='right')
            time.sleep(0.5)
            return True
        return False

    def select_menu_item(self, item_name: str) -> bool:
        """选择右键菜单项"""
        menu_map = {
            'add_annotation': "#rightMenus_addAnnotation",
            'hide_annotation': "#rightMenus_showOrHiddenAnnotation",
            'delete': "button:has-text('删除')"
        }

        if item_name in menu_map:
            element = self.page.locator(menu_map[item_name])
            if element.count() > 0:
                element.click()
                time.sleep(0.5)
                return True
        return False

    def add_annotation(self, text: str, x: int = None, y: int = None) -> bool:
        """添加批注"""
        # 1. 打开右键菜单
        if not self.open_right_menu(x, y):
            return False

        # 2. 选择添加批注
        if not self.select_menu_item('add_annotation'):
            return False

        # 3. 输入批注内容
        time.sleep(0.5)
        annotation_input = self.page.locator(".annotation-input, textarea, [contenteditable='true']").first
        if annotation_input.count() > 0:
            annotation_input.fill(text)
            time.sleep(0.5)

            # 4. 保存
            save_btn = self.page.locator("button:has-text('确定'), button:has-text('保存')").first
            if save_btn.count() > 0:
                save_btn.click()
                time.sleep(0.5)
                print(f"✅ 批注添加成功: {text}")
                return True
        return False

    def delete_annotation(self, index: int = 0) -> bool:
        """删除批注"""
        # 打开批注面板
        self.open_annotation_panel()
        time.sleep(0.5)

        # 找到批注项
        annotation_items = self.page.locator(".annotation-item")
        if annotation_items.count() > index:
            item = annotation_items.nth(index)
            box = item.bounding_box()
            if box:
                # 右键点击批注
                self.page.mouse.click(box['x'] + box['width'] / 2,
                                      box['y'] + box['height'] / 2,
                                      button='right')
                time.sleep(0.5)

                # 点击删除
                if self.select_menu_item('delete'):
                    # 确认删除
                    confirm_btn = self.page.locator(".fc-confirm-btn")
                    if confirm_btn.count() > 0:
                        confirm_btn.click()
                        time.sleep(0.5)
                        print(f"✅ 批注删除成功")
                        return True
        return False

    def open_annotation_panel(self) -> bool:
        """打开批注面板"""
        # 通过底部工具栏的info按钮打开
        info_btn = self.page.locator(".fc-tool-btn-box:has(.ic_info)")
        if info_btn.count() > 0:
            info_btn.click()
            time.sleep(0.5)
            return True
        return False

    def get_annotation_count(self) -> int:
        """获取批注数量"""
        self.open_annotation_panel()
        time.sleep(0.5)
        annotation_items = self.page.locator(".annotation-item")
        return annotation_items.count()

    def clear_all_annotations(self) -> bool:
        """清除所有批注"""
        count = self.get_annotation_count()
        for i in range(count):
            self.delete_annotation(0)
            time.sleep(0.5)
        return True
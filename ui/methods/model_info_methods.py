# methods/model_info_methods.py
from ui.methods.base_methods import BaseMethods
import time


class ModelInfoMethods(BaseMethods):
    """模型信息操作方法类"""

    def __init__(self, page):
        super().__init__(page)

    def open_info_panel(self) -> bool:
        """打开信息面板"""
        info_btn = self.page.locator(".fc-tool-btn-box:has(.ic_info)")
        if info_btn.count() > 0:
            info_btn.click()
            time.sleep(0.5)
            return True
        return False

    def get_model_name(self) -> str:
        """获取模型名称"""
        self.open_info_panel()
        name = self.page.locator(".fc-model-info-item:first-child .fc-info-value")
        if name.count() > 0:
            return name.text_content()
        return ""

    def get_model_volume(self) -> str:
        """获取模型体积"""
        self.open_info_panel()
        volume = self.page.locator(".fc-model-info-item:nth-child(2) .fc-info-value")
        if volume.count() > 0:
            return volume.text_content()
        return ""

    def get_model_area(self) -> str:
        """获取模型表面积"""
        self.open_info_panel()
        area = self.page.locator(".fc-model-info-item:nth-child(3) .fc-info-value")
        if area.count() > 0:
            return area.text_content()
        return ""

    def get_model_bounding_box(self) -> str:
        """获取模型包围盒"""
        self.open_info_panel()
        bbox = self.page.locator(".fc-model-info-item:last-child .fc-info-value")
        if bbox.count() > 0:
            return bbox.text_content()
        return ""

    def is_model_rendered(self) -> bool:
        """判断模型是否渲染成功"""
        try:
            canvas = self.get_canvas()
            if not canvas.is_visible():
                return False

            box = canvas.bounding_box()
            if box and box['width'] > 0 and box['height'] > 0:
                return True
            return False
        except:
            return False
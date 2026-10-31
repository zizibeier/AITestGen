# methods/canvas_methods.py
from ui.methods.base_methods import BaseMethods
from typing import Optional


class CanvasMethods(BaseMethods):
    """Canvas 方法类"""

    def __init__(self, context):
        super().__init__(context)

    def get_info(self) -> Optional[dict]:
        """获取 Canvas 信息"""
        return self.get_canvas_info()

    def wait_for_ready(self, timeout: int = 30000) -> bool:
        """等待 Canvas 就绪"""
        return self.wait_for_canvas(timeout)

    def is_ready(self) -> bool:
        """检查 Canvas 是否就绪"""
        return self.is_canvas_visible()

    def click_at(self, x: int, y: int, button: str = "left") -> bool:
        """在 Canvas 指定坐标点击"""
        try:
            if not self.is_in_iframe():
                self.switch_to_iframe()

            self.mouse_click_at(x, y, button)
            return True
        except Exception as e:
            print(f"点击 Canvas 失败: {e}")
            return False

    def click_relative(self, x_offset: int, y_offset: int, button: str = "left") -> bool:
        """在 Canvas 相对位置点击（基于 Canvas 左上角）"""
        try:
            canvas_info = self.get_canvas_info()
            if canvas_info:
                absolute_x = canvas_info['x'] + x_offset
                absolute_y = canvas_info['y'] + y_offset
                return self.click_at(absolute_x, absolute_y, button)
            return False
        except Exception as e:
            print(f"点击 Canvas 相对位置失败: {e}")
            return False

    def get_pixel_color(self, x: int, y: int) -> Optional[str]:
        """获取 Canvas 指定像素的颜色"""
        try:
            canvas = self.get_canvas()

            color = self.page.evaluate("""
                (canvas, x, y) => {
                    const ctx = canvas.getContext('2d');
                    const pixel = ctx.getImageData(x, y, 1, 1).data;
                    return `rgba(${pixel[0]}, ${pixel[1]}, ${pixel[2]}, ${pixel[3]})`;
                }
            """, canvas.element_handle(), x, y)

            return color
        except Exception as e:
            print(f"获取像素颜色失败: {e}")
            return None

    def screenshot(self, path: str = None):
        """截取 Canvas 截图"""
        try:
            canvas = self.get_canvas()
            canvas.screenshot(path=path)
            return True
        except Exception as e:
            print(f"截取 Canvas 截图失败: {e}")
            return False
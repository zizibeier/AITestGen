# methods/view_methods.py
from ui.methods.base_methods import BaseMethods
from common.utils.logger import log
import time


class ViewMethods(BaseMethods):
    """视图操作方法"""

    def __init__(self, context):
        super().__init__(context)

    def rotate(self, x_offset: int, y_offset: int) -> bool:
        """旋转视图"""

        log.info(f"\n[旋转] 开始，偏移量: ({x_offset}, {y_offset})")

        center = self.get_canvas_center()
        if not center:
            log.error("❌ 无法获取 Canvas 中心点")
            return False

        self.mouse_drag(center['x'], center['y'],
                        center['x'] + x_offset, center['y'] + y_offset)
        time.sleep(0.3)
        return True

    def zoom(self, delta: int) -> bool:
        """缩放视图"""
        center = self.get_canvas_center()
        if not center:
            log.error("❌ 无法获取 Canvas 中心点")
            return False

        self.mouse_wheel(0, delta, center['x'], center['y'])
        time.sleep(0.3)
        return True

    def pan(self, x_offset: int, y_offset: int) -> bool:
        """平移视图"""
        center = self.get_canvas_center()
        if not center:
            log.error("❌ 无法获取 Canvas 中心点")
            return False

        self.mouse_drag(center['x'], center['y'],
                        center['x'] + x_offset, center['y'] + y_offset)
        time.sleep(0.3)
        return True

    # methods/view_methods.py
    def find_all_buttons_in_all_frames(self) -> list:
        """
        遍历所有 frames，找到所有可点击按钮
        返回: [(frame, button_element, button_text), ...]
        """
        all_buttons = []

        # 1. 遍历所有 frames
        for frame in self.page.frames:
            try:
                # 在当前 frame 中查找所有 button
                buttons = frame.locator("button").all()

                for btn in buttons:
                    try:
                        # 检查是否可见
                        if btn.is_visible():
                            text = btn.text_content() or btn.get_attribute("aria-label") or ""
                            all_buttons.append({
                                "frame": frame,
                                "element": btn,
                                "text": text.strip(),
                                "frame_name": frame.name or "main"
                            })
                    except:
                        pass
            except Exception as e:
                log.debug(f"Frame {frame.name} 遍历失败: {e}")

        return all_buttons

    def find_button_in_all_frames(self, target_text: str):
        """
        在所有 frames 中查找包含指定文本的按钮
        """
        log.info(f"在所有 frames 中查找按钮: {target_text}")

        # 遍历所有 frames
        for frame in self.page.frames:
            try:
                # 方法1：使用 has-text 直接查找
                btn = frame.locator(f"button:has-text('{target_text}')")
                if btn.count() > 0 and btn.first.is_visible():
                    log.success(f"在 frame '{frame.name}' 中找到按钮")
                    return btn.first

                # 方法2：遍历所有按钮
                buttons = frame.locator("button").all()
                for btn in buttons:
                    try:
                        text = btn.text_content() or ""
                        if target_text in text and btn.is_visible():
                            log.success(f"在 frame '{frame.name}' 中找到按钮: {text}")
                            return btn
                    except:
                        pass
            except Exception as e:
                log.debug(f"Frame {frame.name} 查找失败: {e}")

        log.error(f"未找到按钮: {target_text}")
        return None


    def reset(self) -> bool:
        """重置视图"""
        log.step("重置视图")
        # 直接调用基类方法
        return self.click_tool_button("回到原点")

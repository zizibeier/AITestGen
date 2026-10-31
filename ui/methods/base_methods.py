# methods/base_methods.py
import time
from pathlib import Path
from typing import Optional

from common.utils.data_utils.yaml_loader import load_config
from common.utils.logger import log

class BaseMethods:
    """
    基础方法类
    职责：加载定位器、iframe 管理、Canvas 操作
    """

    def __init__(self, context):
        """
        初始化基础方法

        Args:
            context: Context 实例
        """
        self.ctx = context
        self.page = context.page
        self.base_page = context.base_page

        # iframe 相关
        self._iframe = None
        self._iframe_selector = "#viewerIframe"

        # 定位器存储
        self._locators = None

    # ==================== 定位器加载 ====================

    def load_locators(self, file_name: str):
        """加载定位器 YAML 文件"""
        self._locators = self.base_page.load_locators(file_name)
        return self

    # ==================== iframe 管理 ====================


    def is_in_iframe(self) -> bool:
        """是否在 iframe 中"""
        return self._iframe is not None

    def switch_to_iframe(self, selector: str = None) -> "BaseMethods":
        """切换到 iframe - 自动查找"""
        if selector:
            log.info(f"尝试切换到指定 iframe: {selector}")
            self._iframe = self.page.frame_locator(selector)
        else:
            # 自动查找包含 canvas 的 iframe
            log.info("自动查找包含 canvas 的 iframe...")
            frames = self.page.frames
            for frame in frames:
                try:
                    # 跳过主 frame
                    if frame == self.page.main_frame:
                        continue

                    # 检查 frame 中是否有 canvas
                    canvas_count = frame.locator('canvas').count()
                    if canvas_count > 0:
                        log.info(f"✅ 找到包含 canvas 的 iframe: {frame.name}")
                        self._iframe = frame
                        break
                except:
                    pass

            # 如果没找到，尝试使用默认选择器
            if not self._iframe:
                log.info("未找到包含 canvas 的 iframe，尝试默认选择器...")
                self._iframe = self.page.frame_locator("iframe")

        return self

    def switch_to_main(self) -> "BaseMethods":
        """切换回主页面"""
        self._iframe = None
        return self

    def get_canvas(self):
        """获取 Canvas 元素 - 自动查找位置"""
        # 1. 先从当前 iframe 获取
        if self._iframe:
            canvas = self._iframe.locator("canvas").first
            if canvas.count() > 0:
                return canvas

        # 2. 从主页面获取
        canvas = self.page.locator("canvas").first
        if canvas.count() > 0:
            log.info("✅ 在主页面找到 Canvas")
            return canvas

        # 3. 遍历所有 frames 查找
        log.info("遍历所有 frames 查找 Canvas...")
        for frame in self.page.frames:
            try:
                canvas = frame.locator("canvas").first
                if canvas.count() > 0:
                    log.info(f"✅ 在 frame {frame.name} 中找到 Canvas")
                    self._iframe = frame
                    return canvas
            except:
                pass

        log.error("❌ 未找到 Canvas")
        return self.page.locator("canvas").first

    def wait_for_canvas(self, timeout: int = 30000):
        """等待 Canvas 可见"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                canvas = self.get_canvas()
                if canvas.count() > 0 and canvas.first.is_visible():
                    log.info("✅ Canvas 可见")
                    return True
            except:
                pass
            time.sleep(0.5)

        log.info("❌ Canvas 不可见")
        return False

    def wait_for_canvas_ready(self, timeout: int = 30000):
        """等待 Canvas 完全就绪（有尺寸）"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                canvas = self.get_canvas()
                if canvas.count() > 0:
                    box = canvas.first.bounding_box()
                    if box and box['width'] > 0 and box['height'] > 0:
                        log.info(f"✅ Canvas 就绪: {box['width']}x{box['height']}")
                        return True
                time.sleep(0.5)
            except Exception as e:
                log.info(f"等待 Canvas 就绪: {e}")
                time.sleep(0.5)

        log.error("❌ Canvas 就绪超时")
        return False

    def get_canvas_center(self) -> Optional[dict]:
        """获取 Canvas 中心点坐标"""
        print("[get_canvas_center] 开始获取 Canvas 中心点")

        # 先确保 Canvas 就绪
        if not self.wait_for_canvas_ready():
            print("[get_canvas_center] ❌ Canvas 未就绪")
            return None

        canvas = self.get_canvas()
        if canvas.count() == 0:
            print("[get_canvas_center] ❌ 未找到 Canvas")
            return None

        try:
            box = canvas.first.bounding_box()
            if box and box['width'] > 0 and box['height'] > 0:
                center = {
                    'x': box['x'] + box['width'] / 2,
                    'y': box['y'] + box['height'] / 2
                }
                log.info(f"[get_canvas_center] ✅ 中心点: ({center['x']:.2f}, {center['y']:.2f})")
                log.info(f"[get_canvas_center] Canvas 尺寸: {box['width']:.2f} x {box['height']:.2f}")
                return center
        except Exception as e:
            log.error(f"[get_canvas_center] ❌ 获取边界框失败: {e}")

        return None

    # ==================== Canvas 截图辅助 ====================

    def get_canvas_overlay_selectors(self) -> list:
        """读取 Canvas 截图时需要隐藏的动态浮层选择器"""
        path = Path(__file__).parent.parent / "locators" / "iframe_locators.yaml"
        return load_config(str(path)).get("canvas_screenshot.overlays", []) or []

    def get_canvas_overlay_style(self) -> str:
        """生成截图时注入的 CSS：隐藏弹窗 / 提示 / 加载态"""
        selectors = self.get_canvas_overlay_selectors()
        if not selectors:
            return ""
        return (
            f"{', '.join(selectors)} "
            "{ visibility: hidden !important; opacity: 0 !important; }"
        )

    def get_canvas_info(self):
        """获取 Canvas 信息"""
        canvas = self.get_canvas()
        box = canvas.bounding_box()
        if box:
            return {
                'x': box['x'],
                'y': box['y'],
                'width': box['width'],
                'height': box['height'],
                'center_x': box['x'] + box['width'] / 2,
                'center_y': box['y'] + box['height'] / 2
            }
        return None

    # ==================== 通用按钮操作 ====================

    def wait_for_toolbar(self, button_text: str = "回到原点", timeout: int = 60000) -> bool:
        """等待查看器工具栏出现（说明模型已渲染完成）

        查看器在桌面/移动布局下的按钮 class 不同，这里两种都检查。
        """
        deadline = time.time() + timeout / 1000
        selectors = [
            f".fc-tool-btn-box:has-text('{button_text}')",
            f".fc-mobile-tool-btn-box:has-text('{button_text}')",
        ]
        while time.time() < deadline:
            for frame in self.page.frames:
                try:
                    for selector in selectors:
                        element = frame.locator(selector)
                        if element.count() > 0 and element.first.is_visible():
                            log.info(f"✅ 工具栏已就绪（{button_text}）")
                            return True
                except Exception:
                    pass
            time.sleep(0.5)
        log.error(f"❌ 等待工具栏超时，未找到按钮: {button_text}")
        return False

    def click_button_by_text(self, button_text: str, timeout: int = 5000) -> bool:
        """
        在所有 frames 中查找并点击指定文本的按钮（通用方法）

        Args:
            button_text: 按钮文本，如 "回到原点"、"测量"、"旋转" 等
            timeout: 超时时间

        Returns:
            bool: 是否点击成功
        """
        log.info(f"查找并点击按钮: {button_text}")

        # 先滚动到底部（确保底部工具栏可见）
        try:
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.3)
        except:
            pass

        # 遍历所有 frames 查找按钮
        for frame in self.page.frames:
            try:
                # 尝试多种选择器（桌面布局 / 移动布局）
                selectors = [
                    f".fc-tool-btn-box:has-text('{button_text}')",
                    f".fc-mobile-tool-btn-box:has-text('{button_text}')",
                    f"button:has-text('{button_text}')",
                    f"[class*='tool']:has-text('{button_text}')"
                ]

                for selector in selectors:
                    try:
                        element = frame.locator(selector)
                        if element.count() > 0 and element.first.is_visible():
                            element.first.scroll_into_view_if_needed()
                            time.sleep(0.2)
                            element.first.click()
                            log.success(f"点击按钮成功: {button_text}")
                            return True
                    except:
                        pass
            except:
                pass

        log.error(f"未找到按钮: {button_text}")
        return False
    def debug_all_buttons_in_all_frames(self):
        """
        调试：打印所有 frames 中的所有可点击按钮
        """
        log.section("遍历所有 Frames 查找按钮")

        log.info(f"共有 {len(self.page.frames)} 个 frames")

        for i, frame in enumerate(self.page.frames):
            frame_name = frame.name or f"frame_{i}"
            log.info(f"\n--- Frame {i}: {frame_name} ---")
            log.info(f"    URL: {frame.url[:80]}")

            try:
                # 查找所有 button
                buttons = frame.locator("button").all()
                log.info(f"    找到 {len(buttons)} 个 button")

                for j, btn in enumerate(buttons):
                    try:
                        text = btn.text_content() or btn.get_attribute("aria-label") or "无文本"
                        is_visible = btn.is_visible()
                        is_enabled = btn.is_enabled()
                        class_name = btn.get_attribute("class") or ""

                        log.info(f"      [{j}] 文本: {text[:40]}")
                        log.info(f"          可见: {is_visible}, 启用: {is_enabled}")
                        log.info(f"          class: {class_name[:50]}")
                    except:
                        pass

                # 查找所有可点击元素（a, div[role='button'] 等）
                clickables = frame.locator("a, [role='button'], .fc-tool-btn-box").all()
                log.info(f"    其他可点击元素: {len(clickables)} 个")

            except Exception as e:
                log.error(f"    遍历失败: {e}")

    def click_tool_button(self, tool_name: str) -> bool:
        """
        点击底部工具栏按钮（快捷方法）

        Args:
            tool_name: 工具名称，如 "回到原点"、"测量"、"旋转" 等
        """
        return self.click_button_by_text(tool_name)
    # ==================== 鼠标操作 ====================

    def mouse_drag(self, start_x: float, start_y: float, end_x: float, end_y: float):
        """鼠标拖拽"""
        return self.base_page.mouse_drag(start_x, start_y, end_x, end_y)

    def mouse_wheel(self, delta_x: int, delta_y: int, x: float = None, y: float = None):
        """鼠标滚轮"""
        return self.base_page.mouse_wheel(delta_x, delta_y, x, y)

    def mouse_click_at(self, x: float, y: float):
        """在指定坐标点击"""
        return self.base_page.mouse_click_at(x, y)

    # ==================== 元素操作（直接代理到 base_page） ====================

    def click(self, *args, **kwargs):
        return self.base_page.click(*args, **kwargs)

    def fill(self, *args, **kwargs):
        return self.base_page.fill(*args, **kwargs)

    def get_text(self, *args, **kwargs):
        return self.base_page.get_text(*args, **kwargs)

    def is_visible(self, *args, **kwargs):
        return self.base_page.is_visible(*args, **kwargs)

    def wait_for_element(self, *args, **kwargs):
        return self.base_page.wait_for_element(*args, **kwargs)

    def highlight_element(self, *args, **kwargs):
        return self.base_page.highlight_element(*args, **kwargs)

    def get_element_info(self, *args, **kwargs):
        return self.base_page.get_element_info(*args, **kwargs)

    def screenshot(self, *args, **kwargs):
        return self.base_page.screenshot(*args, **kwargs)
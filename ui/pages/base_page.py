# pages/base_page.py
from playwright.sync_api import Page, Locator
import yaml
from pathlib import Path
import time
from common.utils.logger import log


class BasePage:
    """基础页面类 - 提供原子操作"""

    def __init__(self, page: Page):
        self.page = page
        self.locators = None

    def load_locators(self, file_name: str) -> dict:
        """加载定位器配置"""
        locator_path = Path(__file__).parent.parent / "locators" / file_name
        log.info(f"加载定位器文件: {locator_path}")
        with open(locator_path, 'r', encoding='utf-8') as f:
            self.locators = yaml.safe_load(f)
        log.success(f"定位器加载成功: {list(self.locators.keys())}")
        return self.locators

    def get_locator(self, *keys) -> str:
        """获取定位器选择器"""
        if not self.locators:
            raise Exception("请先调用 load_locators() 加载定位器文件")

        value = self.locators
        for key in keys:
            log.debug(f"查找定位器: {key}")
            if key not in value:
                log.error(f"定位器键 '{key}' 不存在，可用键: {list(value.keys())}")
                raise KeyError(f"键 '{key}' 不存在")
            value = value[key]

        log.info(f"获取定位器 {'.'.join(keys)}: {value}")
        return value

    def get_element(self, *keys) -> Locator:
        """获取元素"""
        selector = self.get_locator(*keys)
        log.info(f"获取元素: {selector}")
        return self.page.locator(selector)

    def highlight(self, selector: str, duration: int = 2000, color: str = "red"):
        """高亮元素（用于调试）"""
        log.info(f"高亮元素: {selector}")
        self.page.evaluate(f"""
            (selector, duration, color) => {{
                const element = document.querySelector(selector);
                if (element) {{
                    const originalOutline = element.style.outline;
                    const originalBackground = element.style.backgroundColor;
                    element.style.outline = `3px solid ${{color}}`;
                    element.style.outlineOffset = '2px';
                    element.style.backgroundColor = `${{color}}30`;
                    setTimeout(() => {{
                        element.style.outline = originalOutline;
                        element.style.backgroundColor = originalBackground;
                    }}, duration);
                }} else {{
                    console.log('元素未找到: ' + selector);
                }}
            }}
        """, selector, duration, color)
        time.sleep(0.5)  # 等待高亮显示

    def wait_for_element_with_debug(self, *keys, timeout: int = 10000, state: str = "visible"):
        """等待元素并输出调试信息"""
        selector = self.get_locator(*keys)
        log.info(f"等待元素: {selector}, 状态: {state}, 超时: {timeout}ms")

        start_time = time.time()
        while time.time() - start_time < timeout / 1000:
            try:
                element = self.page.locator(selector)
                if state == "visible":
                    if element.is_visible():
                        log.success(f"元素已可见: {selector}")
                        return element
                elif state == "attached":
                    if element.count() > 0:
                        log.success(f"元素已存在: {selector}")
                        return element
            except Exception as e:
                log.debug(f"等待元素中: {e}")

            time.sleep(0.3)

        # 超时后输出详细调试信息
        log.error(f"等待元素超时: {selector}")
        self._debug_element_not_found(selector)
        raise Exception(f"等待元素超时: {selector}")

    def _debug_element_not_found(self, selector: str):
        """元素找不到时的调试信息"""
        log.error(f"========== 元素调试信息 ==========")
        log.error(f"查找的选择器: {selector}")

        # 检查页面中是否存在类似元素
        similar_selectors = [
            selector,
            selector.replace("button:has-text('回到原点')", "button"),
            selector.replace("button:has-text('回到原点')", "[class*='reset']"),
            selector.replace("button:has-text('回到原点')", "[class*='home']"),
            selector.replace("button:has-text('回到原点')", "[class*='origin']"),
        ]

        for sim_sel in similar_selectors[:3]:
            try:
                count = self.page.locator(sim_sel).count()
                if count > 0:
                    log.info(f"找到类似元素: {sim_sel}, 数量: {count}")
                    # 高亮类似元素
                    self.highlight(sim_sel, duration=1000, color="orange")
            except:
                pass

        # 列出所有按钮
        try:
            buttons = self.page.locator("button").all()
            log.info(f"页面中共有 {len(buttons)} 个按钮:")
            for i, btn in enumerate(buttons[:10]):
                try:
                    text = btn.text_content() or btn.get_attribute("aria-label") or "无文本"
                    log.info(f"  按钮 {i + 1}: {text[:50]}")
                except:
                    pass
        except Exception as e:
            log.error(f"获取按钮列表失败: {e}")

        # 截图
        screenshot = self.page.screenshot()
        log.attach_screenshot(screenshot, f"元素未找到_{selector.replace(' ', '_')}")

        log.error(f"==================================")

    # ==================== 基础元素操作 ====================

    def click(self, *keys, timeout: int = 5000, selector: str = None):
        """点击元素"""
        if selector:
            log.info(f"点击元素 (选择器): {selector}")
            try:
                element = self.page.locator(selector)
                element.wait_for(state="visible", timeout=timeout)
                # 高亮后点击
                self.highlight(selector, duration=500, color="green")
                element.click()
                log.success(f"点击成功: {selector}")
            except Exception as e:
                log.error(f"点击失败: {selector}, 错误: {e}")
                self._debug_element_not_found(selector)
                raise
        else:
            selector = self.get_locator(*keys)
            log.info(f"点击元素 (定位器): {'.'.join(keys)} -> {selector}")
            try:
                element = self.page.locator(selector)
                element.wait_for(state="visible", timeout=timeout)
                # 高亮后点击
                self.highlight(selector, duration=500, color="green")
                element.click()
                log.success(f"点击成功: {selector}")
            except Exception as e:
                log.error(f"点击失败: {selector}, 错误: {e}")
                self._debug_element_not_found(selector)
                raise

    def fill(self, text: str, *keys, timeout: int = 5000, selector: str = None):
        """填充文本"""
        if selector:
            log.info(f"填充文本: {selector} = {text}")
        else:
            selector = self.get_locator(*keys)
            log.info(f"填充文本: {'.'.join(keys)} -> {selector} = {text}")

        element = self.page.locator(selector)
        element.wait_for(state="visible", timeout=timeout)
        self.highlight(selector, duration=500, color="blue")
        element.fill(text)
        log.success(f"填充成功: {selector}")

    def get_text(self, *keys, selector: str = None) -> str:
        """获取文本"""
        if selector:
            log.info(f"获取文本: {selector}")
        else:
            selector = self.get_locator(*keys)
            log.info(f"获取文本: {'.'.join(keys)} -> {selector}")

        element = self.page.locator(selector)
        text = element.text_content()
        log.info(f"获取到文本: {text}")
        return text

    def is_visible(self, *keys, selector: str = None) -> bool:
        """检查元素是否可见"""
        if selector:
            log.info(f"检查可见性: {selector}")
        else:
            selector = self.get_locator(*keys)
            log.info(f"检查可见性: {'.'.join(keys)} -> {selector}")

        try:
            is_visible = self.page.locator(selector).is_visible()
            log.info(f"可见性结果: {is_visible}")
            return is_visible
        except Exception as e:
            log.error(f"检查可见性失败: {e}")
            return False

    def wait_for_element(self, *keys, state: str = "visible", timeout: int = 10000, selector: str = None):
        """等待元素状态"""
        if selector:
            log.info(f"等待元素: {selector}, 状态: {state}")
            self.page.locator(selector).wait_for(state=state, timeout=timeout)
        else:
            selector = self.get_locator(*keys)
            log.info(f"等待元素: {'.'.join(keys)} -> {selector}, 状态: {state}")
            self.page.locator(selector).wait_for(state=state, timeout=timeout)

        log.success(f"元素已{state}: {selector}")

    def wait_for_element_disappear(self, *keys, timeout: int = 30000, selector: str = None):
        """等待元素消失"""
        if selector:
            log.info(f"等待元素消失: {selector}")
            self.page.locator(selector).wait_for(state="detached", timeout=timeout)
        else:
            selector = self.get_locator(*keys)
            log.info(f"等待元素消失: {'.'.join(keys)} -> {selector}")
            self.page.locator(selector).wait_for(state="detached", timeout=timeout)

        log.success(f"元素已消失: {selector}")

    # ==================== 鼠标操作 ====================

    def mouse_drag(self, start_x: float, start_y: float, end_x: float, end_y: float):
        """鼠标拖拽"""
        log.info(f"鼠标拖拽: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
        self.page.mouse.move(start_x, start_y)
        self.page.mouse.down()
        self.page.mouse.move(end_x, end_y)
        self.page.mouse.up()
        return True

    def mouse_wheel(self, delta_x: int, delta_y: int, x: float = None, y: float = None):
        """鼠标滚轮"""
        if x and y:
            log.info(f"鼠标滚轮: ({x}, {y}) 滚动 ({delta_x}, {delta_y})")
            self.page.mouse.move(x, y)
        else:
            log.info(f"鼠标滚轮: 滚动 ({delta_x}, {delta_y})")
        self.page.mouse.wheel(delta_x, delta_y)
        return True

    def mouse_click_at(self, x: float, y: float):
        """在指定坐标点击"""
        log.info(f"坐标点击: ({x}, {y})")
        self.page.mouse.click(x, y)
        return True

    # ==================== 调试方法 ====================

    def highlight_element(self, selector: str, color: str = "red", duration: int = 3000):
        """高亮元素（别名）"""
        self.highlight(selector, duration, color)

    def screenshot(self, path: str = None):
        """截图"""
        if path:
            log.info(f"截图保存: {path}")
            self.page.screenshot(path=path)
        else:
            log.info("截图")
            return self.page.screenshot()

    def debug_page(self):
        """调试当前页面状态"""
        log.section("页面调试信息")
        log.info(f"当前URL: {self.page.url}")
        log.info(f"页面标题: {self.page.title()}")

        # 列出所有 iframe
        frames = self.page.frames
        log.info(f"共有 {len(frames)} 个 frames:")
        for i, frame in enumerate(frames):
            log.info(f"  Frame {i}: {frame.name}")

        # 列出所有按钮
        buttons = self.page.locator("button").all()
        log.info(f"共有 {len(buttons)} 个按钮:")
        for i, btn in enumerate(buttons[:20]):
            try:
                text = btn.text_content() or btn.get_attribute("aria-label") or "无文本"
                is_visible = btn.is_visible()
                log.info(f"  按钮 {i + 1}: {text[:50]} (可见: {is_visible})")
            except:
                pass

        # 截图
        screenshot = self.page.screenshot()
        log.attach_screenshot(screenshot, "页面调试截图")
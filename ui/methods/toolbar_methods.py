# methods/toolbar_methods.py
from ui.methods.base_methods import BaseMethods
import time
from typing import List, Optional


class ToolbarMethods(BaseMethods):
    """工具栏方法类"""

    def __init__(self, context):
        super().__init__(context)

    def click_tool(self, tool_name: str, wait_after: float = 0.5) -> bool:
        """点击工具栏按钮"""
        try:
            self.switch_to_main()
            self.click(selector=f"button:has-text('{tool_name}')")
            time.sleep(wait_after)
            return True
        except Exception as e:
            print(f"点击工具 {tool_name} 失败: {e}")
            return False

    def is_tool_active(self, tool_name: str) -> bool:
        """检查工具是否激活"""
        try:
            tool = self.page.locator(f"button:has-text('{tool_name}')")
            class_name = tool.get_attribute("class") or ""
            return "active" in class_name
        except:
            return False

    def get_all_tools(self) -> List[str]:
        """获取所有工具名称"""
        try:
            tools = self.page.locator(".tool-btn, .fc-tool-btn").all()
            return [tool.text_content() for tool in tools if tool.text_content()]
        except Exception as e:
            print(f"获取工具列表失败: {e}")
            return []

    def get_active_tool(self) -> Optional[str]:
        """获取当前激活的工具"""
        try:
            active_tools = self.page.locator(".tool-btn.active, .fc-tool-btn.active").all()
            if active_tools:
                return active_tools[0].text_content()
            return None
        except:
            return None
# methods/measurement_methods.py
from ui.methods.base_methods import BaseMethods
import time
import re
from typing import Optional, List


class MeasurementMethods(BaseMethods):
    """测量工具方法类"""

    def __init__(self, context):
        super().__init__(context)

    def activate(self) -> bool:
        """激活测量工具"""
        try:
            self.switch_to_main()
            self.click(selector="button:has-text('测量')")
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"激活测量工具失败: {e}")
            return False

    def deactivate(self) -> bool:
        """关闭测量工具"""
        try:
            self.click(selector="button:has-text('关闭')")
            time.sleep(0.3)
            return True
        except Exception as e:
            print(f"关闭测量工具失败: {e}")
            return False

    def measure_distance(self, start_x: int, start_y: int, end_x: int, end_y: int) -> Optional[float]:
        """
        测量两点距离

        Args:
            start_x, start_y: 起点坐标
            end_x, end_y: 终点坐标

        Returns:
            float: 测量距离（mm），失败返回 None
        """
        try:
            # 确保在 iframe 中
            if not self.is_in_iframe():
                self.switch_to_iframe()

            # 激活测量工具
            self.activate()

            # 点击起点
            self.mouse_click_at(start_x, start_y)
            time.sleep(0.2)

            # 点击终点
            self.mouse_click_at(end_x, end_y)
            time.sleep(0.5)

            # 获取测量结果
            result_selector = ".measurement-result"
            if self.context.is_visible(selector=result_selector):
                result_text = self.get_text(selector=result_selector)
                match = re.search(r'(\d+\.?\d*)', result_text)
                if match:
                    return float(match.group(1))

            return None

        except Exception as e:
            print(f"测量距离失败: {e}")
            return None

    def clear(self) -> bool:
        """清除所有测量"""
        try:
            self.switch_to_main()
            self.click(selector="button:has-text('清除')")
            time.sleep(0.3)
            return True
        except Exception as e:
            print(f"清除测量失败: {e}")
            return False

    def get_all_measurements(self) -> List[str]:
        """获取所有测量结果"""
        try:
            measurements = self.page.locator(".measurement-item").all()
            return [item.text_content() for item in measurements]
        except Exception as e:
            print(f"获取测量结果失败: {e}")
            return []
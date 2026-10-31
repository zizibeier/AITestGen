# tests/test_coverage.py
import pytest
import allure
from allure_commons.types import AttachmentType

from ui.tests.ui_base_test import BaseDesignTest


@allure.feature("Bug修复验证")
class TestCoverageIssue(BaseDesignTest):
    """覆盖问题测试类 - 专门用于定位按钮被覆盖的问题"""

    @allure.story("按钮覆盖检查")
    def test_button_not_covered(self):
        """测试回到原点按钮是否被覆盖"""
        self.log_info("开始检查按钮覆盖情况")

        # 切换到主页面
        self.design.ensure_in_main()

        # 滚动到底部
        self.design.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.wait(0.5)

        # 获取按钮信息
        btn_selector = ".fc-tool-btn-box"
        btn_info = self.debug_element(btn_selector)

        if btn_info:
            is_covered = btn_info.get('isCovered', False)

            if is_covered:
                covering = btn_info.get('coveringElement', {})
                self.log_error(f"按钮被覆盖: {covering.get('tagName')}.{covering.get('className')}")

                # 高亮覆盖元素
                self.highlight_element(btn_selector, "red", 3000)
                self.take_screenshot("按钮被覆盖截图")

                pytest.fail(f"按钮被 {covering.get('tagName')} 覆盖")
            else:
                self.log_success("按钮未被覆盖")
                self.take_screenshot("按钮正常显示")

        self.design.ensure_in_iframe()

    @allure.story("重置按钮可点击性")
    def test_reset_button_clickable(self):
        """测试回到原点按钮是否可点击"""
        self.log_info("开始测试重置按钮可点击性")

        # 先进行一些视图操作
        self.design.view.rotate(100, 50)
        self.design.view.zoom(200)
        self.take_screenshot("操作后视图")

        # 尝试点击重置按钮（带重试）
        result = self.design.view.reset_with_retry(max_retries=3, debug=True)

        if result:
            self.log_success("重置按钮点击成功")
            self.take_screenshot("重置后视图")
        else:
            # 添加详细调试信息
            self.design.ensure_in_main()
            btn_info = self.design.get_element_info("button:has-text('回到原点')")
            if btn_info:
                allure.attach(
                    f"""
                    重置按钮详细信息:
                    - 位置: ({btn_info['rect']['left']:.2f}, {btn_info['rect']['top']:.2f})
                    - 尺寸: {btn_info['rect']['width']:.2f} x {btn_info['rect']['height']:.2f}
                    - z-index: {btn_info['styles']['zIndex']}
                    - pointer-events: {btn_info['styles']['pointerEvents']}
                    - 是否被覆盖: {btn_info['isCovered']}
                    """,
                    name="重置按钮调试信息",
                    attachment_type=AttachmentType.TEXT
                )

                if btn_info.get('isCovered'):
                    covering = btn_info.get('coveringElement', {})
                    self.highlight_element("button:has-text('回到原点')", "red", 3000)
                    self.take_screenshot("重置按钮被覆盖")

            self.assert_true(result, "重置按钮不可点击")

        self.design.ensure_in_iframe()

    @allure.story("元素堆栈分析")
    def test_analyze_element_stack(self):
        """分析元素堆栈，找出覆盖原因"""
        self.log_info("开始分析元素堆栈")

        self.design.ensure_in_main()
        self.design.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.wait(0.5)

        btn_selector = ".fc-tool-btn-box"

        # 获取元素堆栈
        stack = self.design.context.base_page.page.evaluate("""
            (selector) => {
                const element = document.querySelector(selector);
                if (!element) return [];

                const rect = element.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                const elements = document.elementsFromPoint(centerX, centerY);

                return elements.slice(0, 10).map((el, idx) => ({
                    index: idx,
                    tagName: el.tagName,
                    className: el.className,
                    id: el.id,
                    zIndex: window.getComputedStyle(el).zIndex,
                    position: window.getComputedStyle(el).position,
                    pointerEvents: window.getComputedStyle(el).pointerEvents
                }));
            }
        """, btn_selector)

        # 输出堆栈信息
        stack_info = "元素堆栈信息:\n"
        for el in stack:
            stack_info += f"""
            [{el['index']}] {el['tagName']}.{el['className']}
                - ID: {el['id'] or '无'}
                - z-index: {el['zIndex']}
                - position: {el['position']}
                - pointer-events: {el['pointerEvents']}
            """

        allure.attach(stack_info, name="元素堆栈分析", attachment_type=AttachmentType.TEXT)

        # 找出覆盖元素
        if len(stack) > 1:
            covering = stack[0]
            button = stack[-1] if len(stack) > 0 else None

            self.log_info(f"最上层元素: {covering['tagName']}.{covering['className']}")
            self.log_info(f"目标按钮: {button['tagName']}.{button['className'] if button else '未知'}")

            if covering['tagName'] != button['tagName']:
                self.log_warning(f"按钮被 {covering['tagName']} 覆盖")

                # 高亮覆盖元素
                self.design.highlight_element(btn_selector, "red", 3000)
                self.take_screenshot("覆盖元素高亮")

        self.design.ensure_in_iframe()
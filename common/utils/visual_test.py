# utils/visual_regression.py
import allure
from allure_commons.types import AttachmentType
from PIL import Image
import numpy as np
import io


class VisualRegression:
    """视觉回归测试"""

    @staticmethod
    def capture_canvas_screenshot(model_viewer, name="canvas"):
        """从 ModelViewerPage 捕获 canvas 截图

        Args:
            model_viewer: ModelViewerPage 对象
            name: 截图名称
        """
        try:
            # 使用 iframe_methods 获取 canvas
            canvas = model_viewer.iframe_methods.get_canvas()
            canvas.wait_for(state="visible", timeout=5000)
            screenshot = canvas.screenshot()
            allure.attach(screenshot, name=name, attachment_type=AttachmentType.PNG)
            return screenshot

        except Exception as e:
            print(f"截图失败: {e}")
            # 备用：截图整个页面
            try:
                page_screenshot = model_viewer.page.screenshot()
                allure.attach(page_screenshot, name=f"{name}_fallback", attachment_type=AttachmentType.PNG)
            except:
                pass
            return None


    @staticmethod
    def capture_from_page(page, name="canvas"):
        """从 page 对象捕获 canvas 截图（需要先切换到 iframe）"""
        try:
            iframe = page.frame_locator("#viewerIframe")
            canvas = iframe.locator("canvas").first
            canvas.wait_for(state="visible", timeout=5000)
            screenshot = canvas.screenshot()
            allure.attach(screenshot, name=name, attachment_type=AttachmentType.PNG)
            return screenshot
        except Exception as e:
            print(f"截图失败: {e}")
            return None

    @staticmethod
    def compare_screenshots(baseline, current, threshold=0.95):
        """对比截图相似度"""
        if not baseline or not current:
            return False

        if isinstance(baseline, str):
            img1 = Image.open(baseline)
        else:
            img1 = Image.open(io.BytesIO(baseline))

        if isinstance(current, str):
            img2 = Image.open(current)
        else:
            img2 = Image.open(io.BytesIO(current))

        arr1 = np.array(img1)
        arr2 = np.array(img2)

        if arr1.shape != arr2.shape:
            img2 = img2.resize(img1.size)
            arr2 = np.array(img2)

        diff = np.abs(arr1 - arr2).mean()
        similarity = 1 - diff / 255

        allure.attach(
            f"相似度: {similarity:.2%}\n阈值: {threshold:.2%}",
            name="similarity_score",
            attachment_type=AttachmentType.TEXT
        )

        return similarity >= threshold
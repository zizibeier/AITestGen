# utils/webgl_helper.py
import allure
from allure_commons.types import AttachmentType
import json


class WebGLHelper:
    """WebGL 数据捕获辅助类"""

    @staticmethod
    def capture_webgl_info(model_viewer):
        """捕获 WebGL 信息"""
        try:
            # 通过 iframe 执行 JavaScript
            iframe = model_viewer.page.frame_locator("#viewerIframe")

            webgl_info = iframe.evaluate("""
                () => {
                    const canvas = document.querySelector('canvas');
                    if (!canvas) return { error: 'Canvas not found' };

                    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                    if (!gl) return { error: 'WebGL not supported' };

                    return {
                        vendor: gl.getParameter(gl.VENDOR),
                        renderer: gl.getParameter(gl.RENDERER),
                        version: gl.getParameter(gl.VERSION),
                        max_texture_size: gl.getParameter(gl.MAX_TEXTURE_SIZE)
                    };
                }
            """)

            allure.attach(
                json.dumps(webgl_info, indent=2),
                name="webgl_info",
                attachment_type=AttachmentType.JSON
            )
            return webgl_info
        except Exception as e:
            allure.attach(str(e), name="webgl_error", attachment_type=AttachmentType.TEXT)
            return None
# utils/model_stats.py
import allure
from allure_commons.types import AttachmentType
import json


class ModelStatsHelper:
    """模型统计信息捕获"""

    @staticmethod
    def capture_model_stats(model_viewer):
        """捕获模型统计信息"""
        try:
            # 通过 iframe 执行 JavaScript
            iframe = model_viewer.page.frame_locator("#viewerIframe")

            stats = iframe.evaluate("""
                () => {
                    const stats = {
                        timestamp: new Date().toISOString(),
                        canvas_size: null,
                        objects_count: 0
                    };

                    const canvas = document.querySelector('canvas');
                    if (canvas) {
                        stats.canvas_size = {
                            width: canvas.width,
                            height: canvas.height,
                            client_width: canvas.clientWidth,
                            client_height: canvas.clientHeight
                        };
                    }

                    if (window.scene && window.scene.children) {
                        stats.objects_count = window.scene.children.filter(c => c.isMesh).length;
                    }

                    return stats;
                }
            """)

            allure.attach(
                json.dumps(stats, indent=2),
                name="model_stats",
                attachment_type=AttachmentType.JSON
            )
            return stats
        except Exception as e:
            allure.attach(str(e), name="stats_error", attachment_type=AttachmentType.TEXT)
            return None
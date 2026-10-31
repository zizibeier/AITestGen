# utils/transform_helper.py
import allure
from allure_commons.types import AttachmentType
import json


class TransformHelper:
    """模型变换信息捕获"""

    @staticmethod
    def capture_camera_transform(page):
        """捕获相机变换信息"""
        transform = page.evaluate("""
            () => {
                if (!window.camera) return { error: 'No camera found' };

                const camera = window.camera;
                return {
                    position: {
                        x: camera.position?.x,
                        y: camera.position?.y,
                        z: camera.position?.z
                    },
                    rotation: {
                        x: camera.rotation?.x,
                        y: camera.rotation?.y,
                        z: camera.rotation?.z
                    },
                    zoom: camera.zoom,
                    fov: camera.fov
                };
            }
        """)

        allure.attach(
            json.dumps(transform, indent=2),
            name="camera_transform",
            attachment_type=AttachmentType.JSON
        )
        return transform

    @staticmethod
    def capture_model_transform(page):
        """捕获模型变换信息"""
        transform = page.evaluate("""
            () => {
                if (!window.scene) return { error: 'No scene found' };

                // 尝试获取主要模型的变换
                const mainModel = window.scene.children.find(c => c.isMesh);
                if (!mainModel) return { error: 'No mesh found' };

                return {
                    position: {
                        x: mainModel.position?.x,
                        y: mainModel.position?.y,
                        z: mainModel.position?.z
                    },
                    rotation: {
                        x: mainModel.rotation?.x,
                        y: mainModel.rotation?.y,
                        z: mainModel.rotation?.z
                    },
                    scale: {
                        x: mainModel.scale?.x,
                        y: mainModel.scale?.y,
                        z: mainModel.scale?.z
                    }
                };
            }
        """)

        allure.attach(
            json.dumps(transform, indent=2),
            name="model_transform",
            attachment_type=AttachmentType.JSON
        )
        return transform
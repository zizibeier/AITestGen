# api/endpoints/analysis_endpoints.py
import os
import time
from pathlib import Path
from typing import Dict


from common.config.settings import Config
from common.utils.data_utils.yaml_loader import load_config


class AnalysisEndpoints:
    """CNC 业务端点（使用 APIContext）"""

    def __init__(self, api_context=None, base_url: str = None, webhook_key: str = None):
        """
        初始化 CNC Endpoints

        Args:
            api_context: APIContext 对象
            base_url: API 地址（如果不使用 api_context）
            webhook_key: Webhook 密钥
        """
        # 优先使用 api_context
        if api_context is not None:
            self.ctx = api_context
            self.base_url = api_context.base_url
        else:
            self.ctx = None
            self.base_url = base_url or Config.API_BASE_URL

        self.webhook_key = webhook_key or Config.WEBHOOK_KEY

        # 加载配置文件
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root /"api"/ "data" / "api_config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        self.api_config = load_config(str(config_path))

    def _get_endpoint(self, key: str) -> str:
        """获取端点"""
        endpoint = self.api_config.get(key)
        if not endpoint:
            raise ValueError(f"配置中未找到: {key}")
        return endpoint

    def analysis_upload_file(
            self,
            file_path: str,
            **kwargs

    ) -> Dict:
        """
        零件解析文件上传

        Args:
            file_path: 模型文件路径（必传）
            webhook_key: webhook唯一标识（可选）
            params: 透传参数（可选）
            extra_info: 扩展信息，最大长度255（可选）
            use_cache: 使用缓存，true-使用缓存，false-不使用缓存，默认为true（可选）
            preview_type: 预览模型生成格式，0: glb 1:f3d，默认为1（可选）
            need_business_service: 是否调用业务类服务，0-否 1-是，默认为0（可选）
            need_stl_light_weight: 是否调用stl文件轻量化，0-否 1-是，默认为0（可选）
            minimum_thickness_threshold: 薄壁壁厚定义，单位mm，默认为0.5（可选）
            high_risk_area_define: 高风险区域面积，单位mm²，默认为100（可选）
            cover_color: 封面图颜色，如#85A2CD（可选）

        Returns:
            Dict: 包含 file_id, file_name, response 的上传结果
        """
        # 定义参数名映射字典（必须在使用前定义）
        param_mapping = {
            # Python风格（调用时使用） -> API风格（发送给服务端）
            'webhook_key': 'webhookKey',
            'use_cache': 'useCache',
            'extra_info': 'extraInfo',
            'preview_type': 'previewType',
            'need_business_service': 'needBusinessService',
            'need_stl_light_weight': 'needStlLightWeight',
            'minimum_thickness_threshold': 'minimumThicknessThreshold',
            'high_risk_area_define': 'highRiskAreaDefine',
            'cover_color': 'coverColor',
            # 也支持直接传驼峰风格
            'webhookKey': 'webhookKey',
            'useCache': 'useCache',
            'extraInfo': 'extraInfo',
            'previewType': 'previewType',
            'needBusinessService': 'needBusinessService',
            'needStlLightWeight': 'needStlLightWeight',
            'minimumThicknessThreshold': 'minimumThicknessThreshold',
            'highRiskAreaDefine': 'highRiskAreaDefine',
            'coverColor': 'coverColor',
        }

        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 获取端点
        endpoint = self._get_endpoint('analysis.upload_file')

        # 准备表单数据 - 只添加非None的参数
        data = {}
        for key, value in kwargs.items():
            if value is not None and value != "":
                # 映射参数名
                api_key = param_mapping.get(key, key)
                data[api_key] = value


        # 使用 APIContext 上传文件
        response = self.ctx.post_file(endpoint, file_path, data=data)

        # 解析响应
        result = response.json()

        # 兼容不同的响应格式
        if result.get('code') != '200' and result.get('success') is not True:
            raise Exception(f"上传失败: {result.get('msg', result.get('message', '未知错误'))}")

        # 获取文件ID（兼容多种返回格式）
        data_obj = result.get('data', {})
        file_id = data_obj.get('id') or data_obj.get('fileId') or data_obj.get('file_id')

        return {
            'file_id': file_id,
            'file_name': os.path.basename(file_path),
            'response': result
        }
    def analysis_upload_filepath(
            self,
            file_path: str,
            file_name: str,
            file_type: str,
            **kwargs
    ) -> Dict:
        """
        零件解析文件链接上传

        Args:
            file_path: 模型文件链接路径（必传）
            file_name:模型文件名称（必传）
            file_type：模型文件类型（必传）
            webhook_key: webhook唯一标识（可选）
            params: 透传参数（可选）
            extra_info: 扩展信息，最大长度255（可选）
            use_cache: 使用缓存，true-使用缓存，false-不使用缓存，默认为true（可选）
            preview_type: 预览模型生成格式，0: glb 1:f3d，默认为1（可选）
            need_business_service: 是否调用业务类服务，0-否 1-是，默认为0（可选）
            need_stl_light_weight: 是否调用stl文件轻量化，0-否 1-是，默认为0（可选）
            minimum_thickness_threshold: 薄壁壁厚定义，单位mm，默认为0.5（可选）
            high_risk_area_define: 高风险区域面积，单位mm²，默认为100（可选）
            cover_color: 封面图颜色，如#85A2CD（可选）

        Returns:
            Dict: 包含 file_id, file_name, response 的上传结果
        """

        # 获取端点
        endpoint = self._get_endpoint('analysis.upload_file')

        # 准备表单数据 - 只添加非None的参数
        data = {
            'filePath':file_path,
            'fileType':file_type,
            'fileName':file_name
        }
        # 准备表单数据 - 只添加非None的参数
        for key, value in kwargs.items():
            if value is not None and value != "":
                # 映射参数名
                api_key = mapping.get(key, key)
                data[api_key] = value

        # 使用 APIContext 上传文件
        response = self.ctx.post(endpoint, json=data)

        # 解析响应
        result = response.json()

        # 兼容不同的响应格式
        if result.get('code') != '200' and result.get('success') is not True:
            raise Exception(f"上传失败: {result.get('msg', result.get('message', '未知错误'))}")

        # 获取文件ID（兼容多种返回格式）
        data_obj = result.get('data', {})
        file_id = data_obj.get('id') or data_obj.get('fileId') or data_obj.get('file_id')

        return {
            'file_id': file_id,
            'file_name': file_name,
            'response': result
        }



    def get_status_by_id(self, file_id: str) -> Dict:
        """按 file_id 查询解析记录

        注意：服务端要求表单参数名为 id（不是 fileId，也不是 JSON body）。
        """
        endpoint = self._get_endpoint('analysis.file_by_id')
        response = self.ctx.post(endpoint, data={'id': file_id})
        return response.json()

    def wait_for_record(self, file_id: str, timeout: float = 30,
                        interval: float = 1, expected_code: str = '00000') -> Dict:
        """轮询解析记录，直到可查询或超时

        上传后服务端索引有延迟，立即查询可能返回“数据不存在”（000012）。
        超时返回最后一次响应，由调用方断言。
        """
        deadline = time.time() + timeout
        result = {}
        while True:
            result = self.get_status_by_id(file_id)
            if str(result.get('code')) == expected_code and result.get('data'):
                return result
            if time.time() >= deadline:
                return result
            time.sleep(interval)


    def get_result_by_page(self, file_id: str) -> Dict:
        """获取分析结果"""
        endpoint = self._get_endpoint('analysis.get_result')

        # 统一走 APIContext：鉴权、重试、超时、请求历史都由上下文层负责
        if self.ctx is None:
            raise RuntimeError(
                "AnalysisEndpoints.get_result_by_page 需要 APIContext，"
                "请通过 endpoints fixture 构造"
            )
        response = self.ctx.post(endpoint, json={'fileId': file_id})

        return response.json()
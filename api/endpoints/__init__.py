# api/endpoints/__init__.py
"""
Endpoints 模块
统一导出所有接口类
"""

from api.endpoints.analysis_endpoints import AnalysisEndpoints
from api.endpoints.baidu_endpoints import BaiduEndpoints
from api.endpoints.builder_open_endpoints import BuilderOpenEndpoints
from api.endpoints.builder_web_endpoints import BuilderWebEndpoints

__all__ = [
    "AnalysisEndpoints",
    "BaiduEndpoints",
    "BuilderOpenEndpoints",
    "BuilderWebEndpoints",
]

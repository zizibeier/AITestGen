# api/core/base_endpoints.py
"""API Endpoints 基类。

职责：
1. 持有 APIContext，所有 HTTP 请求统一走 APIContext
2. 从 api/data/api_config.yaml 读取接口路径（接口代码里不出现路径字面量）
3. 统一响应校验与 JSON 解析

注意：本类不创建 requests.Session，避免绕开框架的重试、鉴权、请求历史和 Allure 附件。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import requests

from api.core.api_context import APIContext
from common.utils.data_utils.yaml_loader import load_config


class EndpointError(RuntimeError):
    """接口层异常基类。"""


class EndpointConfigError(EndpointError):
    """接口路径配置缺失或非法。"""


class EndpointResponseError(EndpointError):
    """HTTP 状态码非 200 或响应不是合法 JSON。"""


class BaseEndpoints:
    """所有 Builder 接口封装类的基类。"""

    # api_config.yaml 中该端点组的前缀，如 "builder.web"
    config_prefix: str = ""
    # api_config.yaml 中域名节点，如 "builder_base_url"
    base_url_key: str = "builder_base_url"

    API_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "api_config.yaml"

    def __init__(
        self,
        ctx: APIContext,
        base_url: Optional[str] = None,
        config_path: Optional[str] = None,
    ):
        if ctx is None:
            raise ValueError("BaseEndpoints 需要 APIContext，请通过 endpoints fixture 获取")

        self.ctx = ctx
        self._config_path = Path(config_path) if config_path else self.API_CONFIG_PATH
        self._config = load_config(str(self._config_path))

        configured_base_url = self.config_value(self.base_url_key)
        self.base_url = (base_url or configured_base_url or "").rstrip("/")
        if not self.base_url:
            raise EndpointConfigError(f"配置中未找到域名节点: {self.base_url_key}")

    # ==================== 配置读取 ====================

    def config_value(self, dotted_key: str, default: Any = None) -> Any:
        """按点号路径读取 api_config.yaml，如 auth.get_token。"""
        return self._config.get(dotted_key, default)

    def endpoint(self, key: str) -> str:
        """读取当前端点组下的接口路径，如 endpoint("model_info")。"""
        dotted_key = f"{self.config_prefix}.{key}" if self.config_prefix else key
        path = self.config_value(dotted_key)
        if not path:
            raise EndpointConfigError(f"配置中未找到接口路径: {dotted_key}")
        return path

    def url(self, key: str) -> str:
        """拼接完整 URL。"""
        return f"{self.base_url}{self.endpoint(key)}"

    # ==================== 请求 ====================

    def request(
        self,
        method: str,
        key: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        auth: bool = True,
        **kwargs,
    ) -> requests.Response:
        """使用 APIContext 发起请求。"""
        return self.ctx.request(
            method,
            self.url(key),
            headers=headers,
            auth=auth,
            **kwargs,
        )

    def post(
        self,
        key: str,
        *,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: bool = True,
        **kwargs,
    ) -> requests.Response:
        return self.request(
            "POST", key, json_data=json_data, headers=headers, auth=auth, **kwargs
        )

    def get(
        self,
        key: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: bool = True,
        **kwargs,
    ) -> requests.Response:
        return self.request(
            "GET", key, params=params, headers=headers, auth=auth, **kwargs
        )

    # ==================== 响应处理 ====================

    @staticmethod
    def response_json(response: requests.Response, action: str = "请求") -> Dict[str, Any]:
        """校验 HTTP 200 并解析 JSON。"""
        if response.status_code != 200:
            raise EndpointResponseError(
                f"{action} 失败: HTTP {response.status_code}, "
                f"响应片段: {response.text[:300]}"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise EndpointResponseError(
                f"{action} 响应不是合法 JSON: {exc}; 响应片段: {response.text[:300]}"
            ) from exc

        if not isinstance(body, dict):
            raise EndpointResponseError(f"{action} 响应类型异常: {type(body).__name__}")
        return body

    def post_json(
        self,
        key: str,
        *,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """POST 并返回解析后的 JSON。"""
        response = self.post(
            key, json_data=json_data, headers=headers, auth=auth, **kwargs
        )
        return self.response_json(response, action=key)

    def get_json(
        self,
        key: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """GET 并返回解析后的 JSON。"""
        response = self.get(key, params=params, headers=headers, auth=auth, **kwargs)
        return self.response_json(response, action=key)

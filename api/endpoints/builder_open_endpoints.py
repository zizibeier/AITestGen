# api/endpoints/builder_open_endpoints.py
"""Builder 对外 OpenAPI。

鉴权方式：AppID/Secret 换取 Bearer Token，由 APIContext/AuthManager 自动注入。
域名：api_config.yaml 中的 builder_open_base_url。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from api.core.base_endpoints import BaseEndpoints
from api.core.builder_client import resolve_json_pointer
from common.config.settings import Config
from common.utils.logger import log


class BuilderOpenEndpoints(BaseEndpoints):
    """对外 OpenAPI 封装。"""

    config_prefix = "builder.open"
    base_url_key = "builder_open_base_url"

    # ==================== 鉴权 ====================

    def get_access_token(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
    ) -> Optional[str]:
        """用 AppID/Secret 换取 access_token（返回原始 token）。"""
        token_path = self.config_value("auth.get_token")
        if not token_path:
            raise ValueError("api_config.yaml 缺少 auth.get_token")

        response = self.ctx.get(
            token_path,
            params={
                "app_id": app_id or Config.APP_ID,
                "app_secret": app_secret or Config.APP_SECRET,
            },
            auth=False,
        )
        body = self.response_json(response, action="获取 access_token")

        token = resolve_json_pointer(body, "/data/access_token")
        if not token:
            log.error(f"获取 access_token 失败: code={body.get('code')}, msg={body.get('msg')}")
            return None

        log.info("获取 access_token 成功")
        return token

    def get_bearer_token(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
    ) -> Optional[str]:
        """返回 Authorization 可直接使用的 Bearer Token。"""
        token = self.get_access_token(app_id, app_secret)
        return f"Bearer {token}" if token else None

    # ==================== 自动建模 ====================

    def auto_request_model(
        self,
        model_key: str,
        model_name: str,
        user_id: Optional[str] = None,
        webhook_key: Optional[str] = None,
        attr_info: Optional[List[Dict[str, Any]]] = None,
        **overrides: Any,
    ) -> Dict[str, Any]:
        """触发建模请求，返回原始响应体。

        对应老代码 SimpleBuilderTester.send_build_request。
        """
        if not model_key:
            raise ValueError("model_key 不能为空")

        payload: Dict[str, Any] = {
            "userId": user_id or Config.BUILDER_USER_ID,
            "model_type": "f3d",
            "webhook_key": webhook_key or Config.BUILDER_WEBHOOK_KEY,
            "is_download_request": 0,
            "cache": 0,
            "is_ignore_release": 1,
            "dxfOfView": 0,
            "is_drawing": 0,
            "external_param": json.dumps(
                {
                    "productModelNumber": model_name,
                    "productCode": model_key,
                },
                ensure_ascii=False,
            ),
            "product_code": model_key,
        }
        if attr_info:
            payload["attr_info"] = attr_info

        payload.update(overrides)

        log.info(f"发送建模请求: {model_name} ({model_key})")
        body = self.post_json("auto_request_model", json_data=payload)

        if not body.get("data"):
            log.error(f"建模请求失败: code={body.get('code')}, msg={body.get('msg')}")
        return body

    @staticmethod
    def extract_mq_msg(body: Dict[str, Any]) -> Optional[str]:
        """从建模响应中取 data.mqMsg。"""
        return resolve_json_pointer(body, "/data/mqMsg")

# api/core/auth_manager.py
"""
认证管理器 - 专门负责 Token 的获取和刷新
"""

import time
import requests
from typing import Optional
from common.config.settings import Config
from common.utils.logger import log


class AuthManager:
    """认证管理器 - 只负责 Token 相关逻辑"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or Config.API_BASE_URL
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0
        self.logger = log

    def get_access_token(self) -> str:
        """获取有效的 access_token"""

        if self._access_token and not self._is_token_expired():
            self.logger.debug("使用缓存的 Access Token")
            return self._access_token

        self.logger.info("正在获取新的 Access Token...")
        self._fetch_new_token()
        return self._access_token

    def _fetch_new_token(self):
        """从服务器获取新的 token"""
        url = f"{self.base_url}{Config.TOKEN_URL}"
        params = {
            "app_id": Config.APP_ID,
            "app_secret": Config.APP_SECRET
        }

        response = requests.get(url, params=params, timeout=Config.API_TIMEOUT)

        if response.status_code != 200:
            raise Exception(f"获取 Token 失败: {response.status_code}")

        data = response.json()
        if data.get("code") != 200:
            raise Exception(f"业务错误: {data.get('msg')}")

        self._access_token = data["data"]["access_token"]
        expires_in = data["data"].get("expires_in", 7200)
        self._token_expiry = time.time() + expires_in - 60

        self.logger.info("✅ Access Token 获取成功")
        # 不要打印 Token 明文，避免泄漏到日志 / Allure
        return self._access_token

    def _is_token_expired(self) -> bool:
        """判断 token 是否过期"""
        return time.time() >= self._token_expiry

    def refresh(self):
        """强制刷新 token"""
        self._access_token = None
        return self.get_access_token()

    def get_auth_header(self) -> dict:
        """获取认证头"""
        """获取认证头（自动添加 Bearer 前缀）"""
        token = self.get_access_token()
        if not token:
            return {}

        # 如果 token 已经有 Bearer 前缀，直接使用
        if token.startswith("Bearer "):
            return {"Authorization": token}
        else:
            return {"Authorization": f"Bearer {token}"}

# api/endpoints/baidu_endpoints.py
"""
百度网页搜索接口封装

接口定义见 docs/api_specs/baidu_search.json：
    GET https://www.baidu.com/s?wd=<关键词>
    返回 text/html 页面（不是 JSON）

注意：
1. 这是第三方站点，请求必须带 auth=False，避免把 Forface 的 Bearer Token 发到 baidu.com。
2. 百度对非浏览器请求会 302 到 wappass 验证码页，因此要带浏览器 UA / Accept / Accept-Language。
"""
import time
from pathlib import Path
from typing import Dict

import requests

from common.config.settings import Config
from common.utils.data_utils.yaml_loader import load_config


BROWSER_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class BaiduEndpoints:
    """百度搜索端点（复用 APIContext 的 Session/重试/Allure，但不做 Forface 鉴权）"""

    def __init__(self, api_context=None, base_url: str = None):
        """
        Args:
            api_context: APIContext 对象
            base_url: 覆盖默认站点地址（可选）
        """
        if api_context is None:
            raise RuntimeError(
                "BaiduEndpoints 需要 APIContext，请通过 endpoints fixture 构造"
            )
        self.ctx = api_context

        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "api" / "data" / "api_config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        self.api_config = load_config(str(config_path))

        self.base_url = (base_url or self.api_config.get("baidu.base_url") or "").rstrip("/")
        if not self.base_url:
            raise ValueError("配置中未找到: baidu.base_url")

        # 首页预热是否已完成（拿到 BAIDUID 等 Cookie）
        self._warmed_up = False

    def _get_endpoint(self, key: str) -> str:
        """获取端点"""
        endpoint = self.api_config.get(key)
        if not endpoint:
            raise ValueError(f"配置中未找到: {key}")
        return endpoint

    def search(self, keyword: str, timeout: float = None,
               retries: int = 1) -> requests.Response:
        """关键词搜索

        Args:
            keyword: 搜索关键词（必传）
            timeout: 覆盖默认超时（可选）
            retries: 被反爬拦截后的重试次数（可选，默认 1）

        Returns:
            requests.Response: 百度搜索页面（text/html）

        Raises:
            ValueError: 关键词为空
            RuntimeError: 多次重试后仍被百度反爬拦截，返回验证码页
        """
        if not keyword or not str(keyword).strip():
            raise ValueError("搜索关键词不能为空")

        url = f"{self.base_url}{self._get_endpoint('baidu.search')}"
        params = {"wd": str(keyword).strip()}
        kwargs = {"timeout": timeout} if timeout is not None else {}
        self._warm_up(**kwargs)

        response = None
        for attempt in range(max(0, retries) + 1):
            response = self.ctx.get(
                url, params=params, headers=BROWSER_HEADERS, auth=False, **kwargs
            )
            if not self._is_blocked(response):
                return response
            if attempt < retries:
                # 触发反爬时等一会儿、刷新 Cookie 后再试
                time.sleep(2 * (attempt + 1))
                self._warm_up(force=True, **kwargs)

        self._ensure_not_blocked(response)
        return response

    def _warm_up(self, force: bool = False, **kwargs):
        """访问首页拿 BAIDUID 等 Cookie

        百度对没有 Cookie 的搜索请求更容易直接 302 到验证码页，
        预热一次能显著降低偶发拦截。
        """
        if self._warmed_up and not force:
            return
        try:
            self.ctx.get(
                f"{self.base_url}/", headers=BROWSER_HEADERS, auth=False, **kwargs
            )
            self._warmed_up = True
        except requests.RequestException:
            # 预热失败不阻塞正式搜索
            pass

    @staticmethod
    def _is_blocked(response: requests.Response) -> bool:
        """是否被反爬重定向到验证码页"""
        return "wappass.baidu.com" in response.url

    @staticmethod
    def _ensure_not_blocked(response: requests.Response):
        """识别百度的验证码页（直接请求触发反爬时会 302 到 wappass）"""
        if BaiduEndpoints._is_blocked(response):
            raise RuntimeError(
                "百度返回了验证码页（反爬拦截），请更换出口 IP 或降低请求频率后重试: "
                f"{response.url}"
            )

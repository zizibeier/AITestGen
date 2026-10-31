# api/core/api_context.py
"""
API上下文
继承 BaseContext，实现 API 特有的上下文管理
"""
import json
import time

import requests
import allure
from typing import Optional, Dict, Any, Callable, Union
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from api.core.auth_manager import AuthManager
from common.context.base_context import BaseContext
from common.config.settings import Config
from common.utils.logger import log
from common.utils.allure_helper import APIAllureHelper,StepHelper,AllureDynamicHelper

class APIContext(BaseContext):

    """
    API 上下文

    职责：
    1. 管理 HTTP Session（连接池、重试）
    2. 发送请求
    3. 记录请求历史
    4. 认证委托给 AuthManager
    """

    def __init__(self, base_url: str = None):
        super().__init__()
        #基础配置
        self.base_url = base_url or Config.API_BASE_URL
        self.timeout = Config.API_TIMEOUT
        #session管理
        self.session = None
        self._auth_token: Optional[str] = None
        #请求历史
        self._request_history: list = []
        self._last_request: Optional[Dict] = None
        self._last_response: Optional[requests.Response] = None
        # 初始化认证管理器
        self._auth_manager = AuthManager()

        #初始化allure
        self._allure_helper =APIAllureHelper()

        # 默认请求头
        self.default_headers = {
            "Accept": "application/json"
        }

        self.logger = log

    # ==================== 认证相关（委托给 AuthManager） ====================
    def get_access_token(self) -> str:
        """获取 access_token"""
        return self._auth_manager.get_access_token()

    def refresh_token(self):
        """刷新 token"""
        return self._auth_manager.refresh()

    def ensure_token(self):
        """确保 token 有效"""
        return self._auth_manager.get_access_token()

    def _get_auth_headers(self) -> dict:
        """获取认证头（自动确保 token 有效）"""
        return self._auth_manager.get_auth_header()


    # ==================== 实现 BaseContext 抽象方法 ====================

    def setup(self):
        """初始化 API 上下文"""
        self.logger.info("🚀 初始化 API 上下文")
        self._create_session()
        self.logger.info(f"✅ API 上下文初始化完成: {self.base_url}")
        return self

    def teardown(self):
        """清理 API 上下文"""
        self.logger.info("🧹 清理 API 上下文")
        if self.session:
            self.session.close()
            self.session = None
        self._request_history.clear()
        self._last_request = None
        self._last_response = None
        self.logger.info("✅ API 上下文清理完成")
        return self

    def get_session(self):
        """获取会话对象"""
        return self.session

    def navigate(self, url: str = None):
        """
        API 的 navigate 实际是设置 base_url
        """
        if url:
            self.base_url = url
            self.logger.info(f"切换 API 地址: {self.base_url}")
        return self

    def wait_for(self, condition: Union[str, Callable], timeout: int = None):
        """
        API 的等待条件

        Args:
            condition: 可以是 URL，也可以是返回 bool 的函数
            timeout: 超时时间（秒）
        """
        if timeout is None:
            timeout = Config.API_TIMEOUT

        if isinstance(condition, str):
            # 等待某个接口返回特定状态
            return self._wait_for_endpoint(condition, timeout)
        elif callable(condition):
            # 轮询执行条件函数
            import time
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    if condition():
                        return True
                except Exception as e:
                    self.logger.debug(f"条件检查异常: {e}")
                time.sleep(0.5)
            raise TimeoutError(f"等待条件超时 ({timeout}秒)")
        else:
            raise ValueError(f"不支持的 condition 类型: {type(condition)}")

    # ==================== Session 管理 ====================

    def _create_session(self):
        """创建带重试机制的 session"""
        self.session = requests.Session()

        # 设置重试策略
        retry_strategy = Retry(
            total=Config.API_MAX_RETRIES,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 设置默认请求头
        self.session.headers.update(self.default_headers)

    def set_header(self, key: str, value: str):
        """设置请求头"""
        self.session.headers.update({key: value})
        self.logger.debug(f"设置请求头: {key}:{value}")
        return self
    def set_headers(self, headers: Dict[str, str]):
        """批量设置请求头"""
        self.session.headers.update(headers)
        self.logger.debug(f"批量设置请求头: {list(headers.keys())}")
        return self

    def set_auth_token(self, token: str, token_type: str = "Bearer "):
        """设置认证 token"""
        self._auth_token = token
        self.session.headers.update({
            "Authorization": f"{token_type} {token}"
        })
        self.logger.info("✅ 认证 token 已设置")
        return self

    def clear_auth_token(self):
        """清除认证 token"""
        self._auth_token = None
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]
        self.logger.info("认证 token 已清除")
        return self

    # ==================== 请求方法 ====================
    def request(
            self,
            method: str,
            endpoint: str,
            files: Dict = None,
            data: Dict = None,
            json_data: Dict = None,
            params: Dict = None,
            headers: Dict = None,
            auth: bool = True,
            **kwargs
    ) -> requests.Response:
        """
        发送 HTTP 请求（支持文件上传）

        Args:
            method: HTTP 方法
            endpoint: 接口路径，也可以是完整的绝对 URL（用于第三方站点）
            files: 文件参数（用于上传）
            data: 表单数据
            json_data: JSON 数据
            params: URL 参数
            headers: 额外请求头
            auth: 是否自动附加认证头，默认 True；访问第三方接口时传 False，
                  避免把 Forface 的 Bearer Token 发送到外部站点
        """
        if endpoint.startswith(("http://", "https://")):
            url = endpoint
        else:
            url = f"{self.base_url}{endpoint}"

        # 合并请求头
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)

        # 文件上传时移除 Content-Type，让 requests 自动处理
        if files:
            request_headers.pop("Content-Type", None)

        # 自动添加认证头（跳过登录接口；第三方接口传 auth=False）
        if auth and Config.TOKEN_URL not in endpoint:
            auth_headers = self._get_auth_headers()
            # print(f"🔐 认证头: {auth_headers}")  # 调试打印

            request_headers.update(auth_headers)
        elif not auth:
            # 第三方接口：即使 session 里残留过 Authorization，也不能带出去
            request_headers.pop("Authorization", None)

        # 设置超时
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout

        # 记录请求信息
        self._last_request = {
            "method": method,
            "url": url,
            "headers": dict(request_headers),
            "params": params,
            "has_files": files is not None
        }

        self.logger.info(f"📤 {method} {endpoint}")

        # 发送请求
        start_time = time.time()
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json_data,
            files=files,
            headers=request_headers,
            **kwargs
        )
        elapsed_ms = (time.time() - start_time) * 1000

        # 记录响应
        self._last_response = response
        self._request_history.append({
            "request": self._last_request,
            "response": response,
            "elapsed_ms": elapsed_ms
        })

        self.logger.info(f"📥 {response.status_code} ({elapsed_ms:.0f}ms)")

        # Allure 附件
        self._attach_to_allure(method, url, request_headers, params, data, json_data, files, response, elapsed_ms)

        return response

    def _attach_to_allure(self, method, url, headers, params, data, json_data, files, response, elapsed_ms):
        """附加到 Allure 报告"""
        try:
            # 请求信息
            request_info = f"{method} {url}\n\n"
            if headers:
                request_info += f"Headers:\n{json.dumps(dict(headers), indent=2, ensure_ascii=False)}\n\n"
            if params:
                request_info += f"Params:\n{json.dumps(params, indent=2, ensure_ascii=False)}\n\n"
            if data:
                request_info += f"Data:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n\n"
            if json_data:
                request_info += f"JSON:\n{json.dumps(json_data, indent=2, ensure_ascii=False)}\n\n"
            if files:
                request_info += f"Files: {list(files.keys())}\n\n"

            allure.attach(request_info, name="请求信息", attachment_type=allure.attachment_type.TEXT)

            # 响应信息
            response_info = f"Status: {response.status_code}\nTime: {elapsed_ms:.0f}ms\n\n"
            try:
                response_info += f"Body:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)[:2000]}"
            except:
                response_info += f"Body:\n{response.text[:2000]}"

            allure.attach(response_info, name="响应信息", attachment_type=allure.attachment_type.TEXT)
        except Exception as e:
            self.logger.debug(f"Allure 附件失败: {e}")

    def _merge_headers(self, extra_headers: Dict[str, str]) -> Dict[str, str]:
        if extra_headers:
            headers = self.session.headers.copy()
            headers.update(extra_headers)
            return headers
        return self.session.headers

    # ==================== 便捷请求方法 ====================

    def get(self, endpoint: str, params: Dict = None, headers: Dict = None,
            auth: bool = True, **kwargs) -> requests.Response:
        """GET 请求（auth=False 时不附加认证头，用于第三方接口）"""
        return self.request("GET", endpoint, params=params, headers=headers, auth=auth, **kwargs)

    def post(self, endpoint: str, data: Dict = None, json: Dict = None, headers: Dict = None,
             **kwargs) -> requests.Response:
        """POST 请求（JSON 或表单）"""
        return self.request("POST", endpoint, data=data, json_data=json, headers=headers, **kwargs)

    def post_file(self, endpoint: str, file_path: str, data: Dict = None, headers: Dict = None,
                  **kwargs) -> requests.Response:
        """
        文件上传 POST 请求

        Args:
            endpoint: 接口路径
            file_path: 文件路径
            data: 表单数据
            headers: 额外请求头
        """
        import os
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        files = {'file': (os.path.basename(file_path), open(file_path, 'rb'), 'application/octet-stream')}

        response = self.request("POST", endpoint, files=files, data=data, headers=headers, **kwargs)

        # 关闭文件
        files['file'][1].close()

        return response

    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """PUT 请求"""
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """DELETE 请求"""
        return self.request("DELETE", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs) -> requests.Response:
        """PATCH 请求"""
        return self.request("PATCH", endpoint, **kwargs)


    # ==================== 等待方法 ====================

    def _wait_for_endpoint(self, url: str, timeout: int) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.get(url)
                if response.status_code < 500:
                    return True
            except:
                pass
            time.sleep(1)
        raise TimeoutError(f"接口 {url} 在 {timeout} 秒内不可访问")

    def _wait_for_condition(self, condition: Callable, timeout: int) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if condition():
                    return True
            except:
                pass
            time.sleep(0.5)
        raise TimeoutError(f"条件在 {timeout} 秒内未满足")

    # ==================== 历史查询 ====================

    def get_last_request(self) -> Optional[Dict]:
        return self._last_request

    def get_last_response(self) -> Optional[requests.Response]:
        return self._last_response

    def get_last_response_json(self) -> Optional[Dict]:
        if self._last_response:
            try:
                return self._last_response.json()
            except:
                return None
        return None

    def clear_history(self):
        self._request_history.clear()
        self._last_request = None
        self._last_response = None

        # ==================== 健康检查 ====================

    def health_check(self, endpoint: str = "/health") -> bool:
        try:
            response = self.get(endpoint, timeout=5)
            return response.status_code == 200
        except:
            return False
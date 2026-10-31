# common/assertions/api_assertion.py
import allure
import json
from typing import Any, Dict, List, Optional
from allure_commons.types import AttachmentType
from requests import Response

from common.assertions.base_assertion import BaseAssertion
from common.utils.logger import log


class APIAssertion(BaseAssertion):
    """
    API 专用断言类
    继承 BaseAssertion，扩展 HTTP 和 JSON 相关断言
    """

    def assert_status_code(self, response: Response, expected_code: int, message: str = None):
        """断言 HTTP 状态码"""
        msg = message or f"状态码断言失败: 期望 {expected_code}, 实际 {response.status_code}"
        self.assert_equal(response.status_code, expected_code, msg)

        # 附加到 Allure
        allure.attach(
            f"状态码: {response.status_code} (期望: {expected_code})",
            name="状态码验证",
            attachment_type=AttachmentType.TEXT
        )

    def assert_success(self, response: Response, message: str = None):
        """断言请求成功 (2xx)"""
        msg = message or f"请求失败，状态码: {response.status_code}"
        self.assert_true(200 <= response.status_code < 300, msg)

    def assert_client_error(self, response: Response, message: str = None):
        """断言客户端错误 (4xx)"""
        msg = message or f"期望客户端错误(4xx)，实际状态码: {response.status_code}"
        self.assert_true(400 <= response.status_code < 500, msg)

    def assert_server_error(self, response: Response, message: str = None):
        """断言服务端错误 (5xx)"""
        msg = message or f"期望服务端错误(5xx)，实际状态码: {response.status_code}"
        self.assert_true(500 <= response.status_code < 600, msg)

    def assert_json_path(self, response: Response, json_path: str, expected_value: Any, message: str = None):
        """断言 JSON 路径的值"""
        actual_value = self._get_json_path_value(response.json(), json_path)
        msg = message or f"JSON路径 '{json_path}' 的值应为 {expected_value}, 实际为 {actual_value}"
        self.assert_equal(actual_value, expected_value, msg)

        # 附加到 Allure
        allure.attach(
            f"JSON路径: {json_path}\n期望: {expected_value}\n实际: {actual_value}",
            name=f"JSON断言 - {json_path}",
            attachment_type=AttachmentType.TEXT
        )

    def assert_json_contains(self, response: Response, key: str, message: str = None):
        """断言 JSON 包含指定 key"""
        msg = message or f"JSON 应包含 key: '{key}'"
        self.assert_true(key in response.json(), msg)

    def assert_json_not_contains(self, response: Response, key: str, message: str = None):
        """断言 JSON 不包含指定 key"""
        msg = message or f"JSON 不应包含 key: '{key}'"
        self.assert_true(key not in response.json(), msg)

    def assert_json_length(self, response: Response, key_path: str, expected_length: int, message: str = None):
        """断言 JSON 数组长度"""
        data = response.json()
        value = self._get_json_path_value(data, key_path) if key_path else data

        if isinstance(value, list):
            msg = message or f"数组 '{key_path}' 长度应为 {expected_length}, 实际 {len(value)}"
            self.assert_equal(len(value), expected_length, msg)
        else:
            self.assert_true(False, f"'{key_path}' 不是数组")

    def assert_response_header(self, response: Response, header_name: str, expected_value: str = None):
        """断言响应头"""
        actual_value = response.headers.get(header_name)
        if expected_value:
            self.assert_equal(actual_value, expected_value, f"响应头 '{header_name}' 验证失败")
        else:
            self.assert_is_not_none(actual_value, f"响应头 '{header_name}' 不存在")

    def assert_response_time(self, response: Response, max_ms: int):
        """断言响应时间"""
        if hasattr(response, 'elapsed'):
            elapsed_ms = response.elapsed.total_seconds() * 1000
            self.assert_less(elapsed_ms, max_ms, f"响应时间 {elapsed_ms:.2f}ms 超过阈值 {max_ms}ms")

    def assert_schema(self, response: Response, schema: Dict):
        """断言 JSON Schema（需要安装 jsonschema）"""
        try:
            from jsonschema import validate, ValidationError
            validate(instance=response.json(), schema=schema)
            log.success("✅ JSON Schema 验证通过")
        except ValidationError as e:
            self.assert_true(False, f"JSON Schema 验证失败: {e.message}")
        except ImportError:
            log.warning("jsonschema 未安装，跳过 Schema 验证")

    def assert_business_code(self, response: Response, expected_code: int, code_path: str = "code"):
        """断言业务状态码（常见的 {code: 0, data: {}} 格式）"""
        actual_code = self._get_json_path_value(response.json(), code_path)
        self.assert_equal(actual_code, expected_code, f"业务状态码验证失败")

    # ==================== 私有方法 ====================

    def _get_json_path_value(self, data: Any, path: str) -> Any:
        """简化版 JSON 路径取值"""
        if not path:
            return data

        keys = path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list):
                if key.isdigit():
                    value = value[int(key)]
                else:
                    # 处理数组通配符，这里简化处理
                    return [item.get(key) for item in value if isinstance(item, dict)]
            else:
                return None

        return value
# common/utils/allure_helper.py
"""
Allure 报告辅助类
统一管理 Allure 附件和报告生成
"""

import json
import allure
from typing import Any, Dict, Optional, Union
from pathlib import Path
from datetime import datetime

from allure_commons.types import AttachmentType
from requests import Response


class AllureHelper:
    """
    Allure 报告辅助类

    提供统一的 Allure 附件方法，API 和 UI 测试都可以使用
    """

    @staticmethod
    def attach_text(content: str, name: str = "text"):
        """
        附加文本内容

        Args:
            content: 文本内容
            name: 附件名称
        """
        allure.attach(content, name=name, attachment_type=AttachmentType.TEXT)

    @staticmethod
    def attach_json(data: Union[Dict, list, str], name: str = "json"):
        """
        附加 JSON 内容

        Args:
            data: JSON 数据（字典、列表或 JSON 字符串）
            name: 附件名称
        """
        if isinstance(data, (dict, list)):
            content = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            content = data
        allure.attach(content, name=name, attachment_type=AttachmentType.JSON)

    @staticmethod
    def attach_html(content: str, name: str = "html"):
        """附加 HTML 内容"""
        allure.attach(content, name=name, attachment_type=AttachmentType.HTML)

    @staticmethod
    def attach_xml(content: str, name: str = "xml"):
        """附加 XML 内容"""
        allure.attach(content, name=name, attachment_type=AttachmentType.XML)

    @staticmethod
    def attach_csv(content: str, name: str = "csv"):
        """附加 CSV 内容"""
        allure.attach(content, name=name, attachment_type=AttachmentType.CSV)

    @staticmethod
    def attach_image(image_bytes: bytes, name: str = "screenshot", format: str = "png"):
        """
        附加图片

        Args:
            image_bytes: 图片字节数据
            name: 附件名称
            format: 图片格式 (png, jpg, etc.)
        """
        allure.attach(image_bytes, name=name, attachment_type=AttachmentType.PNG)

    @staticmethod
    def attach_file(file_path: Union[str, Path], name: str = None):
        """
        附加文件

        Args:
            file_path: 文件路径
            name: 附件名称（默认使用文件名）
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, 'rb') as f:
            content = f.read()

        attachment_name = name or file_path.name
        allure.attach(content, name=attachment_name, attachment_type=AttachmentType.TEXT)

    @staticmethod
    def attach_log(message: str, level: str = "INFO"):
        """
        附加日志

        Args:
            message: 日志消息
            level: 日志级别
        """
        content = f"[{level}] {message}"
        allure.attach(content, name=f"log_{datetime.now().strftime('%H%M%S')}",
                      attachment_type=AttachmentType.TEXT)


class APIAllureHelper:
    """
    API 专用的 Allure 辅助类
    用于附加 API 请求和响应信息
    """

    def __init__(self, request_count: int = 0):
        self.request_count = request_count

    def attach_request(self, method: str, url: str, headers: Dict[str, str],
                       params: Optional[Dict], body: Any, status_code: int,
                       elapsed_ms: float):
        """
        附加 API 请求信息

        Args:
            method: HTTP 方法
            url: 请求 URL
            headers: 请求头
            params: 请求参数
            body: 请求体
            status_code: 响应状态码
            elapsed_ms: 耗时（毫秒）
        """
        self.request_count += 1

        # 脱敏处理
        safe_headers = self._sanitize_headers(headers)

        request_text = f"""
        **Request #{self.request_count}**
        
        **Method:** {method}
        **URL:** {url}
        **Status:** {status_code}
        **Time:** {elapsed_ms:.0f}ms
        
        **Headers:**
        ```json
        {json.dumps(safe_headers, indent=2, ensure_ascii=False)}
        {json.dumps(params, indent=2, ensure_ascii=False) if params else 'null'}
        {self._format_json(body)}
        """
        allure.attach(
        request_text,
        name=f"📤 Request #{self.request_count}",
        attachment_type=AttachmentType.TEXT
        )

    def attach_response(self, status_code: int, reason: str, headers: Dict[str, str], body: Any, elapsed_ms: float):
        """附加 API 响应信息"""

        response_text = f"""
        Response #{self.request_count}
        
        Status Code: {status_code}
        Reason: {reason}
        Time: {elapsed_ms:.0f}ms
        
        Response Headers:
        {json.dumps(dict(headers), indent=2, ensure_ascii=False)}
        {self._format_json(body)}
        """
        allure.attach(
            response_text,
            name=f"📥 Response #{self.request_count}",
            attachment_type=AttachmentType.TEXT
        )


    def attach_request_response(self, method: str, url: str, headers: Dict[str, str],
                                params: Optional[Dict], request_body: Any,
                                response: Response, elapsed_ms: float):
        """同时附加请求和响应信息"""

        self.attach_request(method, url, headers, params, request_body,
                            response.status_code, elapsed_ms)
        self.attach_response(response.status_code, response.reason,
                             response.headers, response.text, elapsed_ms)


    @staticmethod
    def _sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """脱敏处理请求头"""


        sensitive_keys = ['Authorization', 'Cookie', 'Set-Cookie', 'X-Auth-Token', 'X-API-Key']
        safe_headers = headers.copy()

        for key in sensitive_keys:
            if key in safe_headers:
                value = safe_headers[key]
                if len(value) > 10:
                    safe_headers[key] = value[:10] + "..."
                else:
                    safe_headers[key] = "***"

        return safe_headers


    @staticmethod
    def _format_json(data: Any) -> str:
        """格式化 JSON 数据"""


        if not data:
            return "null"

        try:
            if isinstance(data, str):
                obj = json.loads(data)
                return json.dumps(obj, indent=2, ensure_ascii=False)
            else:
                return json.dumps(data, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            return str(data)[:2000]


    def reset_counter(self):
        """重置请求计数器"""
        self.request_count = 0


class UIAllureHelper:
    """
    UI 专用的 Allure 辅助类
    用于附加 UI 测试的截图、页面源码等信息
    """


    @staticmethod
    def attach_screenshot(screenshot_bytes: bytes, name: str = "screenshot"):
        """附加截图"""

        allure.attach(
            screenshot_bytes,
            name=f"📸 {name}",
            attachment_type=AttachmentType.PNG
        )


    @staticmethod
    def attach_page_source(html: str, name: str = "page_source"):
        """附加页面源码"""
        allure.attach(
            html,
            name=f"📄 {name}",
            attachment_type=AttachmentType.HTML
        )


    @staticmethod
    def attach_element_screenshot(screenshot_bytes: bytes, element_name: str):
        """附加元素截图"""
        allure.attach(
            screenshot_bytes,
            name=f"🎯 Element: {element_name}",
            attachment_type=AttachmentType.PNG
        )


    @staticmethod
    def attach_console_logs(logs: list, name: str = "console_logs"):
        """附加浏览器控制台日志"""
        content = "\n".join([f"[{log.get('type', 'log')}] {log.get('text', '')}"
                             for log in logs])
        allure.attach(content, name=name, attachment_type=AttachmentType.TEXT)


    @staticmethod
    def attach_performance_metrics(metrics: Dict[str, Any], name: str = "performance"):
        """附加性能指标"""
        content = json.dumps(metrics, indent=2, ensure_ascii=False)
        allure.attach(content, name=f"⚡ {name}", attachment_type=AttachmentType.JSON)


class StepHelper:
    """步骤辅助类，用于记录测试步骤"""

    @staticmethod
    def step(title: str):
        """步骤装饰器"""
        def decorator(func):
            def wrapper(args, **kwargs):

                with allure.step(title):
                    return func(args, **kwargs)

            return wrapper
        return decorator


    @staticmethod
    def log_step(message: str):
        """记录步骤"""
        allure.step(message)


    @staticmethod
    def log_step_with_attachment(message: str, content: str, name: str = "detail"):
        """记录带附件的步骤"""
        with allure.step(message):
            allure.attach(content, name=name, attachment_type=AttachmentType.TEXT)


class AllureDynamicHelper:
    """动态设置 Allure 报告信息"""

    @staticmethod
    def set_title(title: str):
        """设置测试标题"""
        allure.dynamic.title(title)

    @staticmethod
    def set_description(description: str):
        """设置测试描述"""
        allure.dynamic.description(description)


    @staticmethod
    def set_feature(feature: str):
        """设置功能模块"""
        allure.dynamic.feature(feature)


    @staticmethod
    def set_story(story: str):
        """设置用户故事"""
        allure.dynamic.story(story)


    @staticmethod
    def set_severity(severity: str):
        """设置严重程度"""
        severity_map = {
            "critical": allure.severity_level.CRITICAL,
            "high": allure.severity_level.HIGH,
            "normal": allure.severity_level.NORMAL,
            "low": allure.severity_level.LOW,
            "trivial": allure.severity_level.TRIVIAL
        }
        if severity in severity_map:
            allure.dynamic.severity(severity_map[severity])

    @staticmethod
    def set_tag(tag: str):
        """设置标签"""
        allure.dynamic.tag(tag)


    @staticmethod
    def set_tags(tags: list):
        """批量设置标签"""
        for tag in tags:
            allure.dynamic.tag(tag)


    @staticmethod
    def set_link(name: str, url: str, link_type: str = "link"):
        """设置链接"""
        if link_type == "link":
            allure.dynamic.link(url, name=name)
        elif link_type == "issue":
            allure.dynamic.issue(url, name=name)
        elif link_type == "testcase":
            allure.dynamic.testcase(url, name=name)

    @staticmethod
    def set_parameters(parameters: Dict[str, Any]):
        """设置参数"""
        for name, value in parameters.items():
            allure.dynamic.parameter(name, str(value))


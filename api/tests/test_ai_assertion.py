# api/tests/test_ai_assertion.py
"""
AI 断言自测

- 离线用例：不访问网络，验证返回解析、脱敏、失败抛出与软断言收集
- 在线用例：未配置 AI_ASSERT_API_KEY / CEREBRAS_API_KEY 时自动跳过
"""
import allure
import pytest

from common.assertions.ai_assertion import (
    AIAssertion,
    AIAssertionError,
    sanitize_sensitive,
)
from common.assertions.base_assertion import BaseAssertion
from common.base_test import BaseTest
from api.core.api_base_test import APIBaseTest


class _FakeResponse:
    """模拟 OpenAI 兼容接口的响应"""

    def __init__(self, content: str, status_code: int = 200,
                 body=None, headers=None):
        self.status_code = status_code
        self.text = content
        self._content = content
        self._body = body
        self.headers = headers or {}

    def json(self):
        if self._body is not None:
            return self._body
        return {"choices": [{"message": {"content": self._content}}]}


@allure.epic("测试框架")
@allure.feature("AI 断言")
class TestAIAssertionOffline:
    """不依赖网络的 AI 断言测试"""

    @allure.story("返回解析")
    def test_parse_verdict_from_markdown_fence(self):
        """模型返回 ```json 代码块时也能解析"""
        assertion = AIAssertion(api_key="offline-key")
        result = assertion._parse_verdict(
            '```json\n{"passed": true, "reason": "fileId 非空", "confidence": 0.95}\n```'
        )

        assert result.passed is True
        assert result.reason == "fileId 非空"
        assert result.confidence == pytest.approx(0.95)
        assert bool(result) is True

    @allure.story("返回解析")
    def test_parse_verdict_with_surrounding_text(self):
        """模型在 JSON 前后输出多余文字时仍能提取判定"""
        assertion = AIAssertion(api_key="offline-key")
        result = assertion._parse_verdict(
            '判定如下：{"passed": false, "reason": "缺少 fileId", "confidence": 0.8} 以上。'
        )

        assert result.passed is False
        assert result.reason == "缺少 fileId"

    @allure.story("返回解析")
    def test_parse_verdict_with_think_block(self):
        """推理模型先输出 <think>（内含花括号）再输出判定时仍能解析"""
        assertion = AIAssertion(api_key="offline-key")
        result = assertion._parse_verdict(
            '<think>Actual object {"x": 1} is not a number. Output JSON only.</think>\n\n'
            '{"passed": false, "reason": "实际是对象而非数字", "confidence": 0.9}'
        )

        assert result.passed is False
        assert result.reason == "实际是对象而非数字"
        assert result.confidence == pytest.approx(0.9)

    @allure.story("返回解析")
    def test_parse_invalid_content_raises(self):
        """非 JSON 返回应抛出 AIAssertionError"""
        assertion = AIAssertion(api_key="offline-key")

        with pytest.raises(AIAssertionError, match="不是可解析的 JSON"):
            assertion._parse_verdict("我认为可以通过")

    @allure.story("敏感信息脱敏")
    def test_sanitize_sensitive_fields(self):
        """token/secret/password 等字段不应发送给模型"""
        payload = {
            "code": 200,
            "accessToken": "real-token",
            "data": {
                "appSecret": "real-secret",
                "password": "real-password",
                "fileId": "file-123",
            },
            "items": [{"api_key": "real-key"}],
        }

        cleaned = sanitize_sensitive(payload)

        assert cleaned["accessToken"] == "***"
        assert cleaned["data"]["appSecret"] == "***"
        assert cleaned["data"]["password"] == "***"
        assert cleaned["items"][0]["api_key"] == "***"
        assert cleaned["data"]["fileId"] == "file-123"
        assert cleaned["code"] == 200

    @allure.story("敏感信息脱敏")
    def test_sanitize_sensitive_in_plain_text(self):
        """纯文本中的 token 与 Bearer 凭据也应脱敏"""
        text = 'accessToken=abc123, Authorization: Bearer sk-real-key'

        cleaned = sanitize_sensitive(text)

        assert "abc123" not in cleaned
        assert "sk-real-key" not in cleaned
        assert "accessToken=***" in cleaned

    @allure.story("断言通过")
    def test_assert_that_passes(self, monkeypatch):
        """模型判定通过时不抛异常"""
        monkeypatch.setattr(
            "common.assertions.ai_assertion.requests.post",
            lambda *args, **kwargs: _FakeResponse(
                '{"passed": true, "reason": "fileId 非空", "confidence": 0.99}'
            ),
        )
        assertion = AIAssertion(api_key="offline-key")

        result = assertion.assert_that(
            expected="code 为 200 且 data.fileId 非空",
            actual={"code": 200, "data": {"fileId": "file-123"}},
            attach=False,
        )

        assert result.passed is True

    @allure.story("断言失败")
    def test_assert_that_raises_on_failed_verdict(self, monkeypatch):
        """模型判定不通过时抛出 AIAssertionError，并带上模型理由"""
        monkeypatch.setattr(
            "common.assertions.ai_assertion.requests.post",
            lambda *args, **kwargs: _FakeResponse(
                '{"passed": false, "reason": "缺少 fileId", "confidence": 0.9}'
            ),
        )
        assertion = AIAssertion(api_key="offline-key")

        with pytest.raises(AIAssertionError, match="缺少 fileId"):
            assertion.assert_that(
                expected="code 为 200 且 data.fileId 非空",
                actual={"code": 200, "data": {}},
                attach=False,
            )

    @allure.story("未配置")
    def test_missing_api_key_raises_config_error(self):
        """未配置 Key 时给出明确的配置错误"""
        assertion = AIAssertion(api_key="")

        with pytest.raises(AIAssertionError, match="AI_ASSERT_API_KEY"):
            assertion.judge("code 为 200", {"code": 200})

    @allure.story("软断言")
    def test_soft_assert_ai_collects_error(self, monkeypatch):
        """软 AI 断言失败只记录，由 assert_all() 统一抛出"""
        monkeypatch.setattr(
            "common.assertions.ai_assertion.requests.post",
            lambda *args, **kwargs: _FakeResponse(
                '{"passed": false, "reason": "状态不是 success", "confidence": 0.9}'
            ),
        )
        assertion = BaseAssertion()
        assertion._ai = AIAssertion(api_key="offline-key")

        assert assertion.soft_assert_ai("status 为 success", {"status": "failed"}) is False

        with pytest.raises(AssertionError, match="软断言失败"):
            assertion.assert_all()


@allure.epic("测试框架")
@allure.feature("AI 断言")
class TestAIAssertionIntegration(APIBaseTest):
    """验证 BaseTest / APIBaseTest 的代理链路（不访问网络）"""

    def setup_method(self):
        super().setup_method()
        # 注入离线 Key，避免依赖真实环境变量
        self.assertion._ai = AIAssertion(api_key="offline-key")

    @allure.story("BaseTest 代理")
    def test_assert_ai_via_base_test(self, monkeypatch):
        """self.assert_ai 能正确代理到 AIAssertion"""
        monkeypatch.setattr(
            "common.assertions.ai_assertion.requests.post",
            lambda *args, **kwargs: _FakeResponse(
                '{"passed": true, "reason": "code 为 200", "confidence": 0.99}'
            ),
        )

        assert self.assert_ai("code 为 200", {"code": 200}) is True

    @allure.story("APIBaseTest 代理")
    def test_assert_ai_response_via_api_base_test(self, monkeypatch):
        """self.assert_ai_response 能提取响应体并交给 AI 判断"""
        monkeypatch.setattr(
            "common.assertions.ai_assertion.requests.post",
            lambda *args, **kwargs: _FakeResponse(
                '{"passed": true, "reason": "fileId 非空", "confidence": 0.95}'
            ),
        )
        response = _FakeResponse(
            content="",
            body={"code": 200, "data": {"fileId": "file-123"}},
            headers={"Content-Type": "application/json"},
        )

        assert self.assert_ai_response(
            response, "code 为 200 且 data.fileId 非空"
        ) is True


@allure.epic("测试框架")
@allure.feature("AI 断言")
class TestAIAssertionLive(BaseTest):
    """真实调用大模型的冒烟用例（未配置时跳过）"""

    @pytest.mark.skipif(
        not AIAssertion.is_configured(),
        reason="未配置 AI_ASSERT_API_KEY / CEREBRAS_API_KEY",
    )
    @allure.story("语义断言")
    def test_ai_assertion_via_base_test(self):
        """通过 BaseTest.assert_ai 调用真实模型完成一次语义断言"""
        self.assert_ai(
            "结果表示上传成功：code 等于 200，并且 data.fileId 非空",
            {"code": 200, "data": {"fileId": "file-123", "status": "success"}},
        )

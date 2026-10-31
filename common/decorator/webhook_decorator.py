# common/webhook_decorator.py
"""
Webhook 装饰器 - 只负责监听，不查配置
"""

import functools
from typing import Union, List


def wait_for_webhook(
        events: Union[str, List[str]],  # 事件 ID 或事件 ID 列表
        timeout: int = 180
):
    """
    装饰器：等待 Webhook 回调

    Args:
        events: 单个事件 ID 或事件 ID 列表
        timeout: 超时时间（秒）

    使用示例:
        @wait_for_webhook("analysis.costing.finished")
        def test(self):
            return self.upload()

        @wait_for_webhook(["analysis.model.uploaded", "analysis.model.analyzed"])
        def test(self):
            return self.upload()
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # 1. 执行上传，获取 file_id
            upload_result = func(self, *args, **kwargs)

            if isinstance(upload_result, dict):
                file_id = upload_result.get('file_id')
            else:
                file_id = upload_result

            if not file_id:
                raise ValueError("上传结果中没有 file_id")

            # 2. 等待 Webhook
            from common.utils.webhook_utils.webhook_listener import WebhookListener
            from common.config.settings import Config

            listener = WebhookListener(Config.WEBHOOK_BASE_URL)
            listener.reset()

            # 判断是单个事件还是多个事件
            if isinstance(events, str):
                # 单个事件
                record, result = listener.wait_for_specific_event(
                    file_id=file_id,
                    event_id=events,
                    timeout=timeout
                )
                assert record is not None, f"未收到事件: {events}"

                # 结构校验
                if result and not result.is_first:
                    assert result.is_same, f"结构不一致: {result.event_id}"

                return {
                    'upload_result': upload_result,
                    'webhook_record': record,
                    'compare_result': result
                }
            else:
                # 多个事件
                records, results = listener.wait_for_id(
                    file_id=file_id,
                    expected_events=events,
                    timeout=timeout
                )

                # 校验所有期望事件都收到了
                received_events = [r.event_id for r in records]
                for expected in events:
                    assert expected in received_events, f"未收到事件: {expected}"

                # 结构校验
                for result in results:
                    if not result.is_first and not result.is_same:
                        raise AssertionError(f"结构不一致: {result.event_id}")

                return {
                    'upload_result': upload_result,
                    'webhook_records': records,
                    'compare_results': results
                }

        return wrapper

    return decorator
# common/webhook_listener.py
import requests
import time
import json
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class WebhookRecord:
    """Webhook 记录"""
    event_id: str  # 实际事件，如 analysis.costing.finished
    file_id: str  # 文件 ID
    payload: dict  # payload 数据
    raw_data: dict  # 原始数据


class WebhookListener:
    """Webhook 监听器"""

    def __init__(self, base_url: str = "http://47.94.122.228:5000"):
        self.base_url = base_url
        self._last_total = 0

    def _extract_file_id(self, data: dict) -> str:
        """从回调数据中提取文件 ID"""
        # 实际路径：payload.data.id
        payload = data.get('payload', {})
        data_obj = payload.get('data', {})
        return data_obj.get('id', '')

    def _extract_event_id(self, data: dict) -> str:
        """从回调数据中提取事件 ID"""
        # 实际路径：payload.serviceInfo.event
        payload = data.get('payload', {})
        service_info = payload.get('serviceInfo', {})
        return service_info.get('event', '')

    def _get_new_webhooks(self) -> List[WebhookRecord]:
        """获取所有新 webhook"""
        try:
            resp = requests.get(f"{self.base_url}/history", timeout=10)
            data = resp.json()
        except Exception as e:
            print(f"获取 Webhook 历史失败: {e}")
            return []

        total = data.get('total', 0)

        if total <= self._last_total:
            return []

        records = []
        for raw in data.get('records', [])[self._last_total:]:
            body = raw.get('body', '{}')
            try:
                json_data = json.loads(body)
                records.append(WebhookRecord(
                    event_id=self._extract_event_id(json_data),
                    file_id=self._extract_file_id(json_data),
                    payload=json_data.get('payload', {}),
                    raw_data=json_data
                ))
            except Exception as e:
                print(f"解析失败: {e}")
                pass

        self._last_total = total
        return records

    def wait_for_event(self, event_id: str, file_id: str = None, timeout: int = 60) -> Optional[WebhookRecord]:
        """
        等待指定事件

        Args:
            event_id: 事件 ID，如 "analysis.costing.finished"
            file_id: 可选，指定文件 ID
            timeout: 超时时间（秒）
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            for record in self._get_new_webhooks():
                if record.event_id == event_id:
                    if file_id is None or record.file_id == file_id:
                        return record
            time.sleep(1)
        return None

    def wait_for_file_complete(self, file_id: str, timeout: int = 120) -> Optional[WebhookRecord]:
        """等待指定文件定价完成"""
        return self.wait_for_event("analysis.costing.finished", file_id=file_id, timeout=timeout)

    def reset(self):
        """重置计数器"""
        self._last_total = 0


# 快速测试
if __name__ == "__main__":
    listener = WebhookListener()

    # 等待定价完成事件
    result = listener.wait_for_event("analysis.costing.finished", timeout=30)

    if result:
        print(f"收到事件: {result.event_id}")
        print(f"文件 ID: {result.file_id}")
        print(f"文件名: {result.payload.get('data', {}).get('fileName')}")
    else:
        print("未收到事件")
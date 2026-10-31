# common/webhook_listener.py
import requests
import time
import json
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
from common.utils.webhook_utils.webhook_record import save_event, get_event
from common.utils.structure_validator import StructureValidator, CompareResult


@dataclass
class WebhookRecord:
    event_id: str
    file_id: str
    file_name: str
    payload: dict
    raw_data: dict
    timestamp: str


@dataclass
class EventCompareResult:
    event_id: str
    is_first: bool
    is_same: bool
    compare_result: Optional[CompareResult]
    record: WebhookRecord


class WebhookListener:
    """Webhook 监听器（从 Redis 读取）"""

    def __init__(self, webhook_server_url: str = "http://47.94.122.228:5000"):
        self.webhook_server_url = webhook_server_url
        self.validator = StructureValidator()
        self._last_event_count = {}  # 记录每个 file_id 已处理的事件数

    # ========== 数据提取 ==========

    def _extract_event_id(self, data: dict) -> str:
        payload = data.get('payload', {})
        service_info = payload.get('serviceInfo', {})
        return service_info.get('event', '')

    def _extract_file_id(self, data: dict) -> str:
        payload = data.get('payload', {})
        data_obj = payload.get('data', {})
        return data_obj.get('id', '')

    def _extract_file_name(self, data: dict) -> str:
        payload = data.get('payload', {})
        data_obj = payload.get('data', {})
        return data_obj.get('fileName', '')

    # ========== 从 Redis 获取 Webhook ==========

    def get_file_events(self, file_id: str) -> List[WebhookRecord]:
        """从 Redis 获取文件的所有事件"""
        try:
            response = requests.get(f"{self.webhook_server_url}/history/{file_id}", timeout=10)
            if response.status_code != 200:
                return []
            data = response.json()
        except Exception as e:
            print(f"获取文件事件失败: {e}")
            return []

        records = []
        for event in data.get('events', []):
            # 解析 data 字段中的 JSON
            event_data = event.get('data', '{}')
            if isinstance(event_data, str):
                event_data = json.loads(event_data)

            records.append(WebhookRecord(
                event_id=event.get('event_id', ''),
                file_id=event.get('file_id', ''),
                file_name='',
                payload=event_data.get('payload', {}),
                raw_data=event_data,
                timestamp=event.get('timestamp', '')
            ))

        return records

    def get_latest_event(self, file_id: str) -> Optional[WebhookRecord]:
        """获取文件的最新事件"""
        try:
            response = requests.get(f"{self.webhook_server_url}/latest/{file_id}", timeout=10)
            if response.status_code != 200:
                return None
            data = response.json()
        except Exception as e:
            print(f"获取最新事件失败: {e}")
            return None

        if not data or 'message' in data:
            return None

        event_data = data.get('data', '{}')
        if isinstance(event_data, str):
            event_data = json.loads(event_data)

        return WebhookRecord(
            event_id=data.get('event_id', ''),
            file_id=data.get('file_id', ''),
            file_name='',
            payload=event_data.get('payload', {}),
            raw_data=event_data,
            timestamp=data.get('timestamp', '')
        )

    # ========== 监听方法（基于 Redis） ==========

    def wait_for_id(
            self,
            file_id: str,
            timeout: int = 120
    ) -> Tuple[List[WebhookRecord], List[EventCompareResult]]:
        """监听指定文件 ID 的所有回调（从 Redis 轮询）"""
        start_time = time.time()
        collected_records = []
        compare_results = []
        received_events = set()

        print(f"开始监听文件: {file_id}")

        while time.time() - start_time < timeout:
            # 从 Redis 获取该文件的所有事件
            events = self.get_file_events(file_id)

            for event in events:
                if event.event_id not in received_events:
                    received_events.add(event.event_id)
                    collected_records.append(event)
                    print(f"📨 收到事件: {event.event_id}")

                    # 比对并保存
                    result = self._compare_and_save(event)
                    compare_results.append(result)

            time.sleep(1)

        print(f"监听结束，共收到 {len(collected_records)} 个事件")
        return collected_records, compare_results

    def wait_for_specific_event(
            self,
            file_id: str,
            event_id: str,
            timeout: int = 120
    ) -> Tuple[Optional[WebhookRecord], Optional[EventCompareResult]]:
        """监听指定事件"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 从 Redis 获取该文件的所有事件
            events = self.get_file_events(file_id)

            for event in events:
                if event.event_id == event_id:
                    print(f"📨 收到指定事件: {event_id}")
                    result = self._compare_and_save(event)
                    return event, result

            time.sleep(1)

        return None, None

    def wait_for_any_event(self, file_id: str, timeout: int = 120) -> Optional[WebhookRecord]:
        """等待任意事件"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            event = self.get_latest_event(file_id)
            if event:
                return event
            time.sleep(1)

        return None

    # ========== 比对和保存 ==========

    def _compare_and_save(self, record: WebhookRecord) -> EventCompareResult:
        """与数据库中的历史比对并保存"""
        history = get_event(record.event_id)

        if history is None:
            save_event(record.event_id, record.file_id, record.file_name, record.payload)
            print(f"📝 首次事件 [{record.event_id}]，已保存")
            return EventCompareResult(
                event_id=record.event_id,
                is_first=True,
                is_same=True,
                compare_result=None,
                record=record
            )

        compare_result = self.validator.compare(history['payload'], record.payload)
        save_event(record.event_id, record.file_id, record.file_name, record.payload)

        if compare_result.is_same:
            print(f"✅ [{record.event_id}] 结构一致")
        else:
            print(f"❌ [{record.event_id}] {compare_result.summary}")

        return EventCompareResult(
            event_id=record.event_id,
            is_first=False,
            is_same=compare_result.is_same,
            compare_result=compare_result,
            record=record
        )

    # ========== 清理方法 ==========

    def clear_file_events(self, file_id: str):
        """清空文件的事件"""
        try:
            requests.delete(f"{self.webhook_server_url}/clear/{file_id}")
            print(f"已清空文件事件: {file_id}")
        except Exception as e:
            print(f"清空失败: {e}")

    def reset(self):
        """重置计数器"""
        self._last_event_count = {}

    # ========== 差异格式化方法 ==========

    @staticmethod
    def format_differences(compare_result: EventCompareResult) -> str:
        """格式化结构差异信息"""
        if not compare_result:
            return "无比对结果"

        if compare_result.is_first:
            return "📝 首次事件，已保存为基线数据"

        if compare_result.is_same:
            return "✅ 结构与历史记录完全一致"

        diff_text = []
        diff_text.append("=" * 60)
        diff_text.append("📊 结构变化分析报告")
        diff_text.append("=" * 60)
        diff_text.append(f"事件ID: {compare_result.event_id}")
        diff_text.append("")

        result = compare_result.compare_result
        if result:
            if result.missing_fields:
                diff_text.append("❌ 缺失字段（历史存在，新数据缺失）:")
                diff_text.append("-" * 40)
                for field in result.missing_fields[:20]:
                    diff_text.append(f"   - {field}")
                if len(result.missing_fields) > 20:
                    diff_text.append(f"   ... 还有 {len(result.missing_fields) - 20} 个")
                diff_text.append("")

            if result.added_fields:
                diff_text.append("➕ 新增字段（新数据添加，历史不存在）:")
                diff_text.append("-" * 40)
                for field in result.added_fields[:20]:
                    diff_text.append(f"   - {field}")
                if len(result.added_fields) > 20:
                    diff_text.append(f"   ... 还有 {len(result.added_fields) - 20} 个")
                diff_text.append("")

            if result.type_mismatches:
                diff_text.append("⚠️ 类型不匹配:")
                diff_text.append("-" * 40)
                for mismatch in result.type_mismatches:
                    diff_text.append(f"   - {mismatch['path']}: {mismatch['old_type']} → {mismatch['new_type']}")
                diff_text.append("")

            diff_text.append("📝 摘要:")
            diff_text.append(f"   {result.summary}")
            diff_text.append("")

        diff_text.append("=" * 60)
        return "\n".join(diff_text)

    @staticmethod
    def get_key_differences(
            compare_result: EventCompareResult,
            key_fields: List[str] = None
    ) -> Dict[str, Dict]:
        """获取关键字段的差异"""
        if not compare_result or compare_result.is_first or compare_result.is_same:
            return {}

        if key_fields is None:
            key_fields = ['data.id', 'data.wtaAnalysisResult.analysisId']

        if not compare_result.compare_result:
            return {}

        key_diffs = {}
        for diff in compare_result.compare_result.differences:
            if diff.get('path') in key_fields:
                key_diffs[diff['path']] = {
                    'old': diff.get('old'),
                    'new': diff.get('new'),
                    'type': diff.get('type')
                }

        return key_diffs

    @staticmethod
    def print_differences(compare_result: EventCompareResult):
        """打印差异信息到控制台"""
        print(WebhookListener.format_differences(compare_result))

    @staticmethod
    def get_summary(compare_result: EventCompareResult) -> dict:
        """获取结构变化的简要摘要"""
        if not compare_result or compare_result.is_first:
            return {
                'has_change': False,
                'missing_count': 0,
                'added_count': 0,
                'type_mismatch_count': 0,
                'summary': '首次事件或无数据'
            }

        if compare_result.is_same:
            return {
                'has_change': False,
                'missing_count': 0,
                'added_count': 0,
                'type_mismatch_count': 0,
                'summary': '结构一致'
            }

        result = compare_result.compare_result
        return {
            'has_change': True,
            'missing_count': len(result.missing_fields) if result else 0,
            'added_count': len(result.added_fields) if result else 0,
            'type_mismatch_count': len(result.type_mismatches) if result else 0,
            'summary': result.summary if result else '未知变化'
        }
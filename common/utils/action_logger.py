# utils/action_logger.py
import allure
from allure_commons.types import AttachmentType
import time


class ActionLogger:
    """操作日志记录"""

    def __init__(self):
        self.actions = []

    def log(self, action, details=None):
        """记录操作"""
        log_entry = {
            "timestamp": time.time(),
            "action": action,
            "details": details
        }
        self.actions.append(log_entry)

    def attach_to_allure(self):
        """附加到 Allure 报告"""
        import json
        allure.attach(
            json.dumps(self.actions, indent=2, default=str),
            name="user_actions",
            attachment_type=AttachmentType.JSON
        )

    def attach_performance(self, start_time, end_time, operation):
        """附加性能数据"""
        duration = end_time - start_time
        allure.attach(
            f"操作: {operation}\n耗时: {duration:.3f} 秒",
            name=f"performance_{operation}",
            attachment_type=AttachmentType.TEXT
        )
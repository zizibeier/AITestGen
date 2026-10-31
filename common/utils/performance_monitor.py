# common/utils/performance_monitor.py
"""
性能监控类
专门用于收集和管理性能数据
"""

import time
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import allure
from common.utils.logger import log


@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    name: str
    value: float
    unit: str = "ms"
    threshold: Optional[float] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def is_pass(self) -> bool:
        """是否通过阈值检查"""
        if self.threshold is None:
            return True
        return self.value <= self.threshold


class PerformanceMonitor:
    """
    性能监控器

    用于收集、记录、报告性能数据

    使用示例:
        monitor = PerformanceMonitor()

        # 测量函数执行时间
        result, duration = monitor.measure(lambda: api.get_user())
        monitor.add("get_user", duration)

        # 手动添加指标
        monitor.add_metric("fps", 60, unit="fps", threshold=30)

        # 附加到 Allure
        monitor.attach_to_allure()
    """

    def __init__(self, test_name: str = None):
        """
        初始化性能监控器

        Args:
            test_name: 测试名称，用于报告标识
        """
        self.metrics: List[PerformanceMetric] = []
        self.test_name = test_name or "performance"
        self._start_time = time.time()

    def measure(self, func: Callable, *args, **kwargs) -> tuple:
        """
        测量函数执行时间

        Args:
            func: 要测量的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            tuple: (函数返回值, 执行时间毫秒数)
        """
        start = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        return result, duration

    def add(self, name: str, value: float, unit: str = "ms", threshold: float = None):
        """
        添加性能指标

        Args:
            name: 指标名称
            value: 指标值
            unit: 单位
            threshold: 阈值（可选）
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            threshold=threshold
        )
        self.metrics.append(metric)
        log.debug(f"性能指标: {name} = {value}{unit}")

    def add_metric(self, name: str, value: float, unit: str = "ms", threshold: float = None):
        """添加性能指标（add 方法的别名）"""
        self.add(name, value, unit, threshold)

    def add_batch(self, metrics: Dict[str, float], unit: str = "ms", threshold: float = None):
        """
        批量添加性能指标

        Args:
            metrics: 指标字典 {名称: 值}
            unit: 单位
            threshold: 阈值
        """
        for name, value in metrics.items():
            self.add(name, value, unit, threshold)

    def add_fps(self, fps: float, threshold: float = 30):
        """添加帧率指标"""
        self.add("fps", fps, unit="fps", threshold=threshold)

    def add_memory(self, memory_mb: float, threshold: float = 2048):
        """添加内存指标"""
        self.add("memory_mb", memory_mb, unit="MB", threshold=threshold)

    def add_load_time(self, load_time_ms: float, threshold: float = 5000):
        """添加加载时间指标"""
        self.add("load_time_ms", load_time_ms, unit="ms", threshold=threshold)

    def get_total_time(self) -> float:
        """获取总耗时（从创建开始）"""
        return (time.time() - self._start_time) * 1000

    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        total = len(self.metrics)
        passed = sum(1 for m in self.metrics if m.is_pass())
        failed = total - passed

        return {
            "test_name": self.test_name,
            "total_metrics": total,
            "passed": passed,
            "failed": failed,
            "total_time_ms": round(self.get_total_time(), 2),
            "metrics": [m.to_dict() for m in self.metrics]
        }

    def assert_all(self, raise_exception: bool = True) -> bool:
        """
        断言所有性能指标通过

        Args:
            raise_exception: 是否抛出异常

        Returns:
            bool: 是否全部通过
        """
        failed_metrics = [m for m in self.metrics if not m.is_pass()]

        if failed_metrics:
            error_msg = f"性能指标不通过 ({len(failed_metrics)} 个):\n"
            for m in failed_metrics:
                error_msg += f"  - {m.name}: {m.value}{m.unit} (阈值: {m.threshold}{m.unit})\n"

            log.error(error_msg)
            if raise_exception:
                raise AssertionError(error_msg)
            return False

        log.success(f"✅ 所有性能指标通过 ({len(self.metrics)} 个)")
        return True

    def attach_to_allure(self, name: str = None):
        """
        附加性能数据到 Allure 报告

        Args:
            name: 报告名称
        """
        summary = self.get_summary()

        # 格式化报告内容
        report_lines = []
        report_lines.append(f"## 性能测试报告: {summary['test_name']}")
        report_lines.append("")
        report_lines.append(f"**总耗时:** {summary['total_time_ms']:.2f}ms")
        report_lines.append(f"**指标总数:** {summary['total_metrics']}")
        report_lines.append(f"**通过:** ✅ {summary['passed']}")
        report_lines.append(f"**失败:** ❌ {summary['failed']}")
        report_lines.append("")
        report_lines.append("### 详细指标")
        report_lines.append("")
        report_lines.append("| 指标 | 值 | 单位 | 阈值 | 状态 |")
        report_lines.append("|------|-----|------|------|------|")

        for m in self.metrics:
            status = "✅ 通过" if m.is_pass() else "❌ 失败"
            threshold_str = f"{m.threshold}{m.unit}" if m.threshold else "-"
            report_lines.append(f"| {m.name} | {m.value:.2f} | {m.unit} | {threshold_str} | {status} |")

        report_text = "\n".join(report_lines)

        allure.attach(
            report_text,
            name=name or f"性能报告_{self.test_name}",
            attachment_type=allure.attachment_type.TEXT
        )

        # 同时附加 JSON 格式
        allure.attach(
            self.to_json(),
            name=name or f"性能数据_{self.test_name}",
            attachment_type=allure.attachment_type.JSON
        )

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        import json
        return json.dumps(self.get_summary(), indent=2, ensure_ascii=False)

    def reset(self):
        """重置所有指标"""
        self.metrics.clear()
        self._start_time = time.time()
        log.debug("性能监控器已重置")


class PerformanceContext:
    """
    性能监控上下文管理器

    用于 with 语句自动测量代码块执行时间

    使用示例:
        with PerformanceContext("模型加载") as ctx:
            wait_for_model_load()
        ctx.attach_to_allure()
    """

    def __init__(self, name: str, unit: str = "ms", threshold: float = None):
        """
        初始化性能上下文

        Args:
            name: 操作名称
            unit: 单位
            threshold: 阈值
        """
        self.name = name
        self.unit = unit
        self.threshold = threshold
        self.duration = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = (time.time() - self.start_time) * 1000

    def get_duration(self) -> float:
        """获取执行时间"""
        return self.duration

    def to_metric(self) -> PerformanceMetric:
        """转换为性能指标"""
        return PerformanceMetric(
            name=self.name,
            value=self.duration,
            unit=self.unit,
            threshold=self.threshold
        )

    def attach_to_allure(self):
        """附加到 Allure 报告"""
        allure.attach(
            f"{self.name}: {self.duration:.2f}{self.unit}",
            name=f"性能_{self.name}",
            attachment_type=allure.attachment_type.TEXT
        )
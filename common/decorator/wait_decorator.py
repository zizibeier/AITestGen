# common/decorators/wait.py

import time
import allure
from functools import wraps
from typing import Callable, Optional, Tuple, Any


def poll_until(
        timeout: int = 60,
        interval: int = 2,
        description: str = None,
        status_field: str = "status",
        target_status: str = "completed",
        failed_statuses: list = None
):
    """
    轮询等待装饰器

    Args:
        timeout: 超时时间（秒）
        interval: 轮询间隔（秒）
        description: 等待描述
        status_field: 状态字段名
        target_status: 目标状态
        failed_statuses: 失败状态列表

    Example:
        @poll_until(timeout=60, description="等待模型解析完成")
        def get_model_status(model_id):
            return endpoints.model.get_detail(model_id)
    """
    if failed_statuses is None:
        failed_statuses = ["failed", "error"]

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            attempt = 0
            last_response = None

            while time.time() - start_time < timeout:
                attempt += 1

                try:
                    response = func(*args, **kwargs)
                    last_response = response

                    # 提取状态
                    status = _extract_status(response, status_field)

                    # 记录到 Allure
                    _log_wait_attempt(attempt, status, start_time, description)

                    # 检查是否完成
                    if status == target_status:
                        _log_wait_success(attempt, start_time, description)
                        return response

                    # 检查是否失败
                    if status in failed_statuses:
                        raise Exception(f"任务失败，状态: {status}")

                except Exception as e:
                    _log_wait_error(attempt, str(e), description)
                    if attempt >= 3:  # 连续失败3次才抛出
                        raise

                time.sleep(interval)

            # 超时
            raise TimeoutError(
                f"{description or func.__name__} 超时 ({timeout}秒)，"
                f"共尝试 {attempt} 次，最后状态: {_extract_status(last_response, status_field)}"
            )

        return wrapper

    return decorator


def wait_for_condition(
        timeout: int = 60,
        interval: int = 2,
        description: str = None
):
    """
    等待条件函数返回 True

    Example:
        @wait_for_condition(timeout=60, description="等待模型加载")
        def is_model_loaded():
            return endpoints.model.get_status() == "loaded"
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> bool:
            start_time = time.time()
            attempt = 0

            while time.time() - start_time < timeout:
                attempt += 1

                try:
                    if func(*args, **kwargs):
                        _log_wait_success(attempt, start_time, description)
                        return True
                except Exception as e:
                    _log_wait_error(attempt, str(e), description)

                time.sleep(interval)

            raise TimeoutError(f"{description or func.__name__} 超时 ({timeout}秒)")

        return wrapper

    return decorator


def wait_for_response(
        timeout: int = 60,
        interval: int = 2,
        description: str = None
):
    """
    等待接口返回特定条件

    Example:
        @wait_for_response(timeout=60, description="等待任务完成")
        def check_task(task_id):
            resp = endpoints.task.get_status(task_id)
            return resp if resp.json()["status"] == "completed" else None
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            attempt = 0

            while time.time() - start_time < timeout:
                attempt += 1

                try:
                    result = func(*args, **kwargs)
                    if result is not None:
                        _log_wait_success(attempt, start_time, description)
                        return result
                except Exception as e:
                    _log_wait_error(attempt, str(e), description)

                time.sleep(interval)

            raise TimeoutError(f"{description or func.__name__} 超时 ({timeout}秒)")

        return wrapper

    return decorator


# ==================== 辅助函数 ====================

def _extract_status(response, status_field: str) -> str:
    """从响应中提取状态"""
    try:
        if hasattr(response, 'json'):
            data = response.json()
        else:
            data = response

        if isinstance(data, dict):
            # 支持嵌套路径，如 "data.status"
            keys = status_field.split('.')
            value = data
            for key in keys:
                value = value.get(key, {})
            return str(value)
        return str(data)
    except:
        return "unknown"


def _log_wait_attempt(attempt: int, status: str, start_time: float, description: str = None):
    """记录轮询尝试"""
    elapsed = time.time() - start_time
    with allure.step(f"轮询 #{attempt} - 状态: {status}"):
        allure.attach(
            f"描述: {description or '等待任务完成'}\n"
            f"已等待: {elapsed:.1f}秒\n"
            f"当前状态: {status}",
            name="轮询信息",
            attachment_type=allure.attachment_type.TEXT
        )


def _log_wait_success(attempt: int, start_time: float, description: str = None):
    """记录等待成功"""
    elapsed = time.time() - start_time
    with allure.step(f"✅ {description or '等待完成'} - 成功"):
        allure.attach(
            f"尝试次数: {attempt}\n总耗时: {elapsed:.1f}秒",
            name="等待结果",
            attachment_type=allure.attachment_type.TEXT
        )


def _log_wait_error(attempt: int, error: str, description: str = None):
    """记录等待错误"""
    with allure.step(f"⚠️ 轮询 #{attempt} 失败"):
        allure.attach(
            f"错误: {error}",
            name="错误信息",
            attachment_type=allure.attachment_type.TEXT
        )
# common/context/base_context.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from common.utils.logger import log

class BaseContext(ABC):
    """
    上下文基类 - 定义API和UI上下文的统一接口
    类似于抽象类，只定义"应该有什么方法"，不实现具体逻辑
    """

    def __init__(self):
        self._context_data: Dict[str, Any] = {}  # 共享数据容器
        self.logger = log

    #==========必须实现的抽象方法============
    @abstractmethod
    def setup(self):
        """初始化上下文（启动session、浏览器等）"""
        pass

    @abstractmethod
    def teardown(self):
        """清理上下文（关闭连接、关闭浏览器）"""
        pass

    @abstractmethod
    def get_session(self):
        """获取会话对象（requests.Session 或 playwright Page）"""
        pass

    @abstractmethod
    def navigate(self, url: str = None):
        """导航到页面（API就是发送请求，UI就是跳转）"""
        pass


    # ============ 通用方法（子类可以直接用） ============

    def set_data(self, key: str, value: Any):
        """存储数据（API和UI共用）"""
        self._context_data[key] = value
        if self.logger:
            self.logger.debug(f"存储数据: {key} = {value}")

    def get_data(self, key: str) -> Optional[Any]:
        """获取存储的数据"""
        value = self._context_data.get(key)
        if self.logger:
            self.logger.debug(f"获取数据: {key} = {value}")
        return value

    def has_data(self, key: str) -> bool:
        """检查是否有某个数据"""
        return key in self._context_data

    def clear_data(self):
        """清空所有数据"""
        self._context_data.clear()
        self.logger.debug("清空所有上下文数据")
        return self

    def set_batch_data(self, data: Dict[str, Any]):
        """批量设置数据"""
        self._context_data.update(data)
        self.logger.debug(f"批量存储数据: {list(data.keys())}")
        return self

    def get_all_data(self) -> Dict[str, Any]:
        """获取所有数据"""
        return self._context_data.copy()


    @abstractmethod
    def wait_for(self, condition, timeout: int):
        """等待条件满足（API和UI实现不同）"""
        pass
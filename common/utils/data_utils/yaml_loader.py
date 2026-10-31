"""
通用 YAML 配置文件加载器
支持从不同路径加载配置
"""

import yaml
from pathlib import Path
from typing import Any, Optional, Dict
from functools import lru_cache


class YamlLoader:
    """通用 YAML 配置加载器"""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self._data = None

    def _load(self) -> Dict:
        """加载 YAML 文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @property
    def data(self) -> Dict:
        """获取原始数据"""
        if self._data is None:
            self._data = self._load()
        return self._data

    def get(self, path: str = None, default: Any = None) -> Any:
        """
        通过点号路径获取配置
        例如: get("costing.finished")
        """
        if path is None:
            return self.data

        keys = path.split('.')
        result = self.data

        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
                if result is None:
                    return default
            else:
                return default

        return result

    def __getitem__(self, key: str) -> Any:
        """支持 dict 式访问"""
        return self.get(key)


@lru_cache(maxsize=20)
def load_config(config_path: str) -> YamlLoader:
    """加载配置（带缓存）"""
    return YamlLoader(config_path)


# ========== 便捷函数 ==========

def get_api_config(config_name: str):
    """加载 API 配置"""
    return load_config(f"api/config/{config_name}.yaml")


def get_ui_config(config_name: str):
    """加载 UI 配置"""
    return load_config(f"ui/config/{config_name}.yaml")


def get_common_config(config_name: str):
    """加载通用配置"""
    return load_config(f"common/config/{config_name}.yaml")
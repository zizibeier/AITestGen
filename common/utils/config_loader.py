# common/utils/config_loader.py
"""
配置加载器 - 专门加载接口路径等配置
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import json

from common.utils.logger import log


class ConfigLoader:
    """配置加载器 - 用于加载接口路径等配置"""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load(cls, file_path: str = None):
        """加载配置文件"""
        if file_path is None:
            # 获取项目根目录（假设 common/utils/ 在项目根目录下）
            # 向上两级到项目根目录
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent  # common/utils/ -> common/ -> project_root/

            # 默认配置文件路径
            file_path = Path("api/data/api_config.yaml")
            if not file_path.exists():
                log.warning(f"配置文件不存在: {file_path}")
            # 尝试多个可能的路径
            possible_paths = [
                project_root / "api" / "data" / "api_config.yaml",
                project_root / "api" / "data" / "api_config.yml",
                project_root / "api" / "data" / "api_config.json",
                Path("api/data/api_config.yaml"),  # 相对路径
                Path("../api/data/api_config.yaml"),
            ]

            for path in possible_paths:
                if path.exists():
                    file_path = str(path)
                    log.debug(f"找到配置文件: {file_path}")
                    break


        if file_path is None or not Path(file_path).exists():
            log.warning(f"配置文件不存在，将使用默认配置")
            return {}
        # 加载文件...
        if Path(file_path).suffix in ['.yaml', '.yml']:
            with open(file_path, 'r', encoding='utf-8') as f:
                cls._config = yaml.safe_load(f)
        elif Path(file_path).suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                cls._config = json.load(f)

        log.info(f"加载配置文件: {file_path}")
        return cls._config


    @classmethod
    def get(cls, path: str, default=None):
        """
        获取配置值，支持点号路径

        Example:
            url = ConfigLoader.get("auth.login")
            url = ConfigLoader.get("user.detail", default="/api/v1/users")
        """
        if not cls._config:
            cls.load()

        keys = path.split('.')
        value = cls._config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    @classmethod
    def get_endpoint(cls, name: str, **kwargs) -> str:
        """
        获取接口路径，支持参数替换

        Example:
            url = ConfigLoader.get_endpoint("user.detail", user_id=123)
            # 返回: "/api/v1/users/123"
        """
        endpoint = cls.get(name)
        if not endpoint:
            raise ValueError(f"未找到接口配置: {name}")

        # 替换路径参数
        for key, value in kwargs.items():
            endpoint = endpoint.replace(f"{{{key}}}", str(value))

        return endpoint

    @classmethod
    def reload(cls):
        """重新加载配置"""
        cls._config = {}
        cls.load()

if __name__ == '__main__':
    ConfigLoader.load()
    print(ConfigLoader.get_endpoint('analysis.upload_filepath'))



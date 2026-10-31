# common/utils/data_loader.py

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml

from common.utils.logger import log
from common.utils.data_utils.data_handle import DataHandle


class TestDataLoader:
    """测试数据加载器 - 支持 YAML 数据和动态占位符处理"""

    _data: Dict[str, Any] = {}
    _processed_data: Dict[str, Any] = {}  # 处理后的数据缓存
    _data_handle: Optional[DataHandle] = None

    @classmethod
    def _get_data_handle(cls) -> DataHandle:
        """获取 DataHandle 实例（单例）"""
        if cls._data_handle is None:
            # 自动检测工程根目录
            current_file = Path(__file__).resolve()
            # common/utils/data_utils/data_loader.py -> 工程根目录
            project_root = current_file.parent.parent.parent.parent

            cls._data_handle = DataHandle(test_files_dir=str(project_root))

            # 设置全局变量（可以从配置文件中加载）
            cls._set_global_vars()

        return cls._data_handle

    @classmethod
    def _set_global_vars(cls):
        """设置全局变量"""
        handler = cls._data_handle

        # 从环境变量读取配置
        handler.set_global("env", os.getenv("TEST_ENV", "staging"))
        handler.set_global("api_base_url", os.getenv("API_BASE_URL", "https://api.example.com"))

        # 固定的全局配置
        handler.set_global("webhook_key", os.getenv("WEBHOOK_KEY", ""))
        handler.set_global("test_files_dir", "model_test/files")

    @classmethod
    def load(cls, file_path: str = None) -> Dict[str, Any]:
        """
        加载测试数据

        :param file_path: YAML 文件路径，None 则使用默认路径
        :return: 处理后的测试数据
        """
        # 如果已缓存，直接返回
        if file_path is None:
            # model_test/api/data/test.yaml
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent.parent
            file_path = project_root / "model_test" / "api" / "data" / "test.yaml"

        file_path = str(file_path)

        # 检查是否已经加载过
        if file_path in cls._processed_data:
            return cls._processed_data[file_path]

        if not Path(file_path).exists():
            log.warning(f"测试数据文件不存在: {file_path}")
            return {}

        # 读取 YAML 文件
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = yaml.safe_load(f)

        log.info(f"加载测试数据: {file_path}")

        # 使用 DataHandle 处理占位符
        handler = cls._get_data_handle()
        processed_data = handler.process_data(raw_data)

        # 缓存处理后的数据
        cls._processed_data[file_path] = processed_data
        cls._data[file_path] = raw_data

        return processed_data

    @classmethod
    def reload(cls, file_path: str = None, clear_cache: bool = True):
        """
        重新加载测试数据（每次加载都会重新处理占位符）

        :param file_path: YAML 文件路径
        :param clear_cache: 是否清除缓存
        """
        if clear_cache:
            cls._processed_data.clear()
            cls._data.clear()

        # 清除 DataHandle 的文件缓存
        if cls._data_handle:
            cls._data_handle.clear_cache()

        return cls.load(file_path)

    @classmethod
    def get_raw_data(cls, key: str = None) -> Any:
        """
        获取原始数据（未处理的）

        :param key: 数据键，None 返回全部
        :return: 原始数据
        """
        if not cls._data:
            cls.load()

        # 获取最后一个加载的数据
        data = next(iter(cls._data.values())) if cls._data else {}

        if key:
            return data.get(key)
        return data

    @classmethod
    def get_test_cases(cls, key: str = "groups") -> List[Dict]:
        """
        获取测试用例列表（扁平化所有分组中的用例）

        :param key: 数据键，支持点号分隔的路径，如 "groups.standard.cases"
        :return: 测试用例列表
        """
        if not cls._processed_data:
            cls.load()

        data = next(iter(cls._processed_data.values())) if cls._processed_data else {}

        # 支持点号路径
        if '.' in key:
            parts = key.split('.')
            current = data
            for part in parts:
                current = current.get(part, {})
            return current if isinstance(current, list) else []

        # 如果是 "groups"，提取所有分组中的用例
        if key == "groups":
            groups = data.get('groups', [])
            return groups

        return data.get(key, [])

    @classmethod
    def get_all_cases(cls) -> List[Dict]:
        """
        获取所有测试用例（扁平化，所有分组合并）

        :return: 所有测试用例列表，每个用例包含 group 信息
        """
        groups = cls.get_test_cases("groups")
        all_cases = []

        for group in groups:
            group_name = group.get('name', 'unknown')
            group_desc = group.get('description', '')
            cases = group.get('cases', [])

            for case in cases:
                # 添加分组信息到用例中
                case['_group'] = group_name
                case['_group_description'] = group_desc
                all_cases.append(case)

        return all_cases

    @classmethod
    def get_cases_by_group(cls, group_name: str) -> List[Dict]:
        """
        按分组名获取测试用例

        :param group_name: 分组名称，如 "standard", "boundary"
        :return: 该分组的测试用例列表
        """
        groups = cls.get_test_cases("groups")

        for group in groups:
            if group.get('name') == group_name:
                return group.get('cases', [])

        return []

    @classmethod
    def get_case_by_name(cls, case_name: str) -> Optional[Dict]:
        """
        按用例名查找测试用例

        :param case_name: 用例名称
        :return: 测试用例字典，未找到返回 None
        """
        all_cases = cls.get_all_cases()
        for case in all_cases:
            if case.get('name') == case_name:
                return case
        return None

    @classmethod
    def get_parametrize(cls, key: str = "groups", ids_key: str = "name"):
        """
        获取 pytest 参数化格式的数据

        :param key: 数据键
        :param ids_key: 用作测试 ID 的字段名
        :return: (argnames, argvalues, ids)

        示例:
            argnames, argvalues, ids = TestDataLoader.get_parametrize("groups")
            @pytest.mark.parametrize(argnames, argvalues, ids=ids)
        """
        cases = cls.get_all_cases()

        if not cases:
            return [], [], []

        # 需要排除的内部字段
        exclude_fields = {'_group', '_group_description', 'expected_events', 'expect_exception'}

        # 获取所有字段名
        all_fields = set()
        for case in cases:
            all_fields.update(case.keys())

        # 排序字段，确保一致性
        argnames = sorted(list(all_fields - exclude_fields))

        # 获取所有值
        argvalues = [[case.get(k) for k in argnames] for case in cases]

        # 获取 ids
        ids = [case.get(ids_key, str(i)) for i, case in enumerate(cases)]

        return argnames, argvalues, ids

    @classmethod
    def set_global(cls, key: str, value: Any):
        """
        设置全局变量（可以在测试中使用）

        :param key: 变量名
        :param value: 变量值
        """
        handler = cls._get_data_handle()
        handler.set_global(key, value)

    @classmethod
    def get_config(cls) -> Dict:
        """获取配置信息"""
        if not cls._processed_data:
            cls.load()

        data = next(iter(cls._processed_data.values())) if cls._processed_data else {}
        return data.get('config', {})


# ==================== 便捷函数 ====================

def parametrize_from_yaml(key: str = "groups", ids_key: str = "name"):
    """
    从 YAML 获取参数化数据的装饰器

    使用示例:
        @parametrize_from_yaml()
        def test_upload(self, name, file_name, expected_status, ...):
            ...
    """
    import pytest
    argnames, argvalues, ids = TestDataLoader.get_parametrize(key, ids_key)
    return pytest.mark.parametrize(argnames, argvalues, ids=ids)


def load_test_data(file_path: str = None) -> Dict[str, Any]:
    """
    便捷函数：加载测试数据

    :param file_path: YAML 文件路径
    :return: 处理后的测试数据
    """
    return TestDataLoader.load(file_path)


def reload_test_data(file_path: str = None) -> Dict[str, Any]:
    """
    便捷函数：重新加载测试数据（每次都会重新处理占位符）

    :param file_path: YAML 文件路径
    :return: 处理后的测试数据
    """
    return TestDataLoader.reload(file_path)
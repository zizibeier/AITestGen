# test_data/test_data.py

import os
import yaml
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
from copy import deepcopy

from common.config.settings import Config


@dataclass
class FileUploadRequest:
    """文件上传请求参数"""
    name: str
    file_name: str = "配重块.stp"
    params: str = ""
    webhook_key: str = ""
    use_cache: str = "true"
    extra_info: str = ""
    preview_type: str = "1"
    need_business_service: str = "0"
    need_stl_light_weight: str = "0"
    minimum_thickness_threshold: str = "0.5"
    high_risk_area_define: str = "100"
    cover_color: str = "#85A2CD"
    expected_status: str = "success"
    expected_events: List[str] = field(default_factory=list)
    expect_exception: Optional[str] = None

    # 查询用例专用：仅测试侧使用，不参与 to_api_params() 的接口参数映射
    query_timeout: str = "30"
    query_interval: str = "1"

    # 分组信息
    _group: str = field(default="", repr=False)
    _group_description: str = field(default="", repr=False)

    def to_api_params(self) -> Dict[str, str]:
        """转换为API请求参数"""
        params = {}

        mappings = {
            'webhook_key': 'webhookKey',
            'use_cache': 'useCache',
            'extra_info': 'extraInfo',
            'preview_type': 'previewType',
            'need_business_service': 'needBusinessService',
            'need_stl_light_weight': 'needStlLightWeight',
            'minimum_thickness_threshold': 'minimumThicknessThreshold',
            'high_risk_area_define': 'highRiskAreaDefine',
            'cover_color': 'coverColor',
        }

        for py_name, api_name in mappings.items():
            value = getattr(self, py_name, None)
            if value is not None and value != "":
                params[api_name] = value

        if self.params:
            params['params'] = self.params

        return params

    def get_display_name(self) -> str:
        """获取用例的显示名称"""
        return f"[{self._group}] {self.name}"


@dataclass
class TestGroup:
    """测试分组"""
    name: str
    description: str
    cases: List[FileUploadRequest]


class TestDataLoader:
    """测试数据加载器 - 支持 DataHandle 动态占位符处理"""

    def __init__(self, yaml_path: str = None, project_root: str = None):
        """
        初始化测试数据加载器

        :param yaml_path: YAML 文件路径
        :param project_root: 工程根目录
        """
        # 默认 YAML 路径
        if yaml_path is None:
            yaml_path = os.path.join(os.path.dirname(__file__), "analysis_test_data.yaml")

        self.yaml_path = Path(yaml_path)

        # 自动检测工程根目录
        if project_root is None:
            current = Path(__file__).resolve()
            for parent in [current] + list(current.parents):
                if (parent / '.git').exists() or (parent / 'model_test').exists():
                    project_root = str(parent)
                    break
            else:
                project_root = str(current.parent.parent)

        self.project_root = project_root

        # 延迟导入 DataHandle（避免循环导入）
        self._data_handle = None

        # 数据存储
        self._groups: List[TestGroup] = []
        self._raw_data: Dict = {}
        self._processed_data: Dict = {}

        # 加载数据
        self._load()

    def _get_data_handle(self):
        """
        延迟获取 DataHandle 实例

        使用延迟导入避免循环导入问题
        """
        if self._data_handle is None:
            # 在这里导入，而不是在文件顶部
            from common.utils.data_utils.data_handle import DataHandle
            test_files_path = os.path.join(self.project_root,  "files")

            self._data_handle = DataHandle(test_files_dir=test_files_path)

            # ✅ 设置全局变量，YAML 中用 ${global:test_files_dir} 引用
            self._data_handle.set_global('test_files_dir', test_files_path)
            self._data_handle.set_global('webhook_key', Config.WEBHOOK_KEY)
            # self._setup_globals()

        return self._data_handle

    def _setup_globals(self):
        """设置全局变量"""
        handle = self._get_data_handle()
        handle.set_global("env", os.getenv("TEST_ENV", "staging"))
        handle.set_global("webhook_key", Config.WEBHOOK_KEY)
        # handle.set_global("test_files_dir", test_file_path)

    def _load(self):
        """加载并处理 YAML 文件"""
        if not self.yaml_path.exists():
            raise FileNotFoundError(f"YAML文件不存在: {self.yaml_path}")

        # 读取原始 YAML
        with open(self.yaml_path, 'r', encoding='utf-8') as f:
            self._raw_data = yaml.safe_load(f)

        # 尝试使用 DataHandle 处理占位符
        try:
            handle = self._get_data_handle()
            self._processed_data = handle.process_data(deepcopy(self._raw_data))
        except Exception as e:
            # 如果 DataHandle 不可用，直接使用原始数据
            print(f"警告: DataHandle 处理失败，使用原始数据: {e}")
            self._processed_data = deepcopy(self._raw_data)

        # 构建 TestGroup 和 FileUploadRequest
        self._groups = []
        for group_data in self._processed_data.get('groups', []):
            cases = []
            for case_data in group_data.get('cases', []):
                # 过滤 None 值
                filtered = {k: v for k, v in case_data.items() if v is not None}

                # 获取 FileUploadRequest 的有效字段
                valid_fields = {
                    'name', 'file_name', 'params', 'webhook_key',
                    'use_cache', 'extra_info', 'preview_type',
                    'need_business_service', 'need_stl_light_weight',
                    'minimum_thickness_threshold', 'high_risk_area_define',
                    'cover_color', 'expected_status', 'expected_events',
                    'expect_exception', 'query_timeout', 'query_interval'
                }
                valid_data = {k: v for k, v in filtered.items() if k in valid_fields}

                case = FileUploadRequest(**valid_data)
                case._group = group_data.get('name', '')
                case._group_description = group_data.get('description', '')
                cases.append(case)

            self._groups.append(TestGroup(
                name=group_data['name'],
                description=group_data.get('description', ''),
                cases=cases
            ))

    def reload(self):
        """重新加载数据（每次获取不同随机值）"""
        self._groups.clear()
        self._processed_data.clear()
        self._load()
        return self

    def get_config(self) -> Dict:
        """获取配置信息"""
        return self._processed_data.get('config', {})

    @property
    def groups(self) -> List[TestGroup]:
        """获取所有分组"""
        return self._groups

    def get_group(self, group_name: str) -> Optional[TestGroup]:
        """根据名称获取分组"""
        for group in self._groups:
            if group.name == group_name:
                return group
        return None

    def get_all_cases(self, reload: bool = False) -> List[FileUploadRequest]:
        """获取所有测试用例"""
        if reload:
            self.reload()

        all_cases = []
        for group in self._groups:
            all_cases.extend(group.cases)
        return all_cases

    def get_cases_by_group(self, *group_names: str, reload: bool = False) -> List[FileUploadRequest]:
        """根据分组名称获取测试用例"""
        if reload:
            self.reload()

        cases = []
        for group in self._groups:
            if group.name in group_names:
                cases.extend(group.cases)
        return cases

    def get_case_by_name(self, case_name: str) -> Optional[FileUploadRequest]:
        """根据用例名称获取用例"""
        for group in self._groups:
            for case in group.cases:
                if case.name == case_name:
                    return case
        return None

    def get_parametrize_data(self, *group_names: str):
        """
        获取 pytest 参数化数据

        Returns:
            (cases, ids)
        """
        if group_names:
            cases = self.get_cases_by_group(*group_names)
        else:
            cases = self.get_all_cases()

        ids = [case.get_display_name() for case in cases]

        return cases, ids

    def print_summary(self):
        """打印测试数据摘要"""
        print("\n" + "=" * 60)
        print("测试数据摘要")
        print("=" * 60)

        all_cases = self.get_all_cases()
        print(f"总用例数: {len(all_cases)}")
        print(f"总分组数: {len(self._groups)}")

        print("\n分组详情:")
        for group in self._groups:
            print(f"  [{group.name}] {group.description}")
            print(f"    用例数: {len(group.cases)}")
            for case in group.cases[:3]:
                print(f"    - {case.name}: {case.file_name}")
            if len(group.cases) > 3:
                print(f"    ... 还有 {len(group.cases) - 3} 个用例")


# ==================== 全局加载器 ====================

_loader: Optional[TestDataLoader] = None


def get_loader(reload: bool = False) -> TestDataLoader:
    """获取全局加载器实例"""
    global _loader
    if _loader is None or reload:
        _loader = TestDataLoader()
    return _loader


def reload_loader() -> TestDataLoader:
    """强制重新加载数据"""
    global _loader
    _loader = TestDataLoader()
    return _loader


def get_all_cases(reload: bool = False) -> List[FileUploadRequest]:
    """获取所有测试用例"""
    return get_loader(reload).get_all_cases()


def get_cases_by_group(*group_names: str, reload: bool = False) -> List[FileUploadRequest]:
    """根据分组获取测试用例"""
    return get_loader(reload).get_cases_by_group(*group_names)


def get_parametrize_data(*group_names: str):
    """获取参数化数据"""
    return get_loader().get_parametrize_data(*group_names)


def print_summary():
    """打印数据摘要"""
    get_loader().print_summary()


# ==================== 使用示例 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("TestDataLoader 测试")
    print("=" * 60)

    # 获取所有用例
    print("\n1. 获取所有用例:")
    all_cases = get_all_cases()
    for case in all_cases[:5]:
        print(f"  {case.get_display_name()}")
        print(f"    文件: {case.file_name}")

    print(f"\n  ... 共 {len(all_cases)} 个用例")

    # 按分组获取
    print("\n2. 按分组获取:")
    standard_cases = get_cases_by_group("standard")
    print(f"  标准用例: {len(standard_cases)} 个")
    for case in standard_cases:
        print(f"    - {case.name}: {case.file_name}")

    # 参数化数据
    print("\n3. 参数化数据:")
    cases, ids = get_parametrize_data("standard", "boundary")
    print(f"  用例数: {len(cases)}")
    print(f"  IDs: {ids[:5]}...")

    # 重新加载
    print("\n4. 重新加载测试:")
    for i in range(3):
        loader = reload_loader()
        case = loader.get_case_by_name("标准上传-默认参数")
        print(f"  第{i + 1}次: {case.file_name}")

    # 打印摘要
    print_summary()
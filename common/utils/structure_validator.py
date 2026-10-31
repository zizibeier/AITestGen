# common/utils/structure_validator.py
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class CompareResult:
    is_same: bool
    differences: List[Dict] = field(default_factory=list)  # 值差异（暂不使用）
    missing_fields: List[str] = field(default_factory=list)  # 历史有，新数据没有的字段
    added_fields: List[str] = field(default_factory=list)  # 新数据有，历史没有的字段
    type_mismatches: List[Dict] = field(default_factory=list)  # 类型不匹配的字段
    summary: str = ""


class StructureValidator:
    """结构验证器 - 只比对字段结构，忽略具体值变化"""

    @staticmethod
    def get_all_fields(data: Dict, prefix: str = "") -> set:
        """
        递归获取字典中的所有字段路径

        Args:
            data: 要提取的字典
            prefix: 路径前缀

        Returns:
            字段路径集合，如 {"data.id", "data.volume", "data.wtaAnalysisResult.analysisId"}
        """
        fields = set()
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            fields.add(current_path)

            if isinstance(value, dict):
                fields.update(StructureValidator.get_all_fields(value, current_path))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # 列表中的字典，使用 [0] 作为示例
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        fields.update(StructureValidator.get_all_fields(item, f"{current_path}[{i}]"))

        return fields

    @staticmethod
    def get_field_types(data: Dict, prefix: str = "") -> Dict[str, str]:
        """
        递归获取字典中所有字段的类型

        Returns:
            {字段路径: 类型名称}
        """
        types = {}
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            types[current_path] = type(value).__name__

            if isinstance(value, dict):
                types.update(StructureValidator.get_field_types(value, current_path))
            elif isinstance(value, list) and value:
                types[f"{current_path}[]"] = type(value[0]).__name__ if value else "unknown"

        return types

    def compare(self, old_payload: Dict, new_payload: Dict) -> CompareResult:
        """
        比对两个 payload 的字段结构（不比对具体值）

        检查项：
        1. 缺失字段：历史有，新数据没有
        2. 新增字段：新数据有，历史没有
        3. 类型不匹配：同一字段类型发生变化

        忽略项：
        - 字段值的具体变化（如 82474 -> 82475）
        - URL 过期时间变化
        """
        old_fields = self.get_all_fields(old_payload)
        new_fields = self.get_all_fields(new_payload)
        old_types = self.get_field_types(old_payload)
        new_types = self.get_field_types(new_payload)

        # 计算缺失和新增
        missing_fields = list(old_fields - new_fields)
        added_fields = list(new_fields - old_fields)

        # 检查共同字段的类型是否一致
        type_mismatches = []
        common_fields = old_fields & new_fields
        for field in common_fields:
            old_type = old_types.get(field)
            new_type = new_types.get(field)

            # 处理数组类型的特殊情况
            old_base = old_type.replace('[]', '') if old_type else old_type
            new_base = new_type.replace('[]', '') if new_type else new_type

            if old_type != new_type and old_base != new_base:
                type_mismatches.append({
                    'path': field,
                    'old_type': old_type,
                    'new_type': new_type
                })

        is_same = (len(missing_fields) == 0 and
                   len(added_fields) == 0 and
                   len(type_mismatches) == 0)

        # 生成摘要
        if is_same:
            summary = "✅ 结构完全一致，无缺失/新增字段，类型匹配"
        else:
            summary_parts = []
            if missing_fields:
                summary_parts.append(f"缺失 {len(missing_fields)} 个字段")
            if added_fields:
                summary_parts.append(f"新增 {len(added_fields)} 个字段")
            if type_mismatches:
                summary_parts.append(f"类型不匹配 {len(type_mismatches)} 处")
            summary = f"❌ 结构变化: {', '.join(summary_parts)}"

        return CompareResult(
            is_same=is_same,
            differences=[],  # 不记录值差异
            missing_fields=missing_fields,
            added_fields=added_fields,
            type_mismatches=type_mismatches,
            summary=summary
        )

    def validate_structure(self, payload: Dict, required_fields: List[str] = None) -> Tuple[bool, List[str]]:
        """
        验证 payload 是否包含必需字段

        Args:
            payload: 待验证的数据
            required_fields: 必需字段列表，默认使用通用必需字段

        Returns:
            (是否有效, 缺失字段列表)
        """
        if required_fields is None:
            # 通用必需字段（可根据业务调整）
            required_fields = [
                "serviceInfo.event",
                "serviceInfo.service",
                "data.id",
                "data.fileName",
                "data.fileType",
                "data.status",
                "data.createTime",
                "data.updateTime"
            ]

        all_fields = self.get_all_fields(payload)
        missing = [f for f in required_fields if f not in all_fields]

        return len(missing) == 0, missing





















# # common/structure_validator.py
# import json
# import hashlib
# from typing import Any, Dict, List, Optional
# from dataclasses import dataclass
#
#
# @dataclass
# class CompareResult:
#     """比对结果"""
#     is_same: bool
#     differences: List[Dict]
#     missing_fields: List[str]
#     added_fields: List[str]
#     summary: str
#
#
# class StructureValidator:
#     """结构体校验器"""
#
#     # 忽略的动态字段
#     IGNORE_FIELDS = [
#         'timestamp', 'nonce', 'signature',
#         'createTime', 'updateTime', 'createdAt', 'updatedAt',
#         'runTime', 'buyTime'
#     ]
#
#     @classmethod
#     def normalize(cls, data: Any) -> Any:
#         """标准化，移除动态字段"""
#         if isinstance(data, dict):
#             return {
#                 k: cls.normalize(v) for k, v in data.items()
#                 if k not in cls.IGNORE_FIELDS
#             }
#         elif isinstance(data, list):
#             return [cls.normalize(item) for item in data]
#         else:
#             return data
#
#     @classmethod
#     def calculate_hash(cls, data: Any) -> str:
#         """计算结构体哈希"""
#         normalized = cls.normalize(data)
#         json_str = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
#         return hashlib.md5(json_str.encode()).hexdigest()
#
#     @classmethod
#     def compare(cls, old_data: Any, new_data: Any) -> CompareResult:
#         """比对两个结构体"""
#         old_norm = cls.normalize(old_data)
#         new_norm = cls.normalize(new_data)
#
#         differences = []
#         missing_fields = []
#         added_fields = []
#
#         cls._compare_recursive(old_norm, new_norm, "", differences, missing_fields, added_fields)
#
#         is_same = len(differences) == 0 and len(missing_fields) == 0 and len(added_fields) == 0
#
#         if is_same:
#             summary = "结构体一致"
#         else:
#             parts = []
#             if differences:
#                 parts.append(f"{len(differences)}处值差异")
#             if missing_fields:
#                 parts.append(f"{len(missing_fields)}个缺失字段")
#             if added_fields:
#                 parts.append(f"{len(added_fields)}个新增字段")
#             summary = f"发现差异: {', '.join(parts)}"
#
#         return CompareResult(
#             is_same=is_same,
#             differences=differences,
#             missing_fields=missing_fields,
#             added_fields=added_fields,
#             summary=summary
#         )
#
#     @classmethod
#     def _compare_recursive(cls, old_obj, new_obj, path, differences, missing_fields, added_fields):
#         """递归比对"""
#         if old_obj is None and new_obj is None:
#             return
#         if old_obj is None:
#             added_fields.append(path or "root")
#             differences.append({'path': path or 'root', 'type': 'added'})
#             return
#         if new_obj is None:
#             missing_fields.append(path or "root")
#             differences.append({'path': path or 'root', 'type': 'missing'})
#             return
#
#         if type(old_obj) != type(new_obj):
#             differences.append({
#                 'path': path or 'root',
#                 'type': 'type_change',
#                 'old': type(old_obj).__name__,
#                 'new': type(new_obj).__name__
#             })
#             return
#
#         if isinstance(old_obj, dict):
#             all_keys = set(old_obj.keys()) | set(new_obj.keys())
#             for key in all_keys:
#                 new_path = f"{path}.{key}" if path else key
#                 if key not in old_obj:
#                     added_fields.append(new_path)
#                     differences.append({'path': new_path, 'type': 'added'})
#                 elif key not in new_obj:
#                     missing_fields.append(new_path)
#                     differences.append({'path': new_path, 'type': 'missing'})
#                 else:
#                     cls._compare_recursive(old_obj[key], new_obj[key], new_path,
#                                            differences, missing_fields, added_fields)
#
#         elif isinstance(old_obj, list):
#             if len(old_obj) != len(new_obj):
#                 differences.append({
#                     'path': path or 'root',
#                     'type': 'length_change',
#                     'old': len(old_obj),
#                     'new': len(new_obj)
#                 })
#             else:
#                 for i, (item1, item2) in enumerate(zip(old_obj, new_obj)):
#                     cls._compare_recursive(item1, item2, f"{path}[{i}]",
#                                            differences, missing_fields, added_fields)
#
#         elif old_obj != new_obj:
#             differences.append({
#                 'path': path or 'root',
#                 'type': 'value_change',
#                 'old': old_obj,
#                 'new': new_obj
#             })
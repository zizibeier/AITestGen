# common/utils/json_comparator.py
"""参数 JSON 差异对比（纯逻辑，无 Excel 依赖）。

从 legacy_scripts/diffDataJsonExport.py 的 ParameterComparison 迁移而来。
输入是已经解析好的 dict，输出是带中文列名的结果行，便于 excel_reporter 直接消费。
"""

from __future__ import annotations

import json
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from common.utils.logger import log


class ParameterComparison:
    """对比两份 Builder 参数 JSON。"""

    # 标准特征关键词：这类子参数用 interfaceName 组合匹配
    STANDARD_FEATURES = ['键槽', '平面', '孔', '螺纹', '倒角', '圆角', '槽', '凸台', '法兰', '肋板']

    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ==================== 数据提取 ====================

    def extract_component_data(self, data: Dict, data_type: str) -> Dict[str, Dict]:
        """提取组件数据，优先使用 model_interface_id，其次使用 interfaceFullName。"""
        components_data: Dict[str, Dict] = {}

        try:
            if 'params' in data and isinstance(data['params'], list):
                for param_group in data['params']:
                    if 'step' not in param_group or not isinstance(param_group['step'], list):
                        continue

                    for component in param_group['step']:
                        model_key = component.get('model_key', '')
                        interface_name = component.get('interfaceName', '')
                        interface_full_name = component.get('interfaceFullName', '')
                        model_interface_id = component.get('model_interface_id', '')

                        if model_interface_id:
                            component_identifier = model_interface_id
                        elif interface_full_name:
                            component_identifier = interface_full_name
                        elif interface_name:
                            component_identifier = interface_name
                        else:
                            component_identifier = f"COMP_{len(components_data)}"

                        component_info = {
                            'model_interface_id': model_interface_id,
                            'name': component.get('name', '未知组件'),
                            'interfaceName': interface_name,
                            'interfaceFullName': interface_full_name,
                            'driveType': component.get('driveType', ''),
                            'value': component.get('value', ''),
                            'origin_value': component.get('origin_value', ''),
                            'equationDesc': component.get('equationDesc', ''),
                            'data_type': data_type,
                            'model_key': model_key,
                            'sub_params': [],
                        }

                        if 'params' in component and isinstance(component['params'], list):
                            for sub_param in component['params']:
                                if 'step' not in sub_param or not isinstance(sub_param['step'], list):
                                    continue

                                for param_item in sub_param['step']:
                                    sub_param_info = {
                                        'model_interface_id': param_item.get('model_interface_id', ''),
                                        'name': param_item.get('name', ''),
                                        'interfaceName': param_item.get('interfaceName', ''),
                                        'interfaceFullName': param_item.get('interfaceFullName', ''),
                                        'driveType': param_item.get('driveType', ''),
                                        'value': param_item.get('value', ''),
                                        'origin_value': param_item.get('origin_value', ''),
                                        'equationDesc': param_item.get('equationDesc', ''),
                                    }

                                    if (
                                        sub_param_info['name'] == '材质'
                                        and sub_param_info['driveType'] == 'material'
                                    ):
                                        try:
                                            material_data = json.loads(sub_param_info['value'])
                                            sub_param_info['value'] = material_data.get(
                                                'name', sub_param_info['value']
                                            )
                                        except (TypeError, ValueError):
                                            pass

                                    component_info['sub_params'].append(sub_param_info)

                        components_data[component_identifier] = component_info

        except Exception as exc:
            log.error(f"提取组件数据时出错: {exc}")
            log.debug(traceback.format_exc())

        return components_data

    # ==================== 主对比入口 ====================

    def compare_datasets(
        self,
        old_data: Dict,
        new_data: Dict,
        modelname: str = '',
        model_fullname: str = '',
        model_key: str = '',
        attr_info: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """对比两个数据集，生成指定格式的对比结果。"""
        old_components = self.extract_component_data(old_data, 'old')
        new_components = self.extract_component_data(new_data, 'new')

        old_ids = {item['model_interface_id'] for item in old_components.values() if item.get('model_interface_id')}
        new_ids = {item['model_interface_id'] for item in new_components.values() if item.get('model_interface_id')}
        common_ids = old_ids & new_ids

        log.info(f"旧组件ID数量: {len(old_ids)}, 新组件ID数量: {len(new_ids)}, 共同ID数量: {len(common_ids)}")

        all_components: Dict[str, Dict[str, Any]] = {}

        for old_component in old_components.values():
            interface_name = old_component.get('interfaceName', '')
            drive_type = old_component.get('driveType', '')
            model_interface_id = old_component.get('model_interface_id', '')

            if model_interface_id and model_interface_id in common_ids:
                key = f"ID:{model_interface_id}"
            else:
                key = f"NAME:{interface_name}|{drive_type}"

            if key not in all_components:
                all_components[key] = {
                    'old': None,
                    'new': None,
                    'match_type': 'ID匹配' if key.startswith('ID:') else '组合匹配',
                }
            all_components[key]['old'] = old_component

        for new_component in new_components.values():
            interface_name = new_component.get('interfaceName', '')
            drive_type = new_component.get('driveType', '')
            model_interface_id = new_component.get('model_interface_id', '')

            if model_interface_id and model_interface_id in common_ids:
                key = f"ID:{model_interface_id}"
            else:
                key = f"NAME:{interface_name}|{drive_type}"

            if key not in all_components:
                all_components[key] = {
                    'old': None,
                    'new': None,
                    'match_type': 'ID匹配' if key.startswith('ID:') else '组合匹配',
                }
            all_components[key]['new'] = new_component

        all_comparison_results: List[Dict] = []
        changed_results: List[Dict] = []
        unchanged_results: List[Dict] = []

        for components in all_components.values():
            match_type = components['match_type']

            component_comparisons = self._compare_component_level(
                components['old'], components['new'], match_type
            )
            all_comparison_results.extend(component_comparisons)
            self._split_by_status(component_comparisons, changed_results, unchanged_results)

            sub_param_comparisons = self._compare_sub_params_level(
                components['old'], components['new']
            )
            all_comparison_results.extend(sub_param_comparisons)
            self._split_by_status(sub_param_comparisons, changed_results, unchanged_results)

        self._add_user_input_column(all_comparison_results, attr_info)
        self._add_user_input_column(changed_results, attr_info)
        self._add_user_input_column(unchanged_results, attr_info)

        return {
            'modelname': modelname,
            'model_fullname': model_fullname,
            'model_key': model_key,
            'attr_info': attr_info,
            'comparison_time': self.timestamp,
            'total_results': len(all_comparison_results),
            'all_comparison_results': all_comparison_results,
            'changed_results': changed_results,
            'unchanged_results': unchanged_results,
            'unchanged_count': len(unchanged_results),
            'has_changes': len(changed_results) > 0,
            'changes_count': len(changed_results),
        }

    @staticmethod
    def _split_by_status(
        comparisons: List[Dict], changed_results: List[Dict], unchanged_results: List[Dict]
    ):
        for comparison in comparisons:
            if comparison['状态'] != '未变化':
                changed_results.append(comparison)
            else:
                unchanged_results.append(comparison)

    # ==================== 组件级对比 ====================

    def _compare_component_level(
        self, old_component: Optional[Dict], new_component: Optional[Dict], match_type: str = "组合匹配"
    ) -> List[Dict]:
        results: List[Dict] = []

        if not old_component and not new_component:
            return results

        if not old_component and new_component:
            status = '新增'
            model_interface_id = new_component.get('model_interface_id', '')
            name = new_component.get('name', '')
            interface_name = new_component.get('interfaceName', '')
            interface_full_name = new_component.get('interfaceFullName', '')
            drive_type = new_component.get('driveType', '')
        elif old_component and not new_component:
            status = '删除'
            model_interface_id = old_component.get('model_interface_id', '')
            name = old_component.get('name', '')
            interface_name = old_component.get('interfaceName', '')
            interface_full_name = old_component.get('interfaceFullName', '')
            drive_type = old_component.get('driveType', '')
        else:
            status = self._determine_component_status(old_component, new_component)
            model_interface_id = (
                old_component.get('model_interface_id', '')
                or new_component.get('model_interface_id', '')
            )
            name = old_component.get('name', '')
            interface_name = old_component.get('interfaceName', '')
            interface_full_name = (
                old_component.get('interfaceFullName', '')
                or new_component.get('interfaceFullName', '')
            )
            drive_type = old_component.get('driveType', '')

        old_value = old_component.get('value', '') if old_component else ''
        new_value = new_component.get('value', '') if new_component else ''
        old_origin_value = old_component.get('origin_value', '') if old_component else ''
        new_origin_value = new_component.get('origin_value', '') if new_component else ''
        old_equation = old_component.get('equationDesc', '') if old_component else ''
        new_equation = new_component.get('equationDesc', '') if new_component else ''

        results.append(
            {
                '参数标识': interface_full_name,
                '名称': name,
                '接口名': interface_name,
                '类型': drive_type,
                '状态': status,
                '旧匹配值': old_value,
                '新匹配值': new_value,
                '值变更': '否' if self._is_value_equal(old_value, new_value) else '是',
                '方程式': self._format_equation(old_equation, new_equation),
                '旧参数值': old_origin_value,
                '新参数值': new_origin_value,
                '参数类别': '组件参数',
                '用户输入': '',
                'model_interface_id': model_interface_id,
                '匹配方式': match_type,
            }
        )
        return results

    # ==================== 子参数级对比 ====================

    def _compare_sub_params_level(
        self, old_component: Optional[Dict], new_component: Optional[Dict]
    ) -> List[Dict]:
        results: List[Dict] = []

        old_sub_params = old_component.get('sub_params', []) if old_component else []
        new_sub_params = new_component.get('sub_params', []) if new_component else []

        old_parent_ifn = old_component.get('interfaceFullName', '') if old_component else ''
        new_parent_ifn = new_component.get('interfaceFullName', '') if new_component else ''
        parent_ifn = new_parent_ifn or old_parent_ifn

        all_sub_params: Dict[str, Dict[str, Optional[Dict]]] = {}

        for old_sub in old_sub_params:
            identifier = self._sub_param_identifier(old_sub)
            all_sub_params.setdefault(identifier, {'old': None, 'new': None})
            all_sub_params[identifier]['old'] = old_sub

        for new_sub in new_sub_params:
            identifier = self._sub_param_identifier(new_sub)
            all_sub_params.setdefault(identifier, {'old': None, 'new': None})
            all_sub_params[identifier]['new'] = new_sub

        for identifier, params in sorted(all_sub_params.items()):
            old_sub = params['old']
            new_sub = params['new']

            if not old_sub and new_sub:
                status = '新增'
            elif old_sub and not new_sub:
                status = '删除'
            elif old_sub and new_sub:
                status = self._determine_param_status(old_sub, new_sub)
            else:
                continue

            name = old_sub.get('name', '') if old_sub else new_sub.get('name', '')
            interface_name = (
                old_sub.get('interfaceName', '') if old_sub else new_sub.get('interfaceName', '')
            )
            drive_type = (
                old_sub.get('driveType', '') if old_sub else new_sub.get('driveType', '')
            )
            model_interface_id = (
                old_sub.get('model_interface_id', '')
                if old_sub
                else new_sub.get('model_interface_id', '')
            )

            old_interface_fullname = old_sub.get('interfaceFullName', '') if old_sub else ''
            new_interface_fullname = new_sub.get('interfaceFullName', '') if new_sub else ''

            if old_interface_fullname or new_interface_fullname:
                interface_full_name = old_interface_fullname or new_interface_fullname
            elif parent_ifn:
                interface_full_name = f"{parent_ifn}/{name}"
            else:
                interface_full_name = name or interface_name

            old_value = old_sub.get('value', '') if old_sub else ''
            new_value = new_sub.get('value', '') if new_sub else ''
            old_origin_value = old_sub.get('origin_value', '') if old_sub else ''
            new_origin_value = new_sub.get('origin_value', '') if new_sub else ''
            old_equation = old_sub.get('equationDesc', '') if old_sub else ''
            new_equation = new_sub.get('equationDesc', '') if new_sub else ''

            if identifier.startswith("STANDARD:"):
                match_method = "标准特征匹配"
            elif identifier.startswith("ID:"):
                match_method = "ID匹配"
            else:
                match_method = "组合匹配"

            results.append(
                {
                    '参数标识': interface_full_name,
                    '名称': name,
                    '接口名': interface_name,
                    '类型': drive_type,
                    '状态': status,
                    '旧匹配值': old_value,
                    '新匹配值': new_value,
                    '值变更': '否' if self._is_value_equal(old_value, new_value) else '是',
                    '方程式': self._format_equation(old_equation, new_equation),
                    '旧参数值': old_origin_value,
                    '新参数值': new_origin_value,
                    '参数类别': '子参数',
                    '用户输入': '',
                    'model_interface_id': model_interface_id,
                    '匹配方式': match_method,
                }
            )

        return results

    def _sub_param_identifier(self, sub_param: Dict) -> str:
        name = sub_param.get('name', '')
        interface_name = sub_param.get('interfaceName', '')
        drive_type = sub_param.get('driveType', '')
        model_interface_id = sub_param.get('model_interface_id', '')

        is_standard_feature = any(feature in name for feature in self.STANDARD_FEATURES)
        if is_standard_feature:
            return f"STANDARD:{interface_name}"
        if model_interface_id:
            return f"ID:{model_interface_id}"
        return f"OTHER:{interface_name}|{drive_type}"

    # ==================== 用户输入 ====================

    def _add_user_input_column(self, results: List[Dict], attr_info: Optional[List[Dict]]):
        """通过 attr_info 给参数补充“用户输入”列。"""
        if not attr_info:
            return

        for result in results:
            name = result['名称']
            value = result['旧匹配值'] or result['新匹配值']

            matched_attr = None
            for attr in attr_info:
                if attr.get('name', '') == name:
                    matched_attr = attr
                    break

            if not matched_attr:
                continue

            attr_value = matched_attr.get('value')
            if attr_value:
                if str(value) == str(attr_value) or str(attr_value) in str(value):
                    result['用户输入'] = f"{attr_value} (匹配)"
                else:
                    result['用户输入'] = f"{attr_value} (不匹配)"
            else:
                result['用户输入'] = "已配置"

    # ==================== 值/状态判断 ====================

    def _is_value_equal(self, value1, value2) -> bool:
        """判断两个值是否相等（2.00 与 2 视为相等）。"""
        if value1 == value2:
            return True
        if value1 is None and value2 is None:
            return True
        if value1 in ['', None] and value2 in ['', None]:
            return True

        str1 = str(value1).strip() if value1 is not None else ''
        str2 = str(value2).strip() if value2 is not None else ''

        if str1 == str2:
            return True

        def is_numeric_string(text: str) -> bool:
            try:
                float(text.replace(' ', '').replace('"', '').replace("'", ""))
                return True
            except (ValueError, TypeError):
                return False

        if is_numeric_string(str1) and is_numeric_string(str2):
            try:
                num1 = float(str1.replace(' ', '').replace('"', '').replace("'", ""))
                num2 = float(str2.replace(' ', '').replace('"', '').replace("'", ""))
                return abs(num1 - num2) <= 1e-10
            except (ValueError, TypeError):
                pass

        if (str1.startswith('{') and str1.endswith('}')) or (
            str1.startswith('[') and str1.endswith(']')
        ):
            try:
                return self._simple_json_equal(json.loads(str1), json.loads(str2))
            except (TypeError, ValueError):
                pass

        return False

    def _simple_json_equal(self, data1, data2) -> bool:
        if type(data1) is not type(data2):
            return False

        if isinstance(data1, dict):
            if set(data1.keys()) != set(data2.keys()):
                return False
            return all(
                self._is_value_equal(data1[key], data2[key]) for key in data1
            )

        if isinstance(data1, list):
            if len(data1) != len(data2):
                return False
            return all(
                self._is_value_equal(data1[index], data2[index])
                for index in range(len(data1))
            )

        return self._is_value_equal(data1, data2)

    def _determine_component_status(self, old_component: Dict, new_component: Dict) -> str:
        if not old_component and new_component:
            return '新增'
        if old_component and not new_component:
            return '删除'
        if not old_component and not new_component:
            return '未知'

        for field in ['interfaceName', 'value', 'origin_value']:
            if not self._is_value_equal(
                old_component.get(field, ''), new_component.get(field, '')
            ):
                return '修改'
        return '未变化'

    def _determine_param_status(self, old_param: Dict, new_param: Dict) -> str:
        if not old_param and new_param:
            return '新增'
        if old_param and not new_param:
            return '删除'
        if not old_param and not new_param:
            return '未知'

        for field in ['interfaceName', 'value', 'origin_value']:
            if not self._is_value_equal(
                str(old_param.get(field, '')), str(new_param.get(field, ''))
            ):
                return '修改'
        return '未变化'

    @staticmethod
    def _format_equation(old_eq: str, new_eq: str) -> str:
        if not old_eq and not new_eq:
            return ''
        if old_eq == new_eq:
            return old_eq
        if old_eq and new_eq:
            return f"旧: {old_eq} → 新: {new_eq}"
        if old_eq:
            return f"旧: {old_eq} → 新: 空"
        return f"旧: 空 → 新: {new_eq}"

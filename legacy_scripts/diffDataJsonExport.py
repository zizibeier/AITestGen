import ast
import json
import pandas as pd
from datetime import datetime
import os
from typing import Dict, List, Any
import traceback
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl import Workbook
import re


class ParameterComparison:
    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def extract_component_data(self, data: Dict, data_type: str) -> Dict[str, Dict]:
        """提取组件数据，优先使用model_interface_id，其次使用interfaceFullName"""
        components_data = {}

        try:
            if 'params' in data and isinstance(data['params'], list):
                for param_group in data['params']:
                    if 'step' in param_group and isinstance(param_group['step'], list):
                        for component in param_group['step']:
                            component_name = component.get('name', '未知组件')
                            model_key = component.get('model_key','')
                            interface_name = component.get('interfaceName', '')
                            interface_full_name = component.get('interfaceFullName', '')
                            model_interface_id = component.get('model_interface_id', '')

                            # 优先使用model_interface_id作为标识
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
                                'name': component_name,
                                'interfaceName': interface_name,
                                'interfaceFullName': interface_full_name,
                                'driveType': component.get('driveType', ''),
                                'value': component.get('value', ''),
                                'origin_value': component.get('origin_value', ''),
                                'equationDesc': component.get('equationDesc', ''),
                                'data_type': data_type,
                                'model_key': model_key,
                                'sub_params': []
                            }

                            if 'params' in component and isinstance(component['params'], list):
                                for sub_param in component['params']:
                                    if 'step' in sub_param and isinstance(sub_param['step'], list):
                                        for param_item in sub_param['step']:
                                            # 提取子参数信息
                                            sub_model_interface_id = param_item.get('model_interface_id', '')
                                            sub_name = param_item.get('name', '')
                                            sub_interface_name = param_item.get('interfaceName', '')
                                            sub_interface_full_name = param_item.get('interfaceFullName', '')

                                            sub_param_info = {
                                                'model_interface_id': sub_model_interface_id,
                                                'name': sub_name,
                                                'interfaceName': sub_interface_name,
                                                'interfaceFullName': sub_interface_full_name,
                                                'driveType': param_item.get('driveType', ''),
                                                'value': param_item.get('value', ''),
                                                'origin_value': param_item.get('origin_value', ''),
                                                'equationDesc': param_item.get('equationDesc', '')
                                            }

                                            if sub_param_info['name'] == '材质' and sub_param_info['driveType'] == 'material':
                                                try:
                                                    material_data = json.loads(sub_param_info['value'])
                                                    sub_param_info['value'] = material_data.get('name',sub_param_info['value'])
                                                except:
                                                    pass

                                            component_info['sub_params'].append(sub_param_info)

                            components_data[component_identifier] = component_info

        except Exception as e:
            print(f"提取组件数据时出错: {str(e)}")
            traceback.print_exc()

        return components_data

    def compare_datasets(self, old_data: Dict, new_data: Dict, modelname: str = '',
                         model_fullname: str = '', model_key :str='',attr_info: List[Dict] = None) -> Dict[str, Any]:
        """对比两个数据集，生成指定格式的对比结果"""

        old_components = self.extract_component_data(old_data, 'old')
        new_components = self.extract_component_data(new_data, 'new')
        old_ids= {item['model_interface_id'] for item in old_components.values() if item.get('model_interface_id')}
        new_ids= {item['model_interface_id'] for item in new_components.values() if item.get('model_interface_id')}
        common_ids=old_ids &  new_ids
        print(f"旧组件ID数量: {len(old_ids)}")
        print(f"新组件ID数量: {len(new_ids)}")
        print(f"共同ID数量: {len(common_ids)}")
        # 使用name、interfaceName、driveType作为唯一标识收集所有组件
        all_components_by_id = {}
        all_components_by_name={}
        # 处理旧组件
        for interface_full_name, old_component in old_components.items():
            # name = old_component.get('name', '')
            interface_name = old_component.get('interfaceName', '')
            drive_type = old_component.get('driveType', '')
            identifier = f"{interface_name}|{drive_type}"
            _id=identifier
            model_interface_id=old_component.get('model_interface_id','')
            if model_interface_id and model_interface_id in common_ids:
                key=f"ID:{model_interface_id}"
                # all_components_by_id[model_interface_id] = {'old': None, 'new': None}
                # _id=model_interface_id
            else:
                key=f"NAME:{identifier}"
            # elif identifier not in all_components_by_id:
            #     all_components_by_id[identifier] = {'old': None, 'new': None}
            # all_components_by_id[_id]['old'] = old_component
            if key not in all_components_by_id:
                all_components_by_id[key] = {'old': None, 'new': None,
                                             'match_type': 'ID匹配' if 'ID:' in key else '组合匹配'}
            all_components_by_id[key]['old'] = old_component

        # 处理新组件
        for interface_full_name, new_component in new_components.items():
            # name = new_component.get('name', '')
            interface_name = new_component.get('interfaceName', '')
            drive_type = new_component.get('driveType', '')
            model_interface_id=new_component.get('model_interface_id','')
            identifier = f"{interface_name}|{drive_type}"
            # 确定使用的 key：优先使用共同 ID，否则使用名称组合
            if model_interface_id and model_interface_id in common_ids:
                key = f"ID:{model_interface_id}"
            else:
                key = f"NAME:{identifier}"

            if key not in all_components_by_id:
                all_components_by_id[key] = {'old': None, 'new': None,
                                             'match_type': 'ID匹配' if 'ID:' in key else '组合匹配'}
            all_components_by_id[key]['new'] = new_component


        all_comparison_results = []  # 所有参数（包括无变化的）
        changed_results = []  # 有变化的参数
        unchanged_results = []  # 无变化的参数
        # 按照标识排序进行对比
        for key, components in all_components_by_id.items():
            old_component = components['old']
            new_component = components['new']
            match_type = components['match_type']

            # 对比组件自身
            component_comparisons = self._compare_component_level(old_component, new_component, match_type)
            all_comparison_results.extend(component_comparisons)

            for comp in component_comparisons:
                if comp['状态'] != '未变化':
                    changed_results.append(comp)
                else:
                    unchanged_results.append(comp)

            # 对比子参数
            sub_param_comparisons = self._compare_sub_params_level(old_component, new_component)
            all_comparison_results.extend(sub_param_comparisons)

            for comp in sub_param_comparisons:
                if comp['状态'] != '未变化':
                    changed_results.append(comp)
                else:
                    unchanged_results.append(comp)

        # 添加用户输入列
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
            'changes_count': len(changed_results)
        }

    def _compare_component_level(self, old_component: Dict, new_component: Dict,match_type:str="组合匹配") -> List[Dict]:
        """对比组件级别的参数"""
        results = []

        # 获取组件信息
        old_model_interface_id = old_component.get('model_interface_id', '') if old_component else ''
        old_name = old_component.get('name', '') if old_component else ''
        old_interface_name = old_component.get('interfaceName', '') if old_component else ''
        old_drive_type = old_component.get('driveType', '') if old_component else ''

        new_model_interface_id = new_component.get('model_interface_id', '') if new_component else ''
        new_name = new_component.get('name', '') if new_component else ''
        new_interface_name = new_component.get('interfaceName', '') if new_component else ''
        new_drive_type = new_component.get('driveType', '') if new_component else ''


        # if old_model_interface_id or new_model_interface_id:
        #     match_method = "ID匹配"
        # else:
        #     match_method = "组合匹配"

        # 根据是否存在确定状态
        if not old_component and new_component:
            status = '新增'
            model_interface_id = new_model_interface_id
            name = new_name
            interface_name = new_interface_name
            interface_full_name = new_component.get('interfaceFullName', '')
            drive_type = new_drive_type
        elif old_component and not new_component:
            status = '删除'
            model_interface_id = old_model_interface_id
            name = old_name
            interface_name = old_interface_name
            interface_full_name = old_component.get('interfaceFullName', '')
            drive_type = old_drive_type
        elif old_component and new_component:
            # 检查是否有修改
            status = self._determine_component_status(old_component, new_component)
            model_interface_id = old_model_interface_id or new_model_interface_id
            name = old_name
            interface_name = old_interface_name
            interface_full_name = old_component.get('interfaceFullName', '') or new_component.get('interfaceFullName',
                                                                                                  '')
            drive_type = old_drive_type
        else:
            return results

        old_value = old_component.get('value', '') if old_component else ''
        new_value = new_component.get('value', '') if new_component else ''
        old_origin_value = old_component.get('origin_value', '') if old_component else ''
        new_origin_value = new_component.get('origin_value', '') if new_component else ''
        old_equation = old_component.get('equationDesc', '') if old_component else ''
        new_equation = new_component.get('equationDesc', '') if new_component else ''

        # 如果值相等，value_changed 应该是'否'
        value_changed = '否' if self._is_value_equal(old_value, new_value) else '是'

        result = {
            '参数标识': interface_full_name,
            '名称': name,
            '接口名': interface_name,
            '类型': drive_type,
            '状态': status,
            '旧匹配值': old_value,
            '新匹配值': new_value,
            '值变更': value_changed,
            '方程式': self._format_equation(old_equation, new_equation),
            '旧参数值': old_origin_value,
            '新参数值': new_origin_value,
            '参数类别': '组件参数',
            '用户输入': '',
            'model_interface_id': model_interface_id,
            '匹配方式': match_type  # 添加匹配方式
        }

        results.append(result)
        return results


    def _compare_sub_params_level(self, old_component: Dict, new_component: Dict) -> List[Dict]:
        """对比子参数级别的参数 - 根据特征类型使用不同的匹配策略"""
        results = []

        old_sub_params = old_component.get('sub_params', []) if old_component else []
        new_sub_params = new_component.get('sub_params', []) if new_component else []
        # 获取父组件的标识（用于构建完整路径）
        old_parent_ifn = old_component.get('interfaceFullName', '') if old_component else ''
        new_parent_ifn = new_component.get('interfaceFullName', '') if new_component else ''

        # 优先使用新数据的父组件名，如果没有则用旧数据的
        parent_ifn = new_parent_ifn or old_parent_ifn
        # 定义标准特征关键词列表
        standard_features = ['键槽', '平面', '孔', '螺纹', '倒角', '圆角', '槽', '凸台', '法兰', '肋板']

        # 收集所有子参数，根据特征类型使用不同的匹配策略
        all_sub_params = {}

        # 处理旧子参数
        for old_sub in old_sub_params:
            name = old_sub.get('name', '')
            interface_name = old_sub.get('interfaceName', '')
            drive_type = old_sub.get('driveType', '')
            model_interface_id = old_sub.get('model_interface_id', '')

            # 检查是否是标准特征
            is_standard_feature = any(feature in name for feature in standard_features)

            # 创建唯一标识
            if is_standard_feature:
                # 对于标准特征，使用name和interfaceName的组合
                identifier = f"STANDARD:{interface_name}"
            # elif model_interface_id:
            #     # 对于非标准特征但有model_interface_id的，使用ID
            #     identifier = f"ID:{model_interface_id}"
            else:
                # 其他情况使用组合标识
                identifier = f"OTHER:{interface_name}|{drive_type}"

            if identifier not in all_sub_params:
                all_sub_params[identifier] = {'old': None, 'new': None}
            all_sub_params[identifier]['old'] = old_sub

        # 处理新子参数
        for new_sub in new_sub_params:
            name = new_sub.get('name', '')
            interface_name = new_sub.get('interfaceName', '')
            drive_type = new_sub.get('driveType', '')
            model_interface_id = new_sub.get('model_interface_id', '')

            # 检查是否是标准特征
            is_standard_feature = any(feature in name for feature in standard_features)

            # 创建唯一标识
            if is_standard_feature:
                # 对于标准特征，使用name和interfaceName的组合
                identifier = f"STANDARD:{interface_name}"
            elif model_interface_id:
                # 对于非标准特征但有model_interface_id的，使用ID
                identifier = f"ID:{model_interface_id}"
            else:
                # 其他情况使用组合标识
                identifier = f"OTHER:{interface_name}|{drive_type}"

            if identifier not in all_sub_params:
                all_sub_params[identifier] = {'old': None, 'new': None}
            all_sub_params[identifier]['new'] = new_sub

        # 对比每个唯一的子参数
        for identifier, params in sorted(all_sub_params.items()):
            old_sub = params['old']
            new_sub = params['new']

            # 确定状态
            if not old_sub and new_sub:
                status = '新增'
            elif old_sub and not new_sub:
                status = '删除'
            elif old_sub and new_sub:
                # 进一步判断是否有实际变化
                status = self._determine_param_status(old_sub, new_sub)
            else:
                continue

            name = old_sub.get('name', '') if old_sub else new_sub.get('name', '')
            interface_name = old_sub.get('interfaceName', '') if old_sub else new_sub.get('interfaceName', '')
            drive_type = old_sub.get('driveType', '') if old_sub else new_sub.get('driveType', '')
            model_interface_id = old_sub.get('model_interface_id', '') if old_sub else new_sub.get('model_interface_id',
                                                                                                   '')

            # 构建参数标识
            old_interface_fullname = old_sub.get('interfaceFullName', '') if old_sub else ''
            new_interface_fullname = new_sub.get('interfaceFullName', '') if new_sub else ''

            if old_interface_fullname or new_interface_fullname:
                interface_full_name = old_interface_fullname or new_interface_fullname
            else:
                # 基于父组件构造
                parent_ifn = ''
                if old_component:
                    parent_ifn = old_component.get('interfaceFullName', '')
                elif new_component:
                    parent_ifn = new_component.get('interfaceFullName', '')

                if parent_ifn:
                    interface_full_name = f"{parent_ifn}/{name}"
                else:
                    interface_full_name = name or interface_name

            old_value = old_sub.get('value', '') if old_sub else ''
            new_value = new_sub.get('value', '') if new_sub else ''
            old_origin_value = old_sub.get('origin_value', '') if old_sub else ''
            new_origin_value = new_sub.get('origin_value', '') if new_sub else ''
            old_equation = old_sub.get('equationDesc', '') if old_sub else ''
            new_equation = new_sub.get('equationDesc', '') if new_sub else ''

            # 如果值相等，value_changed 应该是'否'
            value_changed = '否' if self._is_value_equal(old_value, new_value) else '是'

            # 添加匹配方式标记
            match_method = ""
            if identifier.startswith("STANDARD:"):
                match_method = "标准特征匹配"
            elif identifier.startswith("ID:"):
                match_method = "ID匹配"
            else:
                match_method = "组合匹配"

            result = {
                '参数标识': interface_full_name,
                '名称': name,
                '接口名': interface_name,
                '类型': drive_type,
                '状态': status,
                '旧匹配值': old_value,
                '新匹配值': new_value,
                '值变更': value_changed,
                '方程式': self._format_equation(old_equation, new_equation),
                '旧参数值': old_origin_value,
                '新参数值': new_origin_value,
                '参数类别': '子参数',
                '用户输入': '',
                'model_interface_id': model_interface_id,
                '匹配方式': match_method  # 添加匹配方式列
            }

            results.append(result)

        return results


    def _add_user_input_column(self, results: List[Dict], attr_info: List[Dict]):
        """添加用户输入列（通过attr参数绑定）"""
        if not attr_info:
            return

        for result in results:
            name = result['名称']
            value = result['旧匹配值'] or result['新匹配值']

            matched_attr = None
            for attr in attr_info:
                attr_name = attr.get('name', '')
                if attr_name == name:
                    matched_attr = attr
                    break

            if matched_attr:
                attr_value = matched_attr.get('value')
                if attr_value:
                    if str(value) == str(attr_value) or str(attr_value) in str(value):
                        result['用户输入'] = f"{attr_value} (匹配)"
                    else:
                        result['用户输入'] = f"{attr_value} (不匹配)"
                else:
                    result['用户输入'] = f"已配置"

    def _is_value_equal(self, value1, value2) -> bool:
        """判断两个值是否相等（支持数值比较，如2.00和2视为相等）"""
        # 如果两个值完全相同
        if value1 == value2:
            return True

        # 如果两个都是None或空值
        if value1 is None and value2 is None:
            return True
        if value1 in ['', None] and value2 in ['', None]:
            return True

        # 转换为字符串
        str1 = str(value1).strip() if value1 is not None else ''
        str2 = str(value2).strip() if value2 is not None else ''

        # 如果字符串相同
        if str1 == str2:
            return True

        # 特殊处理：检查是否为数值（包含小数点和负号）
        def is_numeric_string(s):
            try:
                # 移除所有空白和可能的引号
                s = s.replace(' ', '').replace('"', '').replace("'", "")
                # 检查是否为数值
                float(s)
                return True
            except (ValueError, TypeError):
                return False

        # 如果两个都是数值字符串，进行数值比较
        if is_numeric_string(str1) and is_numeric_string(str2):
            try:
                num1 = float(str1.replace(' ', '').replace('"', '').replace("'", ""))
                num2 = float(str2.replace(' ', '').replace('"', '').replace("'", ""))

                # 使用很小的容差比较浮点数
                tolerance = 1e-10
                return abs(num1 - num2) <= tolerance
            except:
                pass

        # 尝试JSON比较（如果看起来像JSON）
        if (str1.startswith('{') and str1.endswith('}')) or (str1.startswith('[') and str1.endswith(']')):
            try:
                data1 = json.loads(str1)
                data2 = json.loads(str2)
                # 简单的JSON比较
                return self._simple_json_equal(data1, data2)
            except:
                pass

        # 所有比较都失败，返回不相等
        return False

    def _simple_json_equal(self, data1, data2) -> bool:
        """简单的JSON数据比较"""
        if type(data1) != type(data2):
            return False

        if isinstance(data1, dict):
            if set(data1.keys()) != set(data2.keys()):
                return False

            for key in data1:
                if not self._is_value_equal(data1[key], data2[key]):
                    return False
            return True

        elif isinstance(data1, list):
            if len(data1) != len(data2):
                return False

            for i in range(len(data1)):
                if not self._is_value_equal(data1[i], data2[i]):
                    return False
            return True

        else:
            # 对于基本类型，使用相同的比较逻辑
            return self._is_value_equal(data1, data2)

    def _determine_component_status(self, old_component: Dict, new_component: Dict) -> str:
        """确定组件状态"""
        if not old_component and new_component:
            return '新增'
        elif old_component and not new_component:
            return '删除'
        elif old_component and new_component:
            changed = False
            fields_to_check = [ 'interfaceName', 'value', 'origin_value']

            for field in fields_to_check:
                old_val = old_component.get(field, '')
                new_val = new_component.get(field, '')
                if not self._is_value_equal(old_val, new_val):
                    changed = True
                    break

            return '修改' if changed else '未变化'
        else:
            return '未知'

    def _determine_param_status(self, old_param: Dict, new_param: Dict) -> str:
        """确定参数状态"""
        if not old_param and new_param:
            return '新增'
        elif old_param and not new_param:
            return '删除'
        elif old_param and new_param:
            changed = False
            fields_to_check = [ 'interfaceName', 'value', 'origin_value']

            for field in fields_to_check:
                old_val = old_param.get(field, '')
                new_val = new_param.get(field, '')
                if not self._is_value_equal(str(old_val), str(new_val)):
                    changed = True
                    break

            return '修改' if changed else '未变化'
        else:
            return '未知'

    def _format_equation(self, old_eq: str, new_eq: str) -> str:
        """格式化方程式显示"""
        if not old_eq and not new_eq:
            return ''
        elif old_eq == new_eq:
            return old_eq
        else:
            if old_eq and new_eq:
                return f"旧: {old_eq} → 新: {new_eq}"
            elif old_eq:
                return f"旧: {old_eq} → 新: 空"
            else:
                return f"旧: 空 → 新: {new_eq}"






class ExcelBatchReader:
    """从Excel批量读取对比数据的读取器"""

    def __init__(self, excel_path: str):
        self.excel_path = excel_path

    def read_batch_data(self) -> List[Dict]:
        """
        从Excel读取批量对比数据
        attr_info存在于每一行，和old_data一样的读取方式

        Returns:
            List[Dict]: 对比数据列表，每个元素包含modelname, model_fullname, old_data, new_data, attr_info
        """
        batch_data = []

        try:
            print(f"读取Excel文件: {self.excel_path}")

            df = pd.read_excel(self.excel_path, sheet_name=0)
            print(f"读取到 {len(df)} 行数据")
            print(f"Excel列名: {list(df.columns)}")

            for index, row in df.iterrows():
                modelname = None
                model_fullname = None
                attr_info = None
                model_key=None
                attr_info_str=None
                # 提取模型名称
                for col in ['modelname', 'modelName', '模型名称', 'model_name']:
                    if col in row and pd.notna(row[col]):
                        modelname = str(row[col])
                        break

                # 提取模型全名
                for col in ['model_fullname', 'modelFullname', '模型全名', 'modelFullName']:
                    if col in row and pd.notna(row[col]):
                        model_fullname = str(row[col])
                        break
                # 提取model_key
                for col in ['model_key', 'model_key原始','modelKey']:
                    if col in row and pd.notna(row[col]):
                        model_key = str(row[col])
                        break

                # 提取旧数据
                old_data = self._extract_json_data(row, 'old_data')
                # 提取新数据
                new_data = self._extract_json_data(row, 'new_data')
                # 提取attr_info
                for col in ['attr_info', 'attrInfo', 'attr_info_json']:
                    if col in row and pd.notna(row[col]):
                        attr_info_str = str(row[col])
                        attr_info = self._parse_data_string(attr_info_str)
                        break

                if not modelname:
                    modelname = f'模型_{index + 1}'
                if not model_fullname:
                    model_fullname = modelname

                if old_data and new_data:
                    batch_item = {
                        'modelname': modelname,
                        'model_fullname': model_fullname,
                        'model_key': model_key,
                        'old_data': old_data,
                        'new_data': new_data,
                        'attr_info': attr_info,
                        'attr_info_str':attr_info_str,
                    }
                    batch_data.append(batch_item)

                    print(f"✓ 第{index + 1}行: {modelname}")
                    if attr_info:
                        print(f"   读取到attr_info参数: {len(attr_info)}个")
                else:
                    print(f"✗ 第{index + 1}行数据不完整，已跳过")

        except Exception as e:
            print(f"读取Excel文件时出错: {str(e)}")
            traceback.print_exc()

        print(f"\n总共读取到 {len(batch_data)} 个有效模型的对比数据")
        return batch_data

    def _extract_json_data(self, row: pd.Series, column_prefix: str) -> Dict:
        """从行数据中提取JSON数据"""
        data = None

        possible_columns = [
            f'{column_prefix}_json',
            f'{column_prefix}_path',
            column_prefix,
            f'{column_prefix}Data',
            f'{column_prefix}Json'
        ]

        for col_name in possible_columns:
            if col_name in row and pd.notna(row[col_name]):
                cell_value = row[col_name]

                if isinstance(cell_value, str):
                    if col_name.endswith('_path'):
                        try:
                            with open(cell_value, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                break
                        except:
                            continue
                    else:
                        # 尝试解析JSON字符串
                        try:
                            data = json.loads(cell_value)
                            break
                        except json.JSONDecodeError:
                            # 如果失败，尝试修复字符串
                            try:
                                # 移除可能的转义字符
                                fixed_str = cell_value.strip()
                                # 处理单引号
                                if fixed_str.startswith("'") and fixed_str.endswith("'"):
                                    fixed_str = fixed_str[1:-1]
                                # 替换单引号为双引号
                                fixed_str = fixed_str.replace("'", '"')
                                # 处理双引号转义
                                fixed_str = fixed_str.replace('\\"', '"')
                                data = json.loads(fixed_str)
                                break
                            except:
                                continue
                elif isinstance(cell_value, dict):
                    data = cell_value
                    break

        return data or {}

    def _parse_data_string(self, data_str: str) -> List[Dict]:
        """解析数据字符串（支持单引号和双引号JSON）"""
        if not data_str or not isinstance(data_str, str):
            return []

        data_str = data_str.strip()
        if not data_str or data_str.lower() in ['none', 'null', '']:
            return []

        try:
            # 方法1: 使用ast.literal_eval（最安全，支持Python字面量）
            parsed = ast.literal_eval(data_str)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                return [parsed]
            return []
        except (SyntaxError, ValueError) as e:
            try:
                # 方法2: 尝试标准JSON解析（双引号）
                parsed = json.loads(data_str)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict):
                    return [parsed]
                return []
            except json.JSONDecodeError:
                try:
                    # 方法3: 单引号替换后解析
                    # 将单引号替换为双引号，但要小心处理转义
                    fixed_str = data_str.replace("'", '"')
                    parsed = json.loads(fixed_str)
                    if isinstance(parsed, list):
                        return parsed
                    elif isinstance(parsed, dict):
                        return [parsed]
                    return []
                except:
                    print(f"无法解析数据字符串: {data_str[:100]}...")
                    return []


class BatchParameterComparison:
    """批量参数对比处理器 - 每个模型完整对比，每sheet页200个模型"""

    def __init__(self, output_dir: str = '批量对比报告'):
        self.output_dir = output_dir
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs(output_dir, exist_ok=True)

        # 询问用户要显示多少条无变化模型详情
        self.no_change_display_count = self._ask_no_change_display_count()

        # 定义样式
        self.styles = {
            'title_fill': PatternFill(start_color='366092', end_color='366092', fill_type='solid'),
            'title_font': Font(color='FFFFFF', bold=True),

            'header_fill': PatternFill(start_color='4F81BD', end_color='4F81BD', fill_type='solid'),
            'header_font': Font(color='FFFFFF', bold=True),

            'model_title_fill': PatternFill(start_color='E6F3FF', end_color='E6F3FF', fill_type='solid'),
            'model_title_font': Font(bold=True),

            'model_info_fill': PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid'),

            'changed_fill': PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid'),
            'added_fill': PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid'),
            'removed_fill': PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid'),

            'border': Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            ),

            'center_align': Alignment(horizontal='center', vertical='center'),
            'left_align': Alignment(horizontal='left', vertical='center')
        }

    def _ask_no_change_display_count(self) -> int:
        """询问用户要显示多少条无变化模型详情"""
        try:
            count = input("\n要显示多少条无变化模型的匹配详情？(输入0跳过，默认显示5条): ").strip()
            if not count:
                return 5
            count_int = int(count)
            if count_int < 0:
                print("输入无效，将显示5条无变化模型详情")
                return 5
            return count_int
        except ValueError:
            print("输入无效，将显示5条无变化模型详情")
            return 5

    def generate_batch_report(self, batch_comparisons: List[Dict]):
        """生成批量报告，每个sheet页最多200个模型的完整对比"""

        all_model_results = []

        print(f"\n开始处理 {len(batch_comparisons)} 个模型...")

        # 处理所有模型
        for idx, comparison in enumerate(batch_comparisons, 1):
            try:
                print(f"处理第 {idx}/{len(batch_comparisons)} 个模型: {comparison['modelname']}")

                comparator = ParameterComparison()
                result = comparator.compare_datasets(
                    comparison['old_data'],
                    comparison['new_data'],
                    comparison['modelname'],
                    comparison['model_fullname'],
                    comparison['model_key'],
                    comparison.get('attr_info')
                )

                all_model_results.append(result)

                status = "有变化" if result['has_changes'] else "无变化"
                print(f"  状态: {status}, 变化参数: {result['changes_count']}个")

            except Exception as e:
                print(f"  处理失败: {str(e)}")
                traceback.print_exc()

        # 分离有变化和无变化的模型
        changed_models = [r for r in all_model_results if r['has_changes']]
        no_change_models = [r for r in all_model_results if not r['has_changes']]

        # 生成Excel文件
        output_filename = f'批量参数对比_{self.timestamp}.xlsx'
        output_path = os.path.join(self.output_dir, output_filename)

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 1. 创建汇总表
            self._create_summary_sheet(writer, all_model_results, changed_models, no_change_models)

            # 2. 为有变化的模型创建详细对比sheets（每页200个模型）
            if changed_models:
                self._create_changed_models_sheets(writer, changed_models)

            # 3. 创建无变化模型汇总sheet
            if no_change_models:
                self._create_no_change_summary_sheet(writer, no_change_models)

                # 4. 如果用户要求显示无变化模型详情，创建详情sheet
                if self.no_change_display_count > 0 and len(no_change_models) > 0:
                    self._create_no_change_detail_sheet(writer, no_change_models)

        print(f"\n批量报告已生成: {output_path}")
        print(f"总模型数: {len(all_model_results)}")
        print(f"有变化模型数: {len(changed_models)}")
        print(f"无变化模型数: {len(no_change_models)}")

        if self.no_change_display_count > 0 and len(no_change_models) > 0:
            display_count = min(self.no_change_display_count, len(no_change_models))
            print(f"已显示 {display_count} 个无变化模型的匹配详情")

        return output_path

    def _create_summary_sheet(self, writer, all_results: List[Dict],
                              changed_models: List[Dict], no_change_models: List[Dict]):
        """创建汇总工作表"""

        total_models = len(all_results)
        changed_count = len(changed_models)
        no_change_count = len(no_change_models)

        # 准备汇总数据
        summary_rows = []

        # 总体统计
        summary_rows.append({
            '模型型号总数': total_models,
            '有变化模型型号数': changed_count,
            '无变化模型型号数': no_change_count,
            '变化率': f'{(changed_count / total_models * 100):.1f}%' if total_models > 0 else '0%'
        })

        # 空行
        summary_rows.append({})

        # 有变化模型列表
        summary_rows.append({
            '序号': '有变化型号列表',
            '模型标识': '模型全名',
        })

        for idx, model in enumerate(changed_models, 1):
            summary_rows.append({
                '序号': idx,
                '模型名': model['modelname'],
                '变化参数数': f"{model['changes_count']}个",
                '型号': model['model_fullname'],
            })

        # 转换为DataFrame
        summary_df = pd.DataFrame(summary_rows)
        summary_df.to_excel(writer, sheet_name='汇总', index=False)

        worksheet = writer.sheets['汇总']

        # 设置列宽
        worksheet.column_dimensions['A'].width = 15
        worksheet.column_dimensions['B'].width = 25
        worksheet.column_dimensions['C'].width = 20
        worksheet.column_dimensions['D'].width = 40
        worksheet.column_dimensions['E'].width = 20

        # 设置样式
        header_fill = self.styles['title_fill']
        header_font = self.styles['title_font']

        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = self.styles['center_align']

    # 当前代码可能的问题：
    # 1. 合并单元格的坐标计算可能有误
    # 2. 写入的值可能被覆盖了
    # 3. 可能在写入参数数据时覆盖了attr_info单元格

    # 修复方案：
    def _create_changed_models_sheets(self, writer, changed_models: List[Dict]):
        """为有变化的模型创建详细对比sheets，每页200个模型，显示所有参数"""

        total_models = len(changed_models)
        num_sheets = (total_models + 199) // 200  # 每页200个模型

        for sheet_num in range(num_sheets):
            start_idx = sheet_num * 200
            end_idx = min((sheet_num + 1) * 200, total_models)
            sheet_models = changed_models[start_idx:end_idx]

            # 创建sheet名称
            if num_sheets == 1:
                sheet_name = '有变化模型对比'
            else:
                sheet_name = f'有变化模型对比_第{sheet_num + 1}部分'

            # 创建sheet
            workbook = writer.book
            worksheet = workbook.create_sheet(sheet_name)

            current_row = 1

            # 添加sheet标题
            worksheet.merge_cells(f'A{current_row}:P{current_row}')
            title_cell = worksheet[f'A{current_row}']
            title_cell.value = f"有变化模型参数对比（第{sheet_num + 1}/{num_sheets}部分）"
            title_cell.font = Font(bold=True, size=14)
            title_cell.alignment = Alignment(horizontal='center', vertical='center')
            title_cell.fill = PatternFill(start_color='FFD966', end_color='FFD966', fill_type='solid')
            current_row += 2

            # 处理这个sheet中的所有模型
            for model_idx, model_result in enumerate(sheet_models, 1):
                modelname = model_result['modelname']
                model_fullname = model_result['model_fullname']
                model_key = model_result.get('model_key', '')  # 使用get避免KeyError
                all_results = model_result['all_comparison_results']  # 所有参数
                changed_count = model_result['changes_count']
                total_results = model_result['total_results']
                attr_info = model_result.get('attr_info', [])  # 获取attr_info

                # 将attr_info转换为JSON字符串
                attr_json_str = ''
                if attr_info and isinstance(attr_info, list) and len(attr_info) > 0:
                    try:
                        import json
                        # 确保使用正确的编码
                        attr_json_str = json.dumps(attr_info, ensure_ascii=False)
                        # 测试打印出来看看
                        print(f"attr_info JSON: {attr_json_str[:100]}...")
                    except Exception as e:
                        print(f"转换attr_info失败: {str(e)}")
                        attr_json_str = str(attr_info)

                # 计算旧参数数量和新参数数量
                old_params_count = 0
                new_params_count = 0

                for param in all_results:
                    if param.get('旧匹配值', '') or param.get('旧参数值', ''):
                        old_params_count += 1
                    if param.get('新匹配值', '') or param.get('新参数值', ''):
                        new_params_count += 1

                print(f"  写入模型 {model_idx}: {model_fullname} (总参数:{total_results}个, 变化:{changed_count}个)")

                # 1. 添加模型标题
                title_row = current_row
                worksheet.merge_cells(f'A{title_row}:P{title_row}')
                title_cell = worksheet[f'A{title_row}']
                title_cell.value = f"【{model_fullname}】"
                title_cell.font = self.styles['model_title_font']
                title_cell.fill = self.styles['model_title_fill']
                title_cell.alignment = self.styles['center_align']
                title_cell.border = self.styles['border']
                current_row += 1

                # 2. 添加模型基本信息
                info_row = current_row
                worksheet.cell(row=info_row, column=1, value="模型标识:").font = Font(bold=True)
                worksheet.cell(row=info_row, column=2, value=modelname)
                worksheet.cell(row=info_row, column=3, value="model_key:").font = Font(bold=True)
                worksheet.merge_cells(start_row=info_row, start_column=4, end_row=info_row, end_column=7)
                worksheet.cell(row=info_row, column=4, value=model_key)
                worksheet.cell(row=info_row, column=8, value="参数对比:").font = Font(bold=True)
                worksheet.cell(row=info_row, column=9, value=f"旧{old_params_count}->新{new_params_count}")

                # 添加额外的统计信息
                worksheet.cell(row=info_row, column=10, value="总参数:").font = Font(bold=True)
                worksheet.cell(row=info_row, column=11, value=f"{total_results}个")
                worksheet.cell(row=info_row, column=12, value="变化:").font = Font(bold=True)
                worksheet.cell(row=info_row, column=13, value=f"{changed_count}个")

                # 如果有attr_info，添加提示
                if attr_json_str:
                    worksheet.cell(row=info_row, column=14, value="attr_info:").font = Font(bold=True, color='0000FF')
                    worksheet.merge_cells(start_row=info_row, start_column=15, end_row=info_row, end_column=16)
                    attr_cell = worksheet.cell(row=info_row, column=15, value="详见最后一列")
                    attr_cell.font = Font(color='0000FF')
                    attr_cell.alignment = Alignment(horizontal='center', vertical='center')

                current_row += 1

                # 3. 添加空行
                current_row += 1

                # 4. 添加参数对比表头（15列参数 + 1列attr_info = 16列）
                header_row = current_row
                headers = ['参数标识', '名称', '接口名', '类型', '状态',
                           '旧匹配值', '新匹配值', '值变更', '方程式',
                           '旧参数值', '新参数值', '参数类别', '用户输入', 'model_interface_id', '匹配方式']

                # 写入前15列的表头
                for col, header in enumerate(headers, 1):
                    cell = worksheet.cell(row=header_row, column=col, value=header)
                    cell.fill = self.styles['header_fill']
                    cell.font = self.styles['header_font']
                    cell.alignment = self.styles['center_align']
                    cell.border = self.styles['border']

                # 第16列：attr_info表头
                attr_header_cell = worksheet.cell(row=header_row, column=16, value='attr_info')
                attr_header_cell.fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
                attr_header_cell.font = Font(color='FFFFFF', bold=True)
                attr_header_cell.alignment = self.styles['center_align']
                attr_header_cell.border = self.styles['border']

                current_row += 1

                # 5. 记录参数表格的起始行（非常重要！）
                params_start_row = current_row

                # 6. 添加所有参数对比数据（只写入前15列）
                for param in all_results:
                    # 数据列（共15列）
                    data_columns = [
                        '参数标识', '名称', '接口名', '类型', '状态',
                        '旧匹配值', '新匹配值', '值变更', '方程式',
                        '旧参数值', '新参数值', '参数类别', '用户输入', 'model_interface_id', '匹配方式'
                    ]

                    # 只写入前15列数据，第16列保持空白后面再处理
                    for col, col_name in enumerate(data_columns, 1):
                        cell = worksheet.cell(row=current_row, column=col, value=param.get(col_name, ''))
                        cell.border = self.styles['border']
                        cell.alignment = self.styles['left_align']

                    # 根据状态设置行颜色（只设置前15列）
                    status = param.get('状态', '')
                    if status == '新增':
                        fill_color = self.styles['added_fill']
                    elif status == '修改':
                        fill_color = self.styles['changed_fill']
                    elif status == '删除':
                        fill_color = self.styles['removed_fill']
                    elif status == '未变化':
                        # 无变化参数用灰色
                        fill_color = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
                    else:
                        fill_color = None

                    if fill_color:
                        for col in range(1, 16):  # 只设置前15列的颜色
                            worksheet.cell(row=current_row, column=col).fill = fill_color

                    # 值变更列特殊处理（现在是第8列）
                    value_changed = param.get('值变更', '')
                    if value_changed == '是':
                        worksheet.cell(row=current_row, column=8).fill = PatternFill(
                            start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')

                    current_row += 1

                # 7. 记录参数表格的结束行
                params_end_row = current_row - 1

                # 8. 现在处理第16列（attr_info列）的合并和写入
                print(f"   参数行范围: {params_start_row} 到 {params_end_row}")
                print(f"   attr_info长度: {len(attr_json_str) if attr_json_str else 0}")

                if params_start_row <= params_end_row:
                    if attr_json_str and len(attr_json_str.strip()) > 0:
                        # 合并第16列的单元格
                        print(f"   合并单元格: P{params_start_row}:P{params_end_row}")
                        worksheet.merge_cells(start_row=params_start_row, start_column=16,
                                              end_row=params_end_row, end_column=16)

                        # 写入attr_info JSON
                        attr_cell = worksheet.cell(row=params_start_row, column=16, value=attr_json_str)
                        attr_cell.border = self.styles['border']
                        attr_cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
                        attr_cell.font = Font(color='0000FF', size=8, name='微软雅黑')  # 使用中文字体

                        # 设置attr_info单元格的背景色
                        attr_cell.fill = PatternFill(start_color='E6F3FF', end_color='E6F3FF', fill_type='solid')

                        # 设置行高以适应内容
                        num_lines = attr_json_str.count('\n') + 1
                        row_height = min(150, max(20, num_lines * 12))
                        for row in range(params_start_row, params_end_row + 1):
                            worksheet.row_dimensions[row].height = row_height

                        print(f"   成功写入attr_info到合并单元格，行高: {row_height}")
                    else:
                        # 如果没有attr_info，也要合并单元格并留空
                        worksheet.merge_cells(start_row=params_start_row, start_column=16,
                                              end_row=params_end_row, end_column=16)
                        empty_cell = worksheet.cell(row=params_start_row, column=16, value="")
                        empty_cell.border = self.styles['border']
                        empty_cell.fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

                # 9. 在模型之间添加分隔行
                if model_idx < len(sheet_models):
                    current_row += 2
                    worksheet.merge_cells(f'A{current_row}:P{current_row}')
                    separator_cell = worksheet[f'A{current_row}']
                    separator_cell.value = "=" * 80
                    separator_cell.alignment = self.styles['center_align']
                    separator_cell.font = Font(color='808080')
                    current_row += 2

            # 调整列宽 - 保持总宽度不变
            column_widths = {
                'A': 28,  # 参数标识
                'B': 18,  # 名称
                'C': 18,  # 接口名
                'D': 13,  # 类型
                'E': 8,  # 状态
                'F': 13,  # 旧匹配值
                'G': 13,  # 新匹配值
                'H': 8,  # 值变更
                'I': 35,  # 方程式
                'J': 13,  # 旧参数值
                'K': 13,  # 新参数值
                'L': 13,  # 参数类别
                'M': 13,  # 用户输入
                'N': 18,  # model_interface_id
                'O': 13,  # 匹配方式
                'P': 25  # attr_info
            }

            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
    def _create_no_change_summary_sheet(self, writer, no_change_models: List[Dict]):
        """创建无变化模型汇总sheet"""

        summary_data = []
        for model in no_change_models:
            summary_data.append({
                'modelname': model['modelname'],
                'model_fullname': model['model_fullname'],
                '参数总数': model['total_results'],
            })

        total_row = {
            'modelname': '总计',
            'model_fullname': f'共{len(no_change_models)}个模型',
            '参数总数': sum(model['total_results'] for model in no_change_models),
        }

        summary_df = pd.DataFrame([total_row] + summary_data)
        summary_df.to_excel(writer, sheet_name='无变化模型汇总', index=False)

        worksheet = writer.sheets['无变化模型汇总']

        for col in range(1, len(summary_df.columns) + 1):
            worksheet.column_dimensions[chr(64 + col)].width = 20

        header_fill = PatternFill(start_color='00B050', end_color='00B050', fill_type='solid')
        header_font = Font(color='FFFFFF', bold=True)

        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font

    def _create_no_change_detail_sheet(self, writer, no_change_models: List[Dict]):
        """创建无变化模型匹配详情sheet，格式与有变化模型对比相同"""

        # 限制显示数量
        display_count = min(self.no_change_display_count, len(no_change_models))
        display_models = no_change_models[:display_count]

        # 如果没有模型要显示，直接返回
        if display_count == 0:
            return

        # 创建一个sheet
        workbook = writer.book
        worksheet = workbook.create_sheet('无变化模型详情')

        current_row = 1

        # 添加sheet标题
        worksheet.merge_cells(f'A{current_row}:P{current_row}')
        title_cell = worksheet[f'A{current_row}']
        title_cell.value = f"无变化模型参数对比详情（共{display_count}个，总计{len(no_change_models)}个）"
        title_cell.font = Font(bold=True, size=14)
        title_cell.alignment = Alignment(horizontal='center', vertical='center')
        title_cell.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
        current_row += 2

        # 处理要显示的无变化模型
        for model_idx, model_result in enumerate(display_models, 1):
            modelname = model_result['modelname']
            model_fullname = model_result['model_fullname']
            all_results = model_result['all_comparison_results']  # 所有参数
            changed_count = model_result['changes_count']
            total_results = model_result['total_results']
            attr_info = model_result.get('attr_info', [])  # 获取attr_info

            # 计算旧参数数量和新参数数量
            old_params_count = 0
            new_params_count = 0

            for param in all_results:
                if param.get('旧匹配值', '') or param.get('旧参数值', ''):
                    old_params_count += 1
                if param.get('新匹配值', '') or param.get('新参数值', ''):
                    new_params_count += 1

            print(f"  写入无变化模型 {model_idx}: {model_fullname} (总参数:{total_results}个)")

            # 1. 添加模型标题
            title_row = current_row
            worksheet.merge_cells(f'A{title_row}:P{title_row}')
            title_cell = worksheet[f'A{title_row}']
            title_cell.value = f"【{model_fullname}】"
            title_cell.font = self.styles['model_title_font']
            title_cell.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')  # 绿色背景表示无变化
            title_cell.alignment = self.styles['center_align']
            title_cell.border = self.styles['border']
            current_row += 1

            # 2. 添加模型基本信息
            info_row = current_row
            worksheet.cell(row=info_row, column=1, value="模型标识:").font = Font(bold=True)
            worksheet.cell(row=info_row, column=2, value=modelname)
            worksheet.cell(row=info_row, column=3, value="完整名称:").font = Font(bold=True)
            worksheet.merge_cells(start_row=info_row, start_column=4, end_row=info_row, end_column=6)
            worksheet.cell(row=info_row, column=4, value=model_fullname)
            worksheet.cell(row=info_row, column=7, value="参数对比:").font = Font(bold=True)
            worksheet.cell(row=info_row, column=8, value=f"旧{old_params_count}->新{new_params_count}")

            # 添加额外的统计信息
            worksheet.cell(row=info_row, column=9, value="总参数:").font = Font(bold=True)
            worksheet.cell(row=info_row, column=10, value=f"{total_results}个")
            worksheet.cell(row=info_row, column=11, value="变化:").font = Font(bold=True)
            worksheet.cell(row=info_row, column=12, value=f"{changed_count}个")

            # 添加无变化标记
            worksheet.cell(row=info_row, column=13, value="状态:").font = Font(bold=True, color='00B050')
            worksheet.cell(row=info_row, column=14, value="无变化").font = Font(color='00B050', bold=True)

            current_row += 1

            # 3. 如果有attr_info，添加attr_info信息行
            if attr_info and isinstance(attr_info, list) and len(attr_info) > 0:
                attr_row = current_row
                worksheet.cell(row=attr_row, column=1, value="attr_info:").font = Font(bold=True, color='0000FF')
                # 将attr_info转换为字符串显示
                attr_str = ""
                for attr in attr_info:
                    name = attr.get('name', '')
                    value = attr.get('value', '')
                    if name and value:
                        attr_str += f"{name}: {value}, "
                    elif name:
                        attr_str += f"{name}, "

                # 去除最后的逗号和空格
                if attr_str.endswith(", "):
                    attr_str = attr_str[:-2]

                # 合并单元格显示attr_info
                worksheet.merge_cells(start_row=attr_row, start_column=2, end_row=attr_row, end_column=16)
                attr_cell = worksheet.cell(row=attr_row, column=2, value=attr_str)
                attr_cell.font = Font(color='0000FF')
                attr_cell.alignment = Alignment(horizontal='left', vertical='center')
                attr_cell.fill = PatternFill(start_color='E6F3FF', end_color='E6F3FF', fill_type='solid')
                current_row += 1

            # 4. 添加空行
            current_row += 1

            # 5. 添加参数对比表头
            header_row = current_row
            # 包含匹配方式列
            headers = ['参数标识', '名称', '接口名', '类型', '状态',
                       '旧匹配值', '新匹配值', '值变更', '方程式',
                       '旧参数值', '新参数值', '参数类别', '用户输入', 'model_interface_id', '匹配方式']

            for col, header in enumerate(headers, 1):
                cell = worksheet.cell(row=header_row, column=col, value=header)
                cell.fill = self.styles['header_fill']
                cell.font = self.styles['header_font']
                cell.alignment = self.styles['center_align']
                cell.border = self.styles['border']

            current_row += 1

            # 6. 添加所有参数对比数据（包括无变化的）
            for param in all_results:
                # 更新数据列
                data_columns = [
                    '参数标识', '名称', '接口名', '类型', '状态',
                    '旧匹配值', '新匹配值', '值变更', '方程式',
                    '旧参数值', '新参数值', '参数类别', '用户输入', 'model_interface_id', '匹配方式'
                ]

                for col, col_name in enumerate(data_columns, 1):
                    cell = worksheet.cell(row=current_row, column=col, value=param.get(col_name, ''))
                    cell.border = self.styles['border']
                    cell.alignment = self.styles['left_align']

                # 根据状态设置行颜色
                status = param.get('状态', '')
                if status == '新增':
                    fill_color = self.styles['added_fill']
                elif status == '修改':
                    fill_color = self.styles['changed_fill']
                elif status == '删除':
                    fill_color = self.styles['removed_fill']
                elif status == '未变化':
                    # 无变化参数用浅绿色背景
                    fill_color = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
                else:
                    fill_color = None

                if fill_color:
                    for col in range(1, len(headers) + 1):
                        worksheet.cell(row=current_row, column=col).fill = fill_color

                # 值变更列特殊处理（现在是第8列）
                value_changed = param.get('值变更', '')
                if value_changed == '是':
                    worksheet.cell(row=current_row, column=8).fill = PatternFill(
                        start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')

                current_row += 1

            # 7. 在模型之间添加分隔行
            if model_idx < len(display_models):
                current_row += 2
                worksheet.merge_cells(f'A{current_row}:P{current_row}')
                separator_cell = worksheet[f'A{current_row}']
                separator_cell.value = "=" * 80
                separator_cell.alignment = self.styles['center_align']
                separator_cell.font = Font(color='808080')
                current_row += 2

        # 调整列宽
        column_widths = {
            'A': 30, 'B': 20, 'C': 20, 'D': 15, 'E': 10,
            'F': 15,  # F列：旧匹配值
            'G': 15,  # G列：新匹配值
            'H': 10,  # H列：值变更
            'I': 40,  # I列：方程式
            'J': 15,  # J列：旧参数值
            'K': 15,  # K列：新参数值
            'L': 15,  # L列：参数类别
            'M': 15,  # M列：用户输入
            'N': 20,  # N列：model_interface_id
            'O': 15  # O列：匹配方式
        }

        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width





def main():
    """主函数：从Excel读取批量数据并生成对比报告"""

    # excel_file = input("请输入包含对比数据的Excel文件路径: ").strip()
    excel_file=('D:\三维\建模模型\测试报告\建模测试完整报告_20260427_200853.xlsx')
    if not os.path.exists(excel_file):
        print(f"错误: 文件 {excel_file} 不存在")
        return

    print(f"\n正在读取Excel文件: {excel_file}")
    excel_reader = ExcelBatchReader(excel_file)
    batch_data = excel_reader.read_batch_data()

    if not batch_data:
        print("错误: 没有读取到有效的对比数据")
        return

    print(f"\n开始生成批量对比报告...")
    print(f"处理模型数量: {len(batch_data)}")

    batch_processor = BatchParameterComparison(output_dir='批量对比报告')
    report_path = batch_processor.generate_batch_report(batch_data)

    print(f"\n批量报告已生成: {report_path}")
    print("\n报告结构:")
    print("1. 汇总 - 所有模型的对比结果汇总")
    print("2. 有变化参数详情 - 所有有变化的参数详细对比（每sheet最多200条）")
    print("3. 无变化模型汇总 - 无变化模型的统计信息")

    try:
        if os.name == 'nt':  # Windows
            os.startfile('批量对比报告')
        elif os.name == 'posix':  # macOS/Linux
            os.system(f'open "{os.path.dirname(report_path)}"')
    except:
        pass


if __name__ == "__main__":
    try:
        import openpyxl

        print("✓ openpyxl 已安装")
    except ImportError:
        print("✗ 需要安装依赖: pip install pandas openpyxl")
        exit(1)

    main()
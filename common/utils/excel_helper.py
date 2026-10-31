# common/utils/excel_helper.py
"""通用 Excel 读取与合并工具（openpyxl 实现，不依赖 pandas）。

迁移自 legacy_scripts/getRequestData.py 的 read_and_prepare_data / save_results，
以及 legacy_scripts/diffDataJsonExport.py 的 ExcelBatchReader。
"""

from __future__ import annotations

import ast
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from common.utils.logger import log


MODEL_NAME_COLUMNS = ['modelname', 'modelName', '模型名称', 'model_name']
MODEL_FULLNAME_COLUMNS = ['model_fullname', 'modelFullname', '模型全名', 'modelFullName']
MODEL_KEY_COLUMNS = ['model_key', 'model_key原始', 'modelKey']
ATTR_INFO_COLUMNS = ['attr_info', 'attrInfo', 'attr_info_json']


# ==================== 读取 ====================

def _normalize_cell(value: Any) -> Any:
    """空字符串转 None，字符串去首尾空白；其他类型原样保留。"""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return value


def _build_headers(header_row: Tuple[Any, ...]) -> List[str]:
    headers: List[str] = []
    seen: Dict[str, int] = {}

    for index, value in enumerate(header_row, start=1):
        name = str(value).strip() if value is not None else f"column{index}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        headers.append(name)
    return headers


def _read_sheet(
    file_path: str, sheet_name: Optional[str] = None
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """读取 sheet，返回 (表头, 记录列表)；记录里带 _excel_row 表示真实行号。"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Excel 文件不存在: {path}")

    workbook = load_workbook(filename=str(path), data_only=True, read_only=True)
    try:
        worksheet = workbook[sheet_name] if sheet_name else workbook.worksheets[0]
        iterator = worksheet.iter_rows(values_only=True)

        try:
            header_row = next(iterator)
        except StopIteration:
            return [], []

        headers = _build_headers(header_row)
        records: List[Dict[str, Any]] = []

        for excel_row, values in enumerate(iterator, start=2):
            values = tuple(values)
            if not any(value is not None for value in values):
                continue

            record: Dict[str, Any] = {}
            for index, header in enumerate(headers):
                value = values[index] if index < len(values) else None
                record[header] = _normalize_cell(value)
            record['_excel_row'] = excel_row
            records.append(record)

        return headers, records
    finally:
        workbook.close()


def read_and_prepare_data(
    file_path: str, sheet_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """读取建模测试数据：空单元格转 None，并补充 _row_id（Excel 真实行号）。"""
    headers, records = _read_sheet(file_path, sheet_name)
    log.info(f"读取到 {len(records)} 行数据, 列: {headers}")

    required_columns = ['modelKey', 'attr_info']
    missing = [column for column in required_columns if column not in headers]
    if missing:
        log.warning(f"缺少必要列: {missing}")

    for record in records:
        record['_row_id'] = record.pop('_excel_row')

    for record in records[:3]:
        attr_length = len(str(record.get('attr_info'))) if record.get('attr_info') else 0
        log.debug(
            f"数据预览 行{record['_row_id']}: modelKey={record.get('modelKey')}, "
            f"attr_info长度={attr_length}"
        )

    return records


def read_batch_comparison_data(
    file_path: str, sheet_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """读取批量对比数据（old_data / new_data / attr_info）。"""
    _, records = _read_sheet(file_path, sheet_name)
    batch_data: List[Dict[str, Any]] = []

    for index, record in enumerate(records):
        modelname = _first_value(record, MODEL_NAME_COLUMNS)
        model_fullname = _first_value(record, MODEL_FULLNAME_COLUMNS)
        model_key = _first_value(record, MODEL_KEY_COLUMNS)
        attr_info_str = _first_value(record, ATTR_INFO_COLUMNS)

        old_data = _extract_json_data(record, 'old_data')
        new_data = _extract_json_data(record, 'new_data')

        if not old_data or not new_data:
            log.warning(f"第 {index + 1} 行数据不完整，已跳过")
            continue

        batch_data.append(
            {
                'modelname': str(modelname) if modelname else f'模型_{index + 1}',
                'model_fullname': str(model_fullname) if model_fullname else (
                    str(modelname) if modelname else f'模型_{index + 1}'
                ),
                'model_key': str(model_key) if model_key else None,
                'old_data': old_data,
                'new_data': new_data,
                'attr_info': parse_attr_info(attr_info_str),
                'attr_info_str': str(attr_info_str) if attr_info_str else None,
            }
        )

    log.info(f"共读取到 {len(batch_data)} 个有效模型的对比数据")
    return batch_data


def _first_value(record: Dict[str, Any], columns: List[str]) -> Any:
    for column in columns:
        if column in record and record[column] is not None:
            return record[column]
    return None


def _extract_json_data(record: Dict[str, Any], column_prefix: str) -> Dict[str, Any]:
    """从行记录中提取 JSON：支持 JSON 字符串、dict、以及 *_path 指向的文件。"""
    possible_columns = [
        f'{column_prefix}_json',
        f'{column_prefix}_path',
        column_prefix,
        f'{column_prefix}Data',
        f'{column_prefix}Json',
    ]

    for column in possible_columns:
        value = record.get(column)
        if value is None:
            continue

        if isinstance(value, dict):
            return value

        if not isinstance(value, str):
            continue

        if column.endswith('_path'):
            try:
                with open(value, 'r', encoding='utf-8') as file_obj:
                    return json.load(file_obj)
            except (OSError, ValueError) as exc:
                log.warning(f"读取 JSON 文件失败 {value}: {exc}")
                continue

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            try:
                fixed = value.strip().strip("'").replace("'", '"').replace('\\"', '"')
                return json.loads(fixed)
            except (ValueError, AttributeError):
                continue

    return {}


# ==================== attr_info ====================

def parse_attr_info(raw: Any) -> List[Dict[str, Any]]:
    """安全解析 attr_info，支持 JSON / Python 字面量。"""
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return [raw]
    if not isinstance(raw, str):
        return []

    text = raw.strip()
    if not text or text.lower() in ('none', 'null'):
        return []

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError:
        pass

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
    except (SyntaxError, ValueError):
        pass

    if 'name' in text and 'value' in text:
        result = []
        for item in text.split('}, {'):
            item = item.replace('{', '').replace('}', '').strip()
            param: Dict[str, str] = {}
            for part in item.split(', '):
                if ':' not in part:
                    continue
                key, value = part.split(':', 1)
                param[key.strip().strip("'\"")] = value.strip().strip("'\"")
            if param:
                result.append(param)
        if result:
            return result

    log.warning(f"无法解析 attr_info: {text[:100]}...")
    return []


# ==================== 合并保存 ====================

def save_results(
    original_excel_path: str,
    results_data_list: List[Dict[str, Any]],
    output_dir: str,
    timestamp_str: Optional[str] = None,
    join_key: str = '_row_id',
) -> str:
    """把测试结果按 join_key 合并回原始 Excel 并保存。"""
    original_headers, original_records = _read_sheet(original_excel_path)
    for record in original_records:
        record.pop('_excel_row', None)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if timestamp_str is None:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f'建模测试完整报告_{timestamp_str}.xlsx'

    results = list(results_data_list or [])
    result_columns = _ordered_columns(results)

    effective_join_key = join_key
    if results and join_key not in result_columns:
        alternative = '测试request_key' if join_key == '_row_id' else '_row_id'
        if alternative in result_columns:
            effective_join_key = alternative
        else:
            effective_join_key = None

    if results and effective_join_key and effective_join_key not in original_headers:
        if effective_join_key == '_row_id':
            for index, record in enumerate(original_records):
                record['_row_id'] = index + 2
            original_headers = original_headers + ['_row_id']
        else:
            log.warning(f"原始数据中无 '{effective_join_key}' 列，改用按行拼接")
            effective_join_key = None

    if not results:
        merged_headers = original_headers
        merged_rows = original_records
    elif effective_join_key:
        merged_headers, merged_rows = _merge_by_key(
            original_headers, original_records, results, effective_join_key
        )
    else:
        merged_headers, merged_rows = _merge_by_position(
            original_headers, original_records, results
        )

    _write_merged_workbook(output_file, merged_headers, merged_rows)

    log.info(f"合并报告已保存至: {output_file}")
    if results and '状态' in merged_headers:
        success_count = sum(1 for row in merged_rows if row.get('状态') == '成功')
        total_count = len(merged_rows)
        if total_count:
            log.info(
                f"测试成功率: {success_count}/{total_count} "
                f"({success_count / total_count * 100:.1f}%)"
            )

    return str(output_file)


def _ordered_columns(records: List[Dict[str, Any]]) -> List[str]:
    columns: List[str] = []
    for record in records:
        for key in record.keys():
            if key not in columns:
                columns.append(key)
    return columns


def _rename_result_columns(
    original_headers: List[str], result_columns: List[str], join_key: Optional[str]
) -> Dict[str, str]:
    """结果列与原始列重名时加 _测试 后缀（等价 pandas suffixes）。"""
    rename_map: Dict[str, str] = {}
    used = set(original_headers)

    for column in result_columns:
        if column == join_key or column not in original_headers:
            rename_map[column] = column
            continue

        new_name = f'{column}_测试'
        suffix = 2
        while new_name in used:
            new_name = f'{column}_测试_{suffix}'
            suffix += 1
        rename_map[column] = new_name
        used.add(new_name)

    return rename_map


def _merge_by_key(
    original_headers: List[str],
    original_records: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    join_key: str,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    result_columns = _ordered_columns(results)
    rename_map = _rename_result_columns(original_headers, result_columns, join_key)

    results_by_key: Dict[Any, Dict[str, Any]] = {}
    for result in results:
        key = result.get(join_key)
        if key is None or key in results_by_key:
            continue
        results_by_key[key] = result

    merged_rows: List[Dict[str, Any]] = []
    for record in original_records:
        merged = dict(record)
        matched = results_by_key.get(record.get(join_key))
        if matched:
            for column in result_columns:
                merged[rename_map[column]] = matched.get(column)
        merged_rows.append(merged)

    priority_columns = ['测试request_key', '状态', '数据查询时间', 'modelName', 'modelId']
    renamed_columns = [rename_map[column] for column in result_columns]
    ordered_result_columns = [
        column for column in priority_columns if column in renamed_columns
    ]
    ordered_result_columns.extend(
        sorted(column for column in renamed_columns if column not in ordered_result_columns)
    )

    merged_headers = list(original_headers)
    for column in ordered_result_columns:
        if column not in merged_headers:
            merged_headers.append(column)

    return merged_headers, merged_rows


def _merge_by_position(
    original_headers: List[str],
    original_records: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """没有合并键时按行号横向拼接。"""
    result_columns = _ordered_columns(results)
    rename_map = _rename_result_columns(original_headers, result_columns, None)

    merged_headers = list(original_headers)
    for column in result_columns:
        renamed = rename_map[column]
        if renamed not in merged_headers:
            merged_headers.append(renamed)

    merged_rows: List[Dict[str, Any]] = []
    row_count = max(len(original_records), len(results))
    for index in range(row_count):
        merged: Dict[str, Any] = {}
        if index < len(original_records):
            merged.update(original_records[index])
        if index < len(results):
            for column in result_columns:
                merged[rename_map[column]] = results[index].get(column)
        merged_rows.append(merged)

    return merged_headers, merged_rows


def _excel_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _write_merged_workbook(
    output_file: Path,
    headers: List[str],
    rows: List[Dict[str, Any]],
):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = '完整报告'

    for column_index, header in enumerate(headers, start=1):
        worksheet.cell(row=1, column=column_index, value=header)

    for row_index, row in enumerate(rows, start=2):
        for column_index, header in enumerate(headers, start=1):
            worksheet.cell(
                row=row_index, column=column_index, value=_excel_value(row.get(header))
            )

    for column_index, header in enumerate(headers, start=1):
        letter = get_column_letter(column_index)
        if 'JSON' in str(header) or '结果' in str(header):
            worksheet.column_dimensions[letter].width = 80
            for row_index in range(2, len(rows) + 2):
                worksheet.cell(row=row_index, column=column_index).alignment = Alignment(
                    wrapText=True, vertical='top'
                )
            continue

        max_length = len(str(header))
        for row_index in range(2, len(rows) + 2):
            value = worksheet.cell(row=row_index, column=column_index).value
            if value is not None:
                max_length = max(max_length, len(str(value)))

        worksheet.column_dimensions[letter].width = max(min(max_length + 2, 30), 10)

    workbook.save(output_file)

# common/utils/excel_reporter.py
"""批量参数对比 Excel 报表导出（openpyxl 实现）。

从 legacy_scripts/diffDataJsonExport.py 的 BatchParameterComparison 迁移而来：
- 只负责“把对比结果写成 Excel”，对比逻辑在 json_comparator.ParameterComparison
- 不再使用 input()，无变化模型展示数量由构造参数 no_change_display_count 控制
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

from common.utils.json_comparator import ParameterComparison
from common.utils.logger import log


class BatchParameterComparison:
    """批量参数对比报表生成器。"""

    MODELS_PER_SHEET = 200

    SUMMARY_HEADERS = [
        '参数标识', '名称', '接口名', '类型', '状态',
        '旧匹配值', '新匹配值', '值变更', '方程式',
        '旧参数值', '新参数值', '参数类别', '用户输入',
        'model_interface_id', '匹配方式',
    ]

    def __init__(
        self,
        output_dir: str = '批量对比报告',
        no_change_display_count: int = 5,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.no_change_display_count = max(0, int(no_change_display_count))

        self.styles = {
            'title_fill': PatternFill(start_color='366092', end_color='366092', fill_type='solid'),
            'title_font': Font(color='FFFFFF', bold=True),
            'header_fill': PatternFill(start_color='4F81BD', end_color='4F81BD', fill_type='solid'),
            'header_font': Font(color='FFFFFF', bold=True),
            'model_title_fill': PatternFill(start_color='E6F3FF', end_color='E6F3FF', fill_type='solid'),
            'model_title_font': Font(bold=True),
            'changed_fill': PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid'),
            'added_fill': PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid'),
            'removed_fill': PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid'),
            'unchanged_fill': PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid'),
            'border': Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin'),
            ),
            'center_align': Alignment(horizontal='center', vertical='center'),
            'left_align': Alignment(horizontal='left', vertical='center'),
        }

    # ==================== 主入口 ====================

    def generate_batch_report(
        self, batch_comparisons: List[Dict[str, Any]]
    ) -> str:
        """生成批量报告，返回文件路径。"""
        all_model_results = []
        comparator = ParameterComparison()

        log.info(f"开始处理 {len(batch_comparisons)} 个模型")

        for index, comparison in enumerate(batch_comparisons, 1):
            try:
                log.info(
                    f"处理第 {index}/{len(batch_comparisons)} 个模型: "
                    f"{comparison['modelname']}"
                )
                result = comparator.compare_datasets(
                    comparison['old_data'],
                    comparison['new_data'],
                    comparison['modelname'],
                    comparison.get('model_fullname', ''),
                    comparison.get('model_key', ''),
                    comparison.get('attr_info'),
                )
                all_model_results.append(result)
                log.info(
                    f"状态: {'有变化' if result['has_changes'] else '无变化'}, "
                    f"变化参数: {result['changes_count']} 个"
                )
            except Exception as exc:
                log.error(f"处理模型失败 {comparison.get('modelname')}: {exc}")

        changed_models = [item for item in all_model_results if item['has_changes']]
        no_change_models = [item for item in all_model_results if not item['has_changes']]

        workbook = Workbook()
        summary_sheet = workbook.active
        summary_sheet.title = '汇总'
        self._create_summary_sheet(
            summary_sheet, all_model_results, changed_models, no_change_models
        )

        if changed_models:
            self._create_changed_models_sheets(workbook, changed_models)

        if no_change_models:
            self._create_no_change_summary_sheet(workbook, no_change_models)
            if self.no_change_display_count > 0:
                self._create_no_change_detail_sheet(workbook, no_change_models)

        output_path = self.output_dir / f'批量参数对比_{self.timestamp}.xlsx'
        workbook.save(output_path)

        log.info(
            f"批量报告已生成: {output_path}；总模型 {len(all_model_results)}，"
            f"有变化 {len(changed_models)}，无变化 {len(no_change_models)}"
        )
        return str(output_path)

    # ==================== 汇总页 ====================

    def _create_summary_sheet(
        self,
        worksheet: Worksheet,
        all_results: List[Dict],
        changed_models: List[Dict],
        no_change_models: List[Dict],
    ):
        total_models = len(all_results)
        changed_count = len(changed_models)
        no_change_count = len(no_change_models)
        change_rate = (
            f'{(changed_count / total_models * 100):.1f}%' if total_models else '0%'
        )

        overview_headers = [
            '模型型号总数', '有变化模型型号数', '无变化模型型号数', '变化率'
        ]
        overview_values = [total_models, changed_count, no_change_count, change_rate]

        for column, header in enumerate(overview_headers, start=1):
            cell = worksheet.cell(row=1, column=column, value=header)
            cell.fill = self.styles['title_fill']
            cell.font = self.styles['title_font']
            cell.alignment = self.styles['center_align']
            worksheet.cell(row=2, column=column, value=overview_values[column - 1])

        list_headers = ['序号', '模型名', '变化参数数', '型号']
        for column, header in enumerate(list_headers, start=1):
            cell = worksheet.cell(row=4, column=column, value=header)
            cell.fill = self.styles['header_fill']
            cell.font = self.styles['header_font']
            cell.alignment = self.styles['center_align']

        for index, model in enumerate(changed_models, start=1):
            row = index + 4
            worksheet.cell(row=row, column=1, value=index)
            worksheet.cell(row=row, column=2, value=model['modelname'])
            worksheet.cell(row=row, column=3, value=f"{model['changes_count']}个")
            worksheet.cell(row=row, column=4, value=model['model_fullname'])

        for letter, width in {'A': 15, 'B': 25, 'C': 20, 'D': 40}.items():
            worksheet.column_dimensions[letter].width = width

    # ==================== 有变化模型 ====================

    def _create_changed_models_sheets(
        self, workbook: Workbook, changed_models: List[Dict]
    ):
        total_models = len(changed_models)
        num_sheets = (total_models + self.MODELS_PER_SHEET - 1) // self.MODELS_PER_SHEET

        for sheet_num in range(num_sheets):
            start = sheet_num * self.MODELS_PER_SHEET
            end = min((sheet_num + 1) * self.MODELS_PER_SHEET, total_models)
            sheet_models = changed_models[start:end]

            sheet_name = (
                '有变化模型对比'
                if num_sheets == 1
                else f'有变化模型对比_第{sheet_num + 1}部分'
            )
            worksheet = workbook.create_sheet(sheet_name)
            current_row = 1

            worksheet.merge_cells(f'A{current_row}:P{current_row}')
            title_cell = worksheet[f'A{current_row}']
            title_cell.value = f"有变化模型参数对比（第{sheet_num + 1}/{num_sheets}部分）"
            title_cell.font = Font(bold=True, size=14)
            title_cell.alignment = self.styles['center_align']
            title_cell.fill = PatternFill(
                start_color='FFD966', end_color='FFD966', fill_type='solid'
            )
            current_row += 2

            for model_index, model_result in enumerate(sheet_models, 1):
                current_row = self._write_changed_model(
                    worksheet, current_row, model_result
                )

                if model_index < len(sheet_models):
                    current_row += 2
                    worksheet.merge_cells(f'A{current_row}:P{current_row}')
                    separator = worksheet[f'A{current_row}']
                    separator.value = "=" * 80
                    separator.alignment = self.styles['center_align']
                    separator.font = Font(color='808080')
                    current_row += 2

            column_widths = {
                'A': 28, 'B': 18, 'C': 18, 'D': 13, 'E': 8,
                'F': 13, 'G': 13, 'H': 8, 'I': 35, 'J': 13,
                'K': 13, 'L': 13, 'M': 13, 'N': 18, 'O': 13, 'P': 25,
            }
            for column, width in column_widths.items():
                worksheet.column_dimensions[column].width = width

    def _write_changed_model(
        self, worksheet: Worksheet, current_row: int, model_result: Dict
    ) -> int:
        modelname = model_result['modelname']
        model_fullname = model_result['model_fullname']
        model_key = model_result.get('model_key', '')
        all_results = model_result['all_comparison_results']
        changed_count = model_result['changes_count']
        total_results = model_result['total_results']
        attr_info = model_result.get('attr_info', [])

        attr_json_str = ''
        if attr_info and isinstance(attr_info, list):
            try:
                attr_json_str = json.dumps(attr_info, ensure_ascii=False)
            except (TypeError, ValueError) as exc:
                log.warning(f"转换 attr_info 失败: {exc}")
                attr_json_str = str(attr_info)

        old_params_count = sum(
            1 for param in all_results
            if param.get('旧匹配值', '') or param.get('旧参数值', '')
        )
        new_params_count = sum(
            1 for param in all_results
            if param.get('新匹配值', '') or param.get('新参数值', '')
        )

        # 1. 模型标题
        worksheet.merge_cells(f'A{current_row}:P{current_row}')
        title_cell = worksheet[f'A{current_row}']
        title_cell.value = f"【{model_fullname}】"
        title_cell.font = self.styles['model_title_font']
        title_cell.fill = self.styles['model_title_fill']
        title_cell.alignment = self.styles['center_align']
        title_cell.border = self.styles['border']
        current_row += 1

        # 2. 基本信息
        info_row = current_row
        worksheet.cell(row=info_row, column=1, value="模型标识:").font = Font(bold=True)
        worksheet.cell(row=info_row, column=2, value=modelname)
        worksheet.cell(row=info_row, column=3, value="model_key:").font = Font(bold=True)
        worksheet.merge_cells(
            start_row=info_row, start_column=4, end_row=info_row, end_column=7
        )
        worksheet.cell(row=info_row, column=4, value=model_key)
        worksheet.cell(row=info_row, column=8, value="参数对比:").font = Font(bold=True)
        worksheet.cell(
            row=info_row, column=9,
            value=f"旧{old_params_count}->新{new_params_count}",
        )
        worksheet.cell(row=info_row, column=10, value="总参数:").font = Font(bold=True)
        worksheet.cell(row=info_row, column=11, value=f"{total_results}个")
        worksheet.cell(row=info_row, column=12, value="变化:").font = Font(bold=True)
        worksheet.cell(row=info_row, column=13, value=f"{changed_count}个")

        if attr_json_str:
            worksheet.cell(
                row=info_row, column=14, value="attr_info:"
            ).font = Font(bold=True, color='0000FF')
            worksheet.merge_cells(
                start_row=info_row, start_column=15, end_row=info_row, end_column=16
            )
            attr_cell = worksheet.cell(row=info_row, column=15, value="详见最后一列")
            attr_cell.font = Font(color='0000FF')
            attr_cell.alignment = self.styles['center_align']

        current_row += 2

        # 3. 表头
        header_row = current_row
        for column, header in enumerate(self.SUMMARY_HEADERS, start=1):
            cell = worksheet.cell(row=header_row, column=column, value=header)
            cell.fill = self.styles['header_fill']
            cell.font = self.styles['header_font']
            cell.alignment = self.styles['center_align']
            cell.border = self.styles['border']

        attr_header_cell = worksheet.cell(row=header_row, column=16, value='attr_info')
        attr_header_cell.fill = self.styles['title_fill']
        attr_header_cell.font = self.styles['title_font']
        attr_header_cell.alignment = self.styles['center_align']
        attr_header_cell.border = self.styles['border']
        current_row += 1

        # 4. 参数数据
        params_start_row = current_row
        for param in all_results:
            for column, column_name in enumerate(self.SUMMARY_HEADERS, start=1):
                cell = worksheet.cell(
                    row=current_row, column=column, value=param.get(column_name, '')
                )
                cell.border = self.styles['border']
                cell.alignment = self.styles['left_align']

            status = param.get('状态', '')
            fill_color = {
                '新增': self.styles['added_fill'],
                '修改': self.styles['changed_fill'],
                '删除': self.styles['removed_fill'],
                '未变化': self.styles['unchanged_fill'],
            }.get(status)
            if fill_color:
                for column in range(1, 16):
                    worksheet.cell(row=current_row, column=column).fill = fill_color

            if param.get('值变更') == '是':
                worksheet.cell(row=current_row, column=8).fill = self.styles['removed_fill']

            current_row += 1

        params_end_row = current_row - 1

        # 5. attr_info 合并列
        if params_start_row <= params_end_row:
            worksheet.merge_cells(
                start_row=params_start_row, start_column=16,
                end_row=params_end_row, end_column=16,
            )
            attr_cell = worksheet.cell(
                row=params_start_row, column=16, value=attr_json_str
            )
            attr_cell.border = self.styles['border']
            attr_cell.alignment = Alignment(
                horizontal='left', vertical='top', wrap_text=True
            )
            attr_cell.font = Font(color='0000FF', size=8, name='微软雅黑')
            attr_cell.fill = self.styles['model_title_fill']

            num_lines = attr_json_str.count('\n') + 1
            row_height = min(150, max(20, num_lines * 12))
            for row in range(params_start_row, params_end_row + 1):
                worksheet.row_dimensions[row].height = row_height

        return current_row

    # ==================== 无变化模型 ====================

    def _create_no_change_summary_sheet(
        self, workbook: Workbook, no_change_models: List[Dict]
    ):
        worksheet = workbook.create_sheet('无变化模型汇总')
        headers = ['modelname', 'model_fullname', '参数总数']

        for column, header in enumerate(headers, start=1):
            cell = worksheet.cell(row=1, column=column, value=header)
            cell.fill = PatternFill(
                start_color='00B050', end_color='00B050', fill_type='solid'
            )
            cell.font = Font(color='FFFFFF', bold=True)

        total_params = sum(model['total_results'] for model in no_change_models)
        worksheet.cell(row=2, column=1, value='总计')
        worksheet.cell(row=2, column=2, value=f'共{len(no_change_models)}个模型')
        worksheet.cell(row=2, column=3, value=total_params)

        for index, model in enumerate(no_change_models, start=3):
            worksheet.cell(row=index, column=1, value=model['modelname'])
            worksheet.cell(row=index, column=2, value=model['model_fullname'])
            worksheet.cell(row=index, column=3, value=model['total_results'])

        for letter in ('A', 'B', 'C'):
            worksheet.column_dimensions[letter].width = 20

    def _create_no_change_detail_sheet(
        self, workbook: Workbook, no_change_models: List[Dict]
    ):
        display_count = min(self.no_change_display_count, len(no_change_models))
        if display_count == 0:
            return

        worksheet = workbook.create_sheet('无变化模型详情')
        current_row = 1

        worksheet.merge_cells(f'A{current_row}:P{current_row}')
        title_cell = worksheet[f'A{current_row}']
        title_cell.value = (
            f"无变化模型参数对比详情（共{display_count}个，"
            f"总计{len(no_change_models)}个）"
        )
        title_cell.font = Font(bold=True, size=14)
        title_cell.alignment = self.styles['center_align']
        title_cell.fill = PatternFill(
            start_color='C6EFCE', end_color='C6EFCE', fill_type='solid'
        )
        current_row += 2

        for model_index, model_result in enumerate(
            no_change_models[:display_count], 1
        ):
            modelname = model_result['modelname']
            model_fullname = model_result['model_fullname']
            all_results = model_result['all_comparison_results']
            changed_count = model_result['changes_count']
            total_results = model_result['total_results']
            attr_info = model_result.get('attr_info', [])

            old_params_count = sum(
                1 for param in all_results
                if param.get('旧匹配值', '') or param.get('旧参数值', '')
            )
            new_params_count = sum(
                1 for param in all_results
                if param.get('新匹配值', '') or param.get('新参数值', '')
            )

            # 模型标题
            worksheet.merge_cells(f'A{current_row}:P{current_row}')
            title_cell = worksheet[f'A{current_row}']
            title_cell.value = f"【{model_fullname}】"
            title_cell.font = self.styles['model_title_font']
            title_cell.fill = self.styles['added_fill']
            title_cell.alignment = self.styles['center_align']
            title_cell.border = self.styles['border']
            current_row += 1

            # 基本信息
            info_row = current_row
            worksheet.cell(row=info_row, column=1, value="模型标识:").font = Font(bold=True)
            worksheet.cell(row=info_row, column=2, value=modelname)
            worksheet.cell(row=info_row, column=3, value="完整名称:").font = Font(bold=True)
            worksheet.merge_cells(
                start_row=info_row, start_column=4, end_row=info_row, end_column=6
            )
            worksheet.cell(row=info_row, column=4, value=model_fullname)
            worksheet.cell(row=info_row, column=7, value="参数对比:").font = Font(bold=True)
            worksheet.cell(
                row=info_row, column=8,
                value=f"旧{old_params_count}->新{new_params_count}",
            )
            worksheet.cell(row=info_row, column=9, value="总参数:").font = Font(bold=True)
            worksheet.cell(row=info_row, column=10, value=f"{total_results}个")
            worksheet.cell(row=info_row, column=11, value="变化:").font = Font(bold=True)
            worksheet.cell(row=info_row, column=12, value=f"{changed_count}个")
            worksheet.cell(
                row=info_row, column=13, value="状态:"
            ).font = Font(bold=True, color='00B050')
            worksheet.cell(
                row=info_row, column=14, value="无变化"
            ).font = Font(color='00B050', bold=True)
            current_row += 1

            # attr_info
            if attr_info and isinstance(attr_info, list):
                attr_row = current_row
                worksheet.cell(
                    row=attr_row, column=1, value="attr_info:"
                ).font = Font(bold=True, color='0000FF')

                attr_str = ", ".join(
                    f"{attr.get('name')}: {attr.get('value')}"
                    if attr.get('value')
                    else str(attr.get('name'))
                    for attr in attr_info
                    if attr.get('name')
                )

                worksheet.merge_cells(
                    start_row=attr_row, start_column=2,
                    end_row=attr_row, end_column=16,
                )
                attr_cell = worksheet.cell(row=attr_row, column=2, value=attr_str)
                attr_cell.font = Font(color='0000FF')
                attr_cell.alignment = Alignment(horizontal='left', vertical='center')
                attr_cell.fill = self.styles['model_title_fill']
                current_row += 1

            current_row += 1

            # 表头
            header_row = current_row
            for column, header in enumerate(self.SUMMARY_HEADERS, start=1):
                cell = worksheet.cell(row=header_row, column=column, value=header)
                cell.fill = self.styles['header_fill']
                cell.font = self.styles['header_font']
                cell.alignment = self.styles['center_align']
                cell.border = self.styles['border']
            current_row += 1

            # 数据
            for param in all_results:
                for column, column_name in enumerate(self.SUMMARY_HEADERS, start=1):
                    cell = worksheet.cell(
                        row=current_row, column=column, value=param.get(column_name, '')
                    )
                    cell.border = self.styles['border']
                    cell.alignment = self.styles['left_align']

                status = param.get('状态', '')
                fill_color = {
                    '新增': self.styles['added_fill'],
                    '修改': self.styles['changed_fill'],
                    '删除': self.styles['removed_fill'],
                    '未变化': self.styles['added_fill'],
                }.get(status)
                if fill_color:
                    for column in range(1, len(self.SUMMARY_HEADERS) + 1):
                        worksheet.cell(row=current_row, column=column).fill = fill_color

                if param.get('值变更') == '是':
                    worksheet.cell(row=current_row, column=8).fill = self.styles['removed_fill']

                current_row += 1

            if model_index < display_count:
                current_row += 2
                worksheet.merge_cells(f'A{current_row}:P{current_row}')
                separator = worksheet[f'A{current_row}']
                separator.value = "=" * 80
                separator.alignment = self.styles['center_align']
                separator.font = Font(color='808080')
                current_row += 2

        column_widths = {
            'A': 30, 'B': 20, 'C': 20, 'D': 15, 'E': 10,
            'F': 15, 'G': 15, 'H': 10, 'I': 40, 'J': 15,
            'K': 15, 'L': 15, 'M': 15, 'N': 20, 'O': 15,
        }
        for column, width in column_widths.items():
            worksheet.column_dimensions[column].width = width

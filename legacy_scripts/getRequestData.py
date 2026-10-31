import datetime
from email.utils import make_msgid

import pandas as pd
import requests
import json
import time
import traceback
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from tools.BuilderDataManager import BuilderModel
from tools.logger import log


def login_for_api_token(base_url, appid, app_secret):
    """登录获取API token"""
    url = f"{base_url}/forface/external/oauth/getAccessToken"
    params = {"app_id": appid, "app_secret": app_secret}

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 200:
                return f"Bearer {data['data']['access_token']}"
    except Exception as e:
        print(f"登录失败: {e}")

    return None


def save_results(original_excel_path, results_data_list, output_dir, timestamp_str=None, join_key='_row_id'):
    """
    将测试结果与原始Excel数据合并后保存。
    """
    try:
        import pandas as pd
        import os
        from datetime import datetime
        from openpyxl.utils import get_column_letter  # 关键修复：导入正确的方法
        from openpyxl.styles import Alignment
        import traceback

        # 1. 准备输出
        os.makedirs(output_dir, exist_ok=True)
        if timestamp_str is None:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f'建模测试完整报告_{timestamp_str}.xlsx')

        # 2. 读取原始数据
        df_original = pd.read_excel(original_excel_path, engine='openpyxl')
        print(f"[读取] 原始数据共 {len(df_original)} 行，{len(df_original.columns)} 列。")

        # 3. 将结果列表转换为DataFrame
        if not results_data_list:
            print("[警告] 测试结果列表为空，将只保存原始数据。")
            df_results = pd.DataFrame()
        else:
            df_results = pd.DataFrame(results_data_list)
            print(f"[读取] 测试结果共 {len(df_results)} 条。")

        # 4. 合并数据
        if df_results.empty:
            merged_df = df_original
            print("[合并] 无测试结果，仅保存原始数据。")
        else:
            # 确保合并键存在
            if join_key not in df_results.columns:
                alt_key = '测试request_key' if join_key == '_row_id' else '_row_id'
                if alt_key in df_results.columns:
                    print(f"[合并] 使用备用键 '{alt_key}' 进行合并。")
                    join_key = alt_key
                else:
                    # 如果找不到合并键，使用索引合并
                    print("[合并] 未找到合并键，使用索引合并。")
                    merged_df = pd.concat([df_original, df_results], axis=1)

            if join_key in df_results.columns:
                # 确保原始数据有合并键
                if join_key not in df_original.columns:
                    if join_key == '_row_id':
                        df_original[join_key] = range(2, len(df_original) + 2)
                    else:
                        print(f"[警告] 原始数据中无'{join_key}'列，使用索引合并。")
                        merged_df = pd.concat([df_original, df_results], axis=1)

                # 执行合并
                if 'merged_df' not in locals():
                    merged_df = pd.merge(
                        df_original,
                        df_results,
                        on=join_key,
                        how='left',
                        suffixes=('', '_测试')
                    )
                print(f"[合并] 合并完成，总列数：{len(merged_df.columns)}。")

        # 5. 优化列顺序
        if len(merged_df) > 0:
            # 识别原始列和测试列
            original_cols = [col for col in merged_df.columns
                             if not str(col).endswith('_测试') and not str(col).endswith('_test')]
            test_result_cols = [col for col in merged_df.columns if col not in original_cols]

            # 关键测试列优先
            priority_test_cols = ['测试request_key', '状态', '数据查询时间', 'modelName', 'modelId']
            ordered_test_cols = []
            for col in priority_test_cols:
                if col in test_result_cols:
                    ordered_test_cols.append(col)
                    if col in test_result_cols:
                        test_result_cols.remove(col)

            # 剩余测试列排序
            ordered_test_cols.extend(sorted(test_result_cols))

            # 最终列顺序
            final_column_order = original_cols + ordered_test_cols
            # 确保所有列都存在
            final_column_order = [col for col in final_column_order if col in merged_df.columns]
            merged_df = merged_df[final_column_order]

        # 6. 写入Excel并设置格式
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            merged_df.to_excel(writer, index=False, sheet_name='完整报告')

            workbook = writer.book
            worksheet = writer.sheets['完整报告']

            # 关键修复：使用openpyxl的get_column_letter函数
            for col_idx, column_name in enumerate(merged_df.columns, start=1):
                column_letter = get_column_letter(col_idx)  # 修复：正确的列字母获取方式

                # 设置列宽
                if 'JSON' in str(column_name) or '结果' in str(column_name):
                    worksheet.column_dimensions[column_letter].width = 80

                    # 为JSON列设置自动换行
                    for row in range(2, len(merged_df) + 2):
                        cell = worksheet.cell(row=row, column=col_idx)
                        cell.alignment = Alignment(wrapText=True, vertical='top')
                else:
                    # 计算本列最大内容长度
                    max_length = 0
                    for row in range(1, len(merged_df) + 1):
                        cell = worksheet.cell(row=row, column=col_idx)
                        if cell.value:
                            cell_length = len(str(cell.value))
                            max_length = max(max_length, cell_length)

                    # 设置合理列宽，限制最大宽度
                    adjusted_width = min(max_length + 2, 30)
                    worksheet.column_dimensions[column_letter].width = max(adjusted_width, 10)  # 最小宽度10

        print(f"[成功] 合并报告已保存至：{output_path}")

        # 7. 打印报告摘要
        if not df_results.empty and '状态' in merged_df.columns:
            success_count = merged_df['状态'].eq('成功').sum()
            total_count = len(merged_df)
            print(f"[摘要] 测试成功率: {success_count}/{total_count} ({success_count / total_count * 100:.1f}%)")

        return output_path

    except Exception as e:
        print(f"[错误] 保存合并报告失败: {e}")
        traceback.print_exc()

        # 降级方案：使用pandas的简单保存
        try:
            simple_path = os.path.join(output_dir, f'报告_简易版_{timestamp_str}.xlsx')
            merged_df.to_excel(simple_path, index=False)
            print(f"[降级] 已生成简易版报告: {simple_path}")
            return simple_path
        except:
            print("[严重] 所有保存方式均失败。")
            return None

def safe_parse_attr_info(attr_info):
    """安全解析attr_info字段"""
    if not attr_info:
        return []

    try:
        # 如果已经是列表，直接返回
        if isinstance(attr_info, list):
            return attr_info

        # 如果是字符串
        if isinstance(attr_info, str):
            attr_str = attr_info.strip()

            # 如果为空，返回空列表
            if not attr_str:
                return []

            # 尝试JSON解析
            try:
                return json.loads(attr_str)
            except json.JSONDecodeError:
                # 如果不是标准JSON，尝试eval
                try:
                    # 替换单引号为双引号
                    if attr_str.startswith("[") and attr_str.endswith("]"):
                        # 处理Python列表格式
                        return ast.literal_eval(attr_str)
                    elif attr_str.startswith("{") and attr_str.endswith("}"):
                        # 处理字典格式
                        data = ast.literal_eval(attr_str)
                        if isinstance(data, dict):
                            return [data]
                        return data
                except:
                    # 如果还是失败，尝试简单的字符串分割
                    if "name" in attr_str and "value" in attr_str:
                        # 尝试提取基本参数
                        result = []
                        # 简单的分割逻辑
                        items = attr_str.split("}, {")
                        for item in items:
                            item = item.replace("{", "").replace("}", "").strip()
                            parts = item.split(", ")
                            param = {}
                            for part in parts:
                                if ":" in part:
                                    key, value = part.split(":", 1)
                                    key = key.strip().replace("'", "").replace('"', "")
                                    value = value.strip().replace("'", "").replace('"', "")
                                    param[key] = value
                            if param:
                                result.append(param)
                        return result

            # 最后尝试，如果看起来像Python列表，用ast.literal_eval
            if attr_str.startswith("[") and attr_str.endswith("]"):
                try:
                    return ast.literal_eval(attr_str)
                except:
                    pass

            # 如果所有方法都失败，返回空列表
            print(f"警告: 无法解析attr_info: {attr_str[:100]}...")
            return []

        # 其他类型，尝试直接使用
        return attr_info

    except Exception as e:
        print(f"解析attr_info异常: {e}")
        return []


class SimpleBuilderTester:
    """简单的建模测试器"""

    def __init__(self, userId, base_url, webhook):
        self.userId = userId
        self.base_url = base_url
        self.webhook = webhook
        # 请求头
        self.headers = {
            "Content-Type": "application/json"
        }



    def send_build_request(self, data_row):
        """发送mqmsg建模请求"""
        try:
            # 准备请求数据
            model_key = data_row.get('modelKey')
            model_name = data_row.get('modelFullname', data_row.get('modelname', ''))

            if not model_key:
                print(f"缺少modelKey: {data_row}")
                return None

            # 构建请求
            url = f"{self.base_url}/forface/builder/test/external/autoRequestModel"

            request_data = {
                "userId":self.userId,
                "model_type": "f3d",
                "webhook_key": self.webhook,
                "is_download_request": 0,
                "cache": 0,
                "is_ignore_release": 1,
                "dxfOfView": 0,
                "is_drawing": 0,
                "external_param": json.dumps({
                    "productModelNumber": model_name,
                    "productCode": model_key
                }),
                "product_code": model_key
            }

            # 添加attr_info（使用安全解析）
            attr_info = data_row.get('attr_info')
            if attr_info:
                parsed_attr = safe_parse_attr_info(attr_info)
                if parsed_attr:
                    request_data['attr_info'] = parsed_attr
                else:
                    print(f"警告: attr_info解析为空")

            log.info(f"发送建模请求: {model_name} ({model_key})")
            log.info(f"请求数据预览: {json.dumps(request_data, ensure_ascii=False)}...")

            # 发送请求
            response = requests.post(url, headers=self.headers, json=request_data, timeout=60)

            print(f"响应状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                log.info(f"响应数据: {json.dumps(result, ensure_ascii=False)}...")

                if result.get('data'):
                    mqMsg = result['data'].get('mqMsg')
                    if mqMsg:
                        print(f"建模请求成功: {mqMsg}")
                        return mqMsg
                    else:
                        print(f"响应中没有mqMsq")
                else:
                    print(f"API返回错误: code={result.get('code')}, msg={result.get('msg')}")
            else:
                print(f"HTTP请求失败: {response.text[:200]}")

            return None

        except Exception as e:
            print(f"发送建模请求异常: {e}")
            traceback.print_exc()
            return None




    def process_one_row(self, row_data):
        """处理一行数据"""
        try:
            row_id = row_data.get('_row_id', '未知')
            model_key = row_data.get('modelKey', '未知')
            model_name = row_data.get('modelFullname', row_data.get('modelname', '未知'))

            print(f"\n{'=' * 60}")
            print(f"处理第 {row_id} 行: {model_name} ({model_key})")
            print(f"{'=' * 60}")

            # 检查是否已有request_key
            existing_key = row_data.get('测试request_key')
            if existing_key and str(existing_key).strip() and str(existing_key).strip().lower() != 'nan':
                request_key = str(existing_key).strip()
                print(f"使用已有request_key: {request_key}")
                need_new_build = False
            else:
                need_new_build = True
                request_key = None

            # 如果需要新建模
            if need_new_build:
                # 先检查必要字段
                if not model_key:
                    return {
                        '_row_id': row_id,
                        'modelKey': model_key,
                        '测试request_key': '',
                        '状态': '跳过',
                        '原因': '缺少modelKey'
                    }

                attr_info = row_data.get('attr_info')
                if not attr_info:
                    return {
                        '_row_id': row_id,
                        'modelKey': model_key,
                        '测试request_key': '',
                        '状态': '跳过',
                        '原因': '缺少attr_info'
                    }

                print(f"发送新的建模请求{model_key}...")
                print(f"attr_info预览: {str(attr_info)[:200]}...")

                mqMsg = self.send_build_request(row_data)

                if not mqMsg:
                    return {
                        '_row_id': row_id,
                        'modelKey': model_key,
                        'mqMsg': '',
                        '状态': '建模失败',
                        '原因': '建模请求失败'
                    }

                print(f"建模请求成功，mqMsg: {mqMsg}")


            # ========== 新增/修改的部分：构建包含完整JSON的结果字典 ==========
            import json
            from datetime import datetime



            # 2. 为方便生成报告，同时提取一些关键字段单独成列
            result = {
                '_row_id': row_id,
                'modelKey': model_key,
                '测试request_key': request_key,
                '状态': '成功',
                # '数据查询时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                # 关键独立字段
                # 核心：完整的建模结果JSON字符串
                'mqMsg': mqMsg,
            }



            print(f"第 {row_id} 行处理成功")
            return result

        except Exception as e:
            print(f"处理异常: {e}")
            traceback.print_exc()
            return {
                '_row_id': row_data.get('_row_id', '未知'),
                'modelKey': row_data.get('modelKey', '未知'),
                'mqMsg': '',
                '状态': '异常',
                '原因': str(e)[:200]
            }

def read_and_prepare_data(file_path):
    """读取并准备数据"""
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        print(f"读取到 {len(df)} 行数据")

        # 显示列名
        print(f"数据列: {', '.join(df.columns.tolist())}")

        # 检查必要列
        required_cols = ['modelKey', 'attr_info']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"警告: 缺少必要列: {missing_cols}")

        # 添加行号
        data_list = []
        for idx, row in df.iterrows():
            row_dict = {}

            # 处理每一列，确保值正确
            for col in df.columns:
                value = row[col]
                # 处理NaN和空值
                if pd.isna(value):
                    value = None
                elif isinstance(value, str):
                    value = value.strip()
                    if value == '':
                        value = None

                row_dict[col] = value

            row_dict['_row_id'] = idx + 2  # Excel行号（标题行+1）
            data_list.append(row_dict)

        # 显示前几行数据预览
        print(f"\n数据预览（前3行）:")
        for i, row in enumerate(data_list[:3]):
            print(f"行{i + 1}: modelKey={row.get('modelKey')}, "
                  f"attr_info长度={len(str(row.get('attr_info', ''))) if row.get('attr_info') else 0}")

        return data_list
    except Exception as e:
        print(f"读取数据失败: {e}")
        traceback.print_exc()
        return []


def main():
    """主函数"""
    print("=" * 80)
    print("简单建模测试工具")
    print("=" * 80)

    # 配置信息（直接写在这里）
    CONFIG = {
        # 'base_url': 'https://cary-fat-vs.forface3d.com',
        'base_url':'https://api.forface3d.com',
        'userId':'35',
        'webhook': '5C1786CE043459A70E0E2FB5034315D3'
    }

    # 2. 初始化测试器
    tester = SimpleBuilderTester(
        userId=CONFIG['userId'],
        base_url=CONFIG['base_url'],
        webhook=CONFIG['webhook']
    )

    # 3. 读取数据
    print("2. 只查询已有的request_key（不发送新请求）")

    excel_file = 'D:\三维\建模模型\测试报告\建模测试完整报告_20260427_194736.xlsx'
    print(f"\n读取文件: {excel_file}")
    data_list = read_and_prepare_data(excel_file)
    LIST=[]
    if not data_list:
        print("没有数据可处理")
        return

    print(f"准备处理 {len(data_list)} 行数据")

    # 4. 选择处理方式
    print("\n" + "-" * 60)
    print("请选择处理方式:")
    print("1. 全部处理（包括新建模和查询已有）")
    print("2. 只查询已有的request_key（不发送新请求）")
    print("3. 只发送新的建模请求（跳过已有request_key）")
    print("4. 只发送新的建模请求（状态为重测）")

    print("-" * 60)

    choice = input("请输入选择 (1/2/3, 默认1): ").strip() or "1"

    # 5. 过滤数据
    original_count = len(data_list)
    if choice == "2":
        # 只处理已有request_key的数据
        filtered_data = []
        for data in data_list:
            existing_key = data.get('测试request_key')
            if existing_key and str(existing_key).strip() and str(existing_key).strip().lower() != 'nan':
                filtered_data.append(data)

        print(f"筛选出 {len(filtered_data)} 条已有request_key的数据（跳过 {original_count - len(filtered_data)} 条）")
        data_list = filtered_data

    elif choice == "3":
        # 只处理没有request_key的数据
        filtered_data = []
        for data in data_list:
            existing_key = data.get('测试request_key')
            if not existing_key or str(existing_key).strip() == '' or str(existing_key).strip().lower() == 'nan':
                filtered_data.append(data)

        print(f"筛选出 {len(filtered_data)} 条需要新建模的数据（跳过 {original_count - len(filtered_data)} 条已有数据）")
        data_list = filtered_data

    elif choice == "4":
        # 只处理状态为重测的数据
        filtered_data = []
        for data in data_list:
            status = data.get('状态')
            if status== '重测':
                filtered_data.append(data)

        print(f"筛选出 {len(filtered_data)} 条需要新建模的数据（跳过 {original_count - len(filtered_data)} 条已有数据）")
        data_list = filtered_data


    elif choice == "5":
        filtered_data = []
        for data in data_list:
            modelname = data.get('modelname')
            if modelname in LIST:
                filtered_data.append(data)

        print(f"筛选出 {len(filtered_data)} 条需要新建模的数据（跳过 {original_count - len(filtered_data)} 条已有数据）")
        data_list = filtered_data

    if not data_list:

        print("没有数据需要处理")
        return

    # 6. 询问处理数量
    print(f"\n共 {len(data_list)} 条数据需要处理")
    process_all = input(f"是否处理所有 {len(data_list)} 条数据？(y/n, 默认y): ").strip().lower() or "y"

    if process_all != 'y':
        try:
            max_rows = int(input(f"请输入要处理的最大行数 (1-{len(data_list)}): "))
            data_list = data_list[:max_rows]
            print(f"将处理前 {len(data_list)} 条数据")
        except:
            print(f"输入无效，将处理所有 {len(data_list)} 条数据")

    # 7. 并行处理
    print(f"\n开始处理（最大3个线程，避免服务器压力）...")
    start_time = time.time()

    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 提交所有任务
        future_to_data = {
            executor.submit(tester.process_one_row, data): data
            for data in data_list
        }

        # 处理完成的任务
        completed = 0
        for future in as_completed(future_to_data):
            completed += 1
            data = future_to_data[future]

            try:
                result = future.result(timeout=600)  # 10分钟超时
                results.append(result)

                # 显示进度
                total = len(data_list)
                success = sum(1 for r in results if r.get('状态') == '成功')

                print(f"\n[进度] {completed}/{total} | 成功: {success} | 失败: {completed - success}")
                print(f"最近结果: 行{result.get('_row_id')} - {result.get('状态')}")

            except Exception as e:
                print(f"\n任务执行失败: {e}")
                results.append({
                    '_row_id': data.get('_row_id', '未知'),
                    'modelKey': data.get('modelKey', '未知'),
                    '状态': '超时',
                    '原因': '处理超时(10分钟)'
                })

    elapsed_time = time.time() - start_time
    print(f"\n处理完成，总耗时: {elapsed_time:.1f}秒")


    # 调用保存函数，传入原始数据路径和结果列表
    final_report = save_results(
        original_excel_path=excel_file,  # 原始数据文件
        results_data_list=results,  # 测试结果
        output_dir='D:\\三维\\建模模型\\测试报告',  # 输出目录
        join_key='_row_id'  # 按行ID合并（确保process_one_row返回了此字段）
    )

    if final_report:
        print(f"✅ 完整报告已生成: {final_report}")
    else:
        print("❌ 报告生成失败。")


    #
    # if fail_count > 0:
    #     print(f"\n{'=' * 60}")
    #     print("失败详情:")
    #     print(f"{'=' * 60}")
    #
    #     for result in results:
    #         if result.get('状态') != '成功':
    #             row_id = result.get('_row_id', '?')
    #             model_key = result.get('modelKey', '未知')
    #             reason = result.get('原因', '未知')
    #             status = result.get('状态', '未知')
    #             print(f"  第{row_id}行 [{model_key}]: {status} - {reason}")
    #

def debug_attr_info():
    """调试attr_info解析"""
    print("调试attr_info解析")

    # 测试数据
    test_cases = [
        "[{'name': '参数1', 'value': '值1'}, {'name': '参数2', 'value': '值2'}]",
        "[{'name': '参数1', 'value': '值1'}]",
        "{'name': '参数1', 'value': '值1'}",
        "[{'name': 'Height', 'value': 1000}]",
        "",
        None,
        "invalid string"
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test}")
        result = safe_parse_attr_info(test)
        print(f"解析结果: {result}")
        print(f"类型: {type(result)}")


if __name__ == '__main__':
    # 运行主函数
    main()

    # 如果要调试attr_info解析，取消下面的注释
    # debug_attr_info()
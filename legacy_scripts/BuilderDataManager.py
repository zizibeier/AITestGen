import csv
import json
import math
import os
import difflib
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue
import time

import jsonpointer
import requests
from fuzzywuzzy import fuzz
from lxml.html.defs import form_tags

from tools.logger import log
from tools.get_web_token import login
from common.readexcel import ExcelHandle
import pandas as pd


def get_value(result, field):
    """获取JSON值"""
    try:
        json_string = json.loads(str(result.text))
    except:
        json_string = eval(str(result.text))

    if json_string is not None:
        try:
            data = jsonpointer.resolve_pointer(json_string, field)
            return data
        except jsonpointer.JsonPointerException as e:
            log.info(f"JsonPointer异常:{e}")
    else:
        log.info("JSON 文档是 None，请确保它已被正确初始化或加载")
    return None


class BuilderModel():
    def __init__(self, url, token):
        self.header = {"Token": token, "Content-Type": "application/json"}
        self.url = url
        self._session = requests.Session()
        self._session.headers.update(self.header)
        self._lock = threading.Lock()

    def get_all_models(self, page_size=100):
        """获取所有模型列表（支持分页）"""
        all_models = []
        page_num = 1

        while True:
            url = self.url + '/forface/builder/model/queryMyModelList'
            data = {
                "checkStatusList": [],
                "queryString": None,
                "pageNum": page_num,
                "pageSize": page_size,
                "categoryId": None,
                "structureTemplateStatus": [],
                "baseModelType": [],
                "fileType": [],
                "releaseStatusAll": [],
                "equationStatus": []
            }

            try:
                log.info(f"获取模型列表 - 第{page_num}页，每页{page_size}条")
                result = self._session.post(url, json=data, timeout=30)
                data_list = get_value(result, '/data')

                if not data_list:
                    break

                model_vo_list = data_list.get('modelVoList', [])
                if not model_vo_list:
                    break

                for model in model_vo_list:
                    all_models.append({
                        'id': model.get('id'),
                        'name': model.get('modelName'),
                        'fullname': model.get('modelFullname'),
                        'file_type': model.get('fileType'),
                        'has_equation': model.get('equationStatus') == 1  # 假设1表示有方程式
                    })

                log.info(f"第{page_num}页获取到{len(model_vo_list)}个模型")

                # 检查是否还有下一页
                total = data_list.get('total', 0)
                if page_num * page_size >= total:
                    log.info(f"共获取{len(all_models)}个模型，总数{total}")
                    break

                page_num += 1

            except Exception as e:
                log.error(f"获取模型列表失败: {e}")
                break

        return all_models

    def get_model_id(self, queryString='null'):
        """获取模型ID"""
        url = self.url + '/forface/builder/model/queryMyModelList'
        data = {
            "checkStatusList": [], "queryString": queryString, "pageNum": 1,
            "pageSize": 20, "categoryId": None, "structureTemplateStatus": [],
            "baseModelType": [], "fileType": [], "releaseStatusAll": [], "equationStatus": []
        }

        try:
            result = self._session.post(url, json=data, timeout=30)
            modelVoList = get_value(result, '/data/modelVoList')

            if modelVoList:
                for item in modelVoList:
                    if queryString in item.get('modelName', ''):
                        return item.get('id')

                # 如果没有完全匹配，返回第一个
                return modelVoList[0].get('id')
            else:
                log.error(f"未找到模型{queryString}")
        except Exception as e:
            log.error(f"获取模型ID失败 {queryString}: {e}")

        return None

    def argument_value(self, datas):
        """提取参数值"""
        keys_to_remove = {'name', 'interfaceName', 'originValue', 'type', 'value'}
        values = []
        for data in datas:
            value = {k: v for k, v in data.items() if k in keys_to_remove}
            values.append(value)
        return values

    def get_builder_argument(self, modelname=None, modelFullname=None,
                             requestKeyList=None, pagesize=20, equ_list=None):
        """查询模型的建模记录，获取建模参数"""
        json_data = []
        url = self.url + "/forface/builder/requestShunt/queryHistoryList"

        data = {
            "pageNum": 1, "pageSize": pagesize, "modelName": modelname,
            "modelFullname": modelFullname,
            "sourceList": ["1", "2", "3", "4", "0"], "modelTypeList": [],
            "updateTimeStart": "2026-01-01 12:17:42", "updateTimeEnd": "2026-01-31 12:17:42"
        }

        if requestKeyList:
            data["requestKeyList"] = requestKeyList.split(',')

        log.info(f"请求url：{url}, 请求参数:{data}")

        try:
            result = self._session.post(url, json=data, timeout=30)
            data_list = get_value(result, '/data/list')

            if not data_list:
                return json_data

            for item in data_list:
                if not item.get("userParamList"):
                    continue

                request_data = {}
                attr_info = []

                modelName = item.get('modelName')
                modelId = item.get('modelId')
                modelProperty = item.get('modelProperty')
                modelFullname = item.get('modelFullname')
                msg = item.get('msg')

                modelKey = self.get_builder_modelKey(modelId, modelFullname)
                requestParamList = self.argument_value(item.get("requestParamList", []))
                userParamList = self.argument_value(item.get("userParamList", []))

                # 提取用户参数
                for argument_data in item.get("userParamList", []):
                    param = {
                        'name': argument_data.get('name', ''),
                        'value': argument_data.get('value', ''),
                        'groupBy': argument_data.get('groupBy', '')
                    }
                    attr_info.append(param)

                request_data.update({
                    'msg': msg,
                    'modelname': modelName,
                    'equlist': equ_list,
                    'modelProperty': modelProperty,
                    'modelFullname': modelFullname,
                    'modelKey': modelKey,
                    'attr_info': attr_info,
                    'requestParamList': requestParamList,
                    'userParamList': userParamList,
                    'requestKey': item.get('requestKey')
                })

                json_data.append(request_data)

        except Exception as e:
            log.error(f"获取建模参数失败 {modelname}: {e}")

        return json_data

    def value_parse(self, datas):
        """解析参数值"""
        attr_value = []
        for data in datas:
            type_val = data.get('type')
            id_val = data.get('id')
            name = data.get('modelAttrsName')
            treeMark = data.get('treeMark', '').split('-')[-2] if data.get('treeMark') else ''
            haveEquation = data.get('haveEquation')
            child = data.get('children')

            if child:
                attr = self.value_parse(child)
                attr_value.extend(attr)
            elif type_val in ['standardLib', 'standardTolerance'] or haveEquation == 1:
                continue
            else:
                attr_value.append({
                    'name': name,
                    'type': type_val,
                    'groupBy': treeMark,
                    'id': id_val
                })

        return attr_value

    def get_builder_datavalue(self, modelname):
        """获取模型的所有数据值"""
        modelid = self.get_model_id(modelname)
        if not modelid:
            return None

        equ_value = self.queryEquationIsTrue(modelid)
        request_value = self.get_builder_argument(modelname, equ_list=equ_value)
        return request_value

    def get_model_valid_value(self, modelId):
        """获取模型有效值"""
        url = self.url + '/forface/builder/model/modelInfo'
        data = {"id": modelId}

        try:
            result = self._session.post(url, json=data, timeout=30)
            if result.status_code == 200:
                datas = get_value(result, '/data/buModelInterfaceVos')
                return self.value_parse(datas)
        except Exception as e:
            log.error(f"获取模型有效值失败 {modelId}: {e}")

        return None

    def get_builder_modelKey(self, id, full_name=None):
        """获取模型索引"""
        url = self.url + "/forface/builder/model/modelInfo"
        data = {"id": id}

        try:
            result = self._session.post(url, json=data, timeout=30)
            modelIndexList = get_value(result, '/data/modelIndexList')

            if not modelIndexList:
                return None

            if full_name:
                max_score = 0
                best_key = modelIndexList[0]['outsideKey']
                for index_item in modelIndexList:
                    outsideKey = index_item['outsideKey']
                    match = fuzz.partial_ratio(outsideKey.lower(), full_name.lower())
                    if match > max_score:
                        max_score = match
                        best_key = outsideKey
                return best_key
            else:
                return modelIndexList[0]['outsideKey']
        except Exception as e:
            log.error(f"获取模型索引失败 {id}: {e}")

        return None

    def _download_file(self, url, data, filepath):
        """通用下载文件方法"""
        try:
            response = self._session.post(url, json=data, timeout=60)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return True, filepath
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def download_model(self, dir, id, modelname):
        """下载模型文件"""
        url = self.url + '/forface/builder/model/downloadBaseModelFile'
        data = {"id": id}
        filepath = os.path.join(dir, modelname)
        return self._download_file(url, data, filepath)

    def download_Template(self, dir, id, modelname):
        """下载模板文件"""
        url = self.url + '/forface/builder/modelInterface/downloadTemplate'
        data = {"modelId": id}
        modelname = modelname.split('.')[0] + '.xls'
        filepath = os.path.join(dir, modelname)
        return self._download_file(url, data, filepath)

    def download_Equation(self, dir, id, modelname):
        """下载方程式文件"""
        url = self.url + '/forface/builder/equation/exportEquation'
        data = {"modelId": id}
        modelname = modelname.split('.')[0] + '_方程式配置.xlsx'
        filepath = os.path.join(dir, modelname)
        return self._download_file(url, data, filepath)

    def download_drawing(self, dir, id, modelname):
        """下载图纸文件"""
        url = self.url + '/forface/builder/drawing/template/show'
        data = {"modelId": id}

        try:
            response = self._session.post(url, json=data, timeout=30)
            flatTemplateList = get_value(response, '/data/flatTemplateList')

            if not flatTemplateList:
                return True, "无2d工程图"

            success_count = 0
            for i, item in enumerate(flatTemplateList):
                templatePath = item['templatePath']
                base_name = modelname.split('.')[0]
                suffix = f'-副本{i}' if i > 0 else ''
                filename = f'{base_name}{suffix}.SLDDRW'
                filepath = os.path.join(dir, filename)

                try:
                    resp = requests.get(templatePath, timeout=60)
                    if resp.status_code == 200:
                        os.makedirs(dir, exist_ok=True)
                        with open(filepath, 'wb') as f:
                            f.write(resp.content)
                        success_count += 1
                except Exception as e:
                    log.error(f"下载图纸失败 {templatePath}: {e}")

            return True, f"成功下载{success_count}个图纸"
        except Exception as e:
            return False, str(e)

    def queryEquationIsTrue(self, id):
        """查询方程式"""
        equlist = []
        url = self.url + '/forface/builder/equation/queryEquationList'
        data = {"modelId": id}

        try:
            response = self._session.post(url, json=data, timeout=30)
            datas = get_value(response, '/data')

            if datas:
                for data_item in datas:
                    equlist.append({
                        'name': data_item.get('modelAttrsName'),
                        'interfaceName': data_item.get('interfaceName'),
                        'equation': data_item.get('equationDesc')
                    })
        except Exception as e:
            log.error(f"查询方程式失败 {id}: {e}")

        return equlist


class ModelDownloader:
    """模型下载器（多线程）"""

    def __init__(self, builder_model, max_workers=5):
        self.builder = builder_model
        self.max_workers = max_workers
        self._queue = queue.Queue()
        self._results = []
        self._lock = threading.Lock()

    def download_model_task(self, model_info, download_dir):
        """单个模型下载任务"""
        name, model_id, file_type = model_info
        log.info(f"开始下载模型: {name}")

        results = []

        # 下载模型文件
        success, msg = self.builder.download_model(download_dir, model_id, name)
        results.append(('模型', name, success, msg))

        # 下载模板
        success, msg = self.builder.download_Template(download_dir, model_id, name)
        results.append(('模板', name, success, msg))

        # 下载图纸
        success, msg = self.builder.download_drawing(download_dir, model_id, name)
        results.append(('图纸', name, success, msg))

        # 下载方程式
        success, msg = self.builder.download_Equation(download_dir, model_id, name)
        results.append(('方程式', name, success, msg))

        with self._lock:
            self._results.extend(results)

        log.info(f"完成下载模型: {name}")
        return name, results

    def batch_download_models(self, model_list, download_dir):
        """批量下载模型（多线程）"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for model_info in model_list:
                future = executor.submit(self.download_model_task, model_info, download_dir)
                futures.append(future)

            for future in as_completed(futures):
                try:
                    name, results = future.result()
                    log.info(f"模型 {name} 下载完成")
                except Exception as e:
                    log.error(f"下载任务失败: {e}")

        return self._results


class ModelDataCollector:
    """模型数据收集器（多线程）"""

    def __init__(self, builder_model, max_workers=5):
        self.builder = builder_model
        self.max_workers = max_workers
        self._collected_data = []
        self._lock = threading.Lock()

    def collect_model_data_task(self, model_info, sample_size=3):
        """收集单个模型数据的任务"""
        modelname = model_info['name'] if isinstance(model_info, dict) else model_info
        try:
            log.info(f"开始收集模型数据: {modelname}")
            datas = self.builder.get_builder_datavalue(modelname)

            if datas:
                try:
                    # 随机采样
                    sampled_data = random.sample(datas, min(sample_size, len(datas)))
                    with self._lock:
                        self._collected_data.extend(sampled_data)
                    log.info(f"模型 {modelname} 收集到 {len(sampled_data)} 条数据")
                    return modelname, len(sampled_data)
                except ValueError:
                    # 如果数据量不足，使用全部数据
                    with self._lock:
                        self._collected_data.extend(datas)
                    log.info(f"模型 {modelname} 数据量不足，使用全部 {len(datas)} 条数据")
                    return modelname, len(datas)
            else:
                log.warning(f"模型 {modelname} 无数据")
                return modelname, 0

        except Exception as e:
            log.error(f"收集模型 {modelname} 数据失败: {e}")
            return modelname, 0

    def collect_model_with_equation(self, model_info, sample_size=3):
        """收集有方程式的模型数据"""
        modelname = model_info['name']
        try:
            log.info(f"检查模型方程式: {modelname}")
            modelid = model_info['id']

            if not modelid:
                log.warning(f"模型 {modelname} 不存在")
                return None

            # 查询方程式
            equations = self.builder.queryEquationIsTrue(modelid)

            if not equations:
                log.info(f"模型 {modelname} 没有方程式，跳过")
                return None

            log.info(f"模型 {modelname} 有 {len(equations)} 个方程式，开始收集数据")

            # 收集数据
            datas = self.builder.get_builder_datavalue(modelname)

            if datas:
                sampled_data = random.sample(datas, min(sample_size, len(datas)))

                # 添加方程式信息到数据中
                for data_item in sampled_data:
                    data_item['has_equation'] = True
                    data_item['equation_count'] = len(equations)
                    data_item['equations'] = equations
                    data_item['model_id'] = modelid
                    data_item['model_name'] = modelname

                with self._lock:
                    self._collected_data.extend(sampled_data)

                log.info(f"模型 {modelname} 收集完成，方程式数: {len(equations)}，数据条数: {len(sampled_data)}")
                return modelname, len(sampled_data), len(equations)
            else:
                log.warning(f"模型 {modelname} 无数据")
                return None

        except Exception as e:
            log.error(f"处理模型 {modelname} 失败: {e}")
            return None

    def find_models_with_equation(self, model_list, max_workers=20):
        """多线程查找有方程式的模型"""
        models_with_equation = []
        self._equation_lock = threading.Lock()

        def check_model_equation(model):
            try:
                modelid = model['id']
                equations = self.builder.queryEquationIsTrue(modelid)
                if equations:
                    model_with_eq = {
                        'name': model['name'],
                        'id': modelid,
                        'equation_count': len(equations),
                        'equations': equations
                    }
                    return model_with_eq
            except Exception as e:
                log.error(f"检查模型 {model.get('name')} 失败: {e}")
            return None

        # 多线程执行
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_model_equation, model): model
                       for model in model_list}

            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                if result:
                    with self._equation_lock:
                        models_with_equation.append(result)

                # 每100个打印一次进度
                if (i + 1) % 100 == 0:
                    log.info(f"已检查 {i + 1}/{len(model_list)} 个模型，"
                             f"找到 {len(models_with_equation)} 个有方程式的模型")

        return models_with_equation
    # def find_models_with_equation(self, model_list):
    #     """查找有方程式的模型"""
    #     models_with_equation = []
    #
    #     for model in model_list:
    #         try:
    #             modelid = model['id']
    #             if modelid:
    #                 equations = self.builder.queryEquationIsTrue(modelid)
    #                 if equations:
    #                     model_with_eq = {
    #                         'name': model['name'],
    #                         'id': modelid,
    #                         'fullname': model.get('fullname', ''),
    #                         'file_type': model.get('file_type', ''),
    #                         'equation_count': len(equations),
    #                         'equations': equations
    #                     }
    #                     models_with_equation.append(model_with_eq)
    #                     log.info(f"找到有方程式的模型: {model['name']}，方程式数: {len(equations)}")
    #         except Exception as e:
    #             log.error(f"检查模型 {model.get('name', 'Unknown')} 方程式失败: {e}")
    #
    #     return models_with_equation

    def batch_collect_all_models_data(self, model_list, output_file, sample_size=10):
        """批量收集所有模型数据"""
        log.info(f"开始收集 {len(model_list)} 个模型的数据")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for model in model_list:
                future = executor.submit(self.collect_model_data_task, model, sample_size)
                futures.append(future)

            # 等待所有任务完成
            total_collected = 0
            for future in as_completed(futures):
                try:
                    modelname, count = future.result()
                    total_collected += count
                except Exception as e:
                    log.error(f"任务执行失败: {e}")

        # 保存数据到Excel
        if self._collected_data:
            df = pd.DataFrame(self._collected_data)
            df.to_excel(output_file, index=False, engine='openpyxl')
            log.info(f"数据收集完成，共收集 {total_collected} 条数据，保存到 {output_file}")
        else:
            log.warning("未收集到任何数据")

        return total_collected

    def batch_collect_equation_models(self, model_list, output_file, sample_size=10):
        """批量收集有方程式的模型数据"""
        # 先筛选出有方程式的模型
        equation_models = self.find_models_with_equation(model_list)

        if not equation_models:
            log.warning("未找到有方程式的模型")
            return 0

        log.info(f"找到 {len(equation_models)} 个有方程式的模型")

        # 保存方程式模型列表
        equation_models_file = output_file.replace('.xls', '_equation_models.xlsx')
        df_models = pd.DataFrame(equation_models)
        # 将equations列转换为字符串以便保存
        df_models['equations'] = df_models['equations'].apply(lambda x: str(x))
        df_models.to_excel(equation_models_file, index=False, engine='openpyxl')
        log.info(f"方程式模型列表已保存到: {equation_models_file}")

        # 收集这些模型的数据
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for model in equation_models:
                future = executor.submit(self.collect_model_with_equation, model, sample_size)
                futures.append(future)

            total_collected = 0
            total_equations = 0
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        modelname, data_count, equation_count = result
                        total_collected += data_count
                        total_equations += equation_count
                except Exception as e:
                    log.error(f"任务执行失败: {e}")

        # 保存数据到Excel
        if self._collected_data:
            df = pd.DataFrame(self._collected_data)
            # 将equations列转换为字符串以便保存
            if 'equations' in df.columns:
                df['equations'] = df['equations'].apply(lambda x: str(x))
            output_data_file = output_file.replace('.xls', '_equation_data.xlsx')
            df.to_excel(output_data_file, index=False, engine='openpyxl')
            log.info(
                f"方程式模型数据收集完成，共 {len(equation_models)} 个模型，{total_collected} 条数据，{total_equations} 个方程式")
            log.info(f"数据保存到: {output_data_file}")
        else:
            log.warning("未收集到任何数据")

        return total_collected


def main():
    """主函数"""
    # 配置信息
    web_url = 'https://builder.forface3d.com/home'
    api_url = 'https://prod.forface3d.com'
    username = os.getenv("LEGACY_BUILDER_USERNAME", "")
    password = os.getenv("LEGACY_BUILDER_PASSWORD", "")

    # 目录配置
    download_dir = r'D:\三维\建模模型\装配体模型'
    output_excel = r'D:\三维\建模模型\装配体模型\基准测试数据.xls'

    # 登录获取token
    try:
        # token = login(web_url, username, password)
        # token = token.strip('"')
        token = os.getenv("LEGACY_BUILDER_WEB_TOKEN", "")
        log.info("登录成功")
    except Exception as e:
        log.error(f"登录失败: {e}")
        return

    # 创建BuilderModel实例
    builder = BuilderModel(api_url, token)

    # 首先获取所有模型列表
    log.info("正在从接口获取所有模型列表...")
    all_models = builder.get_all_models(page_size=100)

    if not all_models:
        log.error("未获取到任何模型")
        return

    log.info(f"共获取到 {len(all_models)} 个模型")

    # 可以选择过滤文件类型（例如只处理装配体）
    assembly_models = [m for m in all_models if m.get('file_type') == 'SLDASM']
    log.info(f"其中装配体模型: {len(assembly_models)} 个")

    # 选择执行模式
    print("\n请选择模式:")
    print("1: 下载所有模型")
    print("2: 下载装配体模型")
    print("3: 收集所有模型数据")
    print("4: 收集装配体模型数据")
    print("5: 查找有方程式的模型并收集数据")
    print("6: 只查找有方程式的模型（不收集数据）")

    mode = input("请输入模式 (1/2/3/4/5/6): ").strip()

    if mode == '1':
        # 模式1：下载所有模型
        downloader = ModelDownloader(builder, max_workers=5)

        model_list = []
        for model in all_models:
            model_list.append([model['name'], model['id'], model.get('file_type', '')])

        log.info(f"开始批量下载 {len(model_list)} 个模型")
        results = downloader.batch_download_models(model_list, download_dir)

        # 输出下载结果统计
        success_count = sum(1 for r in results if r[2])
        log.info(f"下载完成: 成功 {success_count}/{len(results)}")

    elif mode == '2':
        # 模式2：下载装配体模型
        downloader = ModelDownloader(builder, max_workers=5)

        model_list = []
        for model in assembly_models:
            model_list.append([model['name'], model['id'], model.get('file_type', '')])

        log.info(f"开始批量下载 {len(model_list)} 个装配体模型")
        results = downloader.batch_download_models(model_list, download_dir)

        # 输出下载结果统计
        success_count = sum(1 for r in results if r[2])
        log.info(f"下载完成: 成功 {success_count}/{len(results)}")

    elif mode == '3':
        # 模式3：收集所有模型数据
        collector = ModelDataCollector(builder, max_workers=10)
        total = collector.batch_collect_all_models_data(all_models, output_excel, sample_size=10)
        log.info(f"数据收集完成，共收集 {total} 条数据")

    elif mode == '4':
        # 模式4：收集装配体模型数据
        collector = ModelDataCollector(builder, max_workers=10)
        total = collector.batch_collect_all_models_data(assembly_models, output_excel, sample_size=10)
        log.info(f"数据收集完成，共收集 {total} 条数据")

    elif mode == '5':
        # 模式5：查找有方程式的模型并收集数据
        collector = ModelDataCollector(builder, max_workers=10)
        total = collector.batch_collect_equation_models(all_models, output_excel, sample_size=10)
        log.info(f"方程式模型数据收集完成，共收集 {total} 条数据")

    elif mode == '6':
        # 模式6：只查找有方程式的模型
        collector = ModelDataCollector(builder, max_workers=10)
        equation_models = collector.find_models_with_equation(all_models)

        if equation_models:
            # 保存结果
            output_file = output_excel.replace('.xls', '_equation_models_only.xlsx')
            df = pd.DataFrame(equation_models)
            # 将equations列转换为字符串以便保存
            df['equations'] = df['equations'].apply(lambda x: str(x))
            df.to_excel(output_file, index=False, engine='openpyxl')

            log.info(f"\n找到 {len(equation_models)} 个有方程式的模型:")
            for model in equation_models:
                log.info(f"  - {model['name']}: {model['equation_count']} 个方程式")
            log.info(f"\n详细列表已保存到: {output_file}")
        else:
            log.warning("未找到有方程式的模型")

    else:
        log.error("无效的模式选择")


if __name__ == '__main__':
    main()
# data_handle.py

import os
import re
import random
import glob
import uuid
import json
import csv
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Union, Optional, Callable
from pathlib import Path

# 可选导入
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class FileManager:
    """文件管理器 - 处理文件读取和随机文件选取"""

    def __init__(self):
        self.file_cache = {}
        self.directory_cache = {}

    def read_file(self, file_path: str, file_format: str = 'auto', key: str = None) -> Any:
        cache_key = f"{file_path}:{file_format}:{key}"
        if cache_key in self.file_cache:
            return self.file_cache[cache_key]

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if file_format == 'auto':
            ext = os.path.splitext(file_path)[1].lower()
            format_map = {'.json': 'json', '.yaml': 'yaml', '.yml': 'yaml', '.txt': 'txt', '.csv': 'csv'}
            file_format = format_map.get(ext, 'txt')

        result = None
        try:
            if file_format == 'json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    result = data.get(key) if key else data
            elif file_format == 'yaml':
                if not YAML_AVAILABLE:
                    raise ImportError("需要安装PyYAML")
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    result = data.get(key) if key else data
            elif file_format == 'txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    result = f.read().strip()
            elif file_format == 'csv':
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    result = list(reader)
            else:
                with open(file_path, 'rb') as f:
                    result = f.read()
        except Exception as e:
            raise RuntimeError(f"读取文件失败 {file_path}: {str(e)}")

        if result is not None:
            self.file_cache[cache_key] = result
        return result

    def get_random_file(self, directory: str, patterns: List[str] = None,
                        extensions: List[str] = None, recursive: bool = True) -> Optional[str]:
        """从目录中随机获取一个文件"""
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在: {directory}")

        cache_key = f"{directory}:{patterns}:{extensions}:{recursive}"
        if cache_key in self.directory_cache:
            files = self.directory_cache[cache_key]
        else:
            files = self._find_files(directory, patterns, extensions, recursive)
            self.directory_cache[cache_key] = files

        if not files:
            return None

        return random.choice(files)

    def _find_files(self, directory: str, patterns: List[str],
                    extensions: List[str], recursive: bool) -> List[str]:
        all_files = []

        if extensions:
            for ext in extensions:
                if not ext.startswith('.'):
                    ext = f".{ext}"
                pattern = f"*{ext}"
                if recursive:
                    search_path = os.path.join(directory, "**", pattern)
                    all_files.extend(glob.glob(search_path, recursive=True))
                else:
                    search_path = os.path.join(directory, pattern)
                    all_files.extend(glob.glob(search_path))

        elif patterns:
            for pattern in patterns:
                if recursive:
                    search_path = os.path.join(directory, "**", pattern)
                    all_files.extend(glob.glob(search_path, recursive=True))
                else:
                    search_path = os.path.join(directory, pattern)
                    all_files.extend(glob.glob(search_path))
        else:
            if recursive:
                search_path = os.path.join(directory, "**", "*")
                all_files = glob.glob(search_path, recursive=True)
            else:
                search_path = os.path.join(directory, "*")
                all_files = glob.glob(search_path)
            all_files = [f for f in all_files if os.path.isfile(f)]

        return all_files

    def get_files_list(self, directory: str, pattern: str = "*",
                       recursive: bool = False) -> List[str]:
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在: {directory}")

        if recursive:
            search_path = os.path.join(directory, "**", pattern)
            files = glob.glob(search_path, recursive=True)
        else:
            search_path = os.path.join(directory, pattern)
            files = glob.glob(search_path)

        return [f for f in files if os.path.isfile(f)]

    def clear_cache(self):
        self.file_cache.clear()
        self.directory_cache.clear()


class DataHandle:
    """数据处理核心类"""

    def __init__(self, test_files_dir: str = "test_files"):
        self.file_manager = FileManager()
        self.test_files_dir = test_files_dir
        self.global_vars = {}

        # 内置函数
        self.builtin_functions = {
            'uuid': lambda: str(uuid.uuid4()),
            'timestamp': lambda: int(datetime.now().timestamp()),
            'datetime_now': lambda fmt='%Y-%m-%d %H:%M:%S': datetime.now().strftime(fmt),
            'date_today': lambda: date.today().isoformat(),
            'random_int': lambda min_val=1, max_val=100: random.randint(int(min_val), int(max_val)),
            'random_float': lambda min_val=0.0, max_val=1.0: round(random.uniform(float(min_val), float(max_val)), 2),
            'random_string': lambda length=8: ''.join(random.choices(
                'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=int(length))),
            'random_bool': lambda: random.choice([True, False]),
            'random_choice': lambda *args: random.choice(args) if args else None,
        }

        self.placeholder_pattern = re.compile(r'\$\{([^}]+)\}')

    def set_global(self, key: str, value: Any):
        self.global_vars[key] = value

    def get_global(self, key: str, default=None):
        return self.global_vars.get(key, default)

    # ==================== 主入口 ====================

    def process_data(self, data: Any, context: Dict = None) -> Any:
        """处理数据，替换所有占位符"""
        if context is None:
            context = {}
        full_context = {**self.global_vars, **context}

        if isinstance(data, str):
            return self._process_string(data, full_context)
        elif isinstance(data, dict):
            return {key: self.process_data(value, full_context) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.process_data(item, full_context) for item in data]
        else:
            return data

    def _process_string(self, text: str, context: Dict) -> Any:
        """处理字符串中的占位符"""
        if '${' not in text:
            return text

        # 完整占位符
        expr = self._extract_placeholder(text.strip())
        if expr is not None:
            result = self._resolve_expression(expr, context)
            if not isinstance(result, str):
                return result
            return result

        # 多个占位符
        def replacer(match):
            inner = match.group(1)
            try:
                result = self._resolve_expression(inner, context)
                return str(result) if result is not None else ''
            except Exception as e:
                print(f"解析占位符失败: {inner}, 错误: {e}")
                return match.group(0)

        return self.placeholder_pattern.sub(replacer, text)

    def _extract_placeholder(self, text: str) -> Optional[str]:
        """从 ${...} 中提取表达式，支持嵌套"""
        if not text.startswith('${') or not text.endswith('}'):
            return None

        depth = 0
        for i, ch in enumerate(text[2:], 2):
            if ch == '{':
                depth += 1
            elif ch == '}':
                if depth == 0:
                    if i == len(text) - 1:
                        return text[2:i]
                depth -= 1
        return None

    # ==================== 表达式解析 ====================

    def _resolve_expression(self, expr: str, context: Dict) -> Any:
        """解析表达式"""
        expr = expr.strip()

        # ---- 数据源前缀 ----
        if expr.startswith('getfile:'):
            params = expr[8:]
            params = self._replace_nested(params, context)
            return self._handle_getfile(params)

        if expr.startswith('listfile:'):
            params = expr[9:]
            params = self._replace_nested(params, context)
            return self._handle_listfile(params)

        if expr.startswith('file:'):
            params = expr[5:]
            params = self._replace_nested(params, context)
            return self._handle_file(params)

        if expr.startswith('global:'):
            return self.get_global(expr[7:].strip())

        if expr.startswith('faker:'):
            return self._handle_faker(expr[6:].strip())

        # ---- 函数调用 ----
        func_match = re.match(r'^(\w+)\((.*)\)$', expr)
        if func_match:
            func_name = func_match.group(1)
            args_str = func_match.group(2)
            if func_name in self.builtin_functions:
                return self._call_builtin_function(func_name, args_str, context)

        # ---- 无参内置函数 ----
        if expr in self.builtin_functions:
            return self.builtin_functions[expr]()

        # ---- 变量 ----
        if expr in context:
            return context[expr]

        # ---- 字面量 ----
        if (expr.startswith("'") and expr.endswith("'")) or (expr.startswith('"') and expr.endswith('"')):
            return expr[1:-1]

        if expr.lower() == 'true':
            return True
        if expr.lower() == 'false':
            return False
        if expr.lower() in ('null', 'none'):
            return None

        try:
            return int(expr)
        except ValueError:
            pass
        try:
            return float(expr)
        except ValueError:
            pass

        return f"${{{expr}}}"

    # ==================== 嵌套占位符替换 ====================

    def _replace_nested(self, text: str, context: Dict) -> str:
        """替换文本中的简单占位符 ${xxx}，用于 getfile/listfile/file 参数预处理"""
        def replacer(match):
            inner = match.group(1).strip()

            if inner.startswith('global:'):
                key = inner[7:].strip()
                val = self.global_vars.get(key, '')
                return str(val) if val else match.group(0)

            if inner in self.builtin_functions:
                try:
                    return str(self.builtin_functions[inner]())
                except:
                    return match.group(0)

            m = re.match(r'^(\w+)\((.*)\)$', inner)
            if m:
                fname = m.group(1)
                fargs = m.group(2)
                if fname in self.builtin_functions:
                    return str(self._call_builtin_function(fname, fargs, context))

            return match.group(0)

        result = text
        for _ in range(5):
            new_result = re.sub(r'\$\{([^}]+)\}', replacer, result)
            if new_result == result:
                break
            result = new_result
        return result

    # ==================== getfile / listfile / file 处理 ====================

    def _handle_getfile(self, params: str) -> Optional[str]:
        """
        params 格式: 目录:扩展名
        例: "C:/path/to/files:stp,step"
        """
        # 处理 Windows 盘符
        directory, rest = self._split_path(params)
        extensions = None
        patterns = None

        if rest:
            param = rest[0].strip()
            if param:
                if ',' in param and '*' not in param:
                    extensions = [ext.strip() for ext in param.split(',')]
                elif '*' in param:
                    patterns = [param]
                else:
                    extensions = [param]

        result = self.file_manager.get_random_file(
            directory=directory,
            patterns=patterns,
            extensions=extensions,
            recursive=True
        )

        if result is None:
            raise FileNotFoundError(f"目录中无匹配文件: {directory}")

        return result

    def _handle_listfile(self, params: str) -> List[str]:
        directory, rest = self._split_path(params)
        pattern = rest[0].strip() if rest else "*"
        return self.file_manager.get_files_list(directory, pattern, recursive=True)

    def _handle_file(self, params: str) -> Any:
        directory, rest = self._split_path(params)
        file_format = rest[0].strip() if rest else 'auto'
        key = rest[1].strip() if len(rest) > 1 else None
        return self.file_manager.read_file(directory, file_format, key)

    def _split_path(self, params: str) -> tuple:
        """
        智能分割路径，处理 Windows 盘符
        "C:/a/b:ext"  → ("C:/a/b", ["ext"])
        "/a/b:ext"     → ("/a/b", ["ext"])
        "a/b:ext"      → ("a/b", ["ext"])
        """
        parts = params.split(':')

        # Windows 盘符: C:xxx
        if len(parts) >= 2 and len(parts[0]) == 1 and parts[0].isalpha():
            directory = parts[0] + ':' + parts[1]
            rest = parts[2:]
        else:
            directory = parts[0]
            rest = parts[1:]

        return directory.strip(), rest

    # ==================== 内置函数调用 ====================

    def _call_builtin_function(self, func_name: str, args_str: str, context: Dict) -> Any:
        func = self.builtin_functions[func_name]
        if not args_str.strip():
            return func()

        args, kwargs = self._parse_args(args_str, context)
        try:
            return func(*args, **kwargs)
        except TypeError:
            return func()

    def _parse_args(self, args_str: str, context: Dict) -> tuple:
        args = []
        kwargs = {}
        if not args_str.strip():
            return args, kwargs

        for part in self._split_args(args_str):
            part = part.strip()
            if '=' in part:
                k, v = part.split('=', 1)
                kwargs[k.strip()] = self._eval_arg(v.strip(), context)
            else:
                args.append(self._eval_arg(part, context))
        return args, kwargs

    def _split_args(self, args_str: str) -> List[str]:
        parts = []
        current = []
        in_quotes = False
        quote_char = None
        for ch in args_str:
            if ch in ('"', "'"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = ch
                elif ch == quote_char:
                    in_quotes = False
                    quote_char = None
                current.append(ch)
            elif ch == ',' and not in_quotes:
                parts.append(''.join(current))
                current = []
            else:
                current.append(ch)
        if current:
            parts.append(''.join(current))
        return parts

    def _eval_arg(self, arg: str, context: Dict) -> Any:
        if (arg.startswith("'") and arg.endswith("'")) or (arg.startswith('"') and arg.endswith('"')):
            return arg[1:-1]
        if arg.lower() == 'true': return True
        if arg.lower() == 'false': return False
        try: return int(arg)
        except ValueError: pass
        try: return float(arg)
        except ValueError: pass
        return arg

    # ==================== Faker 处理 ====================

    def _handle_faker(self, method_expr: str) -> Any:
        try:
            from common.utils.data_utils.faker_handle import FakerData
            faker = FakerData()
            match = re.match(r'^(\w+)(?:\((.*)\))?$', method_expr)
            if match:
                method_name = match.group(1)
                args_str = match.group(2) or ""
                method = getattr(faker, method_name, None)
                if method and callable(method):
                    args, kwargs = self._parse_args(args_str, {})
                    return method(*args, **kwargs)
        except Exception as e:
            print(f"Faker调用失败: {e}")
        return f"${{faker:{method_expr}}}"

    # ==================== 工具方法 ====================

    def load_yaml_data(self, yaml_file: str, context: Dict = None) -> Any:
        if not YAML_AVAILABLE:
            raise ImportError("需要安装PyYAML")
        if not os.path.exists(yaml_file):
            raise FileNotFoundError(f"YAML文件不存在: {yaml_file}")
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return self.process_data(data, context)

    def clear_cache(self):
        self.file_manager.clear_cache()
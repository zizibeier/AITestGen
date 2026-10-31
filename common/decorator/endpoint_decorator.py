# common/utils/endpoint_decorator.py
"""
通用接口路径装饰器
"""

from functools import wraps
from typing import Optional, Dict, Any


def with_endpoint(endpoint_name: str, has_id_param: bool = False):
    """
    通用接口路径装饰器

    Args:
        endpoint_name: 配置文件中的路径名称，如 "cnc.list", "user.detail"
        has_id_param: 是否需要路径参数（如 {cnc_id}）

    Example:
        # 无参数路径
        @with_endpoint("cnc.list")
        def get_list(self, endpoint, page=1, size=20):
            return self.get(endpoint, params={"page": page, "size": size})

        # 有参数路径（参数名自动匹配）
        @with_endpoint("cnc.detail", has_id_param=True)
        def get_detail(self, endpoint, cnc_id):
            return self.get(endpoint)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 获取接口路径
            endpoint = self.endpoint(endpoint_name)

            # 如果需要路径参数，自动替换
            if has_id_param:
                # 查找路径参数名（如 cnc_id, user_id, model_id）
                param_names = ['cnc_id', 'user_id', 'model_id', 'scene_id']
                for param in param_names:
                    if param in kwargs:
                        endpoint = endpoint.replace(f"{{{param}}}", str(kwargs[param]))
                        break
                    elif len(args) > 0:
                        # 如果是位置参数，假设第一个参数是 id
                        endpoint = endpoint.replace("{id}", str(args[0]))
                        break

            # 调用原函数，传入 endpoint
            return func(self, endpoint, *args, **kwargs)

        return wrapper

    return decorator


def auto_endpoint():
    """
    自动推断接口路径的装饰器

    根据方法名自动推断配置路径
    例如：get_list -> cnc.list
         get_detail -> cnc.detail
         create_cnc -> cnc.create

    Example:
        @auto_endpoint()
        def get_list(self, endpoint):
            return self.get(endpoint)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 获取类名
            class_name = self.__class__.__name__.replace('Endpoints', '').lower()

            # 根据方法名推断接口名
            method_name = func.__name__

            # 映射规则
            endpoint_map = {
                'get_list': f"{class_name}.list",
                'get_detail': f"{class_name}.detail",
                'create': f"{class_name}.create",
                'update': f"{class_name}.update",
                'delete': f"{class_name}.delete",
            }

            endpoint_name = endpoint_map.get(method_name, f"{class_name}.{method_name}")

            # 获取路径
            endpoint = self.endpoint(endpoint_name)

            # 替换路径参数
            for key, value in kwargs.items():
                endpoint = endpoint.replace(f"{{{key}}}", str(value))

            return func(self, endpoint, *args, **kwargs)

        return wrapper

    return decorator


class Endpoint:
    """
    路径管理类 - 更优雅的装饰器

    使用方式：
        @Endpoint.get("cnc.list")
        def get_list(self, endpoint):
            return self.get(endpoint)

        @Endpoint.post("cnc.create")
        def create(self, endpoint, data):
            return self.post(endpoint, json=data)

        @Endpoint.delete("cnc.delete", id_param="cnc_id")
        def delete(self, endpoint, cnc_id):
            return self.delete(endpoint)
    """

    @staticmethod
    def get(endpoint_name: str, id_param: str = None):
        """GET 请求装饰器"""

        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                endpoint = self.endpoint(endpoint_name)
                if id_param and id_param in kwargs:
                    endpoint = endpoint.replace(f"{{{id_param}}}", str(kwargs[id_param]))
                return func(self, endpoint, *args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def post(endpoint_name: str):
        """POST 请求装饰器"""

        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                endpoint = self.endpoint(endpoint_name)
                return func(self, endpoint, *args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def put(endpoint_name: str, id_param: str = None):
        """PUT 请求装饰器"""

        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                endpoint = self.endpoint(endpoint_name)
                if id_param and id_param in kwargs:
                    endpoint = endpoint.replace(f"{{{id_param}}}", str(kwargs[id_param]))
                return func(self, endpoint, *args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def delete(endpoint_name: str, id_param: str = None):
        """DELETE 请求装饰器"""

        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                endpoint = self.endpoint(endpoint_name)
                if id_param and id_param in kwargs:
                    endpoint = endpoint.replace(f"{{{id_param}}}", str(kwargs[id_param]))
                return func(self, endpoint, *args, **kwargs)

            return wrapper

        return decorator
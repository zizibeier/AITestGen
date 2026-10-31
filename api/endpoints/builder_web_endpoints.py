# api/endpoints/builder_web_endpoints.py
"""Builder Web 前端内部接口。

只被 Builder 网页端调用，鉴权使用 Web 端 Token / Cookie：
- 请求头显式携带 Token / Cookie
- 强制 auth=False，避免 APIContext 自动注入 Authorization
- Token / Cookie 只从环境变量或构造参数传入，不写死

域名：api_config.yaml 中的 builder_base_url。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from api.core.base_endpoints import BaseEndpoints, EndpointError
from api.core.builder_client import BuilderClient, best_match, resolve_json_pointer, sanitize_filename
from common.config.settings import Config
from common.utils.logger import log


class BuilderWebTokenMissing(EndpointError):
    """未配置 Web 端 Token，无法调用内部接口。"""


class BuilderWebEndpoints(BaseEndpoints):
    """Builder Web 内部接口封装。"""

    config_prefix = "builder.web"
    base_url_key = "builder_base_url"

    def __init__(
        self,
        ctx,
        token: Optional[str] = None,
        cookie: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(ctx, base_url=base_url)
        self.token = token or Config.BUILDER_WEB_TOKEN
        self.cookie = cookie or Config.BUILDER_WEB_COOKIE
        self.client = BuilderClient()

    # ==================== 鉴权头 ====================

    def _ensure_token(self):
        if not self.token:
            raise BuilderWebTokenMissing(
                "未配置 Builder Web Token。请设置环境变量 BUILDER_WEB_TOKEN "
                "（可选 BUILDER_WEB_COOKIE）后重试"
            )

    def _headers(self) -> Dict[str, str]:
        """显式注入 Web Token / Cookie，绝不使用 Authorization。"""
        self._ensure_token()
        headers = {
            "Token": self.token,
            "Content-Type": "application/json",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        return headers

    def _post_data(
        self,
        key: str,
        payload: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if timeout is not None:
            kwargs["timeout"] = timeout
        return self.post_json(
            key,
            json_data=payload,
            headers=self._headers(),
            auth=False,
            **kwargs,
        )

    # ==================== 模型列表 ====================

    def query_my_models(
        self,
        page_num: int = 1,
        page_size: int = 100,
        query_string: Optional[str] = None,
        **overrides: Any,
    ) -> Dict[str, Any]:
        """查询我的模型（单页），返回 {total, modelVoList}。"""
        payload: Dict[str, Any] = {
            "checkStatusList": [],
            "queryString": query_string,
            "pageNum": page_num,
            "pageSize": page_size,
            "categoryId": None,
            "structureTemplateStatus": [],
            "baseModelType": [],
            "fileType": [],
            "releaseStatusAll": [],
            "equationStatus": [],
        }
        payload.update(overrides)

        body = self._post_data("query_my_model_list", payload)
        data = body.get("data") or {}
        return {
            "total": data.get("total", 0),
            "modelVoList": [
                self._simplify_model(item) for item in (data.get("modelVoList") or [])
            ],
        }

    def query_all_models(
        self, page_size: int = 100, max_pages: int = 100, **overrides: Any
    ) -> List[Dict[str, Any]]:
        """分页查询全部模型。"""
        return self.client.paginate(
            fetch_page=lambda page_num, size: self.query_my_models(
                page_num=page_num, page_size=size, **overrides
            ),
            page_size=page_size,
            extract_items=lambda body: body.get("modelVoList"),
            extract_total=lambda body: body.get("total"),
            max_pages=max_pages,
        )

    def find_model_by_name(self, query_string: str) -> Optional[Dict[str, Any]]:
        """按名称查询模型：优先名称包含，其次返回第一条。"""
        data = self.query_my_models(query_string=query_string, page_size=20)
        models = data.get("modelVoList") or []
        if not models:
            log.error(f"未找到模型: {query_string}")
            return None

        for model in models:
            if query_string in (model.get("name") or ""):
                return model
        return models[0]

    def get_model_id(self, query_string: str) -> Optional[int]:
        """按名称查询模型 ID。"""
        model = self.find_model_by_name(query_string)
        return model.get("id") if model else None

    @staticmethod
    def _simplify_model(model: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": model.get("id"),
            "name": model.get("modelName"),
            "fullname": model.get("modelFullname"),
            "file_type": model.get("fileType"),
            "has_equation": model.get("equationStatus") == 1,
        }

    # ==================== 建模历史 / 参数 ====================

    def query_history_list(
        self,
        model_name: Optional[str] = None,
        model_fullname: Optional[str] = None,
        request_key_list: Optional[Union[str, Sequence[str]]] = None,
        page_size: int = 20,
        page_num: int = 1,
        update_time_start: Optional[str] = None,
        update_time_end: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """查询建模记录列表。"""
        payload: Dict[str, Any] = {
            "pageNum": page_num,
            "pageSize": page_size,
            "modelName": model_name,
            "modelFullname": model_fullname,
            "sourceList": ["1", "2", "3", "4", "0"],
            "modelTypeList": [],
            "updateTimeStart": update_time_start,
            "updateTimeEnd": update_time_end,
        }
        if request_key_list:
            if isinstance(request_key_list, str):
                payload["requestKeyList"] = request_key_list.split(",")
            else:
                payload["requestKeyList"] = list(request_key_list)

        body = self._post_data("query_history_list", payload)
        return resolve_json_pointer(body, "/data/list", []) or []

    def get_builder_argument(
        self,
        model_name: Optional[str] = None,
        model_fullname: Optional[str] = None,
        request_key_list: Optional[Union[str, Sequence[str]]] = None,
        page_size: int = 20,
        equ_list: Optional[List[Dict[str, Any]]] = None,
        **history_kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """查询建模记录并整理成建模参数（老代码 get_builder_argument）。"""
        items = self.query_history_list(
            model_name=model_name,
            model_fullname=model_fullname,
            request_key_list=request_key_list,
            page_size=page_size,
            **history_kwargs,
        )

        results: List[Dict[str, Any]] = []
        for item in items:
            if not item.get("userParamList"):
                continue

            attr_info = [
                {
                    "name": argument.get("name", ""),
                    "value": argument.get("value", ""),
                    "groupBy": argument.get("groupBy", ""),
                }
                for argument in item.get("userParamList", [])
            ]

            results.append(
                {
                    "msg": item.get("msg"),
                    "modelname": item.get("modelName"),
                    "equlist": equ_list,
                    "modelProperty": item.get("modelProperty"),
                    "modelFullname": item.get("modelFullname"),
                    "modelKey": self.get_model_key(
                        item.get("modelId"), item.get("modelFullname")
                    ),
                    "attr_info": attr_info,
                    "requestParamList": self.argument_value(
                        item.get("requestParamList", [])
                    ),
                    "userParamList": self.argument_value(
                        item.get("userParamList", [])
                    ),
                    "requestKey": item.get("requestKey"),
                }
            )
        return results

    @staticmethod
    def argument_value(datas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """只保留参数的关键字段。"""
        keys = {"name", "interfaceName", "originValue", "type", "value"}
        return [
            {key: value for key, value in data.items() if key in keys}
            for data in datas
        ]

    # ==================== 模型详情 ====================

    def query_model_info(self, model_id: Union[str, int]) -> Dict[str, Any]:
        """查询模型详情（data 节点）。"""
        body = self._post_data("model_info", {"id": model_id})
        return body.get("data") or {}

    def get_model_key(
        self, model_id: Union[str, int], full_name: Optional[str] = None
    ) -> Optional[str]:
        """获取模型索引 outsideKey（老代码 get_builder_modelKey）。"""
        index_list = self.query_model_info(model_id).get("modelIndexList") or []
        if not index_list:
            return None

        if not full_name:
            return index_list[0].get("outsideKey")

        candidates = [
            item.get("outsideKey")
            for item in index_list
            if item.get("outsideKey")
        ]
        return best_match(candidates, full_name, default=index_list[0].get("outsideKey"))

    def get_model_valid_value(self, model_id: Union[str, int]) -> List[Dict[str, Any]]:
        """获取模型有效值（老代码 get_model_valid_value）。"""
        data = self.query_model_info(model_id)
        return self.value_parse(data.get("buModelInterfaceVos") or [])

    def value_parse(self, datas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """递归解析模型属性树。"""
        attr_values: List[Dict[str, Any]] = []
        for data in datas:
            children = data.get("children")
            if children:
                attr_values.extend(self.value_parse(children))
                continue

            type_value = data.get("type")
            if type_value in ("standardLib", "standardTolerance") or data.get("haveEquation") == 1:
                continue

            tree_mark = data.get("treeMark") or ""
            group_by = tree_mark.split("-")[-2] if tree_mark else ""
            attr_values.append(
                {
                    "name": data.get("modelAttrsName"),
                    "type": type_value,
                    "groupBy": group_by,
                    "id": data.get("id"),
                }
            )
        return attr_values

    # ==================== 方程式 ====================

    def query_equation_list(self, model_id: Union[str, int]) -> List[Dict[str, Any]]:
        """查询模型方程式（老代码 queryEquationIsTrue）。"""
        body = self._post_data("query_equation_list", {"modelId": model_id})
        return [
            {
                "name": item.get("modelAttrsName"),
                "interfaceName": item.get("interfaceName"),
                "equation": item.get("equationDesc"),
            }
            for item in (resolve_json_pointer(body, "/data", []) or [])
        ]

    # ==================== 文件下载 ====================

    def download_base_model_file(
        self,
        model_id: Union[str, int],
        dest_dir: Union[str, Path],
        file_name: Optional[str] = None,
    ) -> Path:
        file_name = sanitize_filename(file_name or f"{model_id}.bin")
        return self._download(
            "download_base_model_file",
            {"id": model_id},
            Path(dest_dir) / file_name,
        )

    def download_template(
        self,
        model_id: Union[str, int],
        dest_dir: Union[str, Path],
        file_name: Optional[str] = None,
    ) -> Path:
        base_name = (file_name or str(model_id)).split(".")[0]
        return self._download(
            "download_template",
            {"modelId": model_id},
            Path(dest_dir) / f"{base_name}.xls",
        )

    def export_equation(
        self,
        model_id: Union[str, int],
        dest_dir: Union[str, Path],
        file_name: Optional[str] = None,
    ) -> Path:
        base_name = (file_name or str(model_id)).split(".")[0]
        return self._download(
            "export_equation",
            {"modelId": model_id},
            Path(dest_dir) / f"{base_name}_方程式配置.xlsx",
        )

    def download_drawings(
        self,
        model_id: Union[str, int],
        dest_dir: Union[str, Path],
        base_name: Optional[str] = None,
    ) -> List[Path]:
        """下载模型 2D 工程图；没有图纸时返回空列表。"""
        body = self._post_data("drawing_template_show", {"modelId": model_id})
        template_list = resolve_json_pointer(body, "/data/flatTemplateList", []) or []
        if not template_list:
            log.info(f"模型 {model_id} 没有 2D 工程图")
            return []

        dest_dir = Path(dest_dir)
        saved: List[Path] = []
        base_name = (base_name or str(model_id)).split(".")[0]

        for index, item in enumerate(template_list):
            template_path = item.get("templatePath")
            if not template_path:
                continue

            suffix = f"-副本{index}" if index > 0 else ""
            dest_path = dest_dir / f"{base_name}{suffix}.SLDDRW"
            try:
                self.client.download_url(
                    get_fn=lambda url: self.ctx.get(url, auth=False, timeout=60, stream=True),
                    url=template_path,
                    dest_path=dest_path,
                )
                saved.append(dest_path)
            except Exception as exc:
                log.error(f"下载图纸失败 {template_path}: {exc}")

        return saved

    def _download(
        self,
        key: str,
        payload: Dict[str, Any],
        dest_path: Path,
    ) -> Path:
        """POST 下载接口并把二进制响应落盘。"""
        return self.client.download(
            request_fn=lambda: self.post(
                key,
                json_data=payload,
                headers=self._headers(),
                auth=False,
                timeout=60,
                stream=True,
            ),
            dest_path=dest_path,
        )

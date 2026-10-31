# api/core/builder_client.py
"""Builder 接口的底层工具。

这里只放与业务无关的“脏活”：
- JSON Pointer 深层取值（替代 jsonpointer 依赖）
- 分页循环
- 二进制流式下载
- 模糊匹配（替代 fuzzywuzzy.partial_ratio）
- 文件名/目录处理

本类不持有 Session，所有 HTTP 请求由调用方传入 request_fn，
实际仍由 APIContext 发出。
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import requests

from common.utils.logger import log


class BuilderClientError(RuntimeError):
    """Builder 底层工具异常。"""


class BuilderDownloadError(BuilderClientError):
    """文件下载失败。"""


# ==================== JSON Pointer ====================

def resolve_json_pointer(
    document: Any, pointer: str, default: Any = None
) -> Any:
    """按 RFC 6901 解析 JSON Pointer，例如 /data/modelVoList。

    支持 dict 键、list 下标，以及 ~0 / ~1 转义。
    路径不存在时返回 default，不抛异常。
    """
    if pointer in (None, ""):
        return document
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError(f"非法 JSON Pointer: {pointer!r}")

    current = document
    for raw_token in pointer.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")

        if isinstance(current, dict):
            if token not in current:
                return default
            current = current[token]
        elif isinstance(current, (list, tuple)):
            try:
                index = int(token)
            except (TypeError, ValueError):
                return default
            if index < 0 or index >= len(current):
                return default
            current = current[index]
        else:
            return default

    return current


# ==================== 模糊匹配 ====================

def _ratio(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def partial_ratio(left: str, right: str) -> float:
    """近似 fuzzywuzzy.fuzz.partial_ratio，返回 0-100。"""
    left = (left or "").lower()
    right = (right or "").lower()
    if not left or not right:
        return 0.0

    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    if shorter in longer:
        return 100.0

    best = _ratio(shorter, longer)
    window = len(shorter)
    for start in range(0, len(longer) - window + 1):
        best = max(best, _ratio(shorter, longer[start:start + window]))
    return best * 100


def best_match(
    candidates: Sequence[str], query: str, default: Optional[str] = None
) -> Optional[str]:
    """从候选值中选出与 query 最相似的项。"""
    if not candidates:
        return default

    best_candidate = default
    best_score = -1.0
    for candidate in candidates:
        score = partial_ratio(str(candidate), str(query))
        if score > best_score:
            best_score = score
            best_candidate = candidate
    return best_candidate


# ==================== 文件工具 ====================

_ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def sanitize_filename(name: str, fallback: str = "file") -> str:
    """去掉文件名中的非法字符。"""
    cleaned = _ILLEGAL_FILENAME_CHARS.sub("_", str(name or "")).strip(" .")
    return cleaned or fallback


def ensure_dir(dir_path: str) -> Path:
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


class BuilderClient:
    """Builder 底层工具集合。"""

    def __init__(self, chunk_size: int = 64 * 1024):
        self.chunk_size = chunk_size

    # ==================== 分页 ====================

    def paginate(
        self,
        fetch_page: Callable[[int, int], Dict[str, Any]],
        page_size: int,
        extract_items: Callable[[Dict[str, Any]], Optional[List[Any]]],
        extract_total: Optional[Callable[[Dict[str, Any]], Optional[int]]] = None,
        max_pages: int = 100,
    ) -> List[Any]:
        """通用分页循环。

        Args:
            fetch_page: (page_num, page_size) -> 响应 JSON
            page_size: 每页条数
            extract_items: 从响应中取出当前页列表
            extract_total: 从响应中取出总条数；没有总数时靠“空页/不满页”结束
            max_pages: 安全上限，防止服务端分页异常导致死循环

        Returns:
            所有页的条目拼接后的列表
        """
        if page_size <= 0:
            raise ValueError("page_size 必须大于 0")

        all_items: List[Any] = []
        page_num = 1

        while page_num <= max_pages:
            body = fetch_page(page_num, page_size)
            page_items = extract_items(body) or []
            all_items.extend(page_items)

            total = extract_total(body) if extract_total else None
            log.info(
                f"分页查询: 第 {page_num} 页, 本页 {len(page_items)} 条, "
                f"累计 {len(all_items)} 条, 总数 {total}"
            )

            if not page_items:
                break
            if total is not None and page_num * page_size >= total:
                break
            if len(page_items) < page_size:
                break

            page_num += 1
        else:
            log.warning(f"分页达到安全上限 {max_pages} 页，已停止")

        return all_items

    # ==================== 下载 ====================

    def save_binary(self, response: requests.Response, dest_path: Path) -> Path:
        """把响应体流式写入文件。"""
        dest_path = Path(dest_path)
        if response.status_code != 200:
            raise BuilderDownloadError(
                f"下载失败: HTTP {response.status_code}, "
                f"响应片段: {response.text[:300]}"
            )

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as file_obj:
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                if chunk:
                    file_obj.write(chunk)

        log.info(f"文件已保存: {dest_path} ({dest_path.stat().st_size} bytes)")
        return dest_path

    def download(
        self,
        request_fn: Callable[[], requests.Response],
        dest_path: Path,
    ) -> Path:
        """执行 request_fn 并把响应保存为文件。"""
        return self.save_binary(request_fn(), dest_path)

    def download_url(
        self,
        get_fn: Callable[[str], requests.Response],
        url: str,
        dest_path: Path,
    ) -> Path:
        """下载响应里给出的绝对地址（如图纸 templatePath）。"""
        return self.save_binary(get_fn(url), dest_path)

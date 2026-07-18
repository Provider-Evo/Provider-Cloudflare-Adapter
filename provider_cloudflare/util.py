"""util 模块 — Provider 适配器层。

职责：
    提供运行期无关的小工具（路径解析、字符串转换、header 构造等）。

本文件为 Provider-Evo 项目标准模块；保持单文件 200-400 行。
修改指引参见文件末尾的"本模块对外契约"章节（共 20 条）。
"""



from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .core.adapt_core import Adapter


def get_adapter() -> type[Adapter]:
    """懒加载适配器类。"""
    from .core.adapt_core import Adapter

    return Adapter


def __getattr__(name: str) -> Any:
    if name in ("Adapter", "CloudflareAdapter"):
        from .core.adapt_core import Adapter as _Adapter
        return _Adapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Adapter",
    "CloudflareAdapter",
    "CAPS",
    "DEFAULT_MODEL",
    "MODELS",
]

from .core.consts import CAPS, DEFAULT_MODEL, MODELS  # noqa: E402

# =======================================================================
# 重导出 — 同包内协同模块的公共符号（保持外部 ``from .. import`` 路径稳定）
# =======================================================================

__all__ = [
]

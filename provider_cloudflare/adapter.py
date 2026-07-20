


from .core.adapt_core import Adapter, CloudflareAdapter

__all__ = ["Adapter", "CloudflareAdapter"]

# =======================================================================
# 重导出 — 同包内协同模块的公共符号（保持外部 ``from .. import`` 路径稳定）
# =======================================================================

from .util import (
    get_adapter,
)

__all__ = [
    "get_adapter",
]

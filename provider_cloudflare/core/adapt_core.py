

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import aiohttp

from src.core.dispatch.cand import Candidate
from src.foundation.logger import get_logger
from provider_sdk.extensions.platform.adapter import PlatformAdapter

from ..accounts import API_KEYS
from .client import CloudflareClient
from .consts import CAPS, DEFAULT_MODEL, MODELS

logger = get_logger(__name__)


class Adapter(PlatformAdapter):
    """Cloudflare Workers AI 平台适配器（仅需 API Key）"""

    def __init__(self) -> None:
        self._client: Optional[CloudflareClient] = None

    @property
    def name(self) -> str:
        return "cloudflare"

    @property
    def supported_models(self) -> List[str]:
        if self._client is None:
            return list(MODELS)
        return list(self._client._models)

    @property
    def default_capabilities(self) -> Dict[str, bool]:
        return dict(CAPS)

    async def init(self, session: aiohttp.ClientSession) -> None:
        self._client = CloudflareClient()

        api_key = next((k for k in API_KEYS if k and k.strip()), None)

        if not api_key:
            logger.warning("cloudflare 未配置 API Key，插件将无法使用")
            return

        await self._client.init_immediate(session, api_key)

        # 后台拉取远程模型列表
        asyncio.ensure_future(self._background_refresh())

    async def _background_refresh(self) -> None:
        if self._client is None:
            return
        try:
            await self._client.fetch_remote_models()
        except Exception as e:
            logger.debug("cloudflare 后台刷新模型列表: %s", e)

    async def candidates(self) -> List[Candidate]:
        if self._client is None:
            return []
        return await self._client.candidates()

    async def ensure_candidates(self, count: int) -> int:
        if self._client is None:
            return 0
        return await self._client.ensure_candidates(count)

    async def create_transcription(
        self,
        candidate: Candidate,
        audio_data: bytes,
        model: str = DEFAULT_MODEL,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self._client is None:
            raise RuntimeError("cloudflare adapter not initialized")
        return await self._client.create_transcription(
            candidate, audio_data, model, language,
        )

    async def complete(
        self,
        candidate: Candidate,
        messages: List[Dict[str, Any]],
        model: str,
        stream: bool,
        *,
        thinking: bool = False,
        search: bool = False,
        **kw: Any,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        if self._client is None:
            raise RuntimeError("cloudflare adapter not initialized")
        async for chunk in self._client.complete(
            candidate, messages, model, stream,
            thinking=thinking, search=search, **kw,
        ):
            yield chunk

    async def embed(
        self,
        candidate: Candidate,
        input_data: Union[str, List[str]],
        model: str,
    ) -> Dict[str, Any]:
        if self._client is None:
            raise RuntimeError("cloudflare adapter not initialized")
        from src.core.utils.errors import EmbeddingError

        if isinstance(input_data, str):
            input_data = [input_data]

        payload = {"input": input_data}
        result = await self._client._do_request(model, payload)
        return {
            "object": "list",
            "data": result if isinstance(result, list) else [result],
            "model": model,
            "usage": {},
        }

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()


CloudflareAdapter = Adapter

# =======================================================================
# 重导出 — 同包内协同模块的公共符号（保持外部 ``from .. import`` 路径稳定）
# =======================================================================

__all__ = [
]

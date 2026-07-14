"""Cloudflare Workers AI REST API 客户端。

无需 account_id，使用 /ai/run 端点。
"""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import aiohttp

from src.core.dispatch.candidate import Candidate, make_id
from src.foundation.logger import get_logger

from .constants import (
    BASE_URL,
    CAPS,
    DEFAULT_MODEL,
    FETCH_MODELS_ENABLED,
    MAX_RETRIES,
    MODELS,
    MODELS_URL,
    MODEL_CACHE_TTL,
    REQUEST_TIMEOUT_SEC,
)

logger = get_logger(__name__)


class CloudflareClient:
    """Cloudflare Workers AI REST API 客户端（无需 account_id）。"""

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_key: str = ""
        self._candidates: List[Candidate] = []
        self._models: List[str] = list(MODELS)
        self._model_cache_ts: float = 0.0

    async def init_immediate(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._rebuild_candidates()
        logger.debug(
            "cloudflare 客户端初始化，候选项 %d", len(self._candidates),
        )

    def _rebuild_candidates(self) -> None:
        self._candidates = [
            Candidate(
                id=make_id("cloudflare", self._api_key[:20]),
                platform="cloudflare",
                resource_id=self._api_key[:20],
                models=list(self._models),
                context_length=None,
                meta={"api_key": self._api_key},
                **CAPS,
            )
        ]

    async def candidates(self) -> List[Candidate]:
        return list(self._candidates)

    async def ensure_candidates(self, count: int) -> int:
        return len(self._candidates)

    # ---------- 模型列表 ----------

    async def fetch_remote_models(self) -> List[str]:
        """从 Cloudflare API 拉取可用模型列表。"""
        if not FETCH_MODELS_ENABLED:
            return list(MODELS)

        if not self._session:
            return list(MODELS)

        now = time.time()
        if now - self._model_cache_ts < MODEL_CACHE_TTL and self._models:
            return list(self._models)

        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with self._session.get(
                MODELS_URL,
                headers=headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    logger.warning("cloudflare 获取模型列表失败, HTTP%d", resp.status)
                    return list(MODELS)
                data = await resp.json()
                result = data.get("result", [])
                ids = [m.get("id", "") for m in result if isinstance(m, dict) and m.get("id")]
                if ids:
                    self._models = ids
                    self._model_cache_ts = now
                    self._rebuild_candidates()
                    logger.info("cloudflare 模型列表已更新: %d个", len(ids))
                return list(self._models)
        except Exception as e:
            logger.warning("cloudflare 获取模型列表异常: %s", e)
            return list(MODELS)

    def update_models(self, models: List[str]) -> None:
        self._models = list(models)
        self._rebuild_candidates()

    # ---------- HTTP 工具 ----------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_url(self, model: str) -> str:
        """无需 account_id: /ai/run/{model}"""
        return f"{BASE_URL}/{model}"

    async def _do_request(
        self, model: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """带重试的 POST 请求。"""
        url = self._build_url(model)
        headers = self._headers()

        for attempt in range(MAX_RETRIES):
            try:
                timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SEC)
                async with self._session.post(
                    url,
                    json=payload,
                    headers=headers,
                    ssl=False,
                    timeout=timeout,
                ) as resp:
                    if resp.status >= 400:
                        error_text = await resp.text()
                        raise RuntimeError(
                            f"cloudflare HTTP {resp.status}: {error_text[:200]}"
                        )
                    result = await resp.json()
                    if not result.get("success", False):
                        errors = result.get("errors", [])
                        error_msg = errors[0] if errors else "unknown error"
                        raise RuntimeError(f"cloudflare API error: {error_msg}")
                    return result.get("result", {})
            except Exception as exc:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "cloudflare 请求重试 %d/%d: %s",
                        attempt + 1, MAX_RETRIES, exc,
                    )
                    await asyncio.sleep(1.0 * (2 ** attempt))
                else:
                    raise

    # ---------- 音频转写 ----------

    async def create_transcription(
        self,
        candidate: Candidate,
        audio_data: bytes,
        model: str = DEFAULT_MODEL,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        payload: Dict[str, Any] = {"audio": audio_base64}
        if language:
            payload["language"] = language
        return await self._do_request(model, payload)

    # ---------- 聊天补全 ----------

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
        payload: Dict[str, Any] = {
            "messages": messages,
            "max_tokens": kw.get("max_tokens", 1000),
            "temperature": kw.get("temperature", 0.7),
            "top_p": kw.get("top_p", 0.95),
            "stream": stream,
        }
        result = await self._do_request(model, payload)

        # 非流式：提取文本
        text = ""
        if isinstance(result, dict):
            text = result.get("response", "")
            if not text:
                text = result.get("text", "")
        elif isinstance(result, str):
            text = result

        if text:
            yield text

    # ---------- 资源清理 ----------

    async def close(self) -> None:
        self._session = None
        self._candidates.clear()

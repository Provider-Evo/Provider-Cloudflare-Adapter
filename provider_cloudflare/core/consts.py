


from __future__ import annotations

from typing import Dict, List

# 无需 account_id，直接用 /ai/run
BASE_URL = "https://api.cloudflare.com/client/v4/ai/run"
MODELS_URL = "https://api.cloudflare.com/client/v4/ai/models"

# 远程模型列表拉取开关；该接口持续返回 HTTP 400，关闭后固定使用下方 MODELS 静态列表
FETCH_MODELS_ENABLED = False

# 默认模型列表（降级用）
DEFAULT_MODEL = "@cf/openai/whisper-large-v3-turbo"
MODELS: List[str] = [
    # 音频
    "@cf/openai/whisper-large-v3-turbo",
    # 文本
    "@cf/meta/llama-3.1-8b-instruct",
    "@cf/meta/llama-3.1-70b-instruct",
    "@cf/meta/llama-3.2-3b-instruct",
    "@cf/mistral/mistral-7b-instruct-v0.2",
    "@cf/deepseek/deepseek-math-7b-instruct",
    # 嵌入
    "@cf/baai/bge-base-en-v1.5",
]

# 能力声明
CAPS: Dict[str, bool] = {
    "chat": True,
    "completions": False,
    "vision": False,
    "tools": False,
    "native_tools": False,
    "thinking": False,
    "search": False,
    "embedding": True,
    "audio_transcription": True,
}

# 超时设置（秒）
REQUEST_TIMEOUT_SEC = 60.0

# 重试设置
MAX_RETRIES = 3

# 模型列表缓存 TTL（秒）
MODEL_CACHE_TTL = 300

__all__: List[str] = []

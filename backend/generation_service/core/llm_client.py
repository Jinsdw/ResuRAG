import logging
from typing import Iterator, List, Dict

from zai import ZhipuAiClient

logger = logging.getLogger(__name__)


def _flatten_messages(messages: List[Dict]) -> List[Dict[str, str]]:
    """将 multimodal content 格式转为纯文本，兼容非流式调用（忽略 file_url）。"""
    flat = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if part.get("type") == "text"
            )
        flat.append({"role": msg["role"], "content": content})
    return flat


def _prepare_stream_messages(messages: List[Dict]) -> List[Dict]:
    """流式调用保留 file_url；纯文本 multimodal 仍压平为字符串。"""
    prepared: List[Dict] = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list) and any(
            part.get("type") == "file_url" for part in content
        ):
            prepared.append(msg)
            continue
        if isinstance(content, list):
            prepared.append(
                {
                    "role": msg["role"],
                    "content": "".join(
                        part.get("text", "")
                        for part in content
                        if part.get("type") == "text"
                    ),
                }
            )
        else:
            prepared.append(msg)
    return prepared


class LLMClient:
    """统一的大模型客户端接口"""

    def __init__(self, api_key: str, model: str):
        self.client = ZhipuAiClient(api_key=api_key)
        self.model = model

    def generate_stream(self, messages: List[Dict[str, str]]) -> Iterator:
        """流式生成回答"""
        return self._generate_zhipu_stream(messages)

    def generate_sync(self, messages: List[Dict], *, enable_thinking: bool = False) -> str:
        """非流式生成（用于 query 改写、意图判断等短应答），返回完整文本。"""
        flat = _flatten_messages(messages)
        create_kwargs: Dict = {
            "model": self.model,
            "messages": flat,
            "stream": False,
        }
        if enable_thinking:
            create_kwargs["thinking"] = {"type": "enabled"}
        try:
            response = self.client.chat.completions.create(**create_kwargs)
            message = response.choices[0].message
            content = (message.content or "").strip()
            if content:
                return content
            reasoning = getattr(message, "reasoning_content", None) or ""
            return (reasoning or "").strip()
        except Exception as e:
            logger.error("非流式调用失败: %s", e)
            raise

    def _generate_zhipu_stream(self, messages: List[Dict[str, str]]) -> Iterator:
        """智谱 API 流式调用"""
        prepared = _prepare_stream_messages(messages)
        try:
            return self.client.chat.completions.create(
                model=self.model,
                messages=prepared,
                thinking={"type": "enabled"},
                stream=True,
            )
        except Exception as e:
            logger.error("智谱 API 流式调用失败: %s", e)
            raise

# 全局单例
_llm_client = None

def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        from config import Config
        _llm_client = LLMClient(
            api_key=Config.ZHIPU_API_KEY,
            model=Config.ZHIPU_MODEL
        )
    
    return _llm_client
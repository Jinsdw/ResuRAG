import logging
from typing import Iterator, List, Dict
from zai import ZhipuAiClient

logger = logging.getLogger(__name__)

class LLMClient:
    """统一的大模型客户端接口"""
    
    def __init__(self, api_key: str, model: str):
        """初始化OpenAI客户端"""
        self.client = ZhipuAiClient(api_key=api_key)
        self.model = model
    

    def generate_stream(self, messages: List[Dict[str, str]]) -> Iterator:
        """
        流式生成回答
        messages: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        return self._generate_zhipu_stream(messages)
    
    def _generate_zhipu_stream(self, messages: List[Dict[str, str]]) -> Iterator:
        """智谱 API 流式调用"""
        try:
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                thinking={"type": "enabled"},
                stream=True,
            )
        except Exception as e:
            logger.error(f"智谱 API 调用失败: {e}")
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
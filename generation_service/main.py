import json
import logging
from typing import Iterator, Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import Config
from core.llm_client import get_llm_client
from prompts.templates import build_messages

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="生成服务 (Generation Service)", version="1.0.0")

# ============ 数据模型 ============


class GenerationRequest(BaseModel):
    query: str
    chunks: list  # 检索到的文档切块列表
    enable_faithfulness: Optional[bool] = Config.ENABLE_FAITHFULNESS_CHECK


def _extract_stream_delta(chunk) -> tuple[str | None, str | None]:
    """从智谱流式 chunk 中提取 content / reasoning_content"""
    if not chunk.choices:
        return None, None

    delta = chunk.choices[0].delta
    content = getattr(delta, "content", None) or None
    reasoning = getattr(delta, "reasoning_content", None) or None
    return content, reasoning


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream_llm_response(messages: list) -> Iterator[str]:
    """将 LLM 流式 chunk 转为 SSE 格式"""
    llm = get_llm_client()
    try:
        for chunk in llm.generate_stream(messages=messages):
            content, reasoning = _extract_stream_delta(chunk)
            if content:
                yield _sse_event({"type": "content", "content": content})
            if reasoning:
                yield _sse_event({"type": "reasoning", "content": reasoning})
        yield _sse_event({"type": "done"})
    except Exception as e:
        logger.error(f"流式生成失败: {e}")
        yield _sse_event({"type": "error", "message": str(e)})


# ============ 核心接口 ============


@app.post("/api/v1/generate")
async def generate(request: GenerationRequest):
    """
    流式生成回答（SSE）
    """
    logger.info(f"收到生成请求: {request.query[:50]}...")

    messages = build_messages(
        query=request.query,
        chunks=request.chunks,
    )

    return StreamingResponse(
        _stream_llm_response(messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "service": "generation_service"}


if __name__ == "__main__":
    import uvicorn

    print(f"🧠 生成服务启动中...")
    print(f"🔗 访问地址: http://0.0.0.0:{Config.PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT, reload=True)

import json
import logging
from contextlib import asynccontextmanager
from typing import Iterator, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import Config
from core.llm_client import get_llm_client
from core.session_store import get_session_store
from prompts.templates import build_messages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_session_store()
    logger.info("会话数据库就绪: %s", Config.SESSION_DB_PATH)
    yield


app = FastAPI(title="生成服务 (Generation Service)", version="1.0.0", lifespan=lifespan)

# ============ 数据模型 ============


class GenerationRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="前端会话 ID")
    query: str
    chunks: list
    enable_faithfulness: Optional[bool] = Config.ENABLE_FAITHFULNESS_CHECK


class SessionResponse(BaseModel):
    session_id: str
    subject: str
    created_at: int
    updated_at: int


class SessionListResponse(BaseModel):
    total: int
    sessions: List[SessionResponse]


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


# ============ 会话接口 ============


@app.get("/api/v1/sessions", response_model=SessionListResponse)
async def list_sessions():
    """获取会话列表（按更新时间倒序）"""
    store = get_session_store()
    rows = store.list_all()
    sessions = [SessionResponse(**row) for row in rows]
    return SessionListResponse(total=len(sessions), sessions=sessions)


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话记录"""
    store = get_session_store()
    deleted = store.delete(session_id.strip())
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True, "session_id": session_id}


# ============ 生成接口 ============


@app.post("/api/v1/generate")
async def generate(request: GenerationRequest):
    """流式生成回答（SSE），并在首次请求时创建会话记录"""
    logger.info(
        "收到生成请求: session=%s query=%s...",
        request.session_id,
        request.query[:50],
    )

    store = get_session_store()
    try:
        store.ensure_session(request.session_id.strip(), request.query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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

    print("🧠 生成服务启动中...")
    print(f"🔗 访问地址: http://0.0.0.0:{Config.PORT}")
    print(f"💾 会话数据库: {Config.SESSION_DB_PATH}")
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT, reload=True)

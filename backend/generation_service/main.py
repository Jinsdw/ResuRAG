import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Iterator, List, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import Config
from core.llm_client import get_llm_client
from core.session_store import get_session_store
from prompts.templates import build_messages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FINGERPRINT_HEADER = "X-Browser-Fingerprint"


def _read_fingerprint(x_browser_fingerprint: Optional[str] = Header(None, alias=FINGERPRINT_HEADER)) -> str:
    fingerprint = (x_browser_fingerprint or "").strip()
    if not fingerprint:
        raise HTTPException(status_code=400, detail=f"缺少请求头 {FINGERPRINT_HEADER}")
    return fingerprint

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_session_store()
    logger.info("会话数据库就绪: %s", Config.SESSION_DB_PATH)
    yield


app = FastAPI(title="生成服务 (Generation Service)", version="1.0.0", lifespan=lifespan)

# ============ 数据模型 ============


class GenerationRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="前端会话 ID")
    user_message_id: str = Field(..., min_length=1, description="用户消息 ID")
    assistant_message_id: str = Field(..., min_length=1, description="助手消息 ID")
    query: str
    chunks: list
    citations: Optional[List[Dict[str, Any]]] = None
    enable_faithfulness: Optional[bool] = Config.ENABLE_FAITHFULNESS_CHECK


class SessionResponse(BaseModel):
    session_id: str
    subject: str
    created_at: int
    updated_at: int


class SessionListResponse(BaseModel):
    total: int
    sessions: List[SessionResponse]


class ChatMessageResponse(BaseModel):
    message_id: str
    session_id: str
    role: str
    content: str
    reasoning: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None
    created_at: int


class ChatMessageListResponse(BaseModel):
    session_id: str
    total: int
    messages: List[ChatMessageResponse]


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


def _stream_llm_response(
    messages: list,
    assistant_message_id: str,
) -> Iterator[str]:
    """将 LLM 流式 chunk 转为 SSE 格式，并在结束时持久化助手消息"""
    store = get_session_store()
    llm = get_llm_client()
    content_parts: List[str] = []
    reasoning_parts: List[str] = []

    try:
        for chunk in llm.generate_stream(messages=messages):
            content, reasoning = _extract_stream_delta(chunk)
            if content:
                content_parts.append(content)
                yield _sse_event({"type": "content", "content": content})
            if reasoning:
                reasoning_parts.append(reasoning)
                yield _sse_event({"type": "reasoning", "content": reasoning})
        yield _sse_event({"type": "done"})
    except Exception as e:
        logger.error(f"流式生成失败: {e}")
        yield _sse_event({"type": "error", "message": str(e)})
    finally:
        final_content = "".join(content_parts)
        final_reasoning = "".join(reasoning_parts) or None
        if final_content or final_reasoning:
            store.update_message(
                assistant_message_id,
                content=final_content,
                reasoning=final_reasoning,
            )
        elif not content_parts and not reasoning_parts:
            store.update_message(assistant_message_id, content="")


# ============ 会话接口 ============


@app.get("/api/v1/sessions", response_model=SessionListResponse)
async def list_sessions(
    x_browser_fingerprint: Optional[str] = Header(None, alias=FINGERPRINT_HEADER),
):
    """获取当前浏览器指纹下的会话列表"""
    fingerprint = _read_fingerprint(x_browser_fingerprint)
    store = get_session_store()
    rows = store.list_all(fingerprint)
    sessions = [SessionResponse(**row) for row in rows]
    return SessionListResponse(total=len(sessions), sessions=sessions)

@app.get("/api/v1/sessions/{session_id}/messages", response_model=ChatMessageListResponse)
async def list_session_messages(session_id: str):
    """获取指定会话的聊天记录"""
    store = get_session_store()
    session_id = session_id.strip()
    if not store.get(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")

    rows = store.list_messages(session_id)
    messages = [ChatMessageResponse(**row) for row in rows]
    return ChatMessageListResponse(
        session_id=session_id,
        total=len(messages),
        messages=messages,
    )


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话及其聊天记录"""
    store = get_session_store()
    deleted = store.delete(session_id.strip())
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True, "session_id": session_id}


# ============ 生成接口 ============


@app.post("/api/v1/generate")
async def generate(
    request: GenerationRequest,
    x_browser_fingerprint: Optional[str] = Header(None, alias=FINGERPRINT_HEADER),
):
    """流式生成回答（SSE），并持久化聊天记录"""
    fingerprint = _read_fingerprint(x_browser_fingerprint)
    logger.info(
        "收到生成请求: session=%s query=%s...",
        request.session_id,
        request.query[:50],
    )

    store = get_session_store()
    session_id = request.session_id.strip()
    user_message_id = request.user_message_id.strip()
    assistant_message_id = request.assistant_message_id.strip()

    try:
        store.ensure_session(session_id, request.query, fingerprint)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    llm_messages = build_messages(
        query=request.query,
        chunks=request.chunks,
        session_id=session_id,
    )
    try:
        store.add_message(
            session_id=session_id,
            message_id=user_message_id,
            role="user",
            content=request.query.strip(),
        )
        store.add_message(
            session_id=session_id,
            message_id=assistant_message_id,
            role="assistant",
            content="",
            citations=request.citations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(
        _stream_llm_response(llm_messages, assistant_message_id),
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

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import Config
from core.llm_client import get_llm_client
from core.session_store import get_session_store
from prompts.templates import build_messages, build_direct_chat_messages
from prompts.rewrite import build_rewrite_prompt
from prompts.judge import build_judge_prompt
from prompts.suggestions import (
    build_suggestions_prompt,
    get_default_suggestion_list,
    parse_suggestions,
)
from core.qa_pool import (
    filter_unasked,
    is_similar_question,
    load_qa_questions,
)

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
    load_qa_questions(force_reload=True)
    logger.info("会话数据库就绪: %s", Config.SESSION_DB_PATH)
    yield


app = FastAPI(title="生成服务 (Generation Service)", version="1.0.0", lifespan=lifespan)

# ============ 数据模型 ============


class GenerationRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="前端会话 ID")
    user_message_id: str = Field(..., min_length=1, description="用户消息 ID")
    assistant_message_id: str = Field(..., min_length=1, description="助手消息 ID")
    query: str
    chunks: Optional[list] = None  # 可选：不传则由生成服务内部检索
    citations: Optional[List[Dict[str, Any]]] = None
    top_k: Optional[int] = Field(default=10, ge=1, le=20)
    similarity_threshold: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)
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


class SuggestionsRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class SuggestionsResponse(BaseModel):
    suggestions: List[str]


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


def _sse_status(step: str, message: str) -> str:
    return _sse_event({"type": "status", "step": step, "message": message})


SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


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


def _load_history_for_rewrite(session_id: str, max_turns: int = 6) -> str:
    """加载最近 N 轮对话，用于 query 改写与检索意图判断。"""
    store = get_session_store()
    rows = store.list_messages(session_id)
    lines: List[str] = []
    for row in rows:
        role = row.get("role", "")
        content = (row.get("content") or "").strip()
        if not content:
            continue
        label = "面试官" if role == "user" else "助手"
        lines.append(f"{label}：{content}")
    if not lines:
        return "（无历史对话）"
    if len(lines) > max_turns * 2:
        lines = lines[-(max_turns * 2):]
    return "\n".join(lines)


def _extract_asked_questions(session_id: str) -> List[str]:
    """提取本会话中面试官已提出的问题（去重）。"""
    store = get_session_store()
    rows = store.list_messages(session_id)
    asked: List[str] = []
    for row in rows:
        if row.get("role") != "user":
            continue
        content = (row.get("content") or "").strip()
        if not content:
            continue
        if any(is_similar_question(content, prev) for prev in asked):
            continue
        asked.append(content)
    return asked


def _load_history_for_suggestions(session_id: str, max_turns: int = 8) -> str:
    """加载对话历史，供猜你想问生成使用。"""
    store = get_session_store()
    rows = store.list_messages(session_id)
    lines: List[str] = []
    candidate = Config.CANDIDATE_NAME
    for row in rows:
        role = row.get("role", "")
        content = (row.get("content") or "").strip()
        if not content:
            continue
        label = "面试官" if role == "user" else candidate
        lines.append(f"{label}：{content}")
    if not lines:
        return "（无历史对话）"
    if len(lines) > max_turns * 2:
        lines = lines[-(max_turns * 2) :]
    return "\n".join(lines)


def _normalize_rewrite_text(text: str, fallback: str) -> str:
    """清理改写模型输出，失败时回退原始问题。"""
    cleaned = (text or "").strip()
    if not cleaned:
        return fallback
    for prefix in (
        "改写后的查询：",
        "改写后：",
        "检索查询：",
        "独立查询：",
    ):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    cleaned = cleaned.strip("\"'")
    return cleaned if len(cleaned) >= 2 else fallback


def _parse_retrieval_decision(text: str) -> bool:
    """解析 YES/NO；无法解析时默认需要检索（简历问答场景更安全）。"""
    normalized = (text or "").strip().upper()
    if not normalized:
        return True
    tokens = normalized.replace("\n", " ").split()
    for token in reversed(tokens):
        word = token.strip(".,:;!?\"'()[]，。；：！？")
        if word == "NO":
            return False
        if word == "YES":
            return True
    if normalized.startswith("NO") or normalized.endswith(" NO"):
        return False
    if "YES" in normalized and "NO" not in normalized:
        return True
    return True


async def _rewrite_query(query: str, session_id: str) -> str:
    """利用历史对话改写 query，失败时返回原始 query。"""
    history = _load_history_for_rewrite(session_id)
    llm = get_llm_client()
    messages = build_rewrite_prompt(query, history)
    try:
        rewritten = llm.generate_sync(messages, enable_thinking=False)
        result = _normalize_rewrite_text(rewritten, query.strip())
        logger.info("Query 改写: %s → %s", query[:50], result[:80])
        return result
    except Exception as exc:
        logger.warning("Query 改写失败，使用原始 query: %s", exc)
        return query.strip()


async def _should_retrieve(query: str, session_id: str) -> bool:
    """判断是否需要检索知识库。失败时默认检索。"""
    history = _load_history_for_rewrite(session_id)
    llm = get_llm_client()
    messages = build_judge_prompt(query, history)
    try:
        result = llm.generate_sync(messages, enable_thinking=False)
        need = _parse_retrieval_decision(result)
        logger.info("检索意图判断: query=%s → %s (raw=%s)", query[:50], need, result[:30])
        return need
    except Exception as exc:
        logger.warning("意图判断失败，默认检索: %s", exc)
        return True


async def _retrieve_chunks(
    query: str,
    top_k: int = 10,
    similarity_threshold: float = 0.0,
) -> tuple[list, Optional[str]]:
    """调用检索服务获取 chunks。返回 (results, error_message)。"""
    url = f"{Config.RETRIEVAL_SERVICE_URL.rstrip('/')}/api/v1/search"
    async with httpx.AsyncClient(timeout=Config.RETRIEVAL_TIMEOUT) as client:
        try:
            response = await client.post(
                url,
                json={
                    "query": query,
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold,
                },
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            logger.info("检索完成: query=%s, 命中 %d 条", query[:50], len(results))
            return results, None
        except Exception as exc:
            logger.error("检索服务调用失败: %s", exc)
            return [], str(exc)


@app.get("/api/v1/suggestions/default", response_model=SuggestionsResponse)
async def get_default_suggestions_endpoint():
    """返回新建会话时的默认「猜你想问」，问题来自全景文档 QA。"""
    return SuggestionsResponse(suggestions=get_default_suggestion_list())


@app.post("/api/v1/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    request: SuggestionsRequest,
    x_browser_fingerprint: Optional[str] = Header(None, alias=FINGERPRINT_HEADER),
):
    """结合会话历史 + 简历/全景文档生成「猜你想问」，排除本会话已问问题。"""
    _read_fingerprint(x_browser_fingerprint)
    session_id = request.session_id.strip()
    store = get_session_store()
    asked = _extract_asked_questions(session_id)
    defaults = get_default_suggestion_list(asked=asked)

    if not store.get(session_id):
        return SuggestionsResponse(suggestions=defaults)

    history = _load_history_for_suggestions(session_id)
    if history == "（无历史对话）":
        return SuggestionsResponse(suggestions=defaults)

    available_pool = filter_unasked(load_qa_questions(), asked)
    if len(available_pool) < 2:
        logger.info(
            "猜你想问: session=%s 可选问题不足，返回默认补齐",
            session_id,
        )
        return SuggestionsResponse(suggestions=defaults)

    llm = get_llm_client()
    messages = build_suggestions_prompt(
        history,
        asked_questions=asked,
        available_pool=available_pool,
    )
    try:
        raw = llm.generate_sync(messages, enable_thinking=False)
        suggestions = parse_suggestions(
            raw,
            asked_questions=asked,
            available_pool=available_pool,
            fallback=defaults,
        )
        logger.info(
            "猜你想问生成: session=%s asked=%d picked=%d",
            session_id,
            len(asked),
            len(suggestions),
        )
        return SuggestionsResponse(suggestions=suggestions)
    except Exception as exc:
        logger.warning("猜你想问生成失败，使用默认推荐: %s", exc)
        return SuggestionsResponse(suggestions=defaults)


async def _generate_pipeline_stream(
    request: GenerationRequest,
    session_id: str,
    user_message_id: str,
    assistant_message_id: str,
) -> AsyncIterator[str]:
    """SSE 全流程：推送阶段状态 → 检索/改写 → 流式生成。"""
    from prompts.templates import to_citations

    store = get_session_store()
    client_provided_chunks = request.chunks is not None and len(request.chunks) > 0
    need_retrieval = False
    rewritten_query = request.query.strip()
    chunks: list = list(request.chunks or [])
    resolved_citations: List[Dict[str, Any]] = list(request.citations or [])
    retrieval_error: Optional[str] = None

    if client_provided_chunks:
        need_retrieval = True
        if not resolved_citations:
            resolved_citations = to_citations(chunks)
        logger.info("使用前端传入的 chunks（%d 条），跳过改写与意图判断", len(chunks))
        yield _sse_status("preparing", "已载入检索片段，正在准备生成回答…")
        yield _sse_event({"type": "citations", "citations": resolved_citations})
    else:
        yield _sse_status(
            "rewriting",
            "正在结合对话历史，优化检索查询表述…",
        )
        rewritten_query = await _rewrite_query(request.query, session_id)
        logger.info("改写后 query: %s", rewritten_query[:80])

        yield _sse_status(
            "judging",
            "正在分析问题是否需要检索个人资料…",
        )
        need_retrieval = await _should_retrieve(rewritten_query, session_id)
        logger.info("是否需要检索: %s", need_retrieval)

        if need_retrieval:
            yield _sse_status(
                "retrieving",
                "正在检索个人资料库中的相关片段…",
            )
            chunks, retrieval_error = await _retrieve_chunks(
                rewritten_query,
                top_k=request.top_k or 10,
                similarity_threshold=request.similarity_threshold or 0.0,
            )
            resolved_citations = to_citations(chunks) if chunks else []
            yield _sse_event({"type": "citations", "citations": resolved_citations})
            if retrieval_error:
                logger.warning(
                    "检索失败 session=%s error=%s",
                    session_id,
                    retrieval_error,
                )
                yield _sse_event(
                    {
                        "type": "error",
                        "message": (
                            f"检索服务不可用，请确认 retrieval_service 已启动"
                            f"（{Config.RETRIEVAL_SERVICE_URL}）：{retrieval_error}"
                        ),
                    }
                )
                return
            if not chunks:
                logger.warning("检索结果为空，session=%s", session_id)
        else:
            resolved_citations = []
            chunks = []
            yield _sse_status(
                "direct",
                "该问题无需检索资料，正在准备直接作答…",
            )
            yield _sse_event({"type": "citations", "citations": []})

    use_rag_prompt = need_retrieval or client_provided_chunks
    if use_rag_prompt:
        llm_messages = build_messages(
            query=request.query,
            chunks=chunks,
            session_id=session_id,
        )
        yield _sse_status(
            "generating",
            "正在基于检索片段组织并生成回答…",
        )
    else:
        llm_messages = build_direct_chat_messages(
            query=request.query,
            session_id=session_id,
        )
        yield _sse_status("generating", "正在生成回答…")

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
            citations=resolved_citations,
        )
    except ValueError as exc:
        yield _sse_event({"type": "error", "message": str(exc)})
        return

    for event in _stream_llm_response(llm_messages, assistant_message_id):
        yield event


@app.post("/api/v1/generate")
async def generate(
    request: GenerationRequest,
    x_browser_fingerprint: Optional[str] = Header(None, alias=FINGERPRINT_HEADER),
):
    """流式生成回答（SSE），并持久化聊天记录。

    流程：改写 query → 判断意图 → 检索/直接 → 流式生成"""
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

    return StreamingResponse(
        _generate_pipeline_stream(
            request,
            session_id,
            user_message_id,
            assistant_message_id,
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
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

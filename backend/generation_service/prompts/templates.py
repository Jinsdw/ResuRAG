from typing import List, Optional

from core.session_store import get_session_store

SYSTEM_PROMPT = """你是一个专业的RAG问答助手。请根据提供的文档片段，准确、简洁地回答用户的问题。

## 回答要求
1. **基于事实**：只使用提供的文档片段中的信息，不要添加自己的知识。
2. **引用来源**：在回答中标注引用来源，格式为 [1]、[2]... 对应文档片段的编号。
3. **简洁明了**：用清晰的语言直接回答问题，不要过度展开。
4. **不确定就说不知道**：如果文档中没有相关信息，明确告知"根据提供的文档，无法回答这个问题"。

## 文档片段
{context}

## 引用列表
{citation_list}
"""

USER_TEMPLATE = """问题：{query}
请基于以上文档片段回答："""

LONG_TERM_MEMORY_PREFIX = """## 长期记忆（本会话历史对话）
以下为同一会话中较早轮次的对话，供理解上下文与指代关系：

{memory}

---

"""

def _load_session_memory(
    session_id: Optional[str],
    max_messages: int = 30,
) -> str:
    if not session_id or not session_id.strip():
        return ""

    store = get_session_store()
    sid = session_id.strip()
    if not store.get(sid):
        return ""

    rows = store.list_messages(sid)
    lines: List[str] = []
    for row in rows:
        role = row.get("role", "")
        content = (row.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"{role}：{content}")

    if not lines:
        return ""

    if len(lines) > max_messages:
        lines = lines[-max_messages:]

    return LONG_TERM_MEMORY_PREFIX.format(memory="\n".join(lines))


def build_messages(
    query: str,
    chunks: list,
    session_id: Optional[str] = None,
    max_chunks: int = 5,
    max_memory_messages: int = 30,
) -> list:
    """
    构建 LLM 消息；若提供 session_id，则从数据库加载历史 role/content 作为长期记忆前缀。
    chunks: 检索到的切块列表，每个包含 content, chunk_id 等
    """
    selected_chunks = chunks[:max_chunks]

    context_parts = []
    citation_list = []

    for idx, chunk in enumerate(selected_chunks, start=1):
        content = chunk.get("content", "")
        chunk_id = chunk.get("chunk_id", f"chunk_{idx}")

        if len(content) > 500:
            content = content[:500] + "..."

        context_parts.append(f"[{idx}] {content}")
        citation_list.append(f"[{idx}] {chunk_id}")

    context = "\n\n".join(context_parts)
    citation_list_str = "\n".join(citation_list)

    memory_prefix = _load_session_memory(session_id, max_messages=max_memory_messages)
    system_content = memory_prefix + SYSTEM_PROMPT.format(
        context=context,
        citation_list=citation_list_str,
    )

    user_content = USER_TEMPLATE.format(query=query)

    return [
        {"role": "system", "content": [{"type": "text", "text": system_content}]},
        {"role": "user", "content": [{"type": "text", "text": user_content}]},
    ]

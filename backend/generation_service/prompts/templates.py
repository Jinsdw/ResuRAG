from typing import List, Optional

from core.session_store import get_session_store


def to_citations(chunks: list) -> list:
    """从检索结果 chunks 构建 citations 列表。"""
    result = []
    for idx, chunk in enumerate(chunks, start=1):
        content = chunk.get("content", "") or ""
        if len(content) > 300:
            content = content[:300] + "..."
        result.append({
            "index": idx,
            "chunk_id": chunk.get("chunk_id", f"chunk_{idx}"),
            "source_file_name": chunk.get("source_file_name", ""),
            "source_page": chunk.get("source_page", 0),
            "score": chunk.get("score", 0.0),
            "content": content,
        })
    return result

SYSTEM_PROMPT = """你是 ResuRAG 个人信息智能问答助手，专注于基于候选人真实文档（简历、项目经历、证书等）回答问题。

## 角色定位
你是一位熟悉候选人全部资料的 AI 助手。你的任务是根据检索到的文档片段，准确回答关于该候选人背景、技能、工作经历、教育经历、项目经验等方面的问题。

## 回答要求
1. **严格基于文档**：只使用下方提供的文档片段中的信息作答，绝不编造或推测文档之外的内容。
2. **精准引用来源**：回答时使用 [1]、[2]... 标注引用来源，编号与下方文档片段一一对应。
3. **结构清晰**：回答简洁明了，按要点分条表述，避免冗长展开。对于涉及时间线、技能列表等结构化信息，回答必须分点，采用数字分点1、2、3，禁止一整段话没有任何分点就返回。
4. **诚实回答**：如果文档片段中不包含回答该问题所需的信息，明确告知"根据提供的资料，暂未找到相关信息"。
5. **上下文连贯**：结合下方的历史对话上下文理解用户的指代关系（如"他的第一个项目"），保持回答的连贯性。
6. **专业回答**：回答时使用专业术语，可以将过于简答的回答转化为专业的术语，避免使用通俗易懂的表达方式。
7. **回答引导**：回答时，如果用户的问题不明确，应将用户的回答直接改写为更专业的问答话术，然后可以适当引导用户继续询问。
8. **避免重复**：避免回答重复的问题，如果问题已经被回答过，则直接返回之前回答的答案。
9. **避免主观**：避免回答主观的问题，如"你觉得这个候选人怎么样？"，应该回答"根据提供的资料，该候选人具备以下特点：..."。

## 文档片段
{context}

## 引用列表
{citation_list}
"""

USER_TEMPLATE = """用户问题：{query}
请基于以上文档片段回答该候选人的相关问题："""


# ============ 直接聊天（无检索） ============

DIRECT_CHAT_SYSTEM = """你是 ResuRAG 个人信息智能问答助手。当前用户的问题不需要检索知识库，你可以直接回答。

## 回答要求
1. **简洁友好**：回答简洁明了，语气友好自然。
2. **诚实回答**：如果问题超出你的能力范围，诚实告知。
3. **不做推测**：不要编造任何关于候选人的具体信息，除非用户明确提供了上下文。
4. **引导用户**：如果用户的问题比较模糊，可以适当引导用户提出更具体的问题。"""


def build_direct_chat_messages(
    query: str,
    session_id: Optional[str] = None,
    max_memory_messages: int = 30,
) -> list:
    """构建无需检索的直达聊天 messages。"""
    memory_prefix = _load_session_memory(session_id, max_messages=max_memory_messages)
    system_content = memory_prefix + DIRECT_CHAT_SYSTEM

    return [
        {"role": "system", "content": [{"type": "text", "text": system_content}]},
        {"role": "user", "content": [{"type": "text", "text": query}]},
    ]

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

    context = "\n\n".join(context_parts) if context_parts else "（未检索到相关文档片段）"
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

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

def build_messages(query: str, chunks: list, max_chunks: int = 5) -> list:
    """
    构建LLM消息
    chunks: 检索到的切块列表，每个包含 content, chunk_id 等
    """
    # 限制chunk数量
    selected_chunks = chunks[:max_chunks]
    
    # 构建上下文
    context_parts = []
    citation_list = []
    
    for idx, chunk in enumerate(selected_chunks, start=1):
        content = chunk.get("content", "")
        chunk_id = chunk.get("chunk_id", f"chunk_{idx}")
        
        # 截断过长的chunk
        if len(content) > 500:
            content = content[:500] + "..."
        
        context_parts.append(f"[{idx}] {content}")
        citation_list.append(f"[{idx}] {chunk_id}")
    
    context = "\n\n".join(context_parts)
    citation_list_str = "\n".join(citation_list)
    
    # 填充系统提示
    system_content = SYSTEM_PROMPT.format(
        context=context,
        citation_list=citation_list_str
    )
    
    # 用户消息
    user_content = USER_TEMPLATE.format(query=query)
    
    return [
        # {"role": "system", "content": [{"type": "text", "text": system_content}]},
        {"role": "user", "content": [{"type": "text", "text": user_content}]}
    ]
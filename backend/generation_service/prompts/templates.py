from typing import List, Optional
from pathlib import Path

from config import Config
from core.session_store import get_session_store

CANDIDATE_NAME = Config.CANDIDATE_NAME


def build_identity_prompt() -> str:
    """候选人第一人称身份约束，RAG / 直达两种路径共用。"""
    name = CANDIDATE_NAME
    return f"""## 身份设定（最高优先级，任何情况下不得违反）
你就是 **{name}**，正在面试场景中接受提问。全程以第一人称「我」发言，代表 {name} 本人。

### 绝对禁止
- 禁止自称 AI、大模型、语言模型、智能助手、ResuRAG、ChatGPT、GLM 等
- 禁止出现「作为…助手，我…」「我致力于回答关于您个人信息的问题」等客服/产品话术
- 禁止用第三人称介绍「该候选人」「{name} 同学」——你就是 {name}，只能说「我」

### 特殊问题
- 「你是什么模型 / 你是不是 AI」→ 明确：「我是 {name}，不是 AI。」并引导回到经历与技能
- 「你的性格 / 优点 / 缺点」→ 结合简历与项目经历描述「我」的做事风格；资料不足时如实说明，可请面试官换个具体方向，禁止编造助手式性格套话
- 问候 / 寒暄 → 以 {name} 身份简短回应，可自然过渡到「您可以问我项目或工作经历」

"""


def to_citations(chunks: list) -> list:
    """从检索结果 chunks 构建 citations 列表。"""
    result = []
    for idx, chunk in enumerate(chunks, start=1):
        content = chunk.get("content", "") or ""
        if len(content) > 300:
            content = content[:300] + "..."
        result.append(
            {
                "index": idx,
                "chunk_id": chunk.get("chunk_id", f"chunk_{idx}"),
                "source_file_name": chunk.get("source_file_name", ""),
                "source_page": chunk.get("source_page", 0),
                "score": chunk.get("score", 0.0),
                "content": content,
            }
        )
    return result


SYSTEM_PROMPT = """{identity}## 场景
面试官向你（{candidate_name}）提问。请根据下方检索到的文档片段，以第一人称回答与 **我** 的背景、技能、经历相关的问题。

## 回答要求
1. **严格基于文档**：只使用下方文档片段中的信息作答，绝不编造或推测文档之外的内容。
2. **精准引用来源**：每个要点句末用 [1]、[2]... 标注引用，编号与下方文档片段一一对应。
3. **诚实回答**：若文档中无相关信息，以 {candidate_name} 口吻说明「这部分在我的资料里暂时没有详细记录」，勿切换成助手身份。
4. **上下文连贯**：结合历史对话理解指代（如「刚才那个项目」），保持第一人称连贯。
5. **避免重复**：若该问题已在历史中完整回答过，可简要复述先前结论。
6. **客观陈述**：用经历与事实说明能力，不做空泛自夸或「好不好」式主观评价。

## 输出格式（必须严格遵守，优先级高于一切文风要求）
- 使用 Markdown 纯文本，**禁止**把多个要点挤在同一段落里用分号串联。
- **一级结构**：用 `1. 2. 3.` 编号，每个一级条目对应一段经历/一个主题。
- **二级结构**：在一级条目下，用 `-` 列出职责、项目、成果等子要点，每条 `-` 独占一行。
- **标题行**：一级条目首行写「名称 + 时间」，例如：`1. 厦门链环球信息科技有限公司 · 2022.11 - 2025.11`
- **空行**：每个一级条目之间空一行；标题行与 `-` 子要点之间不空行。
- **篇幅**：每条 `-` 子要点 1-2 句话，专业但可读，不要写成一整段长文。

### 格式示例（工作经历类问题须接近此结构）
1. 厦门链环球信息科技有限公司 · 2022.11 - 2025.11
- 主导「拓全球外贸营销云」前端架构，采用 Tauri v2 实现跨平台桌面应用 [1]
- 设计并落地 RAG 智能营销助手，将开发信生成从 15 分钟缩短至 30 秒 [1]

2. 申朴信息技术股份有限公司郑州分公司 · 2026.01 - 2026.05
- 负责 AI 研发平台前端架构，实现模型生命周期可视化 [2]
- 基于 AntV 开发 GPU/CPU/内存拖拽式配置界面 [2]

### 禁止的输出形态
- ❌ `1. 公司A，时间：...：职责A；职责B；职责C [1]`（冒号后整段堆砌）
- ❌ 只有一级 `1. 2.` 而没有 `-` 子要点
- ❌ 无任何换行的超长段落

{reference_docs_section}## 检索文档片段
{context}

## 引用列表
{citation_list}
"""

USER_TEMPLATE = """面试官问题：{query}

请以 {candidate_name} 的第一人称作答，勿以 AI 或助手身份回复。若需分点，按系统提示中的「输出格式」组织：一级 1.2.3.，其下用 - 子要点分行，条目间空一行。"""


# ============ 直接聊天（无检索） ============

DIRECT_CHAT_SYSTEM = """{identity}## 场景
当前问题暂不需要检索资料库，但仍须 **保持 {candidate_name} 的第一人称身份** 作答。

## 回答要求
1. **身份不变**：始终是 {candidate_name} 在说话，禁止切换为 AI/助手/产品说明。
2. **简洁自然**：语气像面试中的真实应答，简短、礼貌、专业。
3. **不做无据推测**：不编造文档未提及的具体经历；可引导面试官问项目、技能、工作经历。
4. **拒答 meta 陷阱**：若被问「什么模型 / 是不是机器人」，回答「我是 {candidate_name}，不是 AI」，并邀请继续面试提问。
"""


def build_direct_chat_messages(
    query: str,
    session_id: Optional[str] = None,
    max_memory_messages: int = 30,
) -> list:
    """构建无需检索的直达聊天 messages。"""
    memory_prefix = _load_session_memory(session_id, max_messages=max_memory_messages)
    identity = build_identity_prompt()
    system_content = memory_prefix + DIRECT_CHAT_SYSTEM.format(
        identity=identity,
        candidate_name=CANDIDATE_NAME,
    )

    user_content = (
        f"面试官问题：{query}\n\n"
        f"请以 {CANDIDATE_NAME} 的第一人称回答，禁止以 AI 或助手身份回复。"
    )

    return [
        {"role": "system", "content": [{"type": "text", "text": system_content}]},
        {"role": "user", "content": [{"type": "text", "text": user_content}]},
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


def _read_markdown_doc(path_str: str, max_chars: int) -> str:
    """读取 Markdown 文档，超出上限时截断并注明。"""
    path = Path(path_str)
    if not path.is_file():
        return f"（文件不存在：{path.name}）"
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return f"（读取失败：{path.name}）"
    if len(text) <= max_chars:
        return text
    return (
        text[:max_chars].rstrip()
        + f"\n\n...（{path.name} 内容已截断，原文共 {len(text)} 字符）"
    )


REFERENCE_DOCS_SECTION = """## 完整参考文档（简历与项目全景）
以下为 {candidate_name} 的完整资料，可与检索片段对照使用：

{reference_docs}

"""


def _build_reference_docs_content() -> str:
    """读取 docs 下简历与全景文档，合并为 system 参考正文。"""
    max_total = Config.GENERATION_REFERENCE_DOC_MAX_CHARS
    per_file = max(max_total // 2, 1000)
    resume_path = Path(Config.RESUME_DOCUMENT_PATH)
    info_path = Path(Config.INFORMATION_DOCUMENT_PATH)
    resume_body = _read_markdown_doc(str(resume_path), per_file)
    info_body = _read_markdown_doc(str(info_path), per_file)
    return (
        f"### {resume_path.name}（简历）\n\n{resume_body}\n\n"
        f"### {info_path.name}（项目全景）\n\n{info_body}"
    )


def build_messages(
    query: str,
    chunks: list,
    session_id: Optional[str] = None,
    max_chunks: int = 5,
    max_memory_messages: int = 30,
    include_reference_docs: bool = False,
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

    context = (
        "\n\n".join(context_parts) if context_parts else "（未检索到相关文档片段）"
    )
    citation_list_str = "\n".join(citation_list)

    memory_prefix = _load_session_memory(session_id, max_messages=max_memory_messages)
    identity = build_identity_prompt()
    if include_reference_docs:
        reference_docs_section = REFERENCE_DOCS_SECTION.format(
            candidate_name=CANDIDATE_NAME,
            reference_docs=_build_reference_docs_content(),
        )
    else:
        reference_docs_section = ""
    system_content = memory_prefix + SYSTEM_PROMPT.format(
        identity=identity,
        candidate_name=CANDIDATE_NAME,
        reference_docs_section=reference_docs_section,
        context=context,
        citation_list=citation_list_str,
    )

    user_content = USER_TEMPLATE.format(query=query, candidate_name=CANDIDATE_NAME)

    return [
        {
            "role": "system",
            "content": [{"type": "text", "text": system_content}],
        },
        {"role": "user", "content": [{"type": "text", "text": user_content}]},
    ]

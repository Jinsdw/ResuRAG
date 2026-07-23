"""从简历、全景文档加载「猜你想问」候选问题池与参考上下文。"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable, List

from config import Config

logger = logging.getLogger(__name__)

QA_SECTION_TITLE = "## 5. 推荐 QA 问答样本"
QA_QUESTION_PATTERN = re.compile(r"^### Q\d+[：:]\s*(.+?)\s*$", re.MULTILINE)

FALLBACK_SUGGESTIONS: List[str] = [
    "介绍一下你自己？",
    "你的核心竞争力是什么？",
    "ResuRAG 是什么项目？",
    "Clue-Agent 是什么项目？",
]

DEFAULT_SUGGESTION_INDICES = (0, 3, 8, 11)

_cache_questions: List[str] | None = None
_cache_mtime: float | None = None
_cache_doc_context: str | None = None
_cache_doc_mtime_key: tuple[float, float] | None = None


def _resolve_information_path() -> Path:
    return Path(Config.INFORMATION_DOCUMENT_PATH)


def _resolve_resume_path() -> Path:
    return Path(Config.RESUME_DOCUMENT_PATH)


def _read_text(path: Path) -> str:
    if not path.is_file():
        logger.warning("文档不存在: %s", path)
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("读取文档失败 %s: %s", path, exc)
        return ""


def _truncate(text: str, max_chars: int) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def normalize_question(text: str) -> str:
    """用于去重比较的归一化问句。"""
    value = (text or "").strip().lower()
    value = re.sub(r'[\s？?！!，,。.、；;：:"\'（）()\[\]【】]', "", value)
    return value


def is_similar_question(a: str, b: str) -> bool:
    """判断两个问题是否实质重复。"""
    na, nb = normalize_question(a), normalize_question(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if len(na) >= 6 and len(nb) >= 6 and (na in nb or nb in na):
        return True
    return False


def filter_unasked(pool: Iterable[str], asked: Iterable[str]) -> List[str]:
    """从候选池中剔除与会话已问问题重复或高度相似的项。"""
    asked_list = [item.strip() for item in asked if item and item.strip()]
    result: List[str] = []
    for question in pool:
        text = question.strip()
        if not text:
            continue
        if any(is_similar_question(text, prev) for prev in asked_list):
            continue
        if any(is_similar_question(text, kept) for kept in result):
            continue
        result.append(text)
    return result


def _extract_qa_section(text: str) -> str:
    start = text.find(QA_SECTION_TITLE)
    if start < 0:
        return text
    return text[start:]


def _parse_questions(text: str) -> List[str]:
    section = _extract_qa_section(text)
    questions = [match.strip() for match in QA_QUESTION_PATTERN.findall(section)]
    seen: set[str] = set()
    unique: List[str] = []
    for question in questions:
        if question and question not in seen:
            seen.add(question)
            unique.append(question)
    return unique


def load_qa_questions(*, force_reload: bool = False) -> List[str]:
    """加载全景文档 QA 章节中的问题池。"""
    global _cache_questions, _cache_mtime

    path = _resolve_information_path()
    if not path.is_file():
        logger.warning("QA 文档不存在，使用内置推荐问题: %s", path)
        return list(FALLBACK_SUGGESTIONS)

    mtime = path.stat().st_mtime
    if not force_reload and _cache_questions is not None and _cache_mtime == mtime:
        return list(_cache_questions)

    text = _read_text(path)
    questions = _parse_questions(text)
    if len(questions) < 2:
        logger.warning("QA 文档解析结果不足，使用内置推荐问题: %s", path)
        return list(FALLBACK_SUGGESTIONS)

    _cache_questions = questions
    _cache_mtime = mtime
    logger.info("已加载 QA 问题池: %d 条 (%s)", len(questions), path)
    return list(questions)


def get_document_context_for_suggestions(*, force_reload: bool = False) -> str:
    """合并简历与全景文档（不含 QA 正文）作为推荐生成的参考背景。"""
    global _cache_doc_context, _cache_doc_mtime_key

    resume_path = _resolve_resume_path()
    qa_path = _resolve_information_path()
    resume_mtime = resume_path.stat().st_mtime if resume_path.is_file() else 0.0
    qa_mtime = qa_path.stat().st_mtime if qa_path.is_file() else 0.0
    key = (resume_mtime, qa_mtime)

    if not force_reload and _cache_doc_context is not None and _cache_doc_mtime_key == key:
        return _cache_doc_context

    max_total = Config.SUGGESTION_DOC_MAX_CHARS
    resume_budget = max_total // 2
    panorama_budget = max_total - resume_budget

    resume_text = _read_text(resume_path)
    panorama_text = _read_text(qa_path)
    panorama_overview = panorama_text
    qa_start = panorama_text.find(QA_SECTION_TITLE)
    if qa_start > 0:
        panorama_overview = panorama_text[:qa_start]

    parts: List[str] = []
    if resume_text:
        parts.append(
            "### 简历摘要\n"
            + _truncate(resume_text, resume_budget)
        )
    if panorama_overview:
        parts.append(
            "### 项目全景文档摘要\n"
            + _truncate(panorama_overview.strip(), panorama_budget)
        )

    context = "\n\n".join(parts).strip() or "（参考文档暂不可用）"
    _cache_doc_context = context
    _cache_doc_mtime_key = key
    return context


def get_default_suggestions(count: int = 4, asked: Iterable[str] | None = None) -> List[str]:
    """新建会话或无历史时展示的默认推荐问题。"""
    pool = load_qa_questions()
    if asked:
        pool = filter_unasked(pool, asked)
    if not pool:
        return list(FALLBACK_SUGGESTIONS)[:count]

    if len(pool) <= count:
        return pool[:count]

    picked: List[str] = []
    for index in DEFAULT_SUGGESTION_INDICES:
        if index < len(pool):
            candidate = pool[index]
            if candidate not in picked:
                picked.append(candidate)
    for question in pool:
        if question not in picked:
            picked.append(question)
        if len(picked) >= count:
            break
    return picked[:count]


def format_question_pool_for_prompt(
    questions: List[str] | None = None,
    limit: int = 43,
) -> str:
    """将候选问题格式化为 Prompt 文本。"""
    pool = questions or load_qa_questions()
    if not pool:
        pool = list(FALLBACK_SUGGESTIONS)
    lines = [f"{index + 1}. {question}" for index, question in enumerate(pool[:limit])]
    return "\n".join(lines)


def format_asked_questions_for_prompt(asked: Iterable[str]) -> str:
    """格式化已问问题列表。"""
    items = [item.strip() for item in asked if item and item.strip()]
    if not items:
        return "（本会话尚未提问）"
    return "\n".join(f"- {item}" for item in items)


def pick_fallback_from_pool(
    asked: Iterable[str],
    exclude: Iterable[str] | None = None,
    count: int = 4,
) -> List[str]:
    """从问题池中补齐推荐，确保不与已问/已选重复。"""
    excluded = list(asked)
    if exclude:
        excluded = [*excluded, *exclude]
    pool = filter_unasked(load_qa_questions(), excluded)
    if not pool:
        pool = filter_unasked(FALLBACK_SUGGESTIONS, excluded)
    return pool[:count]

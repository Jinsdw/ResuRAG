"""猜你想问 — 推荐追问生成。"""

import json
import re
from typing import Iterable, List

from config import Config
from core.qa_pool import (
    filter_unasked,
    format_asked_questions_for_prompt,
    format_question_pool_for_prompt,
    get_default_suggestions,
    get_document_context_for_suggestions,
    is_similar_question,
    load_qa_questions,
    pick_fallback_from_pool,
)


def get_default_suggestion_list(
    count: int = 4,
    asked: Iterable[str] | None = None,
) -> List[str]:
    return get_default_suggestions(count, asked=asked)


SUGGESTIONS_SYSTEM = """你是面试场景下的「猜你想问」生成器。

## 任务
结合 **参考文档**、**对话历史** 与 **候选问题池**，为面试官挑选 3～4 个后续追问，帮助深入考察候选人 **{candidate_name}**。

## 参考文档（简历 + 项目全景摘要）
{document_context}

## 候选问题池（只能从中选择，须与原文完全一致）
{question_pool}

## 规则
1. **只能从候选池中选择**：输出问题必须与候选池中某一项完全一致，不要改写或自创。
2. **禁止重复**：不得推荐「本会话已问过的问题」列表中的任何问题，也不得推荐与其含义高度相似的问法。
3. **视角**：问题必须是面试官向 {candidate_name} 提问，使用「你」指代候选人。
4. **延续性**：优先结合对话历史向下深挖；若某话题已聊透，从参考文档中挑选尚未覆盖的亮点（项目、技术、业务价值等）。
5. **多样性**：3～4 个问题应覆盖不同主题，避免只换说法重复同一方向。
6. **输出格式**：只输出 JSON 数组，例如：["问题1","问题2","问题3"]
7. **禁止**：不要输出 markdown 代码块、不要输出除 JSON 以外的任何文字。"""

SUGGESTIONS_USER = """## 本会话已问过的问题（禁止再次推荐）
{asked_questions}

## 对话历史
{history}

请从候选问题池中选择 3～4 个「猜你想问」的面试官追问（JSON 数组）："""


def build_suggestions_prompt(
    history: str,
    asked_questions: List[str],
    available_pool: List[str] | None = None,
) -> list:
    candidate_name = Config.CANDIDATE_NAME
    pool = available_pool or filter_unasked(load_qa_questions(), asked_questions)
    document_context = get_document_context_for_suggestions()
    return [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": SUGGESTIONS_SYSTEM.format(
                        candidate_name=candidate_name,
                        document_context=document_context,
                        question_pool=format_question_pool_for_prompt(pool),
                    ),
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": SUGGESTIONS_USER.format(
                        asked_questions=format_asked_questions_for_prompt(asked_questions),
                        history=history,
                    ),
                }
            ],
        },
    ]


def _normalize_to_pool(items: List[str], pool: List[str]) -> List[str]:
    """将模型输出对齐到候选池中的标准问题文本。"""
    if not items or not pool:
        return []

    pool_exact = {question: question for question in pool}
    pool_normalized = {
        re.sub(r"\s+", "", question).lower(): question for question in pool
    }

    matched: List[str] = []
    seen: set[str] = set()
    for item in items:
        text = item.strip()
        if not text:
            continue
        candidate = pool_exact.get(text)
        if not candidate:
            candidate = pool_normalized.get(re.sub(r"\s+", "", text).lower())
        if candidate and candidate not in seen:
            seen.add(candidate)
            matched.append(candidate)
    return matched


def parse_suggestions(
    text: str,
    asked_questions: List[str],
    available_pool: List[str] | None = None,
    fallback: List[str] | None = None,
) -> List[str]:
    """解析模型输出，并剔除与会话已问重复的问题。"""
    full_pool = load_qa_questions()
    pool = available_pool or filter_unasked(full_pool, asked_questions)
    base = list(
        fallback
        or pick_fallback_from_pool(asked_questions, count=4)
    )

    cleaned = (text or "").strip()
    if not cleaned:
        return base[:4]

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    parsed_items: List[str] = []
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            parsed_items = [str(item).strip() for item in data if str(item).strip()]
    except json.JSONDecodeError:
        parsed_items = [
            re.sub(r"^\d+[\.\)、]\s*", "", line.strip())
            for line in cleaned.splitlines()
            if line.strip()
        ]

    matched = _normalize_to_pool(parsed_items, pool)
    matched = [
        question
        for question in matched
        if not any(is_similar_question(question, asked) for asked in asked_questions)
    ]

    if len(matched) >= 2:
        return matched[:4]

    # 模型结果不足时，从剩余候选池补齐
    combined = list(matched)
    for question in pool:
        if question in combined:
            continue
        if any(is_similar_question(question, asked) for asked in asked_questions):
            continue
        combined.append(question)
        if len(combined) >= 4:
            break

    if len(combined) >= 2:
        return combined[:4]

    return base[:4]

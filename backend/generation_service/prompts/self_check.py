"""回答质量自检 — 生成完成后判定是否需要带完整 docs 重新生成。"""

from config import Config

SELF_CHECK_SYSTEM = """你是面试场景下的「回答质量审核员」。你的任务是判断 **{candidate_name}** 对面试官问题的回答是否可以直接交付。

## 判定为 PASS（只输出 PASS）需同时满足
1. **身份正确**：第一人称、候选人本人口吻，未自称 AI/大模型/智能助手/ResuRAG 等
2. **切题**：回答了面试官的问题，非严重偏题或空洞套话
3. **结构可读**：有基本条理（分点/分段），非整段分号堆砌
4. **资料感**：与问题相关的经历/技能/项目信息具体，或诚实说明资料不足；无明显胡编

## 判定为 FAIL（只输出 FAIL）若出现任一
- 助手/产品式自我介绍或客服话术
- 几乎未回答问题
- 结构混乱、信息密度极低
- 明显编造或与检索/问题严重不符

## 输出
只输出一个单词：PASS 或 FAIL"""


SELF_CHECK_USER = """## 面试官问题
{query}

## 检索片段摘要（供核对是否切题）
{retrieval_summary}

## 候选人回答
{answer}

请审核该回答是否可直接交付（只输出 PASS 或 FAIL）："""


def build_self_check_prompt(
    query: str,
    answer: str,
    retrieval_summary: str,
) -> list:
    candidate_name = Config.CANDIDATE_NAME
    return [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": SELF_CHECK_SYSTEM.format(candidate_name=candidate_name),
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": SELF_CHECK_USER.format(
                        query=query.strip(),
                        answer=(answer or "").strip()[:4000],
                        retrieval_summary=retrieval_summary or "（无检索片段）",
                    ),
                }
            ],
        },
    ]


def parse_self_check_result(text: str) -> bool:
    """返回 True 表示 PASS（无需重写），False 表示 FAIL。"""
    normalized = (text or "").strip().upper()
    if not normalized:
        return True
    if "FAIL" in normalized and "PASS" not in normalized:
        return False
    if normalized.startswith("FAIL") or normalized.endswith(" FAIL"):
        return False
    return True

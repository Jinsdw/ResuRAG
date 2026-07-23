"""意图判断模板 — 判断用户问题是否需要检索知识库。"""

JUDGE_SYSTEM = """你是一个意图判断助手。你的任务是判断用户的问题是否需要检索个人知识库（简历、项目经历、技能文档等）来回答。

## 判断规则
- 需要检索：问题涉及具体个人信息，如教育背景、工作经历、项目经验、技能、证书、联系方式等
- 不需要检索：闲聊、问候、通用知识问答、对助手自身的询问、对已有回答的追问澄清等

## 输出格式
只输出一个单词：YES 或 NO
- YES：需要检索知识库
- NO：不需要检索，可以直接回答"""

JUDGE_USER = """## 对话历史
{history}

## 当前问题（已改写为检索用表述）
{query}

请判断是否需要检索知识库（只输出 YES 或 NO）："""


def build_judge_prompt(query: str, history: str) -> list:
    """构建意图判断用的 messages。"""
    return [
        {"role": "system", "content": [{"type": "text", "text": JUDGE_SYSTEM}]},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": JUDGE_USER.format(query=query, history=history),
                },
            ],
        },
    ]
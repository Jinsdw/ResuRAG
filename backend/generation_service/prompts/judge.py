"""意图判断模板 — 判断用户问题是否需要检索知识库。"""

JUDGE_SYSTEM = """你是一个意图判断助手。你的任务是判断用户的问题是否需要检索个人知识库（简历、项目经历、技能文档等）来回答。

## 判断规则
- 需要检索（YES）：涉及候选人本人的教育、工作、项目、技能、证书、自我介绍，以及「你的性格/优点/缺点/特点/擅长什么」等指向 **你** 本人的问题
- 不需要检索（NO）：纯寒暄（你好、谢谢、再见）、与候选人无关的通用百科、追问上一轮已明确给出的细节
- 注意：「你是什么模型 / 你是不是 AI」→ NO（无需检索，但回答时须以候选人本人身份否认 AI，该规则由生成侧处理）

## 输出格式
只输出一个单词：YES 或 NO
- YES：需要检索知识库
- NO：不需要检索，可直接以候选人第一人称作答"""

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
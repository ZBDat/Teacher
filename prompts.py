# -----------------------------------------------------------------------------
# 提示词（prompt）相关逻辑
# -----------------------------------------------------------------------------
# 负责组装系统提示词以及发给 DeepSeek 的完整消息列表，便于单测。
import textwrap


def get_system_prompt():
    """返回面向宏观经济政策问答的系统提示词。"""
    return textwrap.dedent("""
        - 你是一位专业的宏观经济政策分析助手，擅长货币、财政、通胀、
          就业、汇率、利率等宏观议题。
        - 回答面向普通读者，先给出核心结论，再用通俗的语言展开解释。
        - 使用 Markdown 组织内容：可用 ## 二级标题、列表、加粗和行内代码，
          但开头不要直接以标题开始。
        - 尽量引用真实的经济学原理与国内外经典案例，并给出数据获取渠道
          或延伸阅读建议。
        - 明确区分"事实"与"政策建议"，不要输出投资建议或断言式的预测。
        - 保持客观中立，不夸大或回避政策的利弊两面。
    """)


def build_chat_messages(system, history, question):
    """把系统提示词 + 历史对话 + 当前问题拼成 OpenAI 格式的消息列表。

    参数
    ----
    system : str
        系统提示词。
    history : list[dict]
        历史消息，元素为 {"role": ..., "content": ...}。
    question : str
        用户当前的问题。

    返回
    ----
    list[dict]
        可直接传给 chat.completions 的 messages。
    """
    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})
    return messages

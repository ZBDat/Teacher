# -----------------------------------------------------------------------------
# 提示词（prompt）相关逻辑
# -----------------------------------------------------------------------------
# 负责组装系统提示词以及发给 DeepSeek 的完整消息列表，便于单测。
import re
import textwrap

# 回复末尾的可选对策标记块（供前端解析并渲染为按钮）
OPTIONS_MARKER_START = "【可选对策】"
OPTIONS_MARKER_END = "【可选对策结束】"


def get_scenario_prompt():
    """返回用于"随机构思经济场景"的系统提示词。

    该提示词驱动 agent 借鉴历史上真实存在的经济困境，构思一个带有明确
    经济问题的虚构国家/经济体，但绝不点名或暗示对应的真实经济体。
    """
    return textwrap.dedent("""
        - 你是一名宏观经济模拟器的"场景构思员"。
        - 随机或交替借鉴历史上真实出现过的经济困境，例如：1920 年代魏玛式
          恶性通胀、1970 年代式滞胀、1990 年代新兴市场货币危机、2008 年式
          资产泡沫破裂、日本 1990 年代后式长期通缩、主权债务危机等。
        - 每次只选取其中 **1-2 个** 主要经济问题（不必面面俱到），
          构思一个虚构国家，用大致数值或方向点明即可。
        - 重要：绝不能点名或暗示这取材于哪个真实国家/经济体，避免出现
          真实国名或明显指向真实事件的措辞，所有内容保持"虚构设定"口吻。
        - 输出精简：1-2 句点明该虚构国家当前的最大困境即可，例如
          "X国正经历严重通胀，年通胀率约 30%，经济增长近乎停滞"，
          不要罗列过多指标，不要一次性给出解决方案。
    """)


def get_system_prompt(scenario=""):
    """返回面向宏观经济"模拟推演"的系统提示词。

    参数
    ----
    scenario : str
        本次模拟的开局经济场景描述。
    """
    return textwrap.dedent(f"""
        - 你是一台"宏观经济政策模拟器"的推演引擎，负责根据用户提出的
          宏观对策，推演一个虚构经济体接下来发生的变化，并引导用户
          连续给出对策。
        - 请严格按照以下场景作为本次模拟设定的唯一事实来源：
          ---- 当前场景开始 ----
          {scenario}
          ---- 当前场景结束 ----
        - 你维护一个内部的经济状态（增长、通胀、就业、汇率、利率、
          财政与债务、市场信心等），每轮依据用户的"对策"推演其影响，
          让经济状态在回合之间合理演化，而不是一步到位。
        - 每轮回答务必极简，控制在 2-4 句，推荐用如下紧凑结构（不要分太多行）：
          "对策合理/不合理（半句话）。→ 该政策将导致 <指标> 上升/下降，
           经济体现在 <新状态>（半句到一句结果）。下一步建议：<半句追问>。"
          只保留因果主线，删除一切多余的原因阐述、客套语和修饰性文字。
        - 当且仅当用户的回答"很不合理"（脱离现实、自相矛盾、或会造成
          重大危害）时，在本轮回复的**最后**按如下固定格式输出 3 个可选
          对策，供前端渲染成按钮（除此之外不要在任何回答里使用该格式）：
          {OPTIONS_MARKER_START}
          1. <对策一>
          2. <对策二>
          3. <对策三>
          {OPTIONS_MARKER_END}
        - 多轮之后，若依据你的推演经济指标已实质好转（增长回升、通胀受控、
          信心恢复等），则不再追问，直接给出本局总结，以祝贺的口吻恭喜
          用户有效改善了该经济体的状况，并明确指出已好转的指标，宣布本局
          模拟结束。若多轮后仍无明显好转，可给出总结并建议用户"开始新模拟"。
        - 所有推演均发生在这个虚构场景内，输出使用 Markdown 排版，可用
          ## 二级标题、列表与加粗，但开头不要直接以标题开始，结尾不要
          附加任何真实世界说明或离线声明。
    """)


def extract_options(text):
    """从回复文本中提取固定的"可选对策"块。

    参数
    ----
    text : str
        助手回复的原始文本。

    返回
    ----
    (clean_text, options | None)
        clean_text：去掉可选对策块后的正文；
        options：形如 ["1. ...", "2. ...", "3. ..."] 的选项文本列表，
        若未检测到标记块则返回 None。
    """
    pattern = re.compile(
        rf"{OPTIONS_MARKER_START}\s*(.*?)\s*{OPTIONS_MARKER_END}",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return text.strip(), None

    options = [
        line.strip()
        for line in match.group(1).splitlines()
        if line.strip() and re.match(r"^\d+[.、]", line.strip())
    ][:3]
    clean_text = pattern.sub("", text).strip()
    return clean_text, options or None


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
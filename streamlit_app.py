# -----------------------------------------------------------------------------
# 宏观经济政策模拟器（Streamlit 应用）
# -----------------------------------------------------------------------------
# 前端交互沿袭原有聊天气泡式结构：
#   - 首次进入展示开场说明 + "开始新模拟"按钮，触发随机生成经济场景
#   - 场景生成后展示其描述文本，输入框用于提交用户的宏观对策
#   - 每轮由模型推演 + 追问；回答不合理时按标记块给出 3 个对策按钮
#   - 顶部标题栏有"新模拟"按钮用于重新开始
# 后端通过 OpenAI Python SDK 调用 DeepSeek 的 API（见 llm_client.py）。
from htbuilder import div, styles
from htbuilder.units import rem
import streamlit as st

import llm_client
from prompts import (
    build_chat_messages,
    extract_options,
    get_scenario_prompt,
    get_system_prompt,
)

# 页面基础配置
st.set_page_config(page_title="宏观经济政策模拟器", page_icon="🧭", layout="centered")

# 会话状态初始化
st.session_state.setdefault("messages", [])
st.session_state.setdefault("option_sets", {})
st.session_state.setdefault("option_choice", None)
st.session_state.setdefault("scenario", None)


def get_llm_client():
    """创建（并缓存）DeepSeek 对话客户端。"""
    if "llm_client" not in st.session_state:
        st.session_state.llm_client = llm_client.get_client()
    return st.session_state.llm_client


def reset_session():
    """清空本局模拟的所有状态，回到"开始新模拟"入口。"""
    st.session_state.messages = []
    st.session_state.option_sets = {}
    st.session_state.pending_options_index = None
    st.session_state.scenario = None
    st.session_state.option_choice = None


def generate_scenario():
    """调用模型构思一个随机的经济场景，并存入会话状态。"""
    st.session_state.scenario = llm_client.get_response(
        get_llm_client(),
        build_chat_messages(get_scenario_prompt(), [], "请构思本局的经济场景。"),
    )


def history_to_text(chat_history):
    """把对话历史转成文本，便于组织上下文。"""
    return "\n".join(f"[{m['role']}]: {m['content']}" for m in chat_history)


# -----------------------------------------------------------------------------
# 绘制 UI
# -----------------------------------------------------------------------------

# 顶部装饰符
st.html(div(style=styles(font_size=rem(4), line_height=1))["🧭"])

title_row = st.container(
    horizontal=True,
    vertical_alignment="bottom",
)

with title_row:
    st.title(
        ":material/account_balance: 宏观经济政策模拟器",
        anchor=False,
        width="stretch",
    )
    st.button(
        "新模拟",
        icon=":material/refresh:",
        on_click=reset_session,
    )

# 尚无场景：展示开场说明 + "开始新模拟"按钮
if not st.session_state.get("scenario"):
    if "option_choice" not in st.session_state:
        st.session_state.option_choice = None

    st.markdown(
        "你将被任命为某个虚构经济体的新任决策者。"
        "系统会随机生成一个面临经济问题的国家，"
        "你需要连续提出宏观对策，帮助它走出困境。"
    )
    st.button(
        "开始新模拟",
        type="primary",
        on_click=generate_scenario,
    )
    st.stop()

# 已有场景：展示场景描述 + 对策输入框
st.markdown(st.session_state.scenario)

# 判断用户是否刚点过备选对策按钮
option_choice = st.session_state.get("option_choice")
if option_choice:
    st.session_state.option_choice = None
    user_message = option_choice
else:
    user_message = st.chat_input("请输入你的宏观对策（如货币政策、财政政策、结构性改革等）...")

has_message_history = (
    "messages" in st.session_state and len(st.session_state.messages) > 0
)

# 首轮：场景描述会始终展示在顶部，历史为空即可直接进入
if not has_message_history and not user_message:
    st.caption("在上方输入框中提交你的第一个对策。")
    st.stop()

if has_message_history:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                st.container()  # 修复"幽灵消息"bug
            st.markdown(message["content"])

# 渲染历史中已经生成的可选对策按钮
for msg_index, options in (st.session_state.option_sets or {}).items():
    if msg_index < len(st.session_state.messages):
        with st.chat_message("assistant"):
            st.caption("以下是可选的替代对策：")
            for opt in options:
                if st.button(opt, key=f"option_{msg_index}_{opt}"):
                    st.session_state.option_sets.pop(msg_index, None)
                    st.session_state.option_choice = opt
                    st.rerun()

# 处理用户新消息
if not user_message:
    st.stop()

# Streamlit 的 Markdown 会把 "$" 当作 LaTeX 分隔符，这里转义掉
user_message = user_message.replace("$", r"\$")

# 显示用户消息气泡
with st.chat_message("user"):
    st.text(user_message)

# 组织历史上下文并发起请求
history = st.session_state.messages
messages = build_chat_messages(
    system=get_system_prompt(scenario=st.session_state.scenario),
    history=history,
    question=user_message,
)

client = get_llm_client()

# 显示助手气泡并流式输出
with st.chat_message("assistant"):
    with st.spinner("经济推演中..."):
        with st.container():
            response = st.write_stream(
                llm_client.get_response_stream(client, messages)
            )

# 剥离"可选对策"块，抽出按钮选项
clean_response, options = extract_options(response)

# 记录到会话历史
st.session_state.messages.append({"role": "user", "content": user_message})
st.session_state.messages.append({"role": "assistant", "content": clean_response})

# 记录本次可选对策（关联到刚写入的助手消息索引）
if options:
    if "option_sets" not in st.session_state:
        st.session_state.option_sets = {}
    st.session_state.option_sets[len(st.session_state.messages) - 1] = options
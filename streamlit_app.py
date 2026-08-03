# -----------------------------------------------------------------------------
# 宏观经济政策 AI 助手（Streamlit 应用）
# -----------------------------------------------------------------------------
# 前端交互形式仿照 streamlit 官方 demo-ai-assistant：
#   - 首次进入时展示欢迎区 + 示例问题 pills + 对话输入框
#   - 提问后以聊天气泡展示历史，底部为后续输入框，标题栏有 Restart 按钮
# 后端通过 OpenAI Python SDK 调用 DeepSeek 的 API（见 llm_client.py）。
from htbuilder import div, styles
from htbuilder.units import rem
import os

import streamlit as st

import llm_client
from prompts import build_chat_messages, get_system_prompt

# 页面基础配置
st.set_page_config(page_title="宏观经济政策助手", page_icon="🌐", layout="centered")

# 示例问题（pills 中展示的"快捷入口"）
SUGGESTIONS = {
    ":blue[:material/currency_exchange:] 什么是货币政策？": (
        "用通俗的语言解释什么是货币政策，以及它如何影响宏观经济。"
    ),
    ":green[:material/account_balance:] 财政政策如何刺激经济？": (
        "财政政策通常通过哪些手段来刺激经济？请举例说明。"
    ),
    ":orange[:material/trending_up:] 通胀成因与对策": (
        "请分析当前高通胀的主要成因，并给出对应的宏观调控建议。"
    ),
    ":violet[:material/public:] 货币 vs 财政政策比较": (
        "比较货币政策和财政政策在作用机制与适用场景上的异同。"
    ),
    ":red[:material/dashboard:] 利率如何影响汇率？": (
        "央行加息会通过什么传导路径影响本币汇率？"
    ),
}


def get_llm_client():
    """创建（并缓存）DeepSeek 对话客户端。"""
    if "llm_client" not in st.session_state:
        st.session_state.llm_client = llm_client.get_client()
    return st.session_state.llm_client


def clear_conversation():
    """清空当前对话历史，回到欢迎界面。"""
    st.session_state.messages = []
    st.session_state.initial_question = None
    st.session_state.selected_suggestion = None


def history_to_text(chat_history):
    """把对话历史转成文本，便于组织上下文。"""
    return "\n".join(f"[{m['role']}]: {m['content']}" for m in chat_history)


@st.dialog("法律声明")
def show_disclaimer_dialog():
    """展示法律声明弹窗。"""
    st.caption("""
        本助手由 DeepSeek 大模型驱动，仅用于宏观经济与政策的科普讨论，
        不构成任何投资或政策建议。模型的回答可能存在错误、偏颇或不完整，
        任何基于这些回答的决策都应结合权威数据并纳入人工判断。
        请勿在对话中输入任何个人隐私或敏感信息。
    """)


# -----------------------------------------------------------------------------
# 绘制 UI
# -----------------------------------------------------------------------------

# 顶部装饰符（仿照参考应用）
st.html(div(style=styles(font_size=rem(4), line_height=1))["💹"])

title_row = st.container(
    horizontal=True,
    vertical_alignment="bottom",
)

with title_row:
    st.title(
        ":material/account_balance: 宏观经济政策助手",
        anchor=False,
        width="stretch",
    )

# 判断用户是否刚在欢迎界面问过问题 / 点过示例
user_just_asked_initial_question = (
    "initial_question" in st.session_state and st.session_state.initial_question
)
user_just_clicked_suggestion = (
    "selected_suggestion" in st.session_state and st.session_state.selected_suggestion
)
user_first_interaction = user_just_asked_initial_question or user_just_clicked_suggestion
has_message_history = (
    "messages" in st.session_state and len(st.session_state.messages) > 0
)

# 尚未对话：展示欢迎界面（输入框 + 示例问题 pills + 声明按钮）
if not user_first_interaction and not has_message_history:
    st.session_state.messages = []

    with st.container():
        st.chat_input("请提出你的宏观经济问题...", key="initial_question")
        st.pills(
            label="示例问题",
            label_visibility="collapsed",
            options=SUGGESTIONS.keys(),
            key="selected_suggestion",
        )

    st.button(
        "&nbsp;:small[:gray[:material/balance: 法律声明]]",
        type="tertiary",
        on_click=show_disclaimer_dialog,
    )
    st.stop()

# 已进入对话：底部为持续输入框
user_message = st.chat_input("追问一个后续问题...")

# 若用户是从欢迎界面进来的，把欢迎界面的输入作为首条消息
if not user_message:
    if user_just_asked_initial_question:
        user_message = st.session_state.initial_question
    if user_just_clicked_suggestion:
        user_message = SUGGESTIONS[st.session_state.selected_suggestion]

with title_row:
    st.button(
        "重新开始",
        icon=":material/refresh:",
        on_click=clear_conversation,
    )

# 展示历史消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.container()  # 修复"幽灵消息"bug
        st.markdown(message["content"])

# 处理用户新消息
if user_message:
    # Streamlit 的 Markdown 会把 "$" 当作 LaTeX 分隔符，这里转义掉
    user_message = user_message.replace("$", r"\$")

    # 显示用户消息气泡
    with st.chat_message("user"):
        st.text(user_message)

    # 组织历史上下文并发起请求
    history = st.session_state.messages
    messages = build_chat_messages(
        system=get_system_prompt(),
        history=history,
        question=user_message,
    )

    client = get_llm_client()

    # 显示助手气泡并流式输出
    with st.chat_message("assistant"):
        with st.spinner("政策分析中..."):
            with st.container():
                response = st.write_stream(
                    llm_client.get_response_stream(client, messages)
                )

    # 记录到会话历史
    st.session_state.messages.append({"role": "user", "content": user_message})
    st.session_state.messages.append({"role": "assistant", "content": response})

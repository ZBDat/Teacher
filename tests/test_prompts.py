# -----------------------------------------------------------------------------
# 针对提示词拼装逻辑的单元测试
# -----------------------------------------------------------------------------
import pytest

import llm_client
import prompts


def test_get_system_prompt_mentions_policy_topics():
    """模拟推演的系统提示词应覆盖宏观经济的核心主题。"""
    system = prompts.get_system_prompt(scenario="某虚构经济体：高通胀 + 高财政赤字。")
    assert "宏观经济" in system
    assert "货币" in system or "财政" in system


def test_get_system_prompt_embeds_scenario():
    """系统提示词应把传入的场景文本嵌入其中。"""
    scenario = "瓦尔兰国：通胀率 40%，财政赤字 8%，汇率持续贬值。"
    system = prompts.get_system_prompt(scenario=scenario)
    assert scenario in system


def test_get_scenario_prompt_avoids_real_countries():
    """场景生成提示词应要求虚构，且不点名真实国家。"""
    prompt = prompts.get_scenario_prompt()
    assert "虚构" in prompt
    assert "绝不能点名" in prompt


def test_build_chat_messages_order():
    """消息顺序应为：系统 -> 历史 -> 当前问题。"""
    history = [
        {"role": "user", "content": "什么是通胀？"},
        {"role": "assistant", "content": "通胀是指物价普遍上涨。"},
    ]
    messages = prompts.build_chat_messages(
        system="SYS",
        history=history,
        question="如何治理通胀？",
    )
    assert [m["role"] for m in messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert messages[0]["content"] == "SYS"
    assert messages[-1]["content"] == "如何治理通胀？"


def test_build_chat_messages_with_empty_history():
    """无历史时也应保留系统提示词与当前问题。"""
    messages = prompts.build_chat_messages(
        system="SYS", history=[], question="第一个问题"
    )
    assert messages == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "第一个问题"},
    ]


def test_extract_options_returns_clean_text_and_options():
    """应剥离标记块并返回前 3 个选项文本。"""
    raw = (
        "该对策难以直接落地。\n\n"
        "【可选对策】\n"
        "1. 提高基准利率以抑制通胀。\n"
        "2. 削减财政支出降低赤字。\n"
        "3. 引入汇率稳定机制。\n"
        "【可选对策结束】"
    )
    clean, options = prompts.extract_options(raw)
    assert "该对策难以直接落地" in clean
    assert "【可选对策" not in clean
    assert options[0].startswith("1.")
    assert len(options) == 3


def test_extract_options_returns_none_without_block():
    """未包含标记块时应原样返回文本，且选项为 None。"""
    text = "一切正常，这里是普通回复。"
    clean, options = prompts.extract_options(text)
    assert clean == text
    assert options is None


def test_get_api_key_reads_env(monkeypatch):
    """API Key 应只从环境变量读取。"""
    monkeypatch.setenv("DS_APIKEY", "sk-test")
    assert llm_client.get_api_key() == "sk-test"


def test_get_client_uses_deepseek_endpoint(monkeypatch):
    """客户端应指向 DeepSeek 的兼容端点。"""
    monkeypatch.setenv("DS_APIKEY", "sk-test")
    client = llm_client.get_client()
    assert client.base_url == llm_client.DEEPSEEK_BASE_URL
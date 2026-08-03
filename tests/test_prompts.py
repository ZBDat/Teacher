# -----------------------------------------------------------------------------
# 针对提示词拼装逻辑的单元测试
# -----------------------------------------------------------------------------
import pytest

import llm_client
import prompts


def test_get_system_prompt_mentions_policy_topics():
    """系统提示词应覆盖宏观经济的核心主题。"""
    system = prompts.get_system_prompt()
    assert "宏观经济" in system
    assert "货币" in system or "财政" in system


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


def test_get_api_key_reads_env(monkeypatch):
    """API Key 应只从环境变量读取。"""
    monkeypatch.setenv("DS_APIKEY", "sk-test")
    assert llm_client.get_api_key() == "sk-test"


def test_get_client_uses_deepseek_endpoint(monkeypatch):
    """客户端应指向 DeepSeek 的兼容端点。"""
    monkeypatch.setenv("DS_APIKEY", "sk-test")
    client = llm_client.get_client()
    assert client.base_url == llm_client.DEEPSEEK_BASE_URL

# -----------------------------------------------------------------------------
# DeepSeek / OpenAI 客户端封装
# -----------------------------------------------------------------------------
# 统一从这里创建调用 DeepSeek API 的 OpenAI 客户端，方便测试时 mock。
# API Key 只从环境变量 DS_APIKEY 读取，绝不硬编码到代码里。
import os

from openai import OpenAI

# DeepSeek 的 OpenAI 兼容接口地址与推荐模型
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


def get_api_key():
    """从环境变量中读取 DeepSeek API Key。"""
    return os.environ.get("DS_APIKEY", "")


def get_client(api_key=None):
    """创建 OpenAI 客户端，并指向 DeepSeek 的兼容端点。"""
    return OpenAI(
        api_key=api_key or get_api_key(),
        base_url=DEEPSEEK_BASE_URL,
    )


def get_response(client, messages, **kwargs):
    """向 DeepSeek 发起一次非流式对话请求，返回回复文本。"""
    response = client.chat.completions.create(
        model=kwargs.pop("model", DEEPSEEK_MODEL),
        messages=messages,
        **kwargs,
    )
    return response.choices[0].message.content


def get_response_stream(client, messages, **kwargs):
    """向 DeepSeek 发起一次流式对话请求，返回增量文本生成器。"""
    stream = client.chat.completions.create(
        model=kwargs.pop("model", DEEPSEEK_MODEL),
        messages=messages,
        stream=True,
        **kwargs,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# -----------------------------------------------------------------------------
# LLM 客户端（流式 / 非流式）单元测试，全部使用假客户端，不发起真实请求。
# -----------------------------------------------------------------------------
import llm_client


class FakeCompletions:
    """模拟 OpenAI SDK 的 chat.completions.create 返回值。"""

    def __init__(self, streaming):
        self.streaming = streaming

    def create(self, **kwargs):
        if not self.streaming:
            return FakeResponse()
        # 流式：返回若干增量 chunk
        return [
            FakeChunk("第一段"),
            FakeChunk("第二段"),
        ]


class FakeResponse:
    def __init__(self):
        self.choices = [FakeChoice("完整回复")]


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChunk:
    def __init__(self, content):
        self.choices = [FakeDelta(content)]


class FakeDelta:
    def __init__(self, content):
        self.delta = FakeContent(content)


class FakeContent:
    def __init__(self, content):
        self.content = content


class FakeChat:
    """伪造 client.chat 对象。"""

    def __init__(self, streaming):
        self.completions = FakeCompletions(streaming)


class FakeClient:
    def __init__(self, streaming):
        self.chat = FakeChat(streaming)


def test_get_response_returns_text():
    """非流式调用应返回最终的回复文本。"""
    result = llm_client.get_response(FakeClient(streaming=False), messages=[])
    assert result == "完整回复"


def test_get_response_stream_yields_pieces():
    """流式调用应逐段产出增量文本。"""
    pieces = list(llm_client.get_response_stream(FakeClient(streaming=True), messages=[]))
    assert pieces == ["第一段", "第二段"]


def test_get_response_stream_empty_delta_skipped():
    """delta 内容为空的 chunk 应被跳过。"""

    class EmptyDeltaChunk:
        def __init__(self):
            self.choices = [EmptyDeltaChoice()]

    class EmptyDeltaChoice:
        def __init__(self):
            # 真实的 SDK 中 delta 对象始终存在，content 可能为 None
            self.delta = FakeContent(None)

    class CustomFakeCompletions(FakeCompletions):
        def __init__(self):
            super().__init__(streaming=True)

        def create(self, **kwargs):
            return [EmptyDeltaChunk(), FakeChunk("有内容")]

    class CustomFakeClient:
        def __init__(self):
            self.chat = FakeChat(streaming=True)
            self.chat.completions = CustomFakeCompletions()

    pieces = list(
        llm_client.get_response_stream(CustomFakeClient(), messages=[])
    )
    assert pieces == ["有内容"]

# 宏观经济政策助手
基于 Streamlit + DeepSeek 的宏观经济政策问答应用，前端交互仿照
[streamlit demo-ai-assistant](https://demo-ai-assistant.streamlit.app/)。

## 功能
- 首次进入展示欢迎区：对话输入框 + 示例问题快捷入口 + 法律声明
- 提问后以聊天气泡展示历史，底部持续输入，标题栏可"重新开始"
- 回答以流式（streaming）方式输出
- 通过 OpenAI Python SDK 调用 DeepSeek 的兼容接口

## 配置
API Key 从环境变量 `DS_APIKEY` 读取（请勿硬编码到代码中）：

```bash
export DS_APIKEY="sk-xxxx"
```

## 安装与启动
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8848
# 或直接使用仓库内的启动脚本
./run.sh
```

## 测试
```bash
pytest
```

## 代码结构
- `streamlit_app.py`：主应用与前端 UI
- `prompts.py`：系统提示词与消息拼装
- `llm_client.py`：DeepSeek（OpenAI SDK）客户端封装
- `tests/`：单元测试
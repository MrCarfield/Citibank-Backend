多 AI 讨论相关文件一览
================================

本项目中与「多模型协同 / 多 AI 讨论」（LLM Council）强相关的文件如下，方便其他 AI 快速建立上下文。

核心服务模块（LLM Council）
--------------------------

- app/services/llm_council/config.py
- app/services/llm_council/client.py
- app/services/llm_council/core.py
- app/services/llm_council/__init__.py

调用 LLM Council 的业务入口
--------------------------

- app/api/v1/endpoints/translator.py

配置与依赖
----------

- .env.example  （包含 OPENROUTER_API_KEY 等 LLM Council 相关配置项）
- requirements.txt  （包含 httpx 等调用 OpenRouter 所需依赖）


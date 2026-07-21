# ResuRAG

**个人信息智能问答系统** — 基于 RAG 的个人资料问答平台。

系统将个人文档（简历等）切块、向量化并存储，用户通过自然语言提问，系统自动检索相关内容并生成带引用来源的精准回答。

## 系统主题

ResuRAG（Resume + RAG）面向**个人信息查询场景**：

- 面试官 / HR 询问候选人经历、技能、项目
- 个人快速检索自己资料中的细节
- 基于真实文档片段回答，减少幻觉；引用片段在调试面板中展示并可追溯

## 架构概览

```
用户浏览器 (3000)
    │
    ├─► 检索服务 (8003)  混合检索 + 相似度阈值过滤
    │
    └─► 生成服务 (8004)  流式回答 + 会话/聊天记录 (SQLite)
            │
            └─► 智谱 GLM（思考过程 + 正文分离 SSE）

文档流水线（离线/运维）：
  doc_service (8000) → indexing_service (8002) → Milvus
```

| 服务 | 端口 | 职责 |
|------|------|------|
| doc_service | 8000 | 文档上传与切块 |
| indexing_service | 8002 | 向量写入 Milvus |
| retrieval_service | 8003 | 稠密 + 稀疏混合检索 |
| generation_service | 8004 | 流式生成、会话与聊天记录 |
| 前端 (Vite) | 3000 | 三栏 UI，API 经代理转发 |

## 项目结构

```
ResuRAG/
├── backend/
│   ├── doc_service/
│   ├── indexing_service/
│   ├── retrieval_service/
│   ├── generation_service/
│   │   ├── core/              # LLM、SQLite 会话存储
│   │   ├── prompts/           # RAG 提示词 + 会话长期记忆
│   │   └── data/sessions.db   # 会话与聊天记录（运行时生成）
│   ├── docker-compose.yml     # Milvus 等基础设施
│   ├── rag_storage/           # 原始文件与切块 JSON
│   ├── requirements.txt
│   └── .env
└── frontend/                  # React + Vite + TS + Ant Design
```

## 生成服务 API（摘要）

基础路径经前端代理为 `/api/generation`，直连为 `http://localhost:8004`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/sessions` | 当前浏览器指纹下的会话列表 |
| GET | `/api/v1/sessions/{id}/messages` | 会话聊天记录 |
| DELETE | `/api/v1/sessions/{id}` | 删除会话（级联消息） |
| POST | `/api/v1/generate` | SSE 流式生成（含思考/正文事件） |
| GET | `/api/v1/health` | 健康检查 |

**浏览器指纹（无登录隔离）**

- 请求头：`X-Browser-Fingerprint`
- 前端首次访问时在 `localStorage` 生成 UUID 并自动附带
- **会话列表**与**首次创建会话**（通过 `/generate` 的 `ensure_session`）会校验并写入 `sessions.fingerprint` 字段

**检索服务 API**（代理路径 `/api/retrieval`，直连 `http://localhost:8003`）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/search` | 混合检索；body 含 `query`、`top_k`、`similarity_threshold` |
| GET | `/api/v1/health` | 健康检查 |

**生成服务 SSE 事件**

| type | 说明 |
|------|------|
| `reasoning` | 思考过程（流式增量） |
| `content` | 回答正文（流式增量） |
| `done` | 生成结束 |
| `error` | 错误 |

**检索参数**

- `POST /api/v1/search`（检索服务）：请求体含 `similarity_threshold`，阈值在后端过滤，不由前端二次过滤

**SQLite 表**

- `sessions`：`session_id`, `fingerprint`, `subject`, `created_at`, `updated_at`
- `chat_messages`：`message_id`, `session_id`, `role`, `content`, `reasoning`, `citations_json`, `created_at`

## 启动后端

```bash
cd backend
docker compose up -d
pip install -r requirements.txt

# 各开一个终端
python doc_service/main.py
python indexing_service/main.py
python retrieval_service/main.py
python generation_service/main.py
```

在 `backend/.env` 中配置环境变量，例如：

| 变量 | 说明 |
|------|------|
| `ZHIPU_API_KEY` | 智谱 API Key（生成服务） |
| `ZHIPU_MODEL` | 模型名称，默认 `GLM-4.6V-FlashX` |
| `MILVUS_HOST` / `MILVUS_PORT` | Milvus 地址 |
| `GENERATION_PORT` | 生成服务端口，默认 8004 |
| `RETRIEVAL_PORT` | 检索服务端口，默认 8003 |

详见各服务目录下的 `config.py`。

## 启动前端

```bash
cd frontend
yarn install   # 或 npm install
yarn dev       # 或 npm run dev
```

浏览器访问 http://127.0.0.1:3000 。更多 UI 说明见 [frontend/README.md](frontend/README.md)。

## 数据流（一次提问）

1. 前端调用检索服务，携带 `top_k` 与 `similarity_threshold`
2. 前端 SSE 调用生成服务，写入用户/助手消息占位并流式返回 `reasoning` / `content`
3. 生成服务按 `session_id` 加载历史 role/content 拼入系统提示作为长期记忆
4. 调试面板展示本轮引用来源；会话元数据持久化在 SQLite，聊天记录同步服务端

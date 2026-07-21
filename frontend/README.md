# ResuRAG 前端

个人信息智能问答界面：左侧会话历史、中间对话、右侧调试与引用来源。

## 功能概览

| 模块 | 说明 |
|------|------|
| 对话区 | 流式展示**思考过程**与**正式回答**（分区样式与图标） |
| 引用来源 | 位于**调试面板底部**；摘要默认两行，悬停 Tooltip 查看全文 |
| 对话历史 | 会话列表来自生成服务 SQLite；支持新建、切换、删除 |
| 调试面板 | 相似度阈值、检索 Top-K（阈值在后端检索接口生效） |
| 滚动 | 在底部附近时自动跟随流式输出；手动上滑阅读时不强制滚到底 |

## 数据与隔离

- **会话元数据**：通过生成服务 API 持久化（`sessions` 表）
- **聊天记录**：发送问题时写入服务端；切换已持久化会话时拉取历史消息
- **浏览器指纹**：`localStorage` 存 UUID，访问生成服务时自动带请求头 `X-Browser-Fingerprint`，用于会话列表与创建会话时的数据隔离（无账号登录）

本地仍保留：当前选中会话 ID（`localStorage`）。

## 技术栈

React · Vite · TypeScript · Ant Design · Less

## 启动

```bash
yarn install   # 或 npm install
yarn dev       # 或 npm run dev
```

访问 http://127.0.0.1:3000 。需先启动后端（见根目录 [README.md](../README.md)）。

## 开发代理

| 前端路径 | 后端 |
|----------|------|
| `/api/doc` | localhost:8000 |
| `/api/indexing` | localhost:8002 |
| `/api/retrieval` | localhost:8003 |
| `/api/generation` | localhost:8004 |

## 目录结构

```
src/
├── components/
│   ├── chat/       MessageBubble、ChatInput、MessageList
│   ├── debug/      DebugPanel、CitationList、相似度/Top-K
│   ├── layout/     三栏 MainLayout
│   └── session/    SessionList、NewSessionButton
├── context/        AppContext
├── hooks/          useSessions、useChat、useStickToBottomScroll
├── services/       api、session、retrieval、generation
├── utils/          fingerprint（浏览器指纹）
└── styles/         variables.less、global.less
```

## 主要服务封装

| 文件 | 职责 |
|------|------|
| `sessionService.ts` | 会话列表、消息列表、删除 |
| `retrievalService.ts` | `POST .../search`（`top_k`、`similarity_threshold`） |
| `generationService.ts` | SSE `POST .../generate`（`session_id`、消息 id、`citations`） |
| `api.ts` | 统一 fetch；访问 `/api/generation` 时自动附加指纹 Header |

## SSE 事件类型

生成接口返回 `text/event-stream`，每行 `data: {...}`：

| type | 说明 |
|------|------|
| `reasoning` | 思考过程增量 |
| `content` | 回答正文增量 |
| `done` | 流结束 |
| `error` | 错误信息 |

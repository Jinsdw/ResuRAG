# ResuRAG 前端

ResuRAG 是一个**个人信息智能问答系统**。系统将个人资料（如简历、经历文档）向量化入库，用户可通过自然语言提问，系统基于 RAG 检索相关片段并生成带引用来源的回答。

## 功能概览

| 模块 | 说明 |
|------|------|
| 对话区 | 输入个人信息相关问题，流式展示 AI 回答 |
| 引用来源 | 每条回答附带来自个人资料的相关片段及匹配度 |
| 对话历史 | 左侧管理多轮会话，支持新建与删除 |
| 调试面板 | 右侧调节相似度阈值与 Top-K，优化检索效果 |

## 技术栈

React · Vite · TypeScript · Ant Design · Less

## 启动

```bash
npm install
npm run dev
```

访问 http://localhost:3000 ，需先启动后端各服务（见项目根目录 README）。

## 目录结构

```
src/
├── components/
│   ├── chat/       对话消息、输入框、引用展示
│   ├── debug/      相似度阈值、Top-K 调试
│   ├── layout/     三栏布局（历史 / 对话 / 调试）
│   └── session/    会话列表与新建
├── hooks/          会话、聊天逻辑
├── services/       检索与生成 API
└── styles/         全局样式与主题变量
```

# ResuRAG

**个人信息智能问答系统** — 基于 RAG 的个人资料问答平台。

系统将个人文档（简历等）切块、向量化并存储，用户通过自然语言提问，系统自动检索相关内容并生成带引用来源的精准回答。

## 系统主题

ResuRAG（Resume + RAG）面向**个人信息查询场景**：

- 面试官 / HR 询问候选人经历、技能、项目
- 个人快速检索自己资料中的细节
- 基于真实文档片段回答，减少幻觉，每条回答可追溯引用来源

## 项目结构

```
ResuRAG/
├── backend/                 # 后端微服务
│   ├── doc_service/         # 文档切块 (8000)
│   ├── indexing_service/    # 向量索引 (8002)
│   ├── retrieval_service/   # 混合检索 (8003)
│   ├── generation_service/  # 流式生成 (8004)
│   ├── docker-compose.yml   # Milvus 基础设施
│   ├── requirements.txt
│   └── .env
└── frontend/                # 前端界面 (React + Vite + TS + Ant Design)
    └── README.md            # 前端说明
```

## 启动后端

```bash
cd backend
docker compose up -d
pip install -r requirements.txt
python doc_service/main.py
python indexing_service/main.py
python retrieval_service/main.py
python generation_service/main.py
```

## 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 http://localhost:5173 。

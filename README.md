# ResuRAG
个人结合RAG大模型问答系统

## 项目结构

```
ResuRAG/
├── backend/                 # 后端服务
│   ├── doc_service/         # 文档上传与切块 (8000)
│   ├── indexing_service/    # 向量索引 (8002)
│   ├── retrieval_service/   # 检索 (8003)
│   ├── generation_service/  # 生成 (8004)
│   ├── docker-compose.yml   # Milvus 基础设施
│   ├── requirements.txt
│   └── .env                 # 环境变量
└── frontend/                # 前端 (React + Vite + TS + Ant Design)
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

浏览器访问 http://localhost:5173 ，Vite 会将 API 请求代理到各后端服务。

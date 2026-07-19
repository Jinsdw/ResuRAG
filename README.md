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
└── frontend/                # 前端（待开发）
```

## 启动后端

```bash
cd backend
docker compose up -d
pip install -r requirements.txt
python -m doc_service.main
python indexing_service/main.py
python retrieval_service/main.py
python generation_service/main.py
```

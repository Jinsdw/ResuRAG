import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Config:
    BASE_ROOT = os.getenv("RAG_STORAGE_ROOT", str(PROJECT_ROOT / "rag_storage"))
    # Milvus配置
    MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT = int(os.getenv("MILVUS_PORT", 19530))
    MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "rag_chunks")
    
    # Embedding配置
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")  # 支持稠密+稀疏
    EMBEDDING_MODEL_DIR = os.getenv(
        "EMBEDDING_MODEL_DIR", str(PROJECT_ROOT / "models" / "bge-m3")
    )
    EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", 32))
    
    # 向量维度（BGE-M3默认输出1024维）
    DENSE_DIM = 1024
    
    # 服务端口
    PORT = int(os.getenv("INDEXING_PORT", 8002))
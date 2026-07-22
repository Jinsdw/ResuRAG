import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Config:
    # Milvus配置
    MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT = int(os.getenv("MILVUS_PORT", 19530))
    MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "rag_chunks")
    
    # Embedding配置（与索引服务保持一致）
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    EMBEDDING_MODEL_DIR = os.getenv(
        "EMBEDDING_MODEL_DIR", str(PROJECT_ROOT / "models" / "bge-m3")
    )
    
    # 检索参数
    DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", 10))
    MAX_TOP_K = 10  # Top-K 上限：最终采纳的条数
    CANDIDATE_COUNT = int(os.getenv("CANDIDATE_COUNT", 10))  # 每次从 Milvus 固定检索的候选数
    DENSE_WEIGHT = float(os.getenv("DENSE_WEIGHT", 0.7))   # 稠密向量权重
    SPARSE_WEIGHT = float(os.getenv("SPARSE_WEIGHT", 0.3)) # 稀疏向量权重
    
    # 服务端口
    PORT = int(os.getenv("RETRIEVAL_PORT", 8003))
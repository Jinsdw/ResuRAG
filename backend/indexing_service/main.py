import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Any
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config import Config
from core.embedder import get_embedder
from core.milvus_client import get_milvus_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"正在预加载 Embedding 模型: {Config.EMBEDDING_MODEL_DIR}")
    get_embedder()
    print("Embedding 模型已就绪")
    yield


app = FastAPI(title="索引服务 (Indexing Service)", version="1.0.0", lifespan=lifespan)

# ============ 数据模型 ============

class IndexRequest(BaseModel):
    file_uuid: str
    tenant_id: str = "default"
    chunk_dir: str  # 相对于 rag_storage 的切块目录，例如 3_chunks/default/<file_uuid>

class IndexResponse(BaseModel):
    status: str
    file_uuid: str
    total_chunks: int
    indexed_count: int

# ============ 核心业务 ============

def load_chunks_from_dir(chunk_dir: Path) -> List[Dict]:
    """从目录加载所有切块"""
    chunks = []
    for chunk_file in sorted(chunk_dir.glob("chunk_*.json")):
        with open(chunk_file, "r", encoding="utf-8") as f:
            chunks.append(json.load(f))
    return chunks

def resolve_chunk_dir(chunk_dir: str) -> Path:
    """解析切块目录，兼容 Windows 反斜杠和单文件路径。"""
    normalized = chunk_dir.replace("\\", "/").strip("/")
    full_path = Path(Config.BASE_ROOT) / normalized
    if full_path.is_file():
        full_path = full_path.parent
    return full_path


def index_file(file_uuid: str, chunk_dir: str, tenant_id: str = "default") -> Dict:
    """索引单个文件的所有切块"""
    full_chunk_dir = resolve_chunk_dir(chunk_dir)
    print(f"full_chunk_dir: {full_chunk_dir}")
    if not full_chunk_dir.exists():
        raise FileNotFoundError(f"切块目录不存在: {full_chunk_dir}")
    if not full_chunk_dir.is_dir():
        raise FileNotFoundError(f"chunk_dir 必须是目录路径: {full_chunk_dir}")
    
    # 1. 加载切块
    chunks = load_chunks_from_dir(full_chunk_dir)
    if not chunks:
        raise ValueError(f"未找到任何切块: {chunk_dir}")
    
    # 2. 获取embedder
    embedder = get_embedder()
    
    # 3. 批量生成向量
    contents = [c["content"] for c in chunks]
    dense_vectors = embedder.encode_dense(contents, batch_size=Config.EMBEDDING_BATCH_SIZE)
    sparse_vectors = embedder.encode_sparse(contents)
    
    # 4. 构建Milvus数据
    milvus_data = []
    for idx, (chunk, dense_vec, sparse_vec) in enumerate(zip(chunks, dense_vectors, sparse_vectors)):
        record = {
            "id": str(uuid.uuid4()),
            "chunk_id": chunk["chunk_id"],
            "file_uuid": file_uuid,
            "content": chunk["content"],
            "source_file_name": chunk.get("source_file_name", ""),
            "source_page": chunk.get("source_page", 0),
            "metadata": {
                "tenant": tenant_id,
                "original_metadata": chunk.get("metadata", {})
            },
            "dense_vector": dense_vec.tolist(),
            "sparse_vector": sparse_vec,
        }
        milvus_data.append(record)
    
    # 5. 先删除该文件已有的数据（如果存在）
    milvus = get_milvus_client()
    milvus.delete_by_file_uuid(file_uuid)
    
    # 6. 插入新数据
    ids = milvus.insert(milvus_data)
    
    return {
        "file_uuid": file_uuid,
        "total_chunks": len(chunks),
        "indexed_count": len(ids)
    }

# ============ API接口 ============

@app.post("/api/v1/index")
async def index_chunks(request: IndexRequest):
    """索引指定文件的切块"""
    try:
        result = index_file(
            file_uuid=request.file_uuid,
            chunk_dir=request.chunk_dir,
            tenant_id=request.tenant_id
        )
        return {"code": 0, "message": "success", "data": result}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"索引失败: {e!r}")

@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "service": "indexing_service"}

@app.get("/api/v1/collections")
async def get_collection_info():
    """查看Collection信息"""
    milvus = get_milvus_client()
    return {
        "collection": Config.MILVUS_COLLECTION,
        "count": milvus.collection.num_entities
    }

if __name__ == "__main__":
    import uvicorn
    print(f"🔍 索引服务启动中...")
    print(f"📦 Milvus: {Config.MILVUS_HOST}:{Config.MILVUS_PORT}")
    print(f"🧠 Embedding模型: {Config.EMBEDDING_MODEL}")
    print(f"🔗 访问地址: http://0.0.0.0:{Config.PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT, reload=True)
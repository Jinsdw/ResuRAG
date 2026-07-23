from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from config import Config
from core.embedder import get_embedder
from core.retriever import get_retriever
from core.reranker import get_reranker


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"正在预加载 Embedding 模型: {Config.EMBEDDING_MODEL_DIR}")
    get_embedder()
    get_reranker()
    get_retriever()
    print("检索服务就绪")
    yield


app = FastAPI(title="检索服务 (Retrieval Service)", version="1.0.0", lifespan=lifespan)

# ============ 数据模型 ============

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = Config.DEFAULT_TOP_K
    dense_weight: Optional[float] = Config.DENSE_WEIGHT
    similarity_threshold: Optional[float] = 0.0
    filter_file_uuid: Optional[str] = None  # 可选：限定某个 file_uuid，不填则搜索全部
    rerank: Optional[bool] = True  # 是否启用重排序

class SearchResult(BaseModel):
    chunk_id: str
    content: str
    file_uuid: str
    source_file_name: str
    source_page: int
    score: float
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchResult]

# ============ API接口 ============

def build_file_uuid_filter(filter_file_uuid: Optional[str]) -> Optional[str]:
    """忽略空值和 Swagger 默认占位符。"""
    if not filter_file_uuid:
        return None
    value = filter_file_uuid.strip()
    if not value or value.lower() == "string":
        return None
    return f"file_uuid == '{value}'"


@app.post("/api/v1/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """执行混合检索：召回 20 条候选 -> 重排序 -> 按 top_k 采纳"""
    try:
        retriever = get_retriever()
        filter_expr = build_file_uuid_filter(request.filter_file_uuid)
        
        top_k = request.top_k or Config.DEFAULT_TOP_K
        
        # 执行检索
        results = retriever.hybrid_search(
            query=request.query,
            top_k=top_k,
            dense_weight=request.dense_weight,
            filter_expr=filter_expr,
            similarity_threshold=request.similarity_threshold or 0.0,
            rerank=request.rerank if request.rerank is not None else True,
        )
        
        return SearchResponse(
            query=request.query,
            total=len(results),
            results=[SearchResult(**r) for r in results]
        )
    
    except Exception as e:
        raise HTTPException(500, f"检索失败: {str(e)}")

@app.post("/api/v1/search/dense")
async def search_dense(request: SearchRequest):
    """仅使用稠密向量检索（语义匹配）：召回 20 条候选 -> 排序 -> 按 top_k 采纳"""
    retriever = get_retriever()
    dense_vector = retriever.embedder.encode_query_vector(request.query)
    
    filter_expr = build_file_uuid_filter(request.filter_file_uuid)
    top_k = request.top_k or Config.DEFAULT_TOP_K
    
    # 召回 candidate_count 条候选
    results = retriever.milvus.search_dense(
        dense_vector, 
        top_k=Config.CANDIDATE_COUNT, 
        filter_expr=filter_expr
    )
    
    # 按分数排序后取 top_k 条
    threshold = request.similarity_threshold or 0.0
    all_hits = []
    if results and len(results) > 0:
        all_hits = sorted(results[0], key=lambda h: h.score, reverse=True)
    
    formatted = []
    for hit in all_hits[:top_k]:
        score = hit.score
        if threshold > 0 and score < threshold:
            continue
        formatted.append({
            "chunk_id": hit.entity.get("chunk_id", ""),
            "content": hit.entity.get("content", ""),
            "file_uuid": hit.entity.get("file_uuid", ""),
            "source_file_name": hit.entity.get("source_file_name", ""),
            "source_page": hit.entity.get("source_page", 0),
            "score": score,
            "metadata": hit.entity.get("metadata", {})
        })
    
    return {
        "query": request.query,
        "total": len(formatted),
        "results": formatted
    }

@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "service": "retrieval_service"}

if __name__ == "__main__":
    import uvicorn
    print("检索服务启动中...")
    print(f"Milvus: {Config.MILVUS_HOST}:{Config.MILVUS_PORT}")
    print(f"Embedding模型: {Config.EMBEDDING_MODEL}")
    print(f"访问地址: http://0.0.0.0:{Config.PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT, reload=True)
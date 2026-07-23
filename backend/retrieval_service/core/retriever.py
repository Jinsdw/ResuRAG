import logging
from typing import Any, Dict, List, Optional

from config import Config
from .embedder import encode_sparse_text, get_embedder
from .milvus_client import get_milvus_client
from .reranker import get_reranker

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(self):
        self.embedder = get_embedder()
        self.milvus = get_milvus_client()
        self.reranker = get_reranker()
        self.candidate_count = Config.CANDIDATE_COUNT

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        dense_weight: float = 0.7,
        filter_expr: Optional[str] = None,
        similarity_threshold: float = 0.0,
        rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []

        dense_vector = self.embedder.encode_query_vector(query)
        sparse_vector = encode_sparse_text(query)

        # 1. 从 Milvus 召回 candidate_count 条候选
        candidate_n = self.candidate_count
        dense_results = self.milvus.search_dense(
            dense_vector, top_k=candidate_n, filter_expr=filter_expr
        )
        sparse_results = []
        if sparse_vector:
            try:
                sparse_results = self.milvus.search_sparse(
                    sparse_vector, top_k=candidate_n, filter_expr=filter_expr
                )
            except Exception as exc:
                logger.warning("稀疏检索失败，降级为仅稠密检索: %r", exc)

        # 2. 合并 + 按混合分数排序
        merged = self._merge_results(dense_results, sparse_results, dense_weight)
        candidates = sorted(merged.values(), key=lambda x: x["score"], reverse=True)

        # 3. 相似度阈值过滤
        if similarity_threshold > 0:
            candidates = [
                item for item in candidates if item["score"] >= similarity_threshold
            ]

        if not candidates:
            return []

        # 4. 重排序（可选）
        if rerank:
            candidates = self.reranker.rerank(query, candidates, top_k=None)
            # 用 rerank_score 替换 score，保持接口一致性
            for item in candidates:
                item["score"] = item.get("rerank_score", item.get("score", 0.0))

        # 5. 按 top_k 截取最终采用条数
        return candidates[:top_k]

    def _extract_hit(self, hit) -> Dict[str, Any]:
        entity = hit.entity
        return {
            "chunk_id": entity.get("chunk_id", ""),
            "content": entity.get("content", ""),
            "file_uuid": entity.get("file_uuid", ""),
            "source_file_name": entity.get("source_file_name", ""),
            "source_page": entity.get("source_page", 0) or 0,
            "metadata": entity.get("metadata") or {},
        }

    def _merge_results(self, dense_results, sparse_results, dense_weight: float) -> Dict[str, Dict]:
        merged = {}

        if dense_results and len(dense_results) > 0:
            for hit in dense_results[0]:
                item = self._extract_hit(hit)
                chunk_id = item["chunk_id"]
                if not chunk_id:
                    continue
                score = hit.score * dense_weight
                merged[chunk_id] = {
                    **item,
                    "score": 0.0,
                    "dense_score": score,
                    "sparse_score": 0.0,
                }

        if sparse_results and len(sparse_results) > 0:
            sparse_weight = 1.0 - dense_weight
            for hit in sparse_results[0]:
                item = self._extract_hit(hit)
                chunk_id = item["chunk_id"]
                if not chunk_id:
                    continue
                score = hit.score * sparse_weight
                if chunk_id not in merged:
                    merged[chunk_id] = {
                        **item,
                        "score": 0.0,
                        "dense_score": 0.0,
                        "sparse_score": score,
                    }
                else:
                    merged[chunk_id]["sparse_score"] = score

        for item in merged.values():
            item["score"] = item.get("dense_score", 0.0) + item.get("sparse_score", 0.0)
            item.pop("dense_score", None)
            item.pop("sparse_score", None)

        return merged


_retriever = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever

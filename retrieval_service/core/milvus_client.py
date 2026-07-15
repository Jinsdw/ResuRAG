from pymilvus import connections, Collection
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MilvusClient:
    def __init__(self, host: str, port: int, collection_name: str):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.collection = None
        self._connect()
        self._load_collection()
    
    def _connect(self):
        connections.connect(alias="default", host=self.host, port=self.port)
        logger.info(f"Connected to Milvus at {self.host}:{self.port}")
    
    def _load_collection(self):
        self.collection = Collection(self.collection_name)
        self.collection.load()
        logger.info(f"Collection '{self.collection_name}' loaded")
    
    def search_dense(self, query_vector: List[float], top_k: int = 10, filter_expr: str = None):
        """稠密向量检索"""
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        return self._search(query_vector, "dense_vector", search_params, top_k, filter_expr)
    
    def search_sparse(self, query_vector: Dict[int, float], top_k: int = 10, filter_expr: str = None):
        """稀疏向量检索（关键词匹配）"""
        search_params = {"metric_type": "IP"}
        return self._search(query_vector, "sparse_vector", search_params, top_k, filter_expr)
    
    def _search(self, query_vector, vector_field, search_params, top_k, filter_expr):
        self.collection.load()
        results = self.collection.search(
            data=[query_vector],
            anns_field=vector_field,
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["chunk_id", "file_uuid", "content", "source_file_name", "source_page", "metadata"]
        )
        return results

_milvus = None
def get_milvus_client() -> MilvusClient:
    global _milvus
    if _milvus is None:
        from config import Config
        _milvus = MilvusClient(
            host=Config.MILVUS_HOST,
            port=Config.MILVUS_PORT,
            collection_name=Config.MILVUS_COLLECTION
        )
    return _milvus
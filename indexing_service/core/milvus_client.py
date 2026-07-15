from pymilvus import (
    connections, Collection, CollectionSchema, 
    FieldSchema, DataType, utility
)
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
        self._ensure_collection()
    
    def _connect(self):
        """连接Milvus"""
        connections.connect(
            alias="default",
            host=self.host,
            port=self.port
        )
        logger.info(f"Connected to Milvus at {self.host}:{self.port}")
    
    def _ensure_collection(self):
        """确保Collection存在，不存在则创建"""
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' already exists")
        else:
            self._create_collection()
    
    def _create_collection(self):
        """创建Collection（支持多向量）"""
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="file_uuid", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="source_file_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="source_page", dtype=DataType.INT64),
            FieldSchema(name="metadata", dtype=DataType.JSON),
            # 稠密向量（1024维）
            FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
            # 稀疏向量（用于BM25风格检索）
            FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
        ]
        
        schema = CollectionSchema(fields, description="RAG文档切块存储")
        self.collection = Collection(self.collection_name, schema)
        
        # 创建索引
        self._create_indexes()
        logger.info(f"Collection '{self.collection_name}' created with indexes")
    
    def _create_indexes(self):
        """创建向量索引"""
        # 稠密向量索引（IVF_FLAT，平衡速度和精度）
        dense_index = {
            "index_type": "IVF_FLAT",
            "metric_type": "IP",  # 内积（等价于余弦相似度，因为向量已归一化）
            "params": {"nlist": 128}
        }
        self.collection.create_index("dense_vector", dense_index)
        
        # 稀疏向量索引
        sparse_index = {
            "index_type": "SPARSE_INVERTED_INDEX",
            "metric_type": "IP"
        }
        self.collection.create_index("sparse_vector", sparse_index)
        
        self.collection.load()
    
    def insert(self, data: List[Dict[str, Any]]) -> List[str]:
        """插入数据，返回插入的ID列表"""
        if not data:
            return []

        rows = [
            {
                "id": d["id"],
                "chunk_id": d["chunk_id"],
                "file_uuid": d["file_uuid"],
                "content": d["content"],
                "source_file_name": d["source_file_name"],
                "source_page": d.get("source_page", 0),
                "metadata": d.get("metadata", {}),
                "dense_vector": d["dense_vector"],
                "sparse_vector": d["sparse_vector"],
            }
            for d in data
        ]

        self.collection.insert(rows)
        self.collection.flush()

        return [d["id"] for d in data]
    
    def search_dense(self, query_vector: List[float], top_k: int = 10, filter_expr: str = None):
        """稠密向量检索"""
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        return self._search(query_vector, "dense_vector", search_params, top_k, filter_expr)
    
    def search_sparse(self, query_vector: Dict[int, float], top_k: int = 10, filter_expr: str = None):
        """稀疏向量检索"""
        search_params = {"metric_type": "IP"}
        return self._search(query_vector, "sparse_vector", search_params, top_k, filter_expr)
    
    def _search(self, query_vector, vector_field, search_params, top_k, filter_expr):
        """通用检索方法"""
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
    
    def delete_by_file_uuid(self, file_uuid: str):
        """删除某个文件的所有切块"""
        expr = f"file_uuid == '{file_uuid}'"
        self.collection.delete(expr)
        self.collection.flush()
        logger.info(f"Deleted all chunks for file: {file_uuid}")

# 全局单例
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
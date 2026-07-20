from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)

DENSE_DIM = 1024


class MilvusClient:
    def __init__(self, host: str, port: int, collection_name: str):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.collection = None
        self._connect()
        self._ensure_collection()

    def _connect(self):
        connections.connect(alias="default", host=self.host, port=self.port)
        logger.info(f"Connected to Milvus at {self.host}:{self.port}")

    def _ensure_collection(self):
        """确保 Collection 存在，不存在则自动创建（与索引服务 schema 一致）"""
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            self.collection.load()
            logger.info(f"Collection '{self.collection_name}' loaded")
            return

        logger.warning(
            f"Collection '{self.collection_name}' not found, creating empty collection"
        )
        self._create_collection()

    def _create_collection(self):
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="file_uuid", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="source_file_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="source_page", dtype=DataType.INT64),
            FieldSchema(name="metadata", dtype=DataType.JSON),
            FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=DENSE_DIM),
            FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
        ]

        schema = CollectionSchema(fields, description="RAG文档切块存储")
        self.collection = Collection(self.collection_name, schema)
        self._create_indexes()
        logger.info(f"Collection '{self.collection_name}' created with indexes")

    def _create_indexes(self):
        dense_index = {
            "index_type": "IVF_FLAT",
            "metric_type": "IP",
            "params": {"nlist": 128},
        }
        self.collection.create_index("dense_vector", dense_index)

        sparse_index = {
            "index_type": "SPARSE_INVERTED_INDEX",
            "metric_type": "IP",
        }
        self.collection.create_index("sparse_vector", sparse_index)
        self.collection.load()

    def search_dense(self, query_vector: List[float], top_k: int = 10, filter_expr: str = None):
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        return self._search(query_vector, "dense_vector", search_params, top_k, filter_expr)

    def search_sparse(self, query_vector: Dict[int, float], top_k: int = 10, filter_expr: str = None):
        search_params = {"metric_type": "IP"}
        return self._search(query_vector, "sparse_vector", search_params, top_k, filter_expr)

    def _search(self, query_vector, vector_field, search_params, top_k, filter_expr):
        self.collection.load()
        return self.collection.search(
            data=[query_vector],
            anns_field=vector_field,
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=[
                "chunk_id",
                "file_uuid",
                "content",
                "source_file_name",
                "source_page",
                "metadata",
            ],
        )


_milvus = None


def get_milvus_client() -> MilvusClient:
    global _milvus
    if _milvus is None:
        from config import Config

        _milvus = MilvusClient(
            host=Config.MILVUS_HOST,
            port=Config.MILVUS_PORT,
            collection_name=Config.MILVUS_COLLECTION,
        )
    return _milvus

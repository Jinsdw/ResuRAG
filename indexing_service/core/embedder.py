import logging
import threading
from collections import Counter
from pathlib import Path
from typing import Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_embedder = None


def _is_model_ready(model_dir: Path) -> bool:
    if not model_dir.is_dir():
        return False
    has_config = (model_dir / "config.json").exists()
    has_weights = any(model_dir.glob("*.safetensors")) or (
        model_dir / "pytorch_model.bin"
    ).exists()
    return has_config and has_weights


def _ensure_local_model(model_name: str, model_dir: Path) -> str:
    if _is_model_ready(model_dir):
        logger.info("使用本地 Embedding 模型: %s", model_dir)
        return str(model_dir)

    logger.info("本地模型不存在，开始下载 %s -> %s", model_name, model_dir)
    model_dir.parent.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer(model_name)
    model.save(str(model_dir))
    logger.info("模型已保存到本地: %s", model_dir)
    return str(model_dir)


class BGEEmbedder:
    """BGE-M3 多向量编码器（支持稠密+稀疏）"""

    def __init__(self, model_name: str, model_dir: Path):
        model_path = _ensure_local_model(model_name, model_dir)
        self.model = SentenceTransformer(model_path)
        self.dim = 1024

    def encode_dense(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings

    def encode_sparse(self, texts: List[str]) -> List[Dict[int, float]]:
        sparse_vectors = []
        for text in texts:
            tokens = list(text)
            token_counts = Counter(tokens)
            total_tokens = len(tokens)

            sparse_vec = {}
            for token, count in token_counts.items():
                if len(token.strip()) == 0:
                    continue
                weight = count / total_tokens
                sparse_vec[hash(token) % 1000000] = weight

            sparse_vectors.append(sparse_vec)

        return sparse_vectors

    def get_dense_dim(self) -> int:
        return self.dim


def get_embedder() -> BGEEmbedder:
    global _embedder
    if _embedder is None:
        with _lock:
            if _embedder is None:
                from config import Config

                _embedder = BGEEmbedder(
                    Config.EMBEDDING_MODEL,
                    Path(Config.EMBEDDING_MODEL_DIR),
                )
    return _embedder

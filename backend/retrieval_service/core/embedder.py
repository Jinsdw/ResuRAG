import hashlib
import logging
import re
import threading
from collections import Counter
from pathlib import Path
from typing import Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_embedder = None

# 中文字符正则
_CN_RE = re.compile(r"[\u4e00-\u9fff]+")
# 英文/数字词正则
_EN_RE = re.compile(r"[a-zA-Z0-9]+")


def _tokenize(text: str) -> List[str]:
    """混合分词：中文 bigram + 英文整词，无需外部依赖。

    "项目经历" → ["项目", "目经", "经历", "项", "目", "经", "历"]
    "RAG system" → ["rag", "system"]
    """
    tokens = []

    # 1. 中文序列：提取 bigram + 单字
    for cn_match in _CN_RE.finditer(text):
        cn_seq = cn_match.group()
        # bigram（权重更高，语义更强）
        for i in range(len(cn_seq) - 1):
            tokens.append(cn_seq[i : i + 2])
        # 单字（作为补充）
        for ch in cn_seq:
            tokens.append(ch)

    # 2. 英文/数字：整词
    for en_match in _EN_RE.finditer(text):
        tokens.append(en_match.group().lower())

    return tokens


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


def token_to_id(token: str) -> int:
    """跨进程稳定的 token id，避免 Python 内置 hash 随机化。"""
    digest = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(digest, 16) % 1_000_000


def encode_sparse_text(text: str) -> Dict[int, float]:
    """对文本进行分词并生成稀疏向量（中文 bigram + 英文整词）。"""
    tokens = _tokenize(text)
    if not tokens:
        return {}

    token_counts = Counter(tokens)
    total = len(tokens)
    sparse_vec = {}
    for token, count in token_counts.items():
        if not token.strip():
            continue
        # bigram 权重加倍（比单字更有区分度）
        weight = count / total
        if len(token) >= 2:
            weight *= 2.0
        sparse_vec[token_to_id(token)] = weight
    return sparse_vec


class BGEEmbedder:
    def __init__(self, model_name: str, model_dir: Path):
        model_path = _ensure_local_model(model_name, model_dir)
        self.model = SentenceTransformer(model_path)
        self.dim = 1024

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings

    def encode_query_vector(self, query: str) -> List[float]:
        # BGE-M3 查询前缀：提升检索语义匹配效果
        prefixed_query = f"Represent this sentence for searching relevant passages: {query}"
        vector = self.encode([prefixed_query])[0]
        return vector.astype(float).tolist()


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

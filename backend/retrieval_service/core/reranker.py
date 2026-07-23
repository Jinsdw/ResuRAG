import logging
import os
from typing import List, Dict, Any, Optional

from config import Config

logger = logging.getLogger(__name__)


class Reranker:
    """基于 CrossEncoder 的段落重排序器（BGE-Reranker）。

    用法：
        reranker = get_reranker()
        scored = reranker.rerank("query", [{"content": "..."}, ...])
        # scored 按重排序分数降序排列
    """

    def __init__(self):
        self.model = None
        self.model_name = Config.RERANKER_MODEL
        self.model_dir = Config.RERANKER_MODEL_DIR
        self._load()

    def _load(self):
        """加载 CrossEncoder 模型：本地有则直接用，无则下载并缓存到本地。"""
        try:
            from sentence_transformers import CrossEncoder

            local_dir = self.model_dir

            # 1. 检查本地模型目录是否存在且包含 config.json
            if os.path.isdir(local_dir) and os.path.isfile(
                os.path.join(local_dir, "config.json")
            ):
                model_path = local_dir
                logger.info("检测到本地重排序模型，直接加载: %s", local_dir)
            else:
                # 2. 本地不存在，先下载到缓存目录再保存到本地
                logger.info(
                    "本地未找到重排序模型，正在从 HuggingFace 下载: %s",
                    self.model_name,
                )
                logger.info("下载完成后将保存到: %s", local_dir)
                os.makedirs(local_dir, exist_ok=True)
                # sentence_transformers 支持 cache_folder 参数
                # 先用远程名称加载（自动下载到默认缓存）
                tmp_model = CrossEncoder(self.model_name, max_length=512)
                # 保存到本地目录供下次使用
                tmp_model.save(local_dir)
                del tmp_model
                model_path = local_dir
                logger.info("重排序模型已下载并保存到: %s", local_dir)

            # 3. 从本地目录加载模型
            logger.info("正在加载重排序模型: %s", model_path)
            self.model = CrossEncoder(model_path, max_length=512)
            logger.info("重排序模型加载完成")
        except Exception as exc:
            logger.warning(
                "重排序模型加载失败 (%s)，降级为不重排序。错误: %s",
                self.model_name,
                exc,
            )
            self.model = None

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """对召回候选进行重排序，返回按新分数降序排列的结果。

        Args:
            query: 用户查询。
            documents: 召回候选列表，每项至少包含 "content" 键。
            top_k: 重排序后截取条数，None 则返回全部。

        Returns:
            添加了 "rerank_score" 字段并按该字段降序排列的文档列表。
        """
        if not documents:
            return []

        if self.model is None:
            # 模型未加载，直接返回原始顺序（保留原始 score）
            for doc in documents:
                doc["rerank_score"] = doc.get("score", 0.0)
            return documents[:top_k] if top_k else documents

        # 构造 [[query, passage], ...] 输入对
        pairs = [[query, doc.get("content", "")] for doc in documents]

        try:
            scores = self.model.predict(pairs, show_progress_bar=False)
        except Exception as exc:
            logger.warning("重排序推理失败，降级为原始分数: %s", exc)
            for doc in documents:
                doc["rerank_score"] = doc.get("score", 0.0)
            return documents[:top_k] if top_k else documents

        # 附加 rerank_score 并排序
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)

        sorted_docs = sorted(
            documents, key=lambda x: x["rerank_score"], reverse=True
        )
        return sorted_docs[:top_k] if top_k else sorted_docs


_reranker: Optional[Reranker] = None


def get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker

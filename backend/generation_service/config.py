import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

class Config:
    # ========== LLM配置 ==========
    
    # OpenAI配置
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
    ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "GLM-4.6V-FlashX")
    
    # ========== 检索服务 ==========
    RETRIEVAL_SERVICE_URL = os.getenv("RETRIEVAL_SERVICE_URL", "http://localhost:8003")
    RETRIEVAL_TIMEOUT = float(os.getenv("RETRIEVAL_TIMEOUT", 30.0))
    
    # ========== 服务配置 ==========
    PORT = int(os.getenv("GENERATION_PORT", 8004))
    SESSION_DB_PATH = Path(
        os.getenv(
            "SESSION_DB_PATH",
            str(Path(__file__).resolve().parent / "data" / "sessions.db"),
        )
    )
    
    # ========== 候选人身份（生成回答时的人设） ==========
    CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "耿闯")

    # ========== 猜你想问参考文档 ==========
    RESURAG_ROOT = PROJECT_ROOT.parent
    QA_DOCUMENT_PATH = os.getenv(
        "QA_DOCUMENT_PATH",
        str(RESURAG_ROOT / "docs" / "项目全景文档.md"),
    )
    RESUME_DOCUMENT_PATH = os.getenv(
        "RESUME_DOCUMENT_PATH",
        str(RESURAG_ROOT / "docs" / "耿闯-AI应用开发工程师.md"),
    )
    SUGGESTION_DOC_MAX_CHARS = int(os.getenv("SUGGESTION_DOC_MAX_CHARS", "6000"))
    
    # ========== 幻觉检测 ==========
    ENABLE_FAITHFULNESS_CHECK = os.getenv("ENABLE_FAITHFULNESS_CHECK", "true").lower() == "true"
    FAITHFULNESS_MODEL = os.getenv("FAITHFULNESS_MODEL", "microsoft/deberta-v3-base-mnli")
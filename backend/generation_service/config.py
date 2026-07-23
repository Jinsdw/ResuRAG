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

    # ========== 猜你想问 / 生成参考文档 ==========
    RESURAG_ROOT = PROJECT_ROOT.parent
    DOCS_DIR = RESURAG_ROOT / "docs"
    # information.md：项目全景 + QA 问题池；gc-resume.md：简历
    INFORMATION_DOCUMENT_PATH = os.getenv(
        "INFORMATION_DOCUMENT_PATH",
        os.getenv(
            "QA_DOCUMENT_PATH",
            str(DOCS_DIR / "information.md"),
        ),
    )
    RESUME_DOCUMENT_PATH = os.getenv(
        "RESUME_DOCUMENT_PATH",
        str(DOCS_DIR / "gc-resume.md"),
    )
    SUGGESTION_DOC_MAX_CHARS = int(os.getenv("SUGGESTION_DOC_MAX_CHARS", "6000"))
    # 生成回答时注入 system 的参考文档总字符上限（两文件平分）
    GENERATION_REFERENCE_DOC_MAX_CHARS = int(
        os.getenv("GENERATION_REFERENCE_DOC_MAX_CHARS", "12000")
    )
    ENABLE_ANSWER_SELF_CHECK = (
        os.getenv("ENABLE_ANSWER_SELF_CHECK", "true").lower() == "true"
    )
    
    # ========== 幻觉检测 ==========
    ENABLE_FAITHFULNESS_CHECK = os.getenv("ENABLE_FAITHFULNESS_CHECK", "true").lower() == "true"
    FAITHFULNESS_MODEL = os.getenv("FAITHFULNESS_MODEL", "microsoft/deberta-v3-base-mnli")
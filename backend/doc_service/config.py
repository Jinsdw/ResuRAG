import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Config:
    BASE_ROOT = os.getenv("RAG_STORAGE_ROOT", str(PROJECT_ROOT / "rag_storage"))

    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 128

    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
    MAX_FILE_SIZE = 50 * 1024 * 1024

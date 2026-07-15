class Config:
    BASE_ROOT = "./rag_storage"

    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 128

    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
    MAX_FILE_SIZE = 50 * 1024 * 1024

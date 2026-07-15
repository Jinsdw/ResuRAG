from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredPDFLoader,
    UnstructuredWordDocumentLoader,
)


def load_documents(file_path: Path, file_ext: str) -> List[Document]:
    if file_ext in {".txt", ".md"}:
        loader = TextLoader(str(file_path), encoding="utf-8")
        return loader.load()
    if file_ext == ".pdf":
        loader = UnstructuredPDFLoader(str(file_path))
        return loader.load()
    if file_ext == ".docx":
        loader = UnstructuredWordDocumentLoader(str(file_path))
        return loader.load()
    raise ValueError(f"不支持的文件类型: {file_ext}")

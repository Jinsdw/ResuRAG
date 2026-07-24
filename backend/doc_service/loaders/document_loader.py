from pathlib import Path
from typing import List

from langchain_core.documents import Document


def load_documents(file_path: Path, file_ext: str) -> List[Document]:
    if file_ext == ".md":
        text = file_path.read_text(encoding="utf-8")
        return [Document(page_content=text, metadata={"source": str(file_path)})]
    raise ValueError(f"不支持的文件类型: {file_ext}")

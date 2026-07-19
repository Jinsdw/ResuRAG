import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

import aiofiles
from langchain_text_splitters import RecursiveCharacterTextSplitter

from doc_service.config import Config
from doc_service.core.utils import compute_md5, sanitize_filename
from doc_service.loaders import load_documents


class RAGIngestionPipeline:
    def __init__(self, base_root: str):
        self.base = Path(base_root)
        self._init_directories()

    def _init_directories(self):
        layers = ["1_raw", "2_parsed", "3_chunks", "4_index"]
        for layer in layers:
            (self.base / layer).mkdir(parents=True, exist_ok=True)

        registry_path = self.base / "file_registry.json"
        if not registry_path.exists():
            with open(registry_path, "w") as f:
                json.dump([], f)

    def _get_registry(self) -> List[Dict]:
        with open(self.base / "file_registry.json", "r") as f:
            return json.load(f)

    def _update_registry(self, entry: Dict):
        registry = self._get_registry()
        registry.append(entry)
        with open(self.base / "file_registry.json", "w") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

    async def upload_and_chunk(
        self,
        file_bytes: bytes,
        original_filename: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        file_ext = Path(original_filename).suffix.lower()
        if file_ext not in Config.ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")

        if len(file_bytes) > Config.MAX_FILE_SIZE:
            raise ValueError(
                f"文件过大，最大支持 {Config.MAX_FILE_SIZE // 1024 // 1024}MB"
            )

        file_uuid = str(uuid4()).replace("-", "")
        md5_hash = compute_md5(file_bytes)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = sanitize_filename(original_filename)
        final_filename = f"{timestamp}_{file_uuid}_{md5_hash}_{safe_name}"

        raw_dir = (
            self.base
            / "1_raw"
            / tenant_id
            / file_ext[1:]
            / datetime.now().strftime("%Y-%m-%d")
        )
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_file_path = raw_dir / final_filename

        async with aiofiles.open(raw_file_path, "wb") as f:
            await f.write(file_bytes)

        try:
            documents = load_documents(raw_file_path, file_ext)
        except Exception as e:
            raise RuntimeError(f"文档解析失败: {str(e)}")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)

        chunk_dir = self.base / "3_chunks" / tenant_id / file_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        chunk_metas = []
        for idx, doc in enumerate(chunks):
            chunk_id = f"{file_uuid}_c{idx:04d}"
            chunk_data = {
                "chunk_id": chunk_id,
                "source_file_uuid": file_uuid,
                "source_file_name": original_filename,
                "source_page": doc.metadata.get("page_number", 0),
                "content": doc.page_content,
                "content_length": len(doc.page_content),
                "metadata": doc.metadata,
                "created_at": datetime.now().isoformat(),
            }
            chunk_file = chunk_dir / f"chunk_{idx:04d}.json"
            with open(chunk_file, "w", encoding="utf-8") as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=2)

            chunk_metas.append(
                {
                    "chunk_id": chunk_id,
                    "chunk_file": str(chunk_file.relative_to(self.base)),
                }
            )

        manifest = {
            "file_uuid": file_uuid,
            "original_name": original_filename,
            "chunk_strategy": {
                "chunk_size": Config.CHUNK_SIZE,
                "chunk_overlap": Config.CHUNK_OVERLAP,
                "splitter": "RecursiveCharacterTextSplitter",
            },
            "total_chunks": len(chunks),
            "chunks": chunk_metas,
            "raw_file_path": str(raw_file_path.relative_to(self.base)),
            "created_at": datetime.now().isoformat(),
        }
        with open(chunk_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        registry_entry = {
            "file_uuid": file_uuid,
            "original_name": original_filename,
            "file_path": str(raw_file_path.relative_to(self.base)),
            "md5": md5_hash,
            "total_chunks": len(chunks),
            "upload_time": timestamp,
            "tenant": tenant_id,
            "status": "success",
        }
        self._update_registry(registry_entry)

        return {
            "file_uuid": file_uuid,
            "original_name": original_filename,
            "total_chunks": len(chunks),
            "chunk_dir": str(chunk_dir.relative_to(self.base)),
            "manifest": manifest,
        }

import os
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import aiofiles

# 切割器：推荐使用LangChain的递归切割器
from langchain_text_splitters import RecursiveCharacterTextSplitter
# 解析器：按文件类型选择对应 Loader
from langchain_core.documents import Document

app = FastAPI(title="RAG 上传切割服务")

# ==================== 配置区（你可以按需修改） ====================
class Config:
    # 根目录（推荐使用环境变量，这里写死便于演示）
    BASE_ROOT = "./rag_storage"
    
    # 切割参数（工业级黄金比例）
    CHUNK_SIZE = 512          # 每块最大字符数
    CHUNK_OVERLAP = 128       # 重叠字符数（保证语义连贯）
    
    # 支持的文件类型
    ALLOWED_EXTENSIONS = {".md"}
    
    # 最大文件大小（50MB）
    MAX_FILE_SIZE = 50 * 1024 * 1024

# ==================== 核心类：上传切割管道 ====================
class RAGIngestionPipeline:
    def __init__(self, base_root: str):
        self.base = Path(base_root)
        self._init_directories()
    
    def _init_directories(self):
        """创建四层目录结构"""
        layers = ["1_raw", "2_parsed", "3_chunks", "4_index"]
        for layer in layers:
            (self.base / layer).mkdir(parents=True, exist_ok=True)
        
        # 全局注册表（用JSON文件模拟数据库）
        registry_path = self.base / "file_registry.json"
        if not registry_path.exists():
            with open(registry_path, "w") as f:
                json.dump([], f)
    
    def _get_registry(self) -> List[Dict]:
        """读取注册表"""
        with open(self.base / "file_registry.json", "r") as f:
            return json.load(f)
    
    def _update_registry(self, entry: Dict):
        """更新注册表"""
        registry = self._get_registry()
        registry.append(entry)
        with open(self.base / "file_registry.json", "w") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    
    def _compute_md5(self, file_bytes: bytes) -> str:
        """计算文件MD5（用于去重）"""
        return hashlib.md5(file_bytes).hexdigest()[:8]
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名（移除特殊字符）"""
        import re
        name = re.sub(r'[^\w\-_.]', '_', filename)
        return name[:30]  # 截断过长文件名
    
    def _load_documents(self, file_path: Path, file_ext: str) -> List[Document]:
        """根据文件类型选择解析器"""
        if file_ext == ".md":
            text = file_path.read_text(encoding="utf-8")
            return [Document(page_content=text, metadata={"source": str(file_path)})]
        raise ValueError(f"不支持的文件类型: {file_ext}")
    
    async def upload_and_chunk(
        self, 
        file_bytes: bytes, 
        original_filename: str,
        tenant_id: str = "default"
    ) -> Dict[str, Any]:
        """
        主流程：上传 -> 保存原始文件 -> 解析 -> 切割 -> 存储切割结果
        """
        # 1. 文件校验
        file_ext = Path(original_filename).suffix.lower()
        if file_ext not in Config.ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")
        
        if len(file_bytes) > Config.MAX_FILE_SIZE:
            raise ValueError(f"文件过大，最大支持 {Config.MAX_FILE_SIZE // 1024 // 1024}MB")
        
        # 2. 生成唯一标识
        file_uuid = str(uuid4()).replace("-", "")
        md5_hash = self._compute_md5(file_bytes)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self._sanitize_filename(original_filename)
        # 最终文件名：时间戳_UUID_MD5_原文件名
        final_filename = f"{timestamp}_{file_uuid}_{md5_hash}_{safe_name}"
        
        # 3. 保存原始文件到 1_raw
        raw_dir = self.base / "1_raw" / tenant_id / file_ext[1:] / datetime.now().strftime("%Y-%m-%d")
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_file_path = raw_dir / final_filename
        
        # 异步写入文件
        async with aiofiles.open(raw_file_path, "wb") as f:
            await f.write(file_bytes)
        
        # 4. 解析文档（按文件类型选择解析器）
        try:
            documents = self._load_documents(raw_file_path, file_ext)
        except Exception as e:
            raise RuntimeError(f"文档解析失败: {str(e)}")
        
        # 5. 切割文档
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)
        
        # 6. 保存切割结果到 3_chunks
        chunk_dir = self.base / "3_chunks" / tenant_id / file_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)
        
        chunk_metas = []
        for idx, doc in enumerate(chunks):
            chunk_id = f"{file_uuid}_c{idx:04d}"
            chunk_data = {
                "chunk_id": chunk_id,
                "source_file_uuid": file_uuid,
                "source_file_name": original_filename,
                "source_page": doc.metadata.get("page_number", 0),  # 页码信息
                "content": doc.page_content,
                "content_length": len(doc.page_content),
                "metadata": doc.metadata,  # 保留所有元数据
                "created_at": datetime.now().isoformat()
            }
            # 保存单个chunk为JSON文件
            chunk_file = chunk_dir / f"chunk_{idx:04d}.json"
            with open(chunk_file, "w", encoding="utf-8") as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=2)
            
            chunk_metas.append({
                "chunk_id": chunk_id,
                "chunk_file": str(chunk_file.relative_to(self.base))
            })
        
        # 7. 保存Manifest（切割策略记录）
        manifest = {
            "file_uuid": file_uuid,
            "original_name": original_filename,
            "chunk_strategy": {
                "chunk_size": Config.CHUNK_SIZE,
                "chunk_overlap": Config.CHUNK_OVERLAP,
                "splitter": "RecursiveCharacterTextSplitter"
            },
            "total_chunks": len(chunks),
            "chunks": chunk_metas,
            "raw_file_path": str(raw_file_path.relative_to(self.base)),
            "created_at": datetime.now().isoformat()
        }
        with open(chunk_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        
        # 8. 更新全局注册表
        registry_entry = {
            "file_uuid": file_uuid,
            "original_name": original_filename,
            "file_path": str(raw_file_path.relative_to(self.base)),
            "md5": md5_hash,
            "total_chunks": len(chunks),
            "upload_time": timestamp,
            "tenant": tenant_id,
            "status": "success"
        }
        self._update_registry(registry_entry)
        
        # 9. 返回结果（便于后续向量化）
        return {
            "file_uuid": file_uuid,
            "original_name": original_filename,
            "total_chunks": len(chunks),
            "chunk_dir": str(chunk_dir.relative_to(self.base)),
            "manifest": manifest
        }

# ==================== 全局管道实例 ====================
pipeline = RAGIngestionPipeline(Config.BASE_ROOT)

# ==================== FastAPI 接口 ====================
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    tenant_id: str = "default"
):
    """上传文件并切割，返回切割结果元数据"""
    try:
        # 读取文件内容
        file_bytes = await file.read()
        
        # 执行上传+切割管道
        result = await pipeline.upload_and_chunk(
            file_bytes=file_bytes,
            original_filename=file.filename,
            tenant_id=tenant_id
        )
        
        return JSONResponse({
            "status": "success",
            "data": result
        })
    
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")

@app.get("/files")
async def list_files(tenant_id: str = "default"):
    """查看所有已上传文件（注册表）"""
    registry = pipeline._get_registry()
    tenant_files = [f for f in registry if f.get("tenant") == tenant_id]
    return {"files": tenant_files}

@app.get("/chunks/{file_uuid}")
async def get_chunks(file_uuid: str):
    """查看某个文件的所有切割块"""
    chunk_dir = pipeline.base / "3_chunks" / "default" / file_uuid
    if not chunk_dir.exists():
        raise HTTPException(status_code=404, detail="文件未找到")
    
    chunks = []
    for chunk_file in sorted(chunk_dir.glob("chunk_*.json")):
        with open(chunk_file, "r", encoding="utf-8") as f:
            chunks.append(json.load(f))
    
    return {"file_uuid": file_uuid, "total_chunks": len(chunks), "chunks": chunks}

# ==================== 启动服务 ====================
if __name__ == "__main__":
    import uvicorn
    print(f"🚀 RAG上传切割服务启动")
    print(f"📂 存储根目录: {Config.BASE_ROOT}")
    print(f"📝 切割参数: chunk_size={Config.CHUNK_SIZE}, overlap={Config.CHUNK_OVERLAP}")
    uvicorn.run("rag_ingestion:app", host="0.0.0.0", port=8000, reload=True)
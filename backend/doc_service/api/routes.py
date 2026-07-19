import json

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from doc_service.config import Config
from doc_service.core.pipeline import RAGIngestionPipeline

app = FastAPI(title="RAG 上传切割服务")
pipeline = RAGIngestionPipeline(Config.BASE_ROOT)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), tenant_id: str = "default"):
    try:
        file_bytes = await file.read()
        result = await pipeline.upload_and_chunk(
            file_bytes=file_bytes,
            original_filename=file.filename,
            tenant_id=tenant_id,
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@app.get("/files")
async def list_files(tenant_id: str = "default"):
    registry = pipeline._get_registry()
    tenant_files = [f for f in registry if f.get("tenant") == tenant_id]
    return {"files": tenant_files}


@app.get("/chunks/{file_uuid}")
async def get_chunks(file_uuid: str):
    chunk_dir = pipeline.base / "3_chunks" / "default" / file_uuid
    if not chunk_dir.exists():
        raise HTTPException(status_code=404, detail="文件未找到")

    chunks = []
    for chunk_file in sorted(chunk_dir.glob("chunk_*.json")):
        with open(chunk_file, "r", encoding="utf-8") as f:
            chunks.append(json.load(f))

    return {"file_uuid": file_uuid, "total_chunks": len(chunks), "chunks": chunks}

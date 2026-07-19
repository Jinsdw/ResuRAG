from doc_service.api.routes import app
from doc_service.config import Config

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    print("🚀 RAG上传切割服务启动")
    print(f"📂 存储根目录: {Config.BASE_ROOT}")
    print(
        f"📝 切割参数: chunk_size={Config.CHUNK_SIZE}, overlap={Config.CHUNK_OVERLAP}"
    )
    uvicorn.run("doc_service.main:app", host="0.0.0.0", port=8000, reload=True)

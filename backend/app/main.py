from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.routes import projects, export
import os

app = FastAPI(
    title="AI论文翻译平台",
    description="学术论文翻译与在线阅读平台后端API",
    version="1.0.0"
)

static_dir = os.path.join(settings.storage_path, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(projects.router)
app.include_router(export.router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "AI论文翻译平台"}

@app.get("/api/stats")
def get_stats():
    projects = storage.list_projects()
    total_docs = sum(p.get("file_count", 0) for p in projects)
    total_tokens = sum(p.get("total_tokens", 0) for p in projects)
    return {
        "data": {
            "projects": len(projects),
            "documents": total_docs,
            "tokens_used": total_tokens
        }
    }

from app.services.storage import storage_service as storage

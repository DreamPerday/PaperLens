from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.requests import Request
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


class CORSProxyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)

        origin = request.headers.get("origin", "")
        allowed_origins = settings.cors_origin_list
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        elif not origin:
            response.headers["Access-Control-Allow-Origin"] = "*"
        else:
            response.headers["Access-Control-Allow-Origin"] = allowed_origins[0] if allowed_origins else "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With, Cache-Control, DNT, If-Modified-Since, Keep-Alive, Origin, User-Agent"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
        return response


app.add_middleware(CORSProxyMiddleware)

app.include_router(projects.router)
app.include_router(export.router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "AI论文翻译平台"}

@app.get("/api/stats")
def get_stats():
    from app.services.pricing import calculate_cost, normalize_translation_tokens

    projects = storage.list_projects()
    total_docs = 0
    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cached_tokens = 0

    for p in projects:
        pid = p["id"]
        total_docs += len(storage.list_documents(pid))
        translations = storage.list_translations(pid)
        for t in translations:
            tok, prompt, comp, cached = normalize_translation_tokens(t)
            total_tokens += tok
            total_prompt_tokens += prompt
            total_completion_tokens += comp
            total_cached_tokens += cached

    total_cost = calculate_cost(total_prompt_tokens, total_completion_tokens, total_cached_tokens)
    return {
        "data": {
            "projects": len(projects),
            "documents": total_docs,
            "tokens_used": total_tokens,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "cached_tokens": total_cached_tokens,
            "cost": total_cost,
        }
    }

from app.services.storage import storage_service as storage
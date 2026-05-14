from fastapi import APIRouter, HTTPException, UploadFile, File, Body, Query, WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)
from app.models.schemas import ProjectCreate, TranslationRequest
from app.services.storage import storage_service
from app.utils.parser import DocumentParser
from app.services.translator import translate_document_async, save_token_history, get_token_history, split_paragraphs
import os
import uuid
import asyncio
import threading
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil
import base64
import re
from collections import defaultdict

router = APIRouter(prefix="/api/projects", tags=["projects"])

_translation_jobs: dict = {}
_websocket_clients: dict = {}


def _build_partial_text(job: dict) -> str:
    """Build partial translation text from completed chunks, preserving order."""
    chunks = job.get("chunks", {})
    if not chunks:
        return ""
    sorted_indices = sorted(int(k) for k in chunks.keys())
    parts = []
    for idx in sorted_indices:
        chunk = chunks[str(idx)]
        content = chunk.get("content", "")
        if content:
            parts.append(content)
    return "\n\n".join(parts)

@router.get("")
def list_projects():
    projects = storage_service.list_projects()
    return {"data": projects}

@router.post("")
def create_project(body: ProjectCreate):
    project = storage_service.create_project(body.name, body.description)
    return {"data": project, "message": "项目创建成功"}

# --- Documents ---

@router.get("/{project_id}/documents")
def list_documents(project_id: str):
    if not storage_service.get_project(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    docs = storage_service.list_documents(project_id)
    return {"data": docs}

@router.post("/{project_id}/documents/upload")
async def upload_document(project_id: str, file: UploadFile = File(...)):
    if not storage_service.get_project(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")

    ext = Path(file.filename).suffix.lower()
    doc_type_map = {
        ".pdf": "pdf", ".docx": "docx", ".md": "markdown",
        ".tex": "latex", ".txt": "txt", ".html": "html", ".htm": "html"
    }
    doc_type = doc_type_map.get(ext, "txt")

    safe_prefix = re.sub(r'[^\w\-.]', '_', Path(file.filename).stem)[:48]
    safe_name = f"{uuid.uuid4().hex[:8]}_{safe_prefix}{ext}"
    upload_dir = Path(storage_service.base) / "uploads"
    upload_dir.mkdir(exist_ok=True)
    file_path = str(upload_dir / safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    parser = DocumentParser(file_path)
    page_count = parser.get_page_count()

    doc = storage_service.add_document(
        project_id=project_id,
        filename=safe_name,
        original_name=file.filename,
        doc_type=doc_type,
        size=len(content),
        file_path=file_path
    )
    doc["page_count"] = page_count
    storage_service.update_document(project_id, doc["id"], {"page_count": page_count})

    return {"data": doc, "message": "文件上传成功"}

@router.put("/{project_id}/documents/{doc_id}")
def update_document(project_id: str, doc_id: str, body: dict = Body(...)):
    doc = storage_service.get_document(project_id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    updated = storage_service.update_document(project_id, doc_id, body)
    return {"data": updated, "message": "文档已更新"}

@router.delete("/{project_id}/documents/{doc_id}")
def delete_document(project_id: str, doc_id: str):
    if storage_service.delete_document(project_id, doc_id):
        return {"message": "文件已删除"}
    raise HTTPException(status_code=404, detail="文件不存在")

# --- Reader Content ---

@router.get("/{project_id}/documents/{doc_id}/content")
def get_document_content(project_id: str, doc_id: str):
    doc = storage_service.get_document(project_id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = doc.get("file_path", "")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        parser = DocumentParser(file_path)
        original_text = parser.extract_text()
        headings = parser.extract_headings()
    except Exception as e:
        logger.error(f"解析文档失败: project={project_id}, doc={doc_id}, error={e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"文档解析失败: {str(e)}")

    translation = storage_service.get_translation(project_id, doc_id)
    translated_text = translation["content"] if translation else ""

    return {
        "data": {
            "id": doc_id,
            "original_text": original_text,
            "translated_text": translated_text,
            "doc_type": doc["doc_type"],
            "headings": headings
        }
    }

# --- Translation ---

@router.post("/{project_id}/documents/{doc_id}/translate")
def translate_document_endpoint(project_id: str, doc_id: str, body: TranslationRequest):
    doc = storage_service.get_document(project_id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = doc.get("file_path", "")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="源文件不存在")

    job_id = f"{project_id}:{doc_id}"
    existing = _translation_jobs.get(job_id)
    if existing and existing.get("status") == "translating":
        return {"data": existing, "message": "翻译正在进行中"}

    storage_service.update_document(project_id, doc_id, {"status": "translating"})

    _translation_jobs[job_id] = {
        "job_id": job_id,
        "project_id": project_id,
        "doc_id": doc_id,
        "status": "translating",
        "progress": 0,
        "total_chunks": 0,
        "completed_chunks": 0,
        "chunks": {},
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    def run_translation():
        try:
            parser = DocumentParser(file_path)
            text = parser.extract_text()

            async def _translate_task():
                job = _translation_jobs[job_id]

                async def on_chunk_complete(idx: int, comp: int, translated: str):
                    job["completed_chunks"] = comp
                    if job["total_chunks"] > 0:
                        job["progress"] = max(0, min(100, int(comp / job["total_chunks"] * 100)))
                    job["chunks"][str(idx)] = {"index": idx, "content": translated, "done": True}
                    logger.info(f"翻译进度: job={job_id}, chunk={idx+1}/{job['total_chunks']}, progress={job['progress']}%, text_len={len(translated)}")

                    # 增量保存翻译结果 — 页面刷新后可恢复
                    try:
                        partial_text = _build_partial_text(job)
                        storage_service.save_translation(
                            project_id, doc_id,
                            content=partial_text,
                            tokens_used=0,
                        )
                    except Exception as e:
                        logger.warning(f"增量保存翻译状态失败: {e}")

                    ws_list = _websocket_clients.get(job_id, [])
                    if ws_list:
                        logger.info(f"推送WebSocket: job={job_id}, clients={len(ws_list)}, chunk={idx}")
                    dead = []
                    for ws in ws_list:
                        try:
                            await ws.send_json({
                                "type": "chunk",
                                "index": idx,
                                "content": translated,
                                "progress": job["progress"],
                                "completed": comp,
                                "total": job["total_chunks"],
                            })
                        except Exception as e:
                            logger.warning(f"WebSocket推送失败: {e}")
                            dead.append(ws)
                    for d in dead:
                        ws_list.remove(d)

                from app.services.translator import _ast_aware_chunks
                ast_chunks = _ast_aware_chunks(text)
                all_tasks = []
                for i, chunk in enumerate(ast_chunks):
                    all_tasks.append((i, chunk["text"], chunk.get("skip_translate", False)))

                job["total_chunks"] = len(all_tasks)
                logger.info(f"翻译开始: job={job_id}, chunks={job['total_chunks']}, text_len={len(text)}")

                result = await translate_document_async(
                    text, body.source_lang, body.target_lang,
                    on_chunk_complete=on_chunk_complete
                )

                try:
                    if result["success"] or (result.get("text") and len(result["text"]) > len(text) * 0.3):
                        job["status"] = "completed"
                        job["progress"] = 100
                        job["result"] = {"text": result["text"], "tokens": result["tokens"]}
                        logger.info(f"翻译完成: job={job_id}, tokens={result['tokens']}, total_len={len(result['text'])}")
                        storage_service.save_translation(
                            project_id, doc_id,
                            content=result["text"],
                            tokens_used=result["tokens"],
                        )
                        storage_service.update_document(project_id, doc_id, {"status": "completed"})
                        try:
                            para_count = len(split_paragraphs(text))
                            save_token_history(
                                project_id, doc_id, doc.get("original_name", doc_id),
                                result["tokens"], para_count,
                                prompt_tokens=result.get("prompt_tokens", 0),
                                completion_tokens=result.get("completion_tokens", 0),
                                cached_tokens=result.get("cached_tokens", 0),
                            )
                        except Exception as e:
                            logger.warning(f"保存Token历史记录失败: {e}")

                        ws_list = _websocket_clients.get(job_id, [])
                        logger.info(f"发送done消息: job={job_id}, ws_clients={len(ws_list)}")
                        for ws in ws_list:
                            try:
                                await ws.send_json({
                                    "type": "done",
                                    "progress": 100,
                                    "result": {"text": result["text"], "tokens": result["tokens"]},
                                })
                            except Exception as e:
                                logger.warning(f"ws done发送失败: {e}")
                    else:
                        job["status"] = "failed"
                        job["error"] = result.get("error", "翻译失败")
                        logger.error(f"翻译失败: job={job_id}, error={job['error']}")
                        storage_service.update_document(project_id, doc_id, {"status": "failed"})

                        ws_list = _websocket_clients.get(job_id, [])
                        for ws in ws_list:
                            try:
                                await ws.send_json({
                                    "type": "error",
                                    "message": result.get("error", "翻译失败"),
                                })
                            except Exception:
                                pass
                except Exception as e:
                    logger.error(f"翻译后处理异常: job={job_id}, error={e}", exc_info=True)
                    job["status"] = "failed"
                    job["error"] = f"后处理异常: {str(e)}"
                    job["result"] = {"text": result.get("text", ""), "tokens": result.get("tokens", 0)}
                    storage_service.update_document(project_id, doc_id, {"status": "failed"})

            def _run_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_translate_task())
                finally:
                    loop.close()

            threading.Thread(target=_run_async, daemon=True).start()

        except Exception as e:
            logger.error(f"翻译异常: project={project_id}, doc={doc_id}, error={e}", exc_info=True)
            _translation_jobs[job_id]["status"] = "failed"
            _translation_jobs[job_id]["error"] = str(e)
            storage_service.update_document(project_id, doc_id, {"status": "failed"})

    threading.Thread(target=run_translation, daemon=True).start()

    return {"data": _translation_jobs[job_id], "message": "翻译已开始"}


@router.get("/{project_id}/documents/{doc_id}/translate/status")
def get_translation_status(project_id: str, doc_id: str):
    job_id = f"{project_id}:{doc_id}"
    job = _translation_jobs.get(job_id)
    if not job:
        doc = storage_service.get_document(project_id, doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        status = doc.get("status", "uploaded")
        if status == "translating":
            logger.warning(
                f"状态端点: job_id={job_id} 无活跃翻译任务，但文档状态为translating。"
                f"说明翻译已放弃，自动标记为failed"
            )
            storage_service.update_document(project_id, doc_id, {"status": "failed"})
            status = "failed"
        translation = storage_service.get_translation(project_id, doc_id)
        job = {
            "job_id": job_id,
            "project_id": project_id,
            "doc_id": doc_id,
            "status": status,
            "progress": 100 if status == "completed" else 0,
        }
        if translation and translation.get("content"):
            job["result"] = {"text": translation["content"], "tokens": translation.get("tokens_used", 0)}
    return {"data": job}


@router.websocket("/{project_id}/documents/{doc_id}/translate/ws")
async def websocket_translate(websocket: WebSocket, project_id: str, doc_id: str):
    await websocket.accept()
    job_id = f"{project_id}:{doc_id}"

    if job_id not in _websocket_clients:
        _websocket_clients[job_id] = []
    _websocket_clients[job_id].append(websocket)

    try:
        existing = _translation_jobs.get(job_id)
        if existing:
            await websocket.send_json({
                "type": "status",
                "status": existing.get("status", "unknown"),
                "progress": existing.get("progress", 0),
                "total_chunks": existing.get("total_chunks", 0),
                "completed_chunks": existing.get("completed_chunks", 0),
            })
            if existing.get("result"):
                await websocket.send_json({
                    "type": "done",
                    "progress": 100,
                    "result": existing["result"],
                })

        while True:
            data = await websocket.receive_text()
            pass
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if job_id in _websocket_clients and websocket in _websocket_clients[job_id]:
            _websocket_clients[job_id].remove(websocket)

# --- Export (moved to routes/export.py) ---

# --- Search ---

@router.get("/search")
def search_documents(q: str = Query("", min_length=1)):
    results = []
    projects = storage_service.list_projects()
    for project in projects:
        docs = storage_service.list_documents(project["id"])
        for doc in docs:
            try:
                file_path = doc.get("file_path", "")
                if not file_path or not os.path.exists(file_path):
                    continue
                parser = DocumentParser(file_path)
                text = parser.extract_text()
                if q.lower() in text.lower():
                    idx = text.lower().index(q.lower())
                    start = max(0, idx - 80)
                    end = min(len(text), idx + len(q) + 120)
                    snippet = text[start:end]
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(text):
                        snippet = snippet + "..."
                    results.append({
                        "project_id": project["id"],
                        "project_name": project["name"],
                        "doc_id": doc["id"],
                        "doc_name": doc.get("original_name", ""),
                        "doc_type": doc.get("doc_type", ""),
                        "match_position": idx,
                        "snippet": snippet,
                    })
            except Exception:
                continue
    results.sort(key=lambda x: x["project_name"])
    return {"data": results, "query": q, "total": len(results)}

# --- Cleanup ---

@router.get("/storage/orphans")
def list_orphan_files():
    known_paths = set()
    projects = storage_service.list_projects()
    for project in projects:
        docs = storage_service.list_documents(project["id"])
        for doc in docs:
            fp = doc.get("file_path", "")
            if fp:
                known_paths.add(os.path.normpath(fp))

    upload_dir = storage_service.base / "uploads"
    orphan_files = []
    in_use_files = []
    if upload_dir.exists():
        for f in upload_dir.iterdir():
            if f.is_file():
                abs_path = os.path.normpath(str(f))
                info = {
                    "name": f.name,
                    "path": abs_path,
                    "size": f.stat().st_size,
                    "mtime": f.stat().st_mtime,
                }
                if abs_path in known_paths:
                    in_use_files.append(info)
                else:
                    orphan_files.append(info)

    static_dir = storage_service.base / "static" / "images"
    orphan_images = []
    in_use_images = []
    if static_dir.exists():
        for f in static_dir.iterdir():
            if f.is_file():
                abs_path = os.path.normpath(str(f))
                info = {
                    "name": f.name,
                    "path": abs_path,
                    "size": f.stat().st_size,
                    "mtime": f.stat().st_mtime,
                }
                if abs_path in known_paths:
                    in_use_images.append(info)
                else:
                    orphan_images.append(info)

    # Cache files are always orphan unless the upload file still exists
    cache_files = []
    if upload_dir.exists():
        for f in upload_dir.iterdir():
            if f.is_file() and f.suffix == ".cache":
                abs_path = os.path.normpath(str(f))
                cache_files.append({
                    "name": f.name,
                    "path": abs_path,
                    "size": f.stat().st_size,
                    "mtime": f.stat().st_mtime,
                })

    return {
        "data": {
            "orphan_uploads": orphan_files,
            "in_use_uploads": in_use_files,
            "orphan_images": orphan_images,
            "in_use_images": in_use_images,
            "cache_files": cache_files,
            "total_orphans": len(orphan_files) + len(orphan_images) + len(cache_files),
            "total_size": sum(f["size"] for f in orphan_files) + sum(i["size"] for i in orphan_images) + sum(c["size"] for c in cache_files),
        }
    }

@router.post("/storage/orphans/delete-selected")
def delete_selected_orphans(body: dict = Body(...)):
    paths = body.get("paths", [])
    if not paths:
        raise HTTPException(status_code=400, detail="未指定要删除的文件")

    deleted = 0
    total_size = 0
    for p in paths:
        try:
            path_obj = Path(p)
            if path_obj.exists() and path_obj.is_file():
                total_size += path_obj.stat().st_size
                path_obj.unlink()
                deleted += 1
        except Exception:
            continue

    return {"data": {"deleted_count": deleted, "deleted_size": total_size}, "message": f"已删除 {deleted} 个文件，释放 {total_size/1024:.1f} KB"}

@router.delete("/storage/orphans")
def delete_orphan_files():
    known_paths = set()
    projects = storage_service.list_projects()
    for project in projects:
        docs = storage_service.list_documents(project["id"])
        for doc in docs:
            fp = doc.get("file_path", "")
            if fp:
                known_paths.add(os.path.normpath(fp))

    deleted_count = 0
    deleted_size = 0

    upload_dir = storage_service.base / "uploads"
    if upload_dir.exists():
        for f in upload_dir.iterdir():
            if f.is_file() and os.path.normpath(str(f)) not in known_paths:
                s = f.stat().st_size
                f.unlink()
                deleted_count += 1
                deleted_size += s

    static_dir = storage_service.base / "static" / "images"
    if static_dir.exists():
        for f in static_dir.iterdir():
            if f.is_file() and os.path.normpath(str(f)) not in known_paths:
                s = f.stat().st_size
                f.unlink()
                deleted_count += 1
                deleted_size += s

    return {"data": {"deleted_count": deleted_count, "deleted_size": deleted_size}, "message": f"已清理 {deleted_count} 个废弃文件，释放 {deleted_size/1024:.1f} KB"}

# --- Token Stats ---

@router.get("/token-stats")
def get_token_stats():
    from app.services.pricing import calculate_cost, normalize_translation_tokens

    projects = storage_service.list_projects()
    project_breakdown = []
    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cached_tokens = 0

    for project in projects:
        pid = project["id"]
        translations = storage_service.list_translations(pid)
        proj_tokens = 0
        proj_prompt = 0
        proj_completion = 0
        proj_cached = 0
        for t in translations:
            tok, prompt, comp, cached = normalize_translation_tokens(t)
            proj_tokens += tok
            proj_prompt += prompt
            proj_completion += comp
            proj_cached += cached
        total_tokens += proj_tokens
        total_prompt_tokens += proj_prompt
        total_completion_tokens += proj_completion
        total_cached_tokens += proj_cached
        project_breakdown.append({
            "project_id": pid,
            "project_name": project["name"],
            "document_count": len(storage_service.list_documents(pid)),
            "translation_count": len(translations),
            "tokens_used": proj_tokens,
            "prompt_tokens": proj_prompt,
            "completion_tokens": proj_completion,
            "cached_tokens": proj_cached,
            "cost": calculate_cost(proj_prompt, proj_completion, proj_cached),
        })

    total_cost = calculate_cost(total_prompt_tokens, total_completion_tokens, total_cached_tokens)

    user_file = storage_service.base / "user_tokens.json"
    user_tokens = {}
    if user_file.exists():
        try:
            user_tokens = json.loads(user_file.read_text(encoding="utf-8"))
        except Exception:
            user_tokens = {}

    return {
        "data": {
            "total_tokens": total_tokens,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_cached_tokens": total_cached_tokens,
            "total_cost": total_cost,
            "project_breakdown": project_breakdown,
            "user_tokens": user_tokens,
        }
    }

@router.get("/token-history")
def get_token_history_endpoint(days: int = Query(30, ge=1, le=365)):
    records = get_token_history(days)
    daily_summary = defaultdict(lambda: {"tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "cached_tokens": 0, "count": 0})
    for r in records:
        day = r["timestamp"][:10]
        daily_summary[day]["tokens"] += r["tokens_used"]
        daily_summary[day]["prompt_tokens"] += r.get("prompt_tokens", 0)
        daily_summary[day]["completion_tokens"] += r.get("completion_tokens", 0)
        daily_summary[day]["cached_tokens"] += r.get("cached_tokens", 0)
        daily_summary[day]["count"] += 1

    daily = [{"date": k, "tokens": v["tokens"], "prompt_tokens": v["prompt_tokens"],
              "completion_tokens": v["completion_tokens"], "cached_tokens": v["cached_tokens"],
              "count": v["count"]}
             for k, v in sorted(daily_summary.items())]

    total_history_tokens = sum(r["tokens_used"] for r in records)
    total_history_prompt = sum(r.get("prompt_tokens", 0) for r in records)
    total_history_completion = sum(r.get("completion_tokens", 0) for r in records)
    total_history_cached = sum(r.get("cached_tokens", 0) for r in records)
    return {
        "data": {
            "records": records,
            "daily_summary": daily,
            "total_records": len(records),
            "total_tokens": total_history_tokens,
            "total_prompt_tokens": total_history_prompt,
            "total_completion_tokens": total_history_completion,
            "total_cached_tokens": total_history_cached,
            "days": days,
        }
    }


# --- Project CRUD (must be after non-parameterized routes) ---

@router.get("/{project_id}")
def get_project(project_id: str):
    project = storage_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"data": project}


@router.put("/{project_id}")
def update_project(project_id: str, body: dict):
    project = storage_service.update_project(project_id, body)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"data": project}


@router.delete("/{project_id}")
def delete_project(project_id: str):
    if storage_service.delete_project(project_id):
        return {"message": "项目已删除"}
    raise HTTPException(status_code=404, detail="项目不存在")

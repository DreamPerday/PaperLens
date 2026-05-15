from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.services.export import (
    HTMLExporter,
    PDFExporter,
)
from app.services.storage import storage_service
from app.utils.parser import DocumentParser
import os
import re
from pathlib import Path

router = APIRouter(prefix="/api/projects", tags=["export"])

exporters = {
    "html": HTMLExporter(),
    "pdf": PDFExporter(),
}

async def _get_document_content(project_id: str, doc_id: str, include_original: bool, include_translation: bool):
    doc = storage_service.get_document(project_id, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = doc.get("file_path", "")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="源文件不存在")

    original_text = ""
    if include_original:
        parser = DocumentParser(file_path)
        original_text = parser.extract_text()

    translated_text = ""
    if include_translation:
        translation = storage_service.get_translation(project_id, doc_id)
        translated_text = translation["content"] if translation else ""

    return original_text, translated_text, doc

IMG_PATTERN_HTML = re.compile(r'(<img[^>]+src="([^"]+)"[^>]*\/?>)', re.IGNORECASE)
IMG_PATTERN_MD = re.compile(r'(!\[([^\]]*)\]\(([^)]+)\))')

def _enrich_translation_with_images(original_text: str, translated_text: str) -> str:
    all_images = []
    for m in IMG_PATTERN_HTML.finditer(original_text):
        src = m.group(2)
        alt_match = re.search(r'alt="([^"]*)"', m.group(1))
        alt = alt_match.group(1) if alt_match else ""
        all_images.append(("html", src, alt, m.start()))
    for m in IMG_PATTERN_MD.finditer(original_text):
        src = m.group(3)
        alt = m.group(2)
        all_images.append(("md", src, alt, m.start()))
    
    if not all_images:
        return translated_text
    
    o_paras = re.split(r'\n\n+', original_text)
    img_para_indices = {}
    for j, img in enumerate(all_images):
        _, _, _, pos = img
        para_idx = 0
        search_start = 0
        for pi, para in enumerate(o_paras):
            para_start = original_text.find(para, search_start)
            if para_start == -1:
                break
            para_end = para_start + len(para)
            search_start = para_end
            if para_start <= pos < para_end:
                para_idx = pi
                break
        img_para_indices[j] = para_idx
    
    t_paras = re.split(r'\n\n+', translated_text)
    if not t_paras:
        return translated_text
    
    assigned = {}
    for j, img in enumerate(all_images):
        o_ratio = img_para_indices[j] / max(1, len(o_paras) - 1)
        t_idx = min(len(t_paras) - 1, int(o_ratio * (len(t_paras) - 1)))
        t_idx = max(0, min(len(t_paras) - 1, t_idx))
        if t_idx not in assigned:
            assigned[t_idx] = []
        assigned[t_idx].append(img)
    
    parts = []
    for i, para in enumerate(t_paras):
        parts.append(para)
        for img_tuple in assigned.get(i, []):
            kind, src, alt, _ = img_tuple
            parts.append(f"\n\n![{alt}]({src})\n")
    
    return "\n\n".join(parts)

@router.post("/{project_id}/documents/{doc_id}/export")
async def export_document(
    project_id: str,
    doc_id: str,
    body: dict = Body(...),
    background_tasks: BackgroundTasks = None
):
    format_type = body.get("format", "html")
    embed_images = body.get("embed_images", True)
    include_original = body.get("include_original", True)
    include_translation = body.get("include_translation", True)
    theme = body.get("theme", "academic")
    page_size = body.get("page_size", "A4")
    font_size = body.get("font_size", 12)
    include_toc = body.get("include_toc", False)
    watermark = body.get("watermark", None)
    watermark_pos = body.get("watermark_pos", "bottom")
    cover_page = body.get("cover_page", False)
    watermark_tiled = body.get("watermark_tiled", False)
    
    if format_type not in exporters:
        raise HTTPException(status_code=400, detail=f"不支持的导出格式: {format_type}")

    original_text, translated_text, doc = await _get_document_content(
        project_id, doc_id, include_original, include_translation
    )

    if include_translation and translated_text:
        translated_text = _enrich_translation_with_images(original_text, translated_text)

    exporter = exporters[format_type]
    title = doc.get("original_name", "Translation").replace(".pdf", "").replace(".docx", "")

    try:
        result = await exporter.export(
            original_text=original_text,
            translated_text=translated_text,
            doc_id=doc_id,
            title=title,
            include_original=include_original,
            include_translation=include_translation,
            embed_images=embed_images,
            theme=theme,
            page_size=page_size,
            font_size=font_size,
            include_toc=include_toc,
            watermark=watermark,
            watermark_pos=watermark_pos,
            cover_page=cover_page,
            watermark_tiled=watermark_tiled
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

    content = result["content"]
    mime = result["mime"]
    ext = result["extension"]
    filename = f"{title}{ext}"

    if isinstance(content, bytes):
        return StreamingResponse(
            iter([content]),
            media_type=mime,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": mime
            }
        )
    else:
        return {
            "data": {
                "content": content,
                "mime": mime,
                "filename": filename
            }
        }

@router.get("/export/formats")
def get_supported_formats():
    return {
        "data": {
            "formats": ["html", "pdf"],
            "options": {
                "themes": ["academic", "modern", "dark", "compact"],
                "page_sizes": ["A4", "Letter"],
                "default_font_size": 12
            }
        }
    }
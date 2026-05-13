import re
import json
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable, Awaitable

import httpx
from app.config import settings

TRANSLATE_PROMPT = """Translate the following English academic paragraph into fluent, professional Chinese.

Rules:
1. Keep proper names, mathematical symbols, variable names UNCHANGED.
2. Keep paragraph structure and formatting.
3. [FORMULA_N] placeholders MUST be preserved exactly as-is — do not modify, translate, or remove them.
4. Output ONLY the Chinese translation, no explanations.

English text:
{text}

Chinese translation:"""

REFERENCES_START_PATTERNS = [
    r'^#+\s*references?\s*$',
    r'^#+\s*bibliography\s*$',
    r'^references?\s*$',
    r'^bibliography\s*$',
    r'^\[\d+\]',
]

FORMULA_BLOCK_RE = re.compile(
    r'(\$\$[\s\S]*?\$\$|\\begin\{[^}]*\}[\s\S]*?\\end\{[^}]*\})'
)
FORMULA_INLINE_RE = re.compile(r'(\$[^\$]+?\$)')

MAX_CONCURRENT = 10
MAX_RETRIES = 3
NORMAL_CHUNK_MIN = 3500
NORMAL_CHUNK_MAX = 4500
MATH_HEAVY_CHUNK_MIN = 2000
MATH_HEAVY_CHUNK_MAX = 3000
MATH_DENSITY_THRESHOLD = 0.15


def _is_references_section(text: str) -> bool:
    first_line = text.strip().split('\n')[0].strip().lower()
    for pat in REFERENCES_START_PATTERNS:
        if re.match(pat, first_line, re.IGNORECASE):
            return True
    if re.match(r'^\[\d+\]', text.strip()[:20]):
        return True
    ref_count = len(re.findall(r'\[\d+\]', text[:500]))
    if ref_count >= 3 and len(text) < 500:
        return True
    return False


def _protect_formulas(text: str) -> tuple:
    formulas: list[str] = []

    def _replace_block(m):
        formulas.append(m.group(0))
        return f'[FORMULA_{len(formulas) - 1}]'

    text = FORMULA_BLOCK_RE.sub(_replace_block, text)

    def _replace_inline(m):
        formulas.append(m.group(0))
        return f'[FORMULA_{len(formulas) - 1}]'

    text = FORMULA_INLINE_RE.sub(_replace_inline, text)

    return text, formulas


def _restore_formulas(text: str, formulas: list) -> str:
    for i, f in enumerate(formulas):
        text = text.replace(f'[FORMULA_{i}]', f)
    return text


def _math_density(text: str) -> float:
    blocks = len(FORMULA_BLOCK_RE.findall(text))
    inlines = len(FORMULA_INLINE_RE.findall(text))
    return (blocks + inlines) / max(len(text), 1)


def should_skip(text: str) -> bool:
    if not text or len(text.strip()) < 10:
        return True
    if re.match(r'^[\d\s\-.,;:()\[\]{}+*/=<>@#$%^&|\\]+$', text.strip()):
        return True
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    if chinese_chars > len(text) * 0.5:
        return True
    return False


def _smart_chunk_paragraphs(paragraphs: list) -> list:
    chunks = []
    current_parts = []
    current_len = 0
    current_is_refs = False

    for para in paragraphs:
        stripped = para.strip()
        if not stripped:
            continue

        if _is_references_section(stripped):
            if current_parts:
                chunks.append({
                    "text": "\n\n".join(current_parts),
                    "skip_translate": current_is_refs,
                })
                current_parts = []
                current_len = 0
            chunks.append({"text": stripped, "skip_translate": True})
            current_is_refs = False
            continue

        para_text, formulas = _protect_formulas(stripped)
        para_len = len(para_text)
        density = _math_density(stripped)
        max_chunk = MATH_HEAVY_CHUNK_MAX if density > MATH_DENSITY_THRESHOLD else NORMAL_CHUNK_MAX

        if current_len + para_len > max_chunk and current_parts:
            chunks.append({
                "text": "\n\n".join(current_parts),
                "skip_translate": current_is_refs,
            })
            current_parts = [stripped]
            current_len = para_len + 2
            current_is_refs = False
        else:
            current_parts.append(stripped)
            current_len += para_len + 2

    if current_parts:
        chunks.append({
            "text": "\n\n".join(current_parts),
            "skip_translate": current_is_refs,
        })

    return chunks


async def _translate_single_chunk(
    client: httpx.AsyncClient,
    chunk_text: str,
    sem: asyncio.Semaphore,
    chunk_idx: int,
    total: int,
    max_retries: int = MAX_RETRIES,
) -> dict:
    async with sem:
        if should_skip(chunk_text):
            return {"text": chunk_text, "tokens": 0, "success": True, "index": chunk_idx}

        api_url = f"{settings.deepseek_base_url}/v1/chat/completions"

        protected_text, formulas = _protect_formulas(chunk_text)
        prompt = TRANSLATE_PROMPT.format(text=protected_text)

        headers = {
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": settings.deepseek_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 4096,
            "stream": False,
        }

        last_error = None
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=httpx.Timeout(120.0, connect=10.0)
                )

                if response.status_code == 200:
                    result = response.json()
                    translated = result["choices"][0]["message"]["content"] or ""
                    translated = re.sub(
                        r'^((中文|Chinese)\s*)?(翻译|translation)[：:]\s*',
                        '', translated.strip()
                    )
                    translated = _restore_formulas(translated, formulas)
                    usage = result.get("usage", {})
                    tokens = usage.get("total_tokens", len(chunk_text) // 2)
                    return {
                        "text": translated,
                        "tokens": tokens,
                        "success": True,
                        "index": chunk_idx,
                    }
                elif response.status_code == 429:
                    last_error = f"API限流(429): {response.text[:200]}"
                    await asyncio.sleep(5 * (attempt + 1))
                elif response.status_code >= 500:
                    last_error = f"API服务器错误({response.status_code}): {response.text[:200]}"
                    await asyncio.sleep(3 * (attempt + 1))
                else:
                    last_error = f"API错误({response.status_code}): {response.text[:200]}"
                    await asyncio.sleep(2)
            except httpx.TimeoutException:
                last_error = "请求超时"
                await asyncio.sleep(3 * (attempt + 1))
            except Exception as e:
                last_error = str(e)
                await asyncio.sleep(2 * (attempt + 1))

        return {
            "text": chunk_text,
            "tokens": 0,
            "success": False,
            "error": last_error,
            "index": chunk_idx,
        }


async def translate_document_async(
    text: str,
    source_lang: str = "en",
    target_lang: str = "zh",
    on_chunk_complete: Optional[Callable[[int, int, str], Awaitable[None]]] = None,
) -> dict:
    if not settings.deepseek_api_key or settings.deepseek_api_key == "your-api-key-here":
        return {"text": text, "tokens": len(text) // 2, "success": True}

    paragraphs = _smart_chunk_paragraphs(re.split(r'\n\s*\n', text))
    translate_tasks = []
    skip_chunks = []

    for i, chunk in enumerate(paragraphs):
        if chunk["skip_translate"]:
            skip_chunks.append(i)
        translate_tasks.append((i, chunk["text"]))

    total_translatable = len(translate_tasks) - len(skip_chunks)

    if total_translatable == 0:
        results = []
        for i, t in enumerate(paragraphs):
            results.append({"text": t["text"], "tokens": 0, "success": True, "index": i})
        results.sort(key=lambda x: x["index"])
        full_text = "\n\n".join(r["text"] for r in results)
        return {"text": full_text, "tokens": 0, "success": True}

    sem = asyncio.Semaphore(MAX_CONCURRENT)
    completed_count = 0

    async with httpx.AsyncClient() as client:
        async def translate_one(idx: int, chunk_text: str) -> dict:
            nonlocal completed_count
            result = await _translate_single_chunk(
                client, chunk_text, sem, idx, total_translatable
            )
            completed_count += 1
            if on_chunk_complete:
                await on_chunk_complete(idx, completed_count, result.get("text", ""))
            return result

        tasks = [translate_one(i, t) for i, t in translate_tasks]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for r in raw_results:
        if isinstance(r, Exception):
            results.append({"text": "", "tokens": 0, "success": False, "error": str(r), "index": -1})
        else:
            results.append(r)

    results.sort(key=lambda x: x.get("index", -1))
    full_text = "\n\n".join(r.get("text", "") for r in results)
    total_tokens = sum(r.get("tokens", 0) for r in results)
    all_success = all(r.get("success", False) for r in results)

    return {
        "text": full_text,
        "tokens": total_tokens,
        "success": all_success,
    }


def save_token_history(project_id: str, doc_id: str, doc_name: str, tokens_used: int, paragraph_count: int):
    from app.services.storage import storage_service
    history_dir = storage_service.base / "token_history"
    history_dir.mkdir(exist_ok=True)
    history_file = history_dir / "history.jsonl"

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "doc_id": doc_id,
        "doc_name": doc_name,
        "tokens_used": tokens_used,
        "paragraph_count": paragraph_count,
    }
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_token_history(days: int = 30) -> list:
    from app.services.storage import storage_service
    history_file = storage_service.base / "token_history" / "history.jsonl"
    if not history_file.exists():
        return []

    cutoff = None
    if days > 0:
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400

    records = []
    with open(history_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if cutoff:
                    ts = datetime.fromisoformat(rec["timestamp"]).timestamp()
                    if ts < cutoff:
                        continue
                records.append(rec)
            except Exception:
                continue
    return records


def split_paragraphs(text: str) -> list:
    return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
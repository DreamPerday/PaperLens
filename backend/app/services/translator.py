import re
import json
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable, Awaitable

import httpx
from app.config import settings

TRANSLATE_PROMPT = """Translate the following English academic text into fluent, professional Chinese.

CRITICAL — Preserve ALL Markdown formatting markers EXACTLY as-is:
- **bold text**: translate the text between ** and ** markers, keep the markers
- *italic text*: translate the text between * and * markers, keep the markers  
- `inline code`: translate the code text, keep the backticks
- ### headings: translate heading text, keep ### prefix unchanged
- - bullet / * bullet / + bullet list markers: keep markers, translate item text
- 1. numbered / 2. numbered list markers: keep the "N. " prefix, translate item text
- > blockquotes: keep > prefix, translate quoted text
- ``` code blocks ```: keep block delimiters, translate code content
- | table | rows |: keep pipe-separated table structure exactly
- [link text](url): translate link text between [ and ], keep URL in ( )
- Blank lines between paragraphs: preserve paragraph separation

Rules:
1. Keep proper names, mathematical symbols, variable names UNCHANGED.
2. [FORMULA_N] placeholders MUST be preserved exactly as-is — do not modify, translate, or remove them.
3. Output ONLY the Chinese translation, no explanations.

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
    r'(\\begin\{[^}]*\}[\s\S]*?\\end\{[^}]*\}|\$\$[\s\S]*?\$\$)'
)
FORMULA_INLINE_RE = re.compile(r'(\$[^\$]+?\$)')

# Markdown structural formatting patterns to protect (prefixes only, content passes through)
MD_HEADING_PREFIX_RE = re.compile(r'^(#{1,6}\s+)', re.MULTILINE)
MD_LIST_PREFIX_RE = re.compile(r'^(\s*([-*+]|\d+\.)\s+)', re.MULTILINE)
MD_BLOCKQUOTE_PREFIX_RE = re.compile(r'^(>\s*)', re.MULTILINE)
MD_CODE_BLOCK_RE = re.compile(r'(```[\s\S]*?```)')
MD_INLINE_CODE_RE = re.compile(r'(?<!\\)(`[^`\n]+?(?<!\\)`)')
MD_BOLD_RE = re.compile(r'(\*\*[^*\n]+?\*\*)')
MD_ITALIC_RE = re.compile(r'(?<!\*)(\*[^*\n]+?\*)(?!\*)')
MD_LINK_RE = re.compile(r'(\[[^\]]+\]\([^)]+\))')

MAX_CONCURRENT = 10
MAX_RETRIES = 3
NORMAL_CHUNK_MIN = 3500
NORMAL_CHUNK_MAX = 4500
MATH_HEAVY_CHUNK_MIN = 2000
MATH_HEAVY_CHUNK_MAX = 3000
MATH_DENSITY_THRESHOLD = 0.15

# Atomic HTML/XML block patterns — these must NEVER be split across chunks
HTML_BLOCK_RE = re.compile(
    r'(<(?:table|figure|pre|div|section|article|dl|math|svg)\b[^>]*>'  # opening tag
    r'[\s\S]*?'                                                       # content (lazy)
    r'</(?:table|figure|pre|div|section|article|dl|math|svg)>)',      # closing tag
    re.IGNORECASE
)
# Self-closing or void elements that are atomic
HTML_VOID_RE = re.compile(
    r'(<(?:img|br|hr|input|meta|link|col|area|base|embed|source|track|wbr)\b[^>]*/?>)',
    re.IGNORECASE
)
# Markdown fenced code blocks (``` ... ```)
MD_FENCED_CODE_RE = re.compile(r'(```[\s\S]*?```)')
# Blockquotes — consecutive lines starting with >
MULTILINE_BLOCKQUOTE_RE = re.compile(r'((?:^>.*(?:\n|$))+)', re.MULTILINE)
# LaTeX display environments
LATEX_ENV_RE = re.compile(r'(\\begin\{[^}]*\}[\s\S]*?\\end\{[^}]*\})')

ATOMIC_BLOCK_RE = re.compile(
    r'(<(?:table|figure|pre|div|section|article|dl|math|svg)\b[^>]*>[\s\S]*?</(?:table|figure|pre|div|section|article|dl|math|svg)>)'
    r'|(```[\s\S]*?```)'
    r'|(\\begin\{[^}]*\}[\s\S]*?\\end\{[^}]*\})'
    r'|(\$\$[\s\S]*?\$\$)'
    r'|((?:^>.*(?:\n|$))+)',
    re.IGNORECASE | re.MULTILINE
)


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


def _protect_formatting(text: str) -> tuple:
    """Protect markdown formatting elements from AI translation modifications.

    Replaces entire markdown-formatted spans with placeholders like [MDC_0].
    The AI must preserve these placeholders; they are restored after translation.
    Order matters: smaller spans protected first, then larger.
    """
    markers: list[str] = []

    def _replace(pattern, m):
        markers.append(m.group(0))
        return f'[MDC_{len(markers) - 1}]'

    text = MD_INLINE_CODE_RE.sub(lambda m: _replace(MD_INLINE_CODE_RE, m), text)
    text = MD_ITALIC_RE.sub(lambda m: _replace(MD_ITALIC_RE, m), text)
    text = MD_BOLD_RE.sub(lambda m: _replace(MD_BOLD_RE, m), text)
    text = MD_LINK_RE.sub(lambda m: _replace(MD_LINK_RE, m), text)
    text = MD_CODE_BLOCK_RE.sub(lambda m: _replace(MD_CODE_BLOCK_RE, m), text)
    text = MD_BLOCKQUOTE_PREFIX_RE.sub(lambda m: _replace(MD_BLOCKQUOTE_PREFIX_RE, m), text)
    text = MD_LIST_PREFIX_RE.sub(lambda m: _replace(MD_LIST_PREFIX_RE, m), text)
    text = MD_HEADING_PREFIX_RE.sub(lambda m: _replace(MD_HEADING_PREFIX_RE, m), text)

    return text, markers


def _restore_formatting(text: str, markers: list) -> str:
    for i, m in enumerate(markers):
        text = text.replace(f'[MDC_{i}]', m)
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


def _find_atomic_blocks(text: str) -> list[tuple[int, int, str]]:
    """Scan text and identify atomic blocks that must NOT be split.

    Returns list of (start_pos, end_pos, block_type) sorted by start_pos.
    block_type is one of: 'html', 'code', 'latex', 'blockquote'
    """
    blocks = []
    for m in ATOMIC_BLOCK_RE.finditer(text):
        start, end = m.span()
        if m.group(1):   # HTML block
            blocks.append((start, end, 'html'))
        elif m.group(2):  # code block
            blocks.append((start, end, 'code'))
        elif m.group(3):  # LaTeX \begin{}...\end{}
            blocks.append((start, end, 'latex'))
        elif m.group(4):  # $$ display math
            blocks.append((start, end, 'latex'))
        elif m.group(5):  # blockquote
            blocks.append((start, end, 'blockquote'))
    blocks.sort(key=lambda x: x[0])
    return blocks


def _is_inside_atomic(pos: int, blocks: list[tuple[int, int, str]]) -> bool:
    """Check if position falls inside any atomic block."""
    for start, end, _ in blocks:
        if start <= pos < end:
            return True
    return False


def _block_aware_split(text: str) -> list[str]:
    """Split text into paragraphs on double-newlines,
    but NEVER split inside atomic blocks (HTML tables, code blocks, etc.).
    """
    blocks = _find_atomic_blocks(text)
    if not blocks:
        parts = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        return parts

    # Strategy: replace atomic blocks with placeholders, split, then restore
    placeholders = {}
    offset = 0
    working = text
    for start, end, block_type in blocks:
        block_text = text[start:end]
        placeholder = f'__ATOMIC_{len(placeholders)}__'
        placeholders[placeholder] = block_text
        adjusted_start = start - offset
        adjusted_end = end - offset
        working = working[:adjusted_start] + placeholder + working[adjusted_end:]
        offset += (end - start) - len(placeholder)

    parts = [p.strip() for p in re.split(r'\n\s*\n', working) if p.strip()]

    result = []
    for part in parts:
        for ph, original in placeholders.items():
            if ph in part:
                part = part.replace(ph, original)
        result.append(part)

    return result


def _smart_chunk_paragraphs(paragraphs: list) -> list:
    """Group paragraphs into translation chunks.

    Rules:
    1. Atomic blocks (HTML tables, code, LaTeX, blockquotes) go as single chunks if too large
    2. References section detected and marked skip_translate
    3. Normal paragraphs grouped up to NORMAL_CHUNK_MAX / MATH_HEAVY_CHUNK_MAX
    4. Rich text (tables, code blocks) use larger limits since much is markup
    """
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

        is_atomic_html = bool(HTML_BLOCK_RE.search(stripped))
        is_atomic = bool(ATOMIC_BLOCK_RE.search(stripped))
        para_len = len(stripped)

        density = _math_density(stripped)
        if is_atomic_html:
            rich_factor = _rich_text_factor(stripped)
            effective_len = int(para_len * (1.0 - rich_factor * 0.5))
            rich_max_chunk = int(NORMAL_CHUNK_MAX * 1.5)
        else:
            # Account for formula size: formulas become short placeholders
            formula_chars = sum(len(f) for f in FORMULA_BLOCK_RE.findall(stripped))
            formula_chars += sum(len(f) for f in FORMULA_INLINE_RE.findall(stripped))
            effective_len = para_len - max(0, formula_chars - 10 * max(1, density * para_len))
            rich_max_chunk = MATH_HEAVY_CHUNK_MAX if density > MATH_DENSITY_THRESHOLD else NORMAL_CHUNK_MAX

        # Atomic HTML blocks (tables, figures, divs) — flush current, then send alone if too big
        if is_atomic_html and effective_len > rich_max_chunk:
            if current_parts:
                chunks.append({
                    "text": "\n\n".join(current_parts),
                    "skip_translate": current_is_refs,
                })
                current_parts = []
                current_len = 0
            chunks.append({"text": stripped, "skip_translate": current_is_refs})
            continue

        if current_len + effective_len > rich_max_chunk and current_parts:
            chunks.append({
                "text": "\n\n".join(current_parts),
                "skip_translate": current_is_refs,
            })
            current_parts = [stripped]
            current_len = effective_len + 2
            current_is_refs = False
        else:
            current_parts.append(stripped)
            current_len += effective_len + 2

    if current_parts:
        chunks.append({
            "text": "\n\n".join(current_parts),
            "skip_translate": current_is_refs,
        })

    return chunks


def _rich_text_factor(text: str) -> float:
    """Estimate what fraction of text is markup (HTML tags, markdown syntax).

    Returns 0.0 to 1.0 where higher = more markup, less translatable text.
    """
    if not text:
        return 0.0
    html_chars = len(''.join(re.findall(r'<[^>]+>', text)))
    md_chars = len(''.join(re.findall(r'[*#`|\[\]()>]', text)))
    total = html_chars + md_chars
    return min(0.9, total / max(len(text), 1))


def _validate_chunk_completeness(original: str, translated: str, chunk_idx: int) -> dict:
    """Validate that a translated chunk hasn't lost significant content.

    Returns dict with validation metrics.
    """
    orig_len = len(original)
    trans_len = len(translated)

    orig_paras = len([p for p in re.split(r'\n\s*\n', original) if p.strip()])
    trans_paras = len([p for p in re.split(r'\n\s*\n', translated) if p.strip()])

    # Count protected elements in original
    orig_formulas = len(FORMULA_BLOCK_RE.findall(original)) + len(FORMULA_INLINE_RE.findall(original))
    trans_formulas_restored = len(FORMULA_BLOCK_RE.findall(translated)) + len(FORMULA_INLINE_RE.findall(translated))

    # Count format markers
    orig_markers = len(re.findall(r'\[MDC_\d+\]', original))
    trans_markers = len(re.findall(r'\[MDC_\d+\]', translated))

    # Issues
    warnings = []
    issues = []

    if orig_len > 100 and trans_len < orig_len * 0.15:
        issues.append(f"translation too short ({trans_len} vs {orig_len})")
    elif orig_len > 50 and trans_len == 0:
        issues.append("empty translation")

    if orig_markers > 0 and trans_markers != orig_markers:
        warnings.append(f"format markers mismatch: orig={orig_markers} trans={trans_markers}")

    if orig_formulas > 0 and trans_formulas_restored != orig_formulas:
        warnings.append(f"formula count mismatch: orig={orig_formulas} trans={trans_formulas_restored}")

    if orig_paras > 1 and trans_paras < orig_paras * 0.5:
        warnings.append(f"paragraph count dropped: orig={orig_paras} trans={trans_paras}")

    return {
        "ok": len(issues) == 0,
        "orig_len": orig_len,
        "trans_len": trans_len,
        "orig_paras": orig_paras,
        "trans_paras": trans_paras,
        "warnings": warnings,
        "issues": issues,
    }


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
        protected_text, format_markers = _protect_formatting(protected_text)
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
                    translated = _restore_formatting(translated, format_markers)
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

    paragraphs = _smart_chunk_paragraphs(_block_aware_split(text))
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

    # Validation: check each translated chunk for completeness
    validation_log = []
    total_issues = 0
    for i, r in enumerate(results):
        if r.get("index", -1) in skip_chunks:
            continue
        orig_text = paragraphs[r["index"]]["text"] if r.get("index", -1) >= 0 else ""
        validation = _validate_chunk_completeness(orig_text, r.get("text", ""), r.get("index", -1))
        if not validation["ok"] or validation["warnings"]:
            total_issues += len(validation["issues"]) + len(validation["warnings"])
            validation_log.append({
                "chunk": r.get("index", -1),
                **validation
            })

    if validation_log:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"翻译完整性检查: {total_issues} 个问题, "
            f"{len(validation_log)}/{len(results)} 个chunk受影响"
        )
        for entry in validation_log:
            logger.warning(f"  chunk[{entry['chunk']}]: "
                          f"issues={entry['issues']} warnings={entry['warnings']} "
                          f"len: {entry['orig_len']}→{entry['trans_len']}")

    full_text = "\n\n".join(r.get("text", "") for r in results)
    total_tokens = sum(r.get("tokens", 0) for r in results)
    all_success = all(r.get("success", False) for r in results)

    return {
        "text": full_text,
        "tokens": total_tokens,
        "success": all_success,
        "validation": {
            "total_issues": total_issues,
            "affected_chunks": len(validation_log),
            "details": validation_log if validation_log else [],
        },
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
    """Public API: split text preserving atomic blocks.

    Preferred over simple newline splitting for documents with HTML tables, code blocks, etc.
    """
    return _block_aware_split(text)
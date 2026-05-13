from app.models.schemas import DocumentType
from pathlib import Path
import os
import json

class DocumentParser:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.doc_type = self._detect_type()

    def _detect_type(self) -> DocumentType:
        ext = self.file_path.suffix.lower()
        mapping = {
            '.pdf': DocumentType.pdf,
            '.docx': DocumentType.docx,
            '.md': DocumentType.markdown,
            '.tex': DocumentType.latex,
            '.txt': DocumentType.txt,
            '.html': DocumentType.html,
            '.htm': DocumentType.html,
        }
        return mapping.get(ext, DocumentType.txt)

    def extract_text(self) -> str:
        doc_type = self._detect_type()
        if doc_type == DocumentType.pdf:
            return self._extract_pdf()
        elif doc_type == DocumentType.docx:
            return self._extract_docx()
        elif doc_type in (DocumentType.markdown, DocumentType.latex, DocumentType.txt, DocumentType.html):
            return self._read_text()
        return self._read_text()

    def _get_cache_path(self) -> Path:
        return self.file_path.with_suffix(".parsed.cache")

    def _load_cache(self) -> str | None:
        cache_path = self._get_cache_path()
        if not cache_path.exists():
            return None
        pdf_mtime = self.file_path.stat().st_mtime
        cache_mtime = cache_path.stat().st_mtime
        if cache_mtime < pdf_mtime:
            return None
        try:
            with open(str(cache_path), "r", encoding="utf-8") as f:
                return json.loads(f.read()).get("text", "")
        except Exception:
            return None

    def _save_cache(self, text: str):
        try:
            cache_path = self._get_cache_path()
            with open(str(cache_path), "w", encoding="utf-8") as f:
                f.write(json.dumps({"text": text}, ensure_ascii=False))
        except Exception:
            pass

    def _extract_pdf(self) -> str:
        cached = self._load_cache()
        if cached is not None:
            return cached

        try:
            import requests as req
            import base64
            from app.config import settings

            api_url = settings.layout_parsing_api_url
            token = settings.layout_parsing_token

            if not api_url or not token:
                return f"[Layout Parsing API 未配置，请检查 LAYOUT_PARSING_TOKEN 设置]"

            with open(str(self.file_path), "rb") as f:
                file_bytes = f.read()
                file_data = base64.b64encode(file_bytes).decode("ascii")

            headers = {
                "Authorization": f"token {token}",
                "Content-Type": "application/json"
            }

            payload = {
                "file": file_data,
                "fileType": 0,
                "useDocOrientationClassify": False,
                "useDocUnwarping": False,
                "useChartRecognition": False,
            }

            resp = req.post(api_url, json=payload, headers=headers, timeout=180)
            if resp.status_code != 200:
                return f"[Layout Parsing API 请求失败: HTTP {resp.status_code} {resp.text[:200]}]"

            result = resp.json()["result"]

            file_stem = self.file_path.stem
            img_base_dir = Path(settings.storage_path) / "static" / "images" / file_stem
            img_base_dir.mkdir(parents=True, exist_ok=True)

            all_pages = []
            for page_idx, page_res in enumerate(result["layoutParsingResults"]):
                markdown_text = page_res["markdown"]["text"]
                images = page_res["markdown"].get("images", {})

                for img_rel_path, img_url in images.items():
                    try:
                        img_resp = req.get(img_url, timeout=30)
                        if img_resp.status_code == 200:
                            local_img_path = img_base_dir / img_rel_path
                            local_img_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(str(local_img_path), "wb") as img_f:
                                img_f.write(img_resp.content)
                            static_url = f"/static/images/{file_stem}/{img_rel_path}"
                            markdown_text = markdown_text.replace(img_rel_path, static_url)
                    except Exception:
                        pass

                all_pages.append(markdown_text)

            result_text = "\n\n".join(all_pages)
            self._save_cache(result_text)
            return result_text

        except ImportError:
            return f"[PDF解析需要 requests 库: pip install requests]"
        except Exception as e:
            return f"[PDF解析失败: {str(e)}]"

    def _extract_docx(self) -> str:
        try:
            from docx import Document
            doc = Document(str(self.file_path))
            return "\n".join([p.text for p in doc.paragraphs])
        except ImportError:
            return f"[DOCX解析需要python-docx库: {self.file_path.name}]"
        except Exception as e:
            return f"[DOCX解析失败: {str(e)}]"

    def _read_text(self) -> str:
        with open(str(self.file_path), 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def extract_headings(self) -> list:
        text = self.extract_text()
        headings = []
        for i, line in enumerate(text.split("\n")):
            stripped = line.strip()
            if stripped.startswith("# "):
                headings.append({"level": 1, "text": stripped[2:].strip(), "index": i})
            elif stripped.startswith("## "):
                headings.append({"level": 2, "text": stripped[3:].strip(), "index": i})
            elif stripped.startswith("### "):
                headings.append({"level": 3, "text": stripped[4:].strip(), "index": i})
        return headings

    def get_page_count(self) -> int:
        return 0
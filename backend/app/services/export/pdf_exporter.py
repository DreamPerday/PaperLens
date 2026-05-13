import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional
from .html_exporter import HTMLExporter

_SCRIPT_PATH = Path(__file__).parent / "_pdf_generator.py"
_SCRIPT_CONTENT = r'''
import sys
import json
import os
from playwright.sync_api import sync_playwright

data_path = sys.argv[1]
with open(data_path, "r", encoding="utf-8-sig") as f:
    data = json.load(f)

html_content = data["html_content"]
title = data["title"].replace('"', "'").replace("<", "").replace(">", "")
page_size = data["page_size"]
output_path = data["output_path"]
html_path = data_path + ".html"

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--font-render-hinting=none",
                "--disable-web-security",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            locale="zh-CN",
        )
        page = context.new_page()

        page.goto("file:///" + html_path.replace("\\", "/"), wait_until="load", timeout=120000)

        # Wait for images to load
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except:
            page.wait_for_timeout(5000)

        # Scroll the full page to trigger lazy-loaded images
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        page.evaluate("window.scrollTo(0, 0)")

        page.pdf(
            path=output_path,
            format=page_size,
            print_background=True,
            display_header_footer=True,
            header_template="<div style='font-size:10pt;text-align:center;width:100%;color:#666;'>" + title + "</div>",
            footer_template="<div style='font-size:10pt;text-align:center;width:100%;color:#666;'>Page <span class='pageNumber'></span> of <span class='totalPages'></span></div>",
            margin={
                "top": "2.5cm",
                "bottom": "2cm",
                "left": "2cm",
                "right": "2cm"
            }
        )
        context.close()
        browser.close()
    print("SUCCESS")
except Exception as e:
    import traceback
    print(f"ERROR: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
finally:
    for p in [data_path, html_path]:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except:
            pass
'''

if not _SCRIPT_PATH.exists():
    _SCRIPT_PATH.write_text(_SCRIPT_CONTENT, encoding="utf-8")

class PDFExporter:
    def __init__(self):
        self.html_exporter = HTMLExporter()
    
    async def export(self, original_text: str, translated_text: str, doc_id: str, title: str = "Translation",
                    include_original: bool = True, include_translation: bool = True,
                    embed_images: bool = True, page_size: str = "A4", font_size: int = 12,
                    include_toc: bool = False, watermark: Optional[str] = None,
                    watermark_pos: str = "bottom", theme: str = "academic",
                    cover_page: bool = False, subtitle: str = "",
                    watermark_tiled: bool = False, **kwargs) -> Dict[str, bytes]:
        
        html_result = await self.html_exporter.export(
            original_text, translated_text, doc_id, title,
            include_original, include_translation, embed_images,
            theme, page_size, font_size, include_toc, watermark, watermark_pos,
            cover_page, subtitle, watermark_tiled
        )
        
        temp_dir = Path(__file__).parent / "_temp_pdf"
        temp_dir.mkdir(exist_ok=True)
        
        temp_prefix = f"doc_{doc_id[:8]}_"
        output_path = str(temp_dir / f"{temp_prefix}out.pdf")
        data_path = str(temp_dir / f"{temp_prefix}data.json")
        
        try:
            script_data = {
                "html_content": html_result["content"],
                "title": title,
                "page_size": page_size,
                "output_path": output_path
            }
            
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(script_data, f, ensure_ascii=False)
            
            result = subprocess.run(
                [sys.executable, str(_SCRIPT_PATH), data_path],
                capture_output=True,
                text=True,
                timeout=90,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode != 0 or not os.path.exists(output_path):
                error_output = result.stderr or result.stdout or "Unknown error"
                raise RuntimeError(f"PDF生成失败: {error_output[:1000]}")
            
            with open(output_path, "rb") as f:
                pdf_bytes = f.read()
            
            return {
                "content": pdf_bytes,
                "mime": "application/pdf",
                "extension": ".pdf"
            }
        
        finally:
            for path in [output_path, data_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            for f in temp_dir.glob(f"{temp_prefix}*"):
                try:
                    f.unlink()
                except Exception:
                    pass
    
    def shutdown(self):
        pass
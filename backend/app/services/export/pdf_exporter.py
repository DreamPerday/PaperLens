import asyncio
from io import BytesIO
from typing import Dict, Optional
from .html_exporter import HTMLExporter

class PDFExporter:
    def __init__(self):
        self.html_exporter = HTMLExporter()
        self.playwright = None
    
    async def _ensure_playwright(self):
        if self.playwright is None:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
    
    async def export(self, original_text: str, translated_text: str, doc_id: str, title: str = "Translation",
                    include_original: bool = True, include_translation: bool = True,
                    embed_images: bool = True, page_size: str = "A4", font_size: int = 12,
                    include_toc: bool = False, watermark: Optional[str] = None) -> Dict[str, bytes]:
        
        html_result = await self.html_exporter.export(
            original_text, translated_text, doc_id, title,
            include_original, include_translation, embed_images,
            "academic", page_size, font_size, include_toc, watermark
        )
        
        await self._ensure_playwright()
        
        browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--font-render-hinting=none"
            ]
        )
        
        try:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 1024},
                locale="zh-CN"
            )
            
            page = await context.new_page()
            await page.set_content(html_result["content"], wait_until="networkidle")
            
            await page.wait_for_timeout(3000)
            
            pdf_bytes = await page.pdf(
                format=page_size,
                print_background=True,
                display_header_footer=True,
                header_template='<div style="font-size: 10pt; text-align: center; width: 100%; color: #666;">'
                              f'{title}</div>',
                footer_template='<div style="font-size: 10pt; text-align: center; width: 100%; color: #666;">'
                              'Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
                margin={
                    "top": "2cm",
                    "bottom": "2cm",
                    "left": "2cm",
                    "right": "2cm"
                }
            )
            
            await page.close()
            await context.close()
            
            return {
                "content": pdf_bytes,
                "mime": "application/pdf",
                "extension": ".pdf"
            }
        
        finally:
            await browser.close()
    
    async def shutdown(self):
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

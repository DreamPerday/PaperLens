
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

# Save HTML to a file for goto() instead of set_content()
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
            accept_downloads=True
        )
        page = context.new_page()
        page.goto("file:///" + html_path.replace("\\", "/"), wait_until="load", timeout=120000)
        try:
            page.wait_for_function(
                """(() => {
                    const hasKatex = document.querySelector('script[src*="katex.min.js"]') !== null;
                    if (!hasKatex) return true;
                    const hasMath = document.querySelector('.math-block, .math-inline') !== null;
                    if (!hasMath) return true;
                    return document.querySelector('.katex, .katex-display') !== null;
                })()""",
                timeout=20000
            )
        except Exception:
            pass
        page.wait_for_timeout(1500)
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

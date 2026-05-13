import os
import hashlib
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

class TemplateManager:
    def __init__(self, template_dir: str = "templates/export"):
        self.template_dir = Path(template_dir)
        self._hash_file = self.template_dir / ".template_hashes"
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self._ensure_templates()

    def _ensure_templates(self):
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self._create_default_templates()

    def _load_hashes(self) -> dict:
        if not self._hash_file.exists():
            return {}
        hashes = {}
        with open(self._hash_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(":", 1)
                if len(parts) == 2:
                    hashes[parts[0]] = parts[1]
        return hashes

    def _save_hashes(self, hashes: dict):
        with open(self._hash_file, "w", encoding="utf-8") as f:
            for name, h in hashes.items():
                f.write(f"{name}:{h}\n")

    def _compute_hash(self, content: str) -> str:
        return hashlib.md5(content.encode("utf-8")).hexdigest()
    
    def _create_default_templates(self):
        academic_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <style>
        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            color-adjust: exact !important;
        }
        
        @page {
            size: {{ page_size }};
            margin: 2.5cm 2cm;
            {% if watermark %}
            @bottom-right {
                content: "";
            }
            {% else %}
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #888;
            }
            {% endif %}
        }
        
        body {
            font-family: 'Times New Roman', 'SimSun', 'Songti SC', 'Noto Serif CJK SC', serif;
            line-height: 1.85;
            font-size: {{ font_size }}pt;
            color: #222;
            max-width: 900px;
            margin: 0 auto;
            padding: 2em;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
        }
        
        .content-section {
            padding: 1em 0;
        }
        
        .content-section p:first-child {
            margin-top: 0;
        }
        
        {% if cover_page %}
        .cover {
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            page-break-after: always;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        }
        
        .cover h1 {
            font-size: 2.5em;
            color: #1a1a2e;
            margin-bottom: 0.5em;
            border: none;
            padding: 0;
        }
        
        .cover .subtitle {
            font-size: 1.2em;
            color: #666;
            margin-bottom: 2em;
        }
        
        .cover .meta {
            font-size: 0.9em;
            color: #999;
            margin-top: 3em;
        }
        {% endif %}
        
        .page-break {
            page-break-after: always;
        }
        
        .avoid-break {
            page-break-inside: avoid;
            break-inside: avoid;
        }
        
        .keep-with-next {
            page-break-after: avoid;
            break-after: avoid;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-weight: bold;
            page-break-after: avoid;
            break-after: avoid;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        
        h1 {
            font-size: 1.6em;
            border-bottom: 2px solid #333;
            padding-bottom: 0.3em;
            margin-top: 0;
        }
        
        h2 {
            font-size: 1.35em;
            border-bottom: 1px solid #ddd;
            padding-bottom: 0.2em;
        }
        
        h3 { font-size: 1.15em; }
        h4 { font-size: 1.05em; }
        h5 { font-size: 1em; }
        h6 { font-size: 0.95em; }
        
        p {
            margin: 0.7em 0;
            text-align: justify;
            text-indent: 2em;
            orphans: 3;
            widows: 3;
        }
        
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em auto;
            page-break-inside: avoid;
            break-inside: avoid;
        }
        
        .table-wrapper {
            overflow-x: auto;
            max-width: 100%;
            page-break-inside: avoid;
            break-inside: avoid;
        }
        
        .table-wrapper table {
            min-width: 100%;
            font-size: 0.8em;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
            page-break-inside: avoid;
            break-inside: avoid;
            table-layout: auto;
            word-break: break-word;
        }
        
        th, td {
            border: 1px solid #bbb;
            padding: 6px 10px;
            text-align: left;
            vertical-align: top;
            font-size: 0.85em;
        }
        
        th {
            background: #f0f0f0;
            font-weight: bold;
        }
        
        tr:nth-child(even) {
            background: #fafafa;
        }
        
        pre {
            background: #f6f8fa;
            padding: 1em;
            border-radius: 4px;
            overflow-x: auto;
            page-break-inside: avoid;
            break-inside: avoid;
            border: 1px solid #e1e4e8;
            font-size: 0.85em;
            line-height: 1.5;
        }
        
        code {
            font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            background: #f3f4f6;
            padding: 0.15em 0.35em;
            border-radius: 3px;
        }
        
        pre code {
            background: none;
            padding: 0;
        }
        
        blockquote {
            border-left: 3px solid #4a90d9;
            padding: 0.5em 1em;
            margin: 1em 0;
            color: #555;
            background: #f8f9fa;
            page-break-inside: avoid;
            break-inside: avoid;
        }
        
        blockquote p {
            text-indent: 0;
            margin: 0.3em 0;
        }
        
        .section-title {
            font-size: 1.4em;
            font-weight: bold;
            color: #333;
            border-bottom: 2px solid #333;
            padding-bottom: 0.3em;
            margin-top: 2em;
            margin-bottom: 1em;
        }
        
        .toc {
            page-break-after: always;
            margin-bottom: 2em;
        }
        
        .toc h2 {
            border-bottom: none;
            margin-bottom: 0.5em;
        }
        
        .toc-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        
        .toc-list li {
            margin: 0.3em 0;
            padding: 0.2em 0;
        }
        
        .toc-list a {
            color: inherit;
            text-decoration: none;
        }
        
        .toc-list a:hover {
            text-decoration: underline;
        }
        
        .watermark-container {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
            overflow: hidden;
            z-index: 9999;
        }
        
        .watermark {
            position: absolute;
            font-size: 72pt;
            font-weight: bold;
            color: rgba(0, 0, 0, 0.06);
            transform: rotate(-30deg);
            white-space: nowrap;
            {% if watermark_pos == 'center' %}
            top: 40%;
            left: 30%;
            {% elif watermark_pos == 'top' %}
            top: 10%;
            left: 25%;
            {% else %}
            bottom: 15%;
            right: -5%;
            {% endif %}
        }
        
        {% if watermark_tiled %}
        .watermark-tiled {
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            display: flex;
            flex-wrap: wrap;
            align-content: center;
            justify-content: center;
        }
        
        .watermark-tiled span {
            width: 30%;
            margin: 1%;
            font-size: 48pt;
            text-align: center;
        }
        {% endif %}
        
        .page-header {
            display: none;
        }
        
        .math-block {
            text-align: center;
            padding: 1em 0;
            page-break-inside: avoid;
            break-inside: avoid;
        }
        
        .math-inline {
            padding: 0 0.2em;
        }
        
        .figure {
            text-align: center;
            margin: 1.5em 0;
            page-break-inside: avoid;
            break-inside: avoid;
        }
        
        .figure img {
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
        
        .figure-caption {
            font-size: 0.85em;
            color: #666;
            margin-top: 0.5em;
            text-align: center;
            font-style: italic;
        }
        
        hr {
            border: none;
            border-top: 1px solid #ddd;
            margin: 2em 0;
        }
        
        ul, ol {
            margin: 0.7em 0;
            padding-left: 2em;
        }
        
        li {
            margin: 0.3em 0;
        }
        
        .highlight {
            background: #fff3cd;
            padding: 0.1em 0.3em;
            border-radius: 2px;
        }
        
        @media print {
            .watermark-container {
                position: fixed;
            }
        }
    </style>
</head>
<body>
    {% if cover_page %}
    <div class="cover">
        <h1>{{ title }}</h1>
        {% if subtitle %}<div class="subtitle">{{ subtitle }}</div>{% endif %}
        <div class="meta">
            <div>Generated: {{ "now"|date }}</div>
        </div>
    </div>
    {% endif %}
    
    {% if watermark %}
    <div class="watermark-container">
        <div class="watermark">{{ watermark }}</div>
    </div>
    {% endif %}
    
    {% if include_toc and toc %}
    <div class="toc avoid-break">
        <h2 class="section-title">目录 / Table of Contents</h2>
        <div class="toc-list">
            {{ toc|safe }}
        </div>
        <hr class="page-break" style="border: none; page-break-after: always;">
    </div>
    {% endif %}
    
    {% if include_original %}
    <div class="content-section avoid-break">
        <h1 class="section-title">原文 / Original</h1>
        {{ original_content|safe }}
    </div>
    {% endif %}
    
    {% if include_translation %}
    {% if include_original %}
    <hr class="page-break" style="border: none; page-break-after: always;">
    {% endif %}
    <div class="content-section avoid-break">
        <h1 class="section-title">译文 / Translation</h1>
        {{ translated_content|safe }}
    </div>
    {% endif %}
    
</body>
</html>"""
        
        modern_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <style>
        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
        
        @page {
            size: {{ page_size }};
            margin: 2cm;
            @bottom-right {
                content: counter(page);
                font-size: 10pt;
                color: #888;
            }
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            line-height: 1.8;
            font-size: {{ font_size }}pt;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 2em;
        }
        
        .content-section {
            padding: 1em 0;
        }
        
        .content-section p:first-child {
            margin-top: 0;
        }
        
        {% if cover_page %}
        .cover {
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 0 3cm;
            page-break-after: always;
            background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .cover h1 {
            font-size: 2.8em;
            color: white;
            margin-bottom: 0.3em;
            border: none;
            padding: 0;
        }
        
        .cover .subtitle {
            font-size: 1.4em;
            opacity: 0.9;
            margin-bottom: 2em;
        }
        
        .cover .meta {
            font-size: 0.9em;
            opacity: 0.7;
            margin-top: auto;
        }
        {% endif %}
        
        .page-break {
            page-break-after: always;
        }
        
        .avoid-break {
            page-break-inside: avoid;
            break-inside: avoid;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-weight: 600;
            page-break-after: avoid;
            break-after: avoid;
            margin-top: 1.8em;
            margin-bottom: 0.6em;
        }
        
        h1 {
            font-size: 1.8em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 0.3em;
            margin-top: 0;
            background: linear-gradient(90deg, #667eea 0%, transparent 100%);
            padding-left: 0.5em;
        }
        
        h2 {
            font-size: 1.4em;
            border-left: 4px solid #667eea;
            padding-left: 0.5em;
        }
        
        h3 { font-size: 1.2em; }
        h4 { font-size: 1.1em; }
        h5 { font-size: 1em; }
        h6 { font-size: 0.95em; }
        
        p {
            margin: 0.8em 0;
            text-indent: 2em;
            orphans: 3;
            widows: 3;
        }
        
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1.2em auto;
            page-break-inside: avoid;
            break-inside: avoid;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .table-wrapper {
            overflow-x: auto;
            max-width: 100%;
            page-break-inside: avoid;
            break-inside: avoid;
        }
        
        .table-wrapper table {
            min-width: 100%;
            font-size: 0.8em;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.2em 0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
            page-break-inside: avoid;
            table-layout: auto;
            word-break: break-word;
        }
        
        th, td {
            border: none;
            padding: 10px 14px;
            text-align: left;
            vertical-align: top;
            font-size: 0.85em;
        }
        
        th {
            background: #667eea;
            color: white;
            font-weight: 600;
        }
        
        td {
            border-bottom: 1px solid #eee;
        }
        
        tr:last-child td {
            border-bottom: none;
        }
        
        tr:nth-child(even) {
            background: #f8f9ff;
        }
        
        pre {
            background: #f6f8fa;
            padding: 1em;
            border-radius: 8px;
            overflow-x: auto;
            page-break-inside: avoid;
            border-left: 4px solid #667eea;
            font-size: 0.9em;
        }
        
        code {
            font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
            font-size: 0.9em;
            background: #f0f0f5;
            padding: 0.15em 0.4em;
            border-radius: 4px;
        }
        
        pre code {
            background: none;
            padding: 0;
        }
        
        blockquote {
            border-left: 4px solid #764ba2;
            background: linear-gradient(90deg, rgba(118, 75, 162, 0.08) 0%, transparent 100%);
            padding: 0.8em 1.2em;
            margin: 1.2em 0;
            border-radius: 0 8px 8px 0;
        }
        
        .section-title {
            font-size: 1.6em;
            font-weight: 600;
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 0.3em;
            margin-top: 2em;
            margin-bottom: 1em;
        }
        
        .toc {
            page-break-after: always;
            margin-bottom: 2em;
            background: #f8f9ff;
            padding: 2em;
            border-radius: 12px;
        }
        
        .toc h2 {
            border: none;
            border-bottom: 2px solid #667eea;
        }
        
        .toc-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        
        .toc-list li {
            margin: 0.5em 0;
            padding: 0.3em 0;
            border-bottom: 1px dashed #ddd;
        }
        
        .toc-list li:last-child {
            border-bottom: none;
        }
        
        .watermark-container {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
            overflow: hidden;
            z-index: 9999;
        }
        
        .watermark {
            position: absolute;
            font-size: 80pt;
            font-weight: 700;
            color: rgba(102, 126, 234, 0.08);
            transform: rotate(-25deg);
            white-space: nowrap;
            {% if watermark_pos == 'center' %}
            top: 35%;
            left: 25%;
            {% elif watermark_pos == 'top' %}
            top: 8%;
            left: 20%;
            {% else %}
            bottom: 12%;
            right: -5%;
            {% endif %}
        }
        
        .figure {
            text-align: center;
            margin: 1.5em 0;
            page-break-inside: avoid;
        }
        
        .figure-caption {
            font-size: 0.85em;
            color: #888;
            margin-top: 0.8em;
        }
        
        hr {
            border: none;
            border-top: 1px solid #eee;
            margin: 2em 0;
        }
        
        ul, ol {
            margin: 0.8em 0;
            padding-left: 2em;
        }
        
        li {
            margin: 0.4em 0;
        }
        
        @media print {
            .watermark-container {
                position: fixed;
            }
        }
    </style>
</head>
<body>
    {% if cover_page %}
    <div class="cover">
        <h1>{{ title }}</h1>
        {% if subtitle %}<div class="subtitle">{{ subtitle }}</div>{% endif %}
        <div class="meta">
            <div>Generated: {{ "now"|date }}</div>
        </div>
    </div>
    {% endif %}
    
    {% if watermark %}
    <div class="watermark-container">
        <div class="watermark">{{ watermark }}</div>
    </div>
    {% endif %}
    
    {% if include_toc and toc %}
    <div class="toc avoid-break">
        <h2 class="section-title">目录</h2>
        <div class="toc-list">
            {{ toc|safe }}
        </div>
        <hr class="page-break" style="border: none; page-break-after: always;">
    </div>
    {% endif %}
    
</body>
</html>"""
        
        dark_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <style>
        @page {
            size: {{ page_size }};
            margin: 2cm;
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #888;
            }
        }

        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        body {
            font-family: 'Segoe UI', 'Microsoft YaHei', system-ui, sans-serif;
            line-height: 1.8;
            font-size: {{ font_size }}pt;
            color: #e4e4e7;
            background: #1a1a1a;
            max-width: 900px;
            margin: 0 auto;
            padding: 2em;
        }
        
        h1, h2, h3 { color: #f0f0f0; page-break-after: avoid; }
        h1 { font-size: 1.6em; border-bottom: 2px solid #4a90d9; padding-bottom: 0.3em; }
        h2 { font-size: 1.3em; border-bottom: 1px solid #333; }
        
        p { margin: 0.7em 0; text-indent: 2em; }
        
        img { max-width: 100%; display: block; margin: 1em auto; page-break-inside: avoid; }
        
        pre {
            background: #252526;
            padding: 1em;
            border-radius: 6px;
            overflow-x: auto;
            page-break-inside: avoid;
            border: 1px solid #333;
        }
        
        code { background: #333; padding: 0.2em 0.4em; border-radius: 3px; font-family: 'Cascadia Code', monospace; }
        pre code { background: none; padding: 0; }
        
        blockquote { border-left: 3px solid #8b5cf6; background: #252526; padding: 0.5em 1em; margin: 1em 0; }
        
        .section-title { font-size: 1.4em; color: #4a90d9; border-bottom: 2px solid #4a90d9; padding-bottom: 0.3em; margin-top: 2em; }
        
        .toc { page-break-after: always; }
        
        .watermark-container {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            pointer-events: none;
            overflow: hidden;
            z-index: 9999;
        }
        
        .watermark {
            position: absolute;
            font-size: 72pt;
            font-weight: bold;
            color: rgba(255, 255, 255, 0.03);
            transform: rotate(-30deg);
            white-space: nowrap;
            bottom: 15%;
            right: -5%;
        }
        
        .math-block { text-align: center; padding: 1em 0; }
        
        .table-wrapper {
            overflow-x: auto;
            max-width: 100%;
            page-break-inside: avoid;
            break-inside: avoid;
        }
        
        table { width: 100%; border-collapse: collapse; margin: 1em 0; table-layout: auto; word-break: break-word; }
        th, td { border: 1px solid #333; padding: 6px 10px; vertical-align: top; font-size: 0.85em; }
        th { background: #252526; }
        
        hr { border: none; border-top: 1px solid #333; margin: 2em 0; }
    </style>
</head>
<body>
    {% if watermark %}
    <div class="watermark-container"><div class="watermark">{{ watermark }}</div></div>
    {% endif %}
    
    {% if include_toc and toc %}
    <div class="toc"><h2 class="section-title">目录</h2>{{ toc|safe }}</div>
    <hr style="border: none; page-break-after: always;">
    {% endif %}
    
    {% if include_original %}
    <div>
        <h1 class="section-title">原文 / Original</h1>
        {{ original_content|safe }}
    </div>
    {% endif %}
    
    {% if include_translation %}
    {% if include_original %}<hr style="border: none; page-break-after: always;">{% endif %}
    <div>
        <h1 class="section-title">译文 / Translation</h1>
        {{ translated_content|safe }}
    </div>
    {% endif %}
    
</body>
</html>"""
        
        compact_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <style>
        @page {
            size: {{ page_size }};
            margin: 1.5cm;
            @bottom-center {
                content: "Page " counter(page);
                font-size: 9pt;
                color: #666;
            }
        }

        body {
            font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            font-size: {{ font_size }}pt;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 2em;
        }
        
        h1 { font-size: 1.4em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; page-break-after: avoid; }
        h2 { font-size: 1.2em; page-break-after: avoid; }
        h3 { font-size: 1.1em; page-break-after: avoid; }
        
        p { margin: 0.5em 0; text-indent: 2em; }
        img { max-width: 100%; page-break-inside: avoid; }
        pre { font-size: 0.85em; padding: 0.5em; background: #f5f5f5; page-break-inside: avoid; }
        code { font-size: 0.9em; background: #f0f0f0; padding: 0.1em 0.2em; }
        
        .section-title { font-size: 1.2em; border-bottom: 1px solid #333; padding-bottom: 0.2em; margin-top: 1.5em; }
        
        hr { border: none; border-top: 1px solid #ddd; margin: 1.5em 0; }
    </style>
</head>
<body>
    {% if include_original %}
    <div class="content-section">
        <h1 class="section-title">原文 / Original</h1>
        {{ original_content|safe }}
    </div>
    {% endif %}
    
    {% if include_translation %}
    {% if include_original %}<hr>{% endif %}
    <div class="content-section">
        <h1 class="section-title">译文 / Translation</h1>
        {{ translated_content|safe }}
    </div>
    {% endif %}
    
</body>
</html>"""
        
        templates = {
            "academic.html": academic_template,
            "modern.html": modern_template,
            "dark.html": dark_template,
            "compact.html": compact_template
        }
        
        existing_hashes = self._load_hashes()
        new_hashes = {}
        
        for name, content in templates.items():
            template_path = self.template_dir / name
            content_hash = self._compute_hash(content)
            new_hashes[name] = content_hash
            if existing_hashes.get(name) != content_hash or not template_path.exists():
                template_path.write_text(content, encoding="utf-8")
        
        if new_hashes != existing_hashes:
            self._save_hashes(new_hashes)
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
    
    def render(self, template_name: str, **context) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    def get_available_templates(self) -> list:
        return [f.stem for f in self.template_dir.glob("*.html")]

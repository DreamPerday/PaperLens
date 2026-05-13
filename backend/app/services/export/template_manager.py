import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

class TemplateManager:
    def __init__(self, template_dir: str = "templates/export"):
        self.template_dir = Path(template_dir)
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
    
    def _create_default_templates(self):
        academic_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js" onload="renderMathInElement(document.body);"></script>
    <style>
        @page {
            size: {{ page_size }};
            margin: 2cm;
            @top-center {
                content: "{{ title }}";
                font-size: 10pt;
                color: #666;
            }
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Times New Roman', 'SimSun', serif;
            line-height: 1.8;
            font-size: {{ font_size }}pt;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        h1, h2, h3, h4, h5, h6 {
            page-break-after: avoid;
            font-weight: bold;
        }
        
        h1 { font-size: 1.8em; border-bottom: 2px solid #333; padding-bottom: 0.3em; margin-top: 2em; }
        h2 { font-size: 1.5em; margin-top: 1.8em; }
        h3 { font-size: 1.3em; margin-top: 1.5em; }
        h4 { font-size: 1.1em; }
        
        p { margin: 0.8em 0; text-align: justify; }
        
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em auto;
            page-break-inside: avoid;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
            page-break-inside: avoid;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }
        
        th { background: #f5f5f5; font-weight: bold; }
        
        pre {
            background: #f8f9fa;
            padding: 1em;
            border-radius: 6px;
            overflow-x: auto;
            page-break-inside: avoid;
            border: 1px solid #e9ecef;
        }
        
        code {
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
        }
        
        blockquote {
            border-left: 4px solid #007bff;
            padding-left: 1em;
            margin: 1em 0;
            color: #666;
            background: #f8f9fa;
            padding: 1em;
        }
        
        .math-display {
            text-align: center;
            margin: 1em 0;
        }
        
        .dual-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2em;
        }
        
        .original-section { border-right: 1px solid #eee; padding-right: 2em; }
        .translation-section { padding-left: 2em; }
        
        .watermark {
            position: fixed;
            bottom: 2cm;
            right: 2cm;
            opacity: 0.1;
            font-size: 48pt;
            color: #000;
            pointer-events: none;
            transform: rotate(-15deg);
        }
        
        @media print {
            body { padding: 0; max-width: none; }
            .watermark { display: block; }
        }
    </style>
</head>
<body>
    {% if watermark %}
    <div class="watermark">{{ watermark }}</div>
    {% endif %}
    
    {% if include_toc %}
    <div class="toc">
        <h2>Table of Contents</h2>
        {{ toc|safe }}
    </div>
    {% endif %}
    
    {% if include_original %}
    <div class="original-section">
        <h1>Original</h1>
        {{ original_content|safe }}
    </div>
    {% endif %}
    
    {% if include_translation %}
    <div class="{% if include_original %}translation-section{% endif %}">
        <h1>Translation</h1>
        {{ translated_content|safe }}
    </div>
    {% endif %}
    
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            renderMathInElement(document.body, {
                delimiters: [
                    {left: "$$", right: "$$", display: true},
                    {left: "$", right: "$", display: false}
                ]
            });
        });
    </script>
</body>
</html>
"""
        dark_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            line-height: 1.7;
            font-size: {{ font_size }}pt;
            color: #e4e4e7;
            background: #18181b;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }
        h1, h2, h3 { color: #fafafa; }
        pre { background: #27272a; padding: 1em; border-radius: 8px; }
        code { background: #3f3f46; padding: 0.2em 0.4em; border-radius: 4px; }
        blockquote { border-left: 4px solid #8b5cf6; background: #27272a; }
        table { border-color: #3f3f46; }
        th { background: #3f3f46; }
    </style>
</head>
<body>
    {{ original_content|safe }}
    {{ translated_content|safe }}
</body>
</html>
"""
        compact_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body { font-family: sans-serif; line-height: 1.5; font-size: 12pt; max-width: 100%; margin: 0; padding: 1rem; }
        h1 { font-size: 1.4em; } h2 { font-size: 1.2em; } h3 { font-size: 1.1em; }
        pre { font-size: 0.9em; padding: 0.5em; }
        img { max-width: 100%; }
        table { font-size: 0.9em; }
    </style>
</head>
<body>
    {{ original_content|safe }}
    {{ translated_content|safe }}
</body>
</html>
"""
        templates = {
            "academic.html": academic_template,
            "dark.html": dark_template,
            "compact.html": compact_template
        }
        
        for name, content in templates.items():
            template_path = self.template_dir / name
            if not template_path.exists():
                template_path.write_text(content, encoding="utf-8")
    
    def render(self, template_name: str, **context) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    def get_available_templates(self) -> list:
        return [f.stem for f in self.template_dir.glob("*.html")]

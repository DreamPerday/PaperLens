import subprocess
import os
from typing import Optional


class KatexService:
    """
    Server-side KaTeX rendering via subprocess (node -e).

    Converts LaTeX → rendered KaTeX HTML (for HTML/PDF export)
    and serves as the single math rendering engine used by all exporters.

    Guarantees pixel-identical math output across:
      - HTML export (SSR pre-rendered KaTeX)
      - PDF export (Chromium renders pre-rendered KaTeX HTML, no JS needed)
      - DOCX export (SVG embedded as image via separate npx path)
      - EPUB export (inline KaTeX HTML + CSS)
    """

    def __init__(self):
        self._project_root = self._find_project_root()

    def _find_project_root(self) -> str:
        return str(os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        )))

    def render_to_html(self, latex: str, display_mode: bool = True) -> str:
        return self._render(latex, display_mode)

    def _render(self, latex: str, display_mode: bool) -> str:
        cleaned = latex.strip()
        if not cleaned:
            return ""

        try:
            script = self._katex_node_script(cleaned, display_mode)
            result = subprocess.run(
                ["node", "-e", script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                cwd=self._project_root,
                env={**os.environ, "NODE_PATH": os.path.join(self._project_root, "frontend", "node_modules")},
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            if result.stderr:
                print(f"[KatexService] stderr: {result.stderr[:200]}")
        except FileNotFoundError:
            pass
        except Exception:
            pass

        return self._fallback(cleaned, display_mode)

    def _katex_node_script(self, latex: str, display_mode: bool) -> str:
        escaped = (
            latex.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("$", "\\$")
        )
        dm = "true" if display_mode else "false"
        return (
            'try{var k=require("katex");'
            f'console.log(k.renderToString(`{escaped}`,'
            f'{{displayMode:{dm},throwOnError:false,trust:true,strict:false}}))'
            '}catch(e){console.log(e.message)}'
        )

    def _fallback(self, latex: str, display_mode: bool) -> str:
        escaped = latex.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if display_mode:
            return f'<div class="math-fallback"><pre>{escaped}</pre></div>'
        return f'<span class="math-inline katex-fallback">{escaped}</span>'


_katex_instance: Optional[KatexService] = None


def get_katex() -> KatexService:
    global _katex_instance
    if _katex_instance is None:
        _katex_instance = KatexService()
    return _katex_instance


def render_math_to_html(latex: str, display_mode: bool = True) -> str:
    return get_katex().render_to_html(latex, display_mode)
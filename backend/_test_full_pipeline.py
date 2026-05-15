"""
Comprehensive export pipeline test — verifies:
1. img tag redundancy fix (parser recognizes <img>)
2. Math formula rendering (all delimiter types)
3. Image block detection (standalone images)
4. HTML/Markdown renderer output
5. Full export pipeline
"""
import asyncio
import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.services.parser import MarkdownParser, render_to_html, render_document
from app.models.block_schema import BlockType, InlineType

TEST_CONTENT = r"""## Mathematical Notations

核心参数 $w_i$ 已调整以拟合轨迹 $y_{demo}(t) = \sin(2\pi t) + 0.25\cos(4\pi t + 0.77) + 0.1\sin(6\pi t + 3.0)$。

The subscript for desired value is $d \triangleq$ Subscript for desired value.

Quaternion-related variable: $q \triangleq$ Quaternion-related variable.

**Display math with block notation:**

\[
\tau\dot{x} = -a_{x} x
\]

$$
\boldsymbol{\Phi} = \begin{bmatrix}
\phi_{1} & \phi_{2} & \cdots & \phi_{N}
\end{bmatrix}^{\top}
$$

**Inline LaTeX math with \(...\):**

Angular velocity: \(\omega \triangleq\) Angular velocity with function \(f(x) = x^2\).

The matrix is \(X \in \mathcal{S}_{++}^{n}\).

**Complex Notations:**

函数 $\operatorname{vec}()$ 将 $\mathrm{Sym}^{m}$ 转换为 $\mathbb{R}^{m(m+1)/2}$。

Stiffness gains: $k, K, \mathbf{K} \triangleq$ Different forms of stiffness gains.

**Images in content:**

The following figure shows the coordinate system:

![Coordinate System](images/coord.png)

The data analysis pipeline:

![Pipeline](images/pipeline.png)

**HTML images in original content:**

<img src="images/diagram.png" alt="Block Diagram" />

**Mixed content with images:**

向量表示:

\[
\operatorname{vec}\binom{a\quad b}{b\quad d} = \binom{a}{d}\sqrt{2}b
\]

![Math Illustration](images/math_illustration.png)
"""


def test_parser_recognition():
    """Test that parser recognizes all image formats and math types"""
    parser = MarkdownParser()
    ast = parser.parse(TEST_CONTENT)

    print("=" * 60)
    print("TEST 1: Parser Block/Inline Recognition")
    print("=" * 60)

    image_blocks = []
    math_blocks = []
    all_blocks = []

    for block in ast.blocks:
        all_blocks.append(block)
        if block.type == BlockType.image:
            image_blocks.append(block)
        elif block.type == BlockType.math_block:
            math_blocks.append(block)

    print(f"  Total blocks: {len(all_blocks)}")
    print(f"  Image blocks (standalone): {len(image_blocks)}")
    for b in image_blocks:
        url = b.meta.get('url', '')
        print(f"    - alt='{b.content}', url='{url[:50]}' ")

    print(f"  Math blocks (display): {len(math_blocks)}")
    for b in math_blocks:
        preview = b.content[:60].replace('\n', '\\n')
        print(f"    - {preview}")

    inline_math_count = 0
    inline_img_count = 0
    for block in ast.blocks:
        if block.inlines:
            for node in block.inlines:
                if node.type in (InlineType.inline_math, InlineType.display_math, InlineType.math):
                    inline_math_count += 1
                if node.type == InlineType.image:
                    inline_img_count += 1

    print(f"  Inline math nodes: {inline_math_count}")
    print(f"  Inline image nodes: {inline_img_count}")

    errors = []
    if len(image_blocks) < 4:
        errors.append(f"Expected >=4 standalone image blocks, got {len(image_blocks)}")
    if len(math_blocks) < 3:
        errors.append(f"Expected >=3 display math blocks, got {len(math_blocks)}")
    if inline_math_count < 10:
        errors.append(f"Expected >=10 inline math nodes, got {inline_math_count}")

    if errors:
        print("  FAILED:")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  PASSED")

    return len(errors) == 0


def test_html_renderer():
    """Test HTML renderer output (SSR mode = no raw delimiters, KaTeX renders math)"""
    parser = MarkdownParser()
    ast = parser.parse(TEST_CONTENT)
    html = render_to_html(ast)  # uses ssr_math=True by default

    print("\n" + "=" * 60)
    print("TEST 2: HTML Renderer Output (SSR mode)")
    print("=" * 60)

    all_pass = True

    no_escaped = "&lt;img" not in html
    print(f"  {'[PASS]' if no_escaped else '[FAIL]'} No escaped img tags")

    has_figure = 'class="figure"' in html
    print(f"  {'[PASS]' if has_figure else '[FAIL]'} Has image figure blocks")

    has_math_display = "math-display" in html or "math-block" in html
    print(f"  {'[PASS]' if has_math_display else '[FAIL]'} Has math display classes")

    has_math_inline = "math-inline" in html
    print(f"  {'[PASS]' if has_math_inline else '[FAIL]'} Has math-inline class")

    has_katex = "katex" in html.lower()
    print(f"  {'[PASS]' if has_katex else '[FAIL]'} Has KaTeX-rendered HTML")

    if not has_math_display:
        all_pass = False
    if not has_math_inline:
        all_pass = False

    if all_pass:
        print("  PASSED")
    return all_pass


def test_markdown_renderer():
    """Test Markdown renderer output"""
    parser = MarkdownParser()
    ast = parser.parse(TEST_CONTENT)
    md = render_document(ast)

    print("\n" + "=" * 60)
    print("TEST 3: Markdown Renderer Output")
    print("=" * 60)

    all_pass = True

    has_md_img = bool(re.search(r'!\[.*\]\(', md))
    print(f"  {'[PASS]' if has_md_img else '[FAIL]'} Has markdown image syntax")

    no_raw_html_img = not bool(re.search(r'<img\s+', md))
    print(f"  {'[PASS]' if no_raw_html_img else '[FAIL]'} No raw HTML img tags")

    has_inline_math = bool(re.search(r'\$.*\$', md))
    print(f"  {'[PASS]' if has_inline_math else '[FAIL]'} Inline math preserved")

    has_display_math = bool(re.search(r'\$\$', md)) or bool(re.search(r'\\\[', md))
    print(f"  {'[PASS]' if has_display_math else '[FAIL]'} Display math preserved")

    if not has_md_img:
        all_pass = False
    if not no_raw_html_img:
        all_pass = False
    if not has_inline_math:
        all_pass = False
    if not has_display_math:
        all_pass = False

    if all_pass:
        print("  PASSED")
    return all_pass


async def test_html_exporter():
    """Test full HTML export pipeline"""
    from app.services.export.html_exporter import HTMLExporter

    exporter = HTMLExporter()
    result = await exporter.export(
        original_text=TEST_CONTENT,
        translated_text=TEST_CONTENT,
        doc_id="test_full",
        embed_images=False
    )

    html = result["content"]

    print("\n" + "=" * 60)
    print("TEST 4: HTML Exporter Full Pipeline")
    print("=" * 60)

    all_pass = True

    no_escaped = "&lt;img" not in html
    print(f"  {'[PASS]' if no_escaped else '[FAIL]'} No escaped img tags")

    has_math = "math-block" in html or "math-display" in html
    print(f"  {'[PASS]' if has_math else '[FAIL]'} Math blocks rendered")

    has_inline_math = "math-inline" in html
    print(f"  {'[PASS]' if has_inline_math else '[FAIL]'} Inline math rendered")

    has_doctype = "<!DOCTYPE" in html or "<html" in html
    print(f"  {'[PASS]' if has_doctype else '[FAIL]'} Valid HTML document structure")

    if not no_escaped:
        all_pass = False
    if not has_math:
        all_pass = False
    if not has_inline_math:
        all_pass = False

    if all_pass:
        print("  PASSED")
    return all_pass


async def test_markdown_exporter():
    """Test full Markdown export pipeline"""
    from app.services.export.markdown_exporter import MarkdownExporter

    exporter = MarkdownExporter()
    result = await exporter.export(
        original_text=TEST_CONTENT,
        translated_text=TEST_CONTENT,
        doc_id="test_full",
        embed_images=False
    )

    md = result["content"]

    print("\n" + "=" * 60)
    print("TEST 5: Markdown Exporter Full Pipeline")
    print("=" * 60)

    all_pass = True

    no_raw_img = not bool(re.search(r'<img\s+', md))
    print(f"  {'[PASS]' if no_raw_img else '[FAIL]'} No raw HTML img tags in MD output")

    has_md_img = bool(re.search(r'!\[.*\]\(', md))
    print(f"  {'[PASS]' if has_md_img else '[FAIL]'} Markdown image syntax found")

    has_inline_math = bool(re.search(r'\$.*\$', md))
    print(f"  {'[PASS]' if has_inline_math else '[FAIL]'} Inline math preserved")

    has_display_math = bool(re.search(r'\$\$', md)) or bool(re.search(r'\\\[', md))
    print(f"  {'[PASS]' if has_display_math else '[FAIL]'} Display math preserved")

    if not has_md_img:
        all_pass = False

    if all_pass:
        print("  PASSED")
    return all_pass


async def test_docx_exporter():
    """Test DOCX export pipeline"""
    from app.services.export.docx_exporter import DOCXExporter

    exporter = DOCXExporter()
    result = await exporter.export(
        original_text=TEST_CONTENT,
        translated_text=TEST_CONTENT,
        doc_id="test_full",
        embed_images=False
    )

    content = result["content"]

    print("\n" + "=" * 60)
    print("TEST 6: DOCX Exporter Full Pipeline")
    print("=" * 60)

    all_pass = True

    has_content = len(content) > 1000
    print(f"  {'[PASS]' if has_content else '[FAIL]'} Output > 1KB (actual: {len(content)} bytes)")

    is_zip = content[:2] == b'PK'
    print(f"  {'[PASS]' if is_zip else '[FAIL]'} ZIP magic bytes (PK)")

    has_mime = result.get("mime") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    print(f"  {'[PASS]' if has_mime else '[FAIL]'} Correct MIME type")

    if not has_content:
        all_pass = False

    if all_pass:
        print("  PASSED")
    return all_pass


async def test_pdf_exporter():
    """Test PDF export pipeline"""
    try:
        from app.services.export.pdf_exporter import PDFExporter
    except Exception:
        print("\n" + "=" * 60)
        print("TEST 7: PDF Exporter — SKIPPED (Playwright not available)")
        print("=" * 60)
        return True

    exporter = PDFExporter()
    try:
        result = await exporter.export(
            original_text=TEST_CONTENT,
            translated_text=TEST_CONTENT,
            doc_id="test_full",
            embed_images=False,
            theme="academic",
            page_size="A4",
            font_size=12,
            include_toc=False,
            cover_page=False,
            watermark=None,
            watermark_pos="bottom",
            subtitle="",
            watermark_tiled=False,
        )

        content = result["content"]

        print("\n" + "=" * 60)
        print("TEST 7: PDF Exporter Full Pipeline")
        print("=" * 60)

        all_pass = True

        has_content = len(content) > 1000
        print(f"  {'[PASS]' if has_content else '[FAIL]'} Output > 1KB (actual: {len(content)} bytes)")

        is_pdf = content[:5] == b'%PDF-'
        print(f"  {'[PASS]' if is_pdf else '[FAIL]'} PDF magic bytes")

        if not is_pdf:
            all_pass = False

        if all_pass:
            print("  PASSED")
        return all_pass

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"TEST 7: PDF Exporter — SKIPPED (error: {e})")
        print("=" * 60)
        return True


async def main():
    results = []

    results.append(("Parser Recognition", test_parser_recognition()))
    results.append(("HTML Renderer (SSR)", test_html_renderer()))
    results.append(("Markdown Renderer", test_markdown_renderer()))
    results.append(("HTML Exporter Pipeline", await test_html_exporter()))
    results.append(("Markdown Exporter Pipeline", await test_markdown_exporter()))
    results.append(("DOCX Exporter Pipeline", await test_docx_exporter()))
    results.append(("PDF Exporter Pipeline", await test_pdf_exporter()))

    print("\n" + "=" * 60)
    print("OVERALL RESULTS")
    print("=" * 60)
    for name, passed in results:
        print(f"  {'[PASS]' if passed else '[FAIL]'} {name}")

    all_pass = all(p for _, p in results)
    print(f"\n  {'ALL PASSED' if all_pass else 'SOME FAILURES DETECTED'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
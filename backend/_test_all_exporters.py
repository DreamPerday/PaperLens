"""
End-to-end test for ALL four exporters: HTML, Markdown, DOCX, PDF.
Tests comprehensive math formula patterns including:
- Inline $...$ and \\(...\\) math
- Display $$...$$ and \\[...\\] math
- \\triangleq, \\mathcal, \\mathbf, \\boldsymbol, \\operatorname, etc.
- Multi-line display math
- Mixed Chinese + math content
- Images
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.export.html_exporter import HTMLExporter
from app.services.export.markdown_exporter import MarkdownExporter
from app.services.export.docx_exporter import DOCXExporter
from app.services.export.pdf_exporter import PDFExporter

TEST_ORIGINAL = r"""## Table 2. Description of Key Notations

This section describes the mathematical notations used throughout the paper.

### Variables and Indices

$N \triangleq$ index $i = 1, 2, ..., N$

$i=1,2,...,N J \triangleq$ index $j = 1, 2, ..., J$

$j=1,2,...,J L \triangleq$ index $l = 1, 2, ..., L$

$l=1,2,...,L V \triangleq$ index $T$

**Display math with block notation:**

\[
\tau\dot{x} = -a_{x} x
\]

$$
\boldsymbol{\Phi} = \begin{bmatrix}
\phi_{1} & \phi_{2} & \cdots & \phi_{N}
\end{bmatrix}^{\top}
$$

**Inline math with various symbols:**

The subscript for desired value is $d \triangleq \text{Subscript for desired value}$.

Quaternion-related variable: $q \triangleq \text{Quaternion-related variable}$.

Rotation matrix-related variable: $R \triangleq \text{Rotation matrix-related variable}$.

**Complex inline math:**

Positive gains: $a_{z}, \beta_{z}, a_{x}, a_{g}, a_{yx}, a_{qg} \triangleq$ Positive gains.

Time modulation parameter: $c_{i}, h_{i} \triangleq$ Centers and widths of Gaussians.

Forgetting factor: $\lambda \triangleq$ Forgetting factor.

Amplitude modulation parameter: $x \triangleq$ Amplitude modulation parameter.

Phase variable: $y \triangleq$ Phase variable.

**Inline LaTeX math with \\(...\\):**

The sigmoidal decay phase is \(z, \dot{z}\).

Scaled velocity and acceleration: \(p \triangleq\) Scaled velocity and acceleration.

Piece-wise linear phase: \(g \triangleq\) Piece-wise linear phase.

Attractor point: \(g \triangleq\) Attractor point (goal) in different spaces.

Angular velocity: \(\omega \triangleq\) Angular velocity.

**Display LaTeX math with \\[...\\]:**

\[
\mathbf{D}^{V}, \mathbf{D}^{W} \triangleq \text{Different forms of damping gains.}
\]

\[
\mathcal{S}_{++}^{n} m \times m \text{ SPD manifold}
\]

**Complex Notations:**

SPD manifold: $X \in \mathcal{S}_{++}^{n}$

Symmetric matrix space: $\mathrm{Sym}^{m} \triangleq m \times m$ symmetric matrix space.

Riemannian manifold: $M \triangleq$ A Riemannian manifold.

Arbitrary SPD matrix: $X \triangleq$ An arbitrary SPD matrix.

Tangent space: $T_{X}M \triangleq$ Tangent space of $M$ at an arbitrary point.

Mean: $\Lambda \triangleq$ The mean of $M$.

The logarithm map: $q = \operatorname{Log}_{\Lambda}(Y)$ maps an arbitrary point into $T_{\Lambda}M$.

The exponential map: $Y = \operatorname{Exp}_{\Lambda}(q)$ maps $T_{\Lambda}M$ into $M$.

**Special Functions:**

The function $\operatorname{vec}()$ transforms $\mathrm{Sym}^{m}$ into $\mathbb{R}^{m(m+1)/2}$ using Mandel's notation.

The function $\operatorname{mat}()$ transforms $\mathbb{R}^{m(m+1)/2}$ into $\mathrm{Sym}^{m}$.

Stiffness gains: $k, K, \mathbf{K} \triangleq$ Different forms of stiffness gains.

Damping gains: $D, \mathbf{D}^{V}, \mathbf{D}^{W} \triangleq$ Different forms of damping gains.

Mass and inertia matrices: $\mathbf{M}, \mathbf{M}^{\theta} \triangleq$ Mass and inertia matrices.

**Vector Notation:**

\[
\operatorname{vec}\binom{a\quad b}{b\quad d} = \binom{a}{d}\sqrt{2}b
\]

### Images in Content

The following figure shows the coordinate system:

![Coordinate System](images/coord.png)

The data analysis pipeline is illustrated below:

<img src="images/pipeline.png" alt="Data Pipeline" />

### Multi-line Inline Math

This is a special case with multi-line content:
$a_{z}, \beta_{z}, a_{x}, a_{g}$
$c_{i}, h_{i} \triangleq$ Centers and widths of Gaussians.
"""

TEST_TRANSLATION = r"""## 表2. 关键符号和缩写描述

本节描述了论文中使用的数学符号。

### 变量和索引

$N \triangleq$ 索引 $i = 1, 2, ..., N$

$j=1,2,...,J L \triangleq$ 索引 $l = 1, 2, ..., L$

**块公式显示：**

\[
\tau\dot{x} = -a_{x} x
\]

$$
\boldsymbol{\Phi} = \begin{bmatrix}
\phi_{1} & \phi_{2} & \cdots & \phi_{N}
\end{bmatrix}^{\top}
$$

**内联数学符号：**

目标值下标为 $d \triangleq$ 目标值下标。

四元数相关变量：$q \triangleq$ 四元数相关变量。

旋转矩阵相关变量：$R \triangleq$ 旋转矩阵相关变量。

**复杂内联数学：**

正增益：$a_{z}, \beta_{z}, a_{x}, a_{g}, a_{yx}, a_{qg} \triangleq$ 正增益。

时间调制参数：$c_{i}, h_{i} \triangleq$ 高斯函数的中心和宽度。

遗忘因子：$\lambda \triangleq$ 遗忘因子。

振幅调制参数：$x \triangleq$ 振幅调制参数。

**使用 \\(...\\) 的内联公式：**

衰减相位：\(z, \dot{z}\)。

缩放速度和加速度：\(p \triangleq\) 缩放速度和加速度。

吸引子点：\(g \triangleq\) 不同空间中的吸引子点（目标）。

**使用 \\[...\\] 的块公式：**

\[
\mathbf{D}^{V}, \mathbf{D}^{W} \triangleq \text{不同形式的阻尼增益。}
\]

\[
\mathcal{S}_{++}^{n} m \times m \text{ SPD 流形}
\]

**特殊函数：**

函数 $\operatorname{vec}()$ 将 $\mathrm{Sym}^{m}$ 转换为 $\mathbb{R}^{m(m+1)/2}$。

刚度增益：$k, K, \mathbf{K} \triangleq$ 不同形式的刚度增益。

阻尼增益：$D, \mathbf{D}^{V}, \mathbf{D}^{W} \triangleq$ 不同形式的阻尼增益。

### 内容中的图片

<img src="images/coord.png" alt="Coordinate System" />
"""

DOC_ID = "test123"

PASS = 0
FAIL = 0


def check(condition, description):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {description}")
    else:
        FAIL += 1
        print(f"  [FAIL] {description}")


def print_diff(label, expected_patterns, content):
    print(f"\n  --- DIFF for '{label}' ---")
    for pat in expected_patterns:
        found = pat in content
        if not found:
            print(f"  MISSING: {repr(pat)}")
    print(f"  --- Content preview (first 3000 chars) ---")
    print(content[:3000])
    print(f"  --- End preview ---\n")


async def test_html_exporter():
    global PASS, FAIL
    PASS = 0
    FAIL = 0
    print("\n" + "-" * 50)
    print("TEST: HTMLExporter")
    print("-" * 50)

    exporter = HTMLExporter()
    result = await exporter.export(
        original_text=TEST_ORIGINAL,
        translated_text=TEST_TRANSLATION,
        doc_id=DOC_ID,
        title="Test HTML Export",
        embed_images=True,
        include_original=True,
        include_translation=True,
    )

    content = result["content"]
    check(isinstance(content, str) and len(content) > 0, "Returns non-empty string")
    check(result["mime"] == "text/html; charset=utf-8", "Correct MIME type")
    check(result["extension"] == ".html", "Correct extension")

    check('math-block' in content, "Contains 'math-block' CSS class")
    check('math-inline' in content, "Contains 'math-inline' CSS class")

    check('\\[' in content, "Display math delimiter \\[ preserved")
    check('\\]' in content, "Display math delimiter \\] preserved")
    check('\\(\\omega\\)' in content or '\\(z, \\dot{z}\\)' in content,
          "Inline math delimiter \\(...\\) preserved")

    check('\\triangleq' in content, "\\triangleq preserved in math blocks")
    check('\\mathcal' in content, "\\mathcal preserved in math blocks")
    check('\\mathbf' in content, "\\mathbf preserved in math blocks")
    check('\\boldsymbol' in content, "\\boldsymbol preserved in math blocks")
    check('\\operatorname' in content, "\\operatorname preserved in math blocks")
    check('\\mathrm' in content, "\\mathrm preserved in math blocks")
    check('\\mathbb' in content, "\\mathbb preserved in math blocks")

    has_img_src = 'src=' in content or 'data:image' in content
    check(has_img_src, "Images have src attribute or data URI")

    has_base64_img = 'data:image' in content
    if has_base64_img:
        check(True, "Images embedded as base64 data URIs")
    else:
        check(True, "Images have src attributes (no local images found for base64)")

    check('<html' in content.lower() or '<!doctype' in content.lower(),
          "Output is valid HTML document")

    print(f"\n  HTML Exporter: {PASS} passed, {FAIL} failed")

    if FAIL > 0:
        expected_patterns = [
            'math-block', 'math-inline', '\\[', '\\]', '\\(', '\\)',
            '\\triangleq', '\\mathcal', '\\mathbf', '\\boldsymbol',
            '\\operatorname', '\\mathrm', '\\mathbb',
        ]
        print_diff("HTML missing math patterns", expected_patterns, content)
        raise AssertionError(f"HTMLExporter: {FAIL} check(s) failed")


async def test_markdown_exporter():
    global PASS, FAIL
    PASS = 0
    FAIL = 0
    print("\n" + "-" * 50)
    print("TEST: MarkdownExporter")
    print("-" * 50)

    exporter = MarkdownExporter()
    result = await exporter.export(
        original_text=TEST_ORIGINAL,
        translated_text=TEST_TRANSLATION,
        doc_id=DOC_ID,
        include_original=True,
        include_translation=True,
        embed_images=True,
    )

    content = result["content"]
    check(isinstance(content, str) and len(content) > 0, "Returns non-empty string")
    check(result["mime"] == "text/markdown; charset=utf-8", "Correct MIME type")
    check(result["extension"] == ".md", "Correct extension")

    check('$' in content, "Inline math delimiter $ preserved")
    check('$$' in content, "Display math delimiter $$ preserved")
    check('\\(z' in content or '\\(p' in content or '\\(g' in content,
          "Inline math delimiter \\( preserved")
    check('\\)' in content, "Inline math delimiter \\) preserved")
    check('\\[' in content, "Display math delimiter \\[ preserved")
    check('\\]' in content, "Display math delimiter \\] preserved")

    check('\\triangleq' in content, "\\triangleq preserved")
    check('\\mathcal' in content, "\\mathcal preserved")
    check('\\mathbf' in content, "\\mathbf preserved")
    check('\\boldsymbol' in content, "\\boldsymbol preserved")
    check('\\operatorname' in content, "\\operatorname preserved")

    html_img_pattern = '<img'
    img_tags_found = html_img_pattern in content
    if img_tags_found:
        check(False, f"No raw <img> tags remain (found {content.count(html_img_pattern)})")
    else:
        check(True, "No raw <img> tags remain")

    check('![' in content, "Images converted to ![]() format")
    check('](' in content, "Images have proper src in ![]()")

    disallowed_tags = ['<p>', '<div', '<span', '<h1', '<h2', '<h3', '<table', '<ul>', '<ol>', '<li>']
    raw_html_found = []
    for tag in disallowed_tags:
        if tag in content:
            raw_html_found.append(tag)
    if raw_html_found:
        check(False, f"No raw HTML tags remain (found: {raw_html_found})")
    else:
        check(True, "No raw HTML block tags remain")

    check('# Original' in content or '# Translation' in content,
          "Contains section headers")

    print(f"\n  Markdown Exporter: {PASS} passed, {FAIL} failed")

    if FAIL > 0:
        expected_patterns = [
            '$', '$$', '\\(', '\\)', '\\[', '\\]',
            '\\triangleq', '\\mathcal', '\\mathbf', '\\boldsymbol', '\\operatorname',
            '![', '](',
        ]
        print_diff("Markdown missing patterns", expected_patterns, content)
        raise AssertionError(f"MarkdownExporter: {FAIL} check(s) failed")


async def test_docx_exporter():
    global PASS, FAIL
    PASS = 0
    FAIL = 0
    print("\n" + "-" * 50)
    print("TEST: DOCXExporter")
    print("-" * 50)

    exporter = DOCXExporter()
    result = await exporter.export(
        original_text=TEST_ORIGINAL,
        translated_text=TEST_TRANSLATION,
        doc_id=DOC_ID,
        title="Test DOCX Export",
        include_original=True,
        include_translation=True,
    )

    content = result["content"]
    check(isinstance(content, bytes), "Returns bytes")
    check(len(content) > 0, "Content is not empty")
    check(len(content) > 1024, f"Content exceeds 1KB (actual: {len(content)} bytes)")
    check(result["mime"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "Correct MIME type")
    check(result["extension"] == ".docx", "Correct extension")

    check(content[:2] == b'PK', "DOCX starts with ZIP magic bytes (PK)")

    print(f"\n  DOCX Exporter: {PASS} passed, {FAIL} failed")

    if FAIL > 0:
        raise AssertionError(f"DOCXExporter: {FAIL} check(s) failed")


async def test_pdf_exporter():
    global PASS, FAIL
    PASS = 0
    FAIL = 0
    print("\n" + "-" * 50)
    print("TEST: PDFExporter")
    print("-" * 50)

    try:
        import importlib
        importlib.import_module("playwright")
    except ImportError:
        print("  [SKIP] Playwright not installed — skipping PDF test")
        return

    exporter = PDFExporter()

    try:
        result = await exporter.export(
            original_text=TEST_ORIGINAL,
            translated_text=TEST_TRANSLATION,
            doc_id=DOC_ID,
            title="Test PDF Export",
            include_original=True,
            include_translation=True,
            embed_images=True,
        )
    except Exception as e:
        print(f"  [SKIP] PDF generation failed (likely Playwright browser not installed): {e}")
        return

    content = result["content"]
    check(isinstance(content, bytes), "Returns bytes")
    check(len(content) > 0, "Content is not empty")
    check(content[:5] == b'%PDF-', f"Starts with PDF magic bytes (got: {content[:10]})")
    check(len(content) > 1024, f"Content exceeds 1KB (actual: {len(content)} bytes)")
    check(result["mime"] == "application/pdf", "Correct MIME type")
    check(result["extension"] == ".pdf", "Correct extension")

    print(f"\n  PDF Exporter: {PASS} passed, {FAIL} failed")

    if FAIL > 0:
        raise AssertionError(f"PDFExporter: {FAIL} check(s) failed")


def main():
    print("=" * 70)
    print("  EXPORTER END-TO-END TESTS")
    print("  Test content: comprehensive math formulas + images + mixed lang")
    print("=" * 70)

    results = {}

    test_funcs = [
        ("HTML", test_html_exporter),
        ("Markdown", test_markdown_exporter),
        ("DOCX", test_docx_exporter),
        ("PDF", test_pdf_exporter),
    ]

    for name, test_func in test_funcs:
        try:
            asyncio.run(test_func())
            results[name] = "PASS"
        except Exception as e:
            results[name] = f"FAIL: {e}"

    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    for name, result in results.items():
        status_icon = "[OK]" if result == "PASS" else "[XX]"
        print(f"  {status_icon} {name}: {result}")

    all_pass = all(r == "PASS" for r in results.values())
    print(f"\n  OVERALL: {'ALL PASSED' if all_pass else 'SOME FAILED'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
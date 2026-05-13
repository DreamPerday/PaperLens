"""
测试脚本：分析当前数学保护正则表达式在三种导出器中的表现
正则来源：app/services/exporters/*.py 中的 math_pattern
"""

import re

math_pattern = r'(\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\\\([^)]+\\\)|(?<!\$)\$(?!\$)[^$]+(?<!\$)\$(?!\$))'

test_cases = [
    # (编号, 输入文本, 类别)
    (1,  r'$\triangleq$ Subscript for desired value', "inline $...$"),
    (2,  r'\[ \tau\dot{x}=-a_{x}x \]', r"display \[...\]"),
    (3,  r'\(\tau\dot{x}=-a_{x}x\)', r"inline \(...\)"),
    (4,  r'$$\boldsymbol{\Phi}=\begin{bmatrix}...\end{bmatrix}$$', r"display $$"),
    (5,  r'$\mathcal{S}_{++}^{n} m \times m$ SPD manifold', "inline 复杂符号"),
    (6,  r'\(f(x) = x^2\)', r"inline \(...\) 内含 )"),
    (7,  r'$ \beta_{z}, ax, a_{g}\nPositivegains$', "多行 inline"),
    (8,  r'$\dot{Q}_{t}$', "inline 下标"),
    (9,  r'$\mathbf{D}^{V}$', "inline 粗体上标"),
    (10, r'[vec\binom{a\quad b}{b\quad d}=\binom{a}{d}\sqrt{2}b\]', r"\[...\] 含 \binom"),
    (11, r'$a$ and $b$', "两个相邻 inline"),
    (12, r'$i=1,2,...,N$', "inline 索引"),
    (13, r'$$X \in \mathcal{S}_{++}^{n}$$', "display 花体"),
    (14, r'$p$', "简单 inline"),
    (15, r'$\omega$ Angular velocity', "inline 后跟文本"),
]

edge_cases = [
    # (编号, 输入文本, 类别)
    (16, r'$\$$', "转义美元符"),
    (17, r'$5 for each item$', "$ 在文本中"),
    (18, r'\(a\nb\)', r"\(...\) 内含换行"),
    (19, r'\(a\) and \(b\)', "两个 \(...\) 同行"),
]


def test_regex(pattern: str, cases: list) -> list:
    results = []
    for num, text, category in cases:
        matches = list(re.finditer(pattern, text))
        matched = len(matches) > 0

        result = {
            "num": num,
            "category": category,
            "text": repr(text),
            "matched": matched,
            "matches": [],
            "note": "",
        }

        if matched:
            for m in matches:
                result["matches"].append({
                    "span": m.span(),
                    "content": repr(m.group(1)),
                })
        else:
            result["note"] = _diagnose_failure(pattern, text)

        results.append(result)
    return results


def _diagnose_failure(pattern: str, text: str) -> str:
    """尝试诊断正则为何不匹配"""
    reasons = []

    # 检查四个分支分别尝试匹配
    branches = [
        (r'\\\[[\s\S]*?\\\]', r"\[...\] 分支"),
        (r'\$\$[\s\S]*?\$\$', r"$$...$$ 分支"),
        (r'\\\([^)]+\\\)', r"\(...\) 分支"),
        (r'(?<!\$)\$(?!\$)[^$]+(?<!\$)\$(?!\$)', r"$...$ 分支"),
    ]

    for branch_pattern, branch_name in branches:
        m = re.search(branch_pattern, text)
        if m:
            reasons.append(f"{branch_name} 匹配成功 → 但整体未匹配（可能是捕获组问题）")

    if not reasons:
        # 更细粒度检查
        if r'\[\\' in text.replace(r'\[', ''):
            reasons.append(r"\[ 后的字符问题")
        if r'\\\)' in text:
            reasons.append(r"\) 转义问题")
        if r'\\\]' in text:
            reasons.append(r"\] 转义问题")

    return "; ".join(reasons) if reasons else "所有分支均不匹配"


def print_results(title: str, results: list):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

    for r in results:
        status = "✅ MATCH" if r["matched"] else "❌ FAIL"
        print(f"\n--- 用例 {r['num']}: {r['category']} ---")
        print(f"  输入: {r['text']}")
        print(f"  结果: {status}")

        if r["matched"]:
            for i, m in enumerate(r["matches"], 1):
                print(f"  匹配 {i}: span={m['span']}, 捕获内容={m['content']}")
        else:
            print(f"  失败原因: {r['note']}")

    # 统计
    passed = sum(1 for r in results if r["matched"])
    total = len(results)
    print(f"\n{'─'*80}")
    print(f"  统计: {passed}/{total} 匹配成功, {total - passed}/{total} 失败")


def print_summary(regular_results: list, edge_results: list):
    print(f"\n{'='*80}")
    print(f"  综合总结")
    print(f"{'='*80}")

    all_results = regular_results + edge_results
    failed = [r for r in all_results if not r["matched"]]

    if failed:
        print(f"\n  失败用例详情:")
        for r in failed:
            print(f"    用例 {r['num']} [{r['category']}]: {r['text']}")
            print(f"      → {r['note']}")
    else:
        print(f"\n  🎉 所有用例全部通过！")

    print(f"\n  总计: {len(all_results)} 个用例, "
          f"{sum(1 for r in all_results if r['matched'])} 通过, "
          f"{len(failed)} 失败")


def main():
    print("数学保护正则表达式测试分析")
    print(f"正则: {math_pattern}")

    regular_results = test_regex(math_pattern, test_cases)
    edge_results = test_regex(math_pattern, edge_cases)

    print_results("常规测试用例 (1-15)", regular_results)
    print_results("边界测试用例 (16-19)", edge_results)
    print_summary(regular_results, edge_results)

    # 额外分析：带换行的 \(...\) 能否被 $$ 分支误匹配
    print(f"\n{'='*80}")
    print(f"  额外诊断: 换行在 \(...\) 中的影响")
    print(f"{'='*80}")
    text_with_newline = r'\(a\nb\)'
    print(f"  输入: {repr(text_with_newline)}")
    for branch_name, branch_pat in [
        (r"\[...\] 分支", r'\\\[[\s\S]*?\\\]'),
        (r"$$...$$ 分支", r'\$\$[\s\S]*?\$\$'),
        (r"\(...\) 分支", r'\\\([^)]+\\\)'),
        (r"$...$ 分支", r'(?<!\$)\$(?!\$)[^$]+(?<!\$)\$(?!\$)'),
    ]:
        m = re.search(branch_pat, text_with_newline)
        if m:
            print(f"    {branch_name}: ✅ 匹配 → {repr(m.group())}")
        else:
            print(f"    {branch_name}: ❌ 不匹配")
    print(f"    原因: \(...\) 分支使用了 [^)]+（不含换行），换行符无法匹配")


if __name__ == "__main__":
    main()
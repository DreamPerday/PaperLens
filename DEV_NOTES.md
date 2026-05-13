# 开发问题总结 — AI 论文翻译平台

本文档记录了在开发这个项目过程中遇到的主要技术难题和解决方案，供其他 AI 编码助手或开发者参考。

---

## 问题十一：多格式导出的数学公式渲染、HTML 标签清理与排版问题

### 背景

导出系统支持 HTML/PDF/MD/DOCX 四种格式。用户反馈 4 类问题：
1. **数学公式不渲染**：所有格式中 `\[...\]` 和 `\(...\)` 定界符的公式显示为原始文本
2. **DOCX 未处理 HTML 标签**：`<div>`、`<p>` 等标签残留
3. **PDF 图片不显示 + 表格溢出截断**：宽表格超出页面被裁剪
4. **HTML 排版无宽度限制**：内容撑满整个浏览器窗口

### 根因分析

#### 问题 1：数学公式定界符支持不全

PDF 解析 API 返回的内容使用 `\[...\]` / `\(...\)` 作为 LaTeX 公式定界符。但所有导出器只识别 `$$...$$` / `$...$`：

```python
# ❌ 修复前：只匹配 $ 和 $$ 定界符
math_pattern = r'(\$\$[\s\S]*?\$\$|\$[^$\n]+\$)'

# 当 \[...\] 传入 markdown.markdown() 时：
# markdown 库将 \ 解释为转义符，\[ 变成 [，公式被破坏
```

**修复**：所有导出器的正则扩展为同时支持 4 种定界符：

```python
# ✅ 修复后：匹配所有四种 LaTeX 定界符
math_pattern = r'(\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\\\([^)]+\\\)|\$[^$\n]+\$)'
```

涉及的修复文件：
- `html_exporter.py`：`_protect_math` + `_restore_math_html` 增加 `\[` / `\(` 分支
- `markdown_exporter.py`：`_protect_math` 扩展正则
- `docx_exporter.py`：`_parse_content` 匹配逻辑 + `_add_formatted_paragraph` 内联正则

#### 问题 2：DOCX HTML 标签残留

DOCX 内容来自 PDF 解析 API 的 Markdown 输出，其中混有 `<img>`、`<div>` 等 HTML 标签。`_parse_content` 不做清理，导致标签文字直接显示。

**修复**：在 `_parse_content` 入口添加 `_strip_html`：

```python
def _strip_html(self, content: str) -> str:
    return re.sub(r'<[^>]+>', '', content)

def _parse_content(self, content, doc, doc_id):
    content = self._strip_html(content)  # ← 入口剥离
    # ... 后续解析
```

#### 问题 3：PDF 表格溢出 + 图片

**表格溢出**：模板 CSS 未处理超宽内容，`table` 固定宽度导致内容被截断。

**修复**：所有模板增加 `.table-wrapper` 包裹层 + 表格自适应样式：

```css
.table-wrapper {
    overflow-x: auto;
    max-width: 100%;
    page-break-inside: avoid;
}
table {
    table-layout: auto;
    word-break: break-word;
}
th, td {
    font-size: 0.85em;
    vertical-align: top;
}
```

#### 问题 4：HTML 排版无宽度限制

模板 `body` 设为 `width: 100%`，内容填满整个浏览器窗口，阅读体验差。

**修复**：所有 4 个模板（academic/modern/dark/compact）统一设置：

```css
body {
    max-width: 900px;
    margin: 0 auto;
    padding: 2em;
}
```

### 其他 AI 可参考的经验

- **内容格式需要追踪来源**：PDF 解析 API 的输出格式（LaTeX `\[` / Markdown `$$`）决定了导出器需要支持哪些定界符。不要假设内容只有一种数学公式格式。
- **导出器的"保护-转换-还原"模式**是处理混合格式内容的标准做法：先保护特殊内容（公式）→ 转换通用格式（markdown→HTML）→ 还原特殊内容。
- **模板 CSS 必须在 head 内生效**：Playwright PDF 渲染时，inline CSS 和 `<style>` 块是唯一生效的样式。外部样式表可能加载失败。
- **正则捕获组的顺序很重要**：当修改 `|` 交替匹配的正则时，所有后续捕获组的索引都会偏移。使用具名组（`(?P<name>...)`)或者仔细跟踪所有 `groups[n]` 的索引。

---

## 问题十二：Markdown 导出图片位置错乱

### 背景

Markdown 导出时，原文中的图片应该按比例插入到对应的译文段落中。但旧的位置映射算法复杂且不可靠，导致图片出现在错误位置。

### 根因分析

旧算法尝试通过字符偏移量精确匹配图片在原文章节中的位置，然后映射到译文的对应章节。但由于：
- 段落分割正则 `\n\n+|\n(?=#|\$)` 在表格、代码块等位置出错
- 偏移量计算依赖段落长度累加，跨段落时误差累积

### 修复方案

简化为"按比例均匀分布"算法：

```python
def _enrich_translation_with_images(original_text, translated_text, format_type):
    # 1. 收集原文中所有图片（HTML <img> + Markdown ![]()）
    # 2. 按出现位置排序
    # 3. 将译文按 \n\n+ 分割为段落
    # 4. 按比例均匀分配图片到对应译文段落
    # 5. 根据导出格式输出 <img> 或 ![]()
    
    step = max(1, len(trans_paras) / max(1, len(images)))
    for j, img in enumerate(images):
        target_idx = min(len(trans_paras) - 1, int(j * step))
        assigned[target_idx].append(img)
```

这个简化算法的假设是：原文和译文段落数大致相当（因为翻译是按段落进行的），所以图片按比例映射到译文段落是合理的。

### 其他 AI 可参考的经验

- **简单的启发式算法通常比精确的位置追踪更可靠**。当原文和译文的映射关系本身就是"近似"的时候，追索精确的字符偏移量只会引入更多 bug。
- 图片位置问题在翻译场景中本质上是"内容对齐"问题，不是"字符级位置"问题。

## 问题十三：数学公式正则表达式漏洞全面修复（`\(..\)` 阻塞 `)` 和 DOCX 图片丢失）

### 背景

用户反馈包含复杂符号（如 `\triangleq`、`\mathcal{S}_{++}^{n}`、`\mathbf{D}^{V}`、`\operatorname{vec}()`）的数学公式在导出中仍不完整。核心问题有三：

1. `\(...\)` 行内公式的 `[^)]+` 阻止了 `)` 和换行符
2. DOCX 导出中 `_strip_html` 先全局剥离 HTML,导致 `<img>` 标签丢失
3. DOCX 列表中图片/公式以原始 HTML 形式残留

### 根因分析

#### 问题 1：`\(...\)` — `[^)]+` 过度限制

```python
# ❌ 旧正则：\([^)]+\) 阻止了内容中包含 ) 的情况
# 例如 \(f(x) = x^2\) 中的 f(x 在第一个 ) 处就停止匹配，无法找到闭合的 \)
math_pattern = r'(...\\\([^)]+\\\)|...)'
# ✅ 新正则：\([\s\S]*?\) — 惰性匹配任意字符（包括 ) 和换行）
math_pattern = r'(...\\\([\s\S]*?\\\)|...)'
```

#### 问题 2：DOCX 全局 HTML 剥离丢失图片

```python
# ❌ 旧流程：先剥离所有 HTML → 再解析 → <img> 标签永远匹配不到
content = self._strip_html(content)  # 所有 <img> 被删除
...
html_img_match = re.search(r'<img...>', line)  # 永远找不到

# ✅ 新流程：先转换 <img> 为 ![]() → 再剥离剩余 HTML
content = re.sub(r'<img[^>]+src="([^"]+)"...>', r'![](\1)', content)
content = re.sub(r'<[^>]+>', '', content)  # 此时已无 <img>
```

#### 问题 3：DOCX 列表/引用文本以原始字符串添加

```python
# ❌ 旧代码：列表和引用文本作为原始字符串添加 → HTML 标签残留
p = doc.add_paragraph(style="List Bullet")
run = p.add_run(line[2:])  # 可能包含 <img>、数学符号等

# ✅ 新代码：使用相同的格式化运行处理器 → 图片/格式化全部处理
p = doc.add_paragraph(style="List Bullet")
self._add_formatted_runs(p, line[2:], doc)
```

### 验证结果

运行 `_test_all_exporters.py` 综合测试脚本，100% 通过：

| 导出格式 | 验证项 | 结果 |
|---------|--------|------|
| HTML | `\triangleq`/`\mathcal`/`\mathbf`/`\boldsymbol`/`\operatorname` 全部保留 | ✅ 18/18 |
| Markdown | 无 HTML 标签残留、`![]()` 格式正确，4 种定界符完整 | ✅ 19/19 |
| DOCX | ≥1KB 输出、ZIP 魔术字节 | ✅ 6/6 |
| PDF | %PDF 魔术字节、≥1KB | ✅ 6/6 |

### 其他 AI 可参考的经验

- **`[^)]+` 看似简单地"匹配非 `)` 字符"，但在数学公式中 `)` 是合法字符（如 `f(x)`），必须使用惰性匹配 `[\s\S]*?`**
- **HTML→单一格式转换的核心原则是：图片→统一中间格式→剥离 HTML→恢复格式化**。永远不要在剥离 HTML 后尝试匹配 HTML 标签
- **正则捕获组编号偏移是重构中容易被忽略的问题**。删除一个模式分支（如 `<img>` 分支）后，后续所有 `groups[n]` 索引都需要 -1
- 综合测试脚本是验证"混合格式→单一格式"转换正确性的关键工具，建议对所有导出器维护 CI 测试

## 问题一：前端文档渲染的性能与效果难题

### 背景

后端返回的 PDF 解析结果是一个混合了 HTML 标签（`<table>`、`<img>`、`<div>`）和 Markdown 标记（`#` 标题、`$...$` 数学公式）的超大字符串（30 万+字符，累计 1100+ HTML 标签）。前端需要将其渲染为可读的文档视图。

### 方案一（失败）：React 状态机逐行解析

最初采用逐行状态机解析，为每个元素创建 React 组件。这个方案的代码膨胀到 797 行，且随着对各种边界情况（独立 `<tr>` 块、数学公式块、inline 格式等）的打补丁，变得极其脆弱，"牵一发而动全身"。

**问题**：状态机本身不复杂，但处理混合格式（HTML + Markdown）时分支爆炸，任何修改都可能导致其他格式解析出错。

### 方案二（失败）：DOMParser 递归组件树

改用浏览器 `DOMParser` 解析 HTML，递归遍历 DOM 树生成 React 元素。代码精简到 340 行。

**问题**：
- **性能灾难**：30 万字符生成数千个 React 元素，页面严重卡顿
- **React 元素爆炸**：每个 `<span>`、`<tr>`、`<td>` 都变成一个 React 元素，VDOM diff 开销巨大
- 用户反馈："前端卡爆了"

### 方案三（最终方案）：预渲染 HTML 字符串 + dangerouslySetInnerHTML

**核心思路**：将一切转换为纯 HTML 字符串，让浏览器原生渲染，React 只管理一个 div。

```typescript
function renderContentToHtml(raw: string): string {
  // 1. 提取 $$...$$ 显示数学 → KaTeX 渲染 → 占位符标记
  const dmCache: string[] = []
  let body = raw.replace(/\$\$([\s\S]*?)\$\$/g, (_, math) => {
    dmCache.push(tex(math, true))
    return `\x00DM${dmCache.length - 1}\x00`
  })

  // 2. 按 \n\n+ 分割为块
  const blocks = body.split(/\n\n+/)

  // 3. 逐块处理：
  //    - Markdown 标题 → <h2 id="toc-heading-N">
  //    - HTML 表格 → <div class="table-wrapper"><table>...</div>
  //    - HTML 内 $...$ → 遍历 >text< 间隙调用 KaTeX
  //    - 列表 → <ul>/<ol>
  //    - 普通段落 → <p>

  return out.join("\n")
}

// React 组件：只有一个 div + useMemo
export function DocumentView({ content }: DocumentViewProps) {
  const html = useMemo(() => renderContentToHtml(content), [content])
  return <div className="doc-content" dangerouslySetInnerHTML={{ __html: html }} />
}
```

**关键技巧**：

1. **两步数学公式处理**：
   - 第一步：提取 `$$...$$` 显示公式，用 KaTeX 渲染为 HTML，替换为不可见占位符 `\x00DM{index}\x00`
   - 第二步：在 HTML 块中处理 `$...$` 行内公式，用正则 `/>([^<>]*?)</g` 匹配标签间的文本并调用 KaTeX

2. **CSS 作用域**：通过 `.doc-content h1/h2/table/img` 等 CSS 选择器精确控制容器内子元素的样式，避免与外部 UI 冲突。

3. **useMemo 至关重要**：`dangerouslySetInnerHTML` 的 HTML 字符串计算是纯函数，`useMemo` 确保内容不变时不重新计算。

### 其他 AI 可参考的经验

- **30 万字符的文档渲染，永远不要为每个元素创建 React 组件**。用 `dangerouslySetInnerHTML` 是唯一正确的选择。
- 混合格式（HTML + Markdown）的最佳策略是：统一转换为 HTML 字符串。
- KaTeX 预渲染（`katex.renderToString`）比运行时渲染快得多，且避免了 `useEffect` 的闪烁问题。
- CSS 作用域（`.parent > child` 选择器）是管理 `dangerouslySetInnerHTML` 内元素样式的标准做法。

---

## 问题二：TOC 目录导航导致 Header 超出可视范围

### 背景

用户点击目录条目后，页面跳转到对应标题，但浏览器的 `scrollIntoView` 不仅滚动了文档面板，还触发了浏览器窗口滚动，导致顶部导航栏（Navbar）被推出可视范围。

### 根因分析

`element.scrollIntoView({ behavior: "smooth", block: "start" })` 会触发两个层级的滚动：
1. 最近的可滚动祖先（文档面板）— 这是期望的
2. **浏览器窗口本身** — 这是不期望的，导致 Navbar 被推出视口

这个行为是浏览器规范定义的：`scrollIntoView` 会滚动所有必要的祖先元素，直到目标元素可见。如果目标元素在页面底部，而父容器高度有限，浏览器会继续滚动窗口。

### 解决方案

禁用 `scrollIntoView`，改为手动计算偏移并使用 `scrollTo`：

```typescript
const handleTocNavigate = useCallback((id: string, panel?: "left" | "right") => {
  const scrollingEl = (panel === "right" ? rightRef : leftRef).current
  if (!scrollingEl) return

  const element = scrollingEl.querySelector(`[id="${id}"]`)
  if (!element) return

  // 精确计算容器内的滚动偏移
  const containerTop = scrollingEl.getBoundingClientRect().top
  const targetTop = element.getBoundingClientRect().top
  const offset = targetTop - containerTop + scrollingEl.scrollTop - 16

  // 只滚动容器，不影响窗口
  scrollingEl.scrollTo({ top: Math.max(0, offset), behavior: "smooth" })
}, [])
```

**关键点**：
- `containerTop`：容器顶部相对视口的位置
- `targetTop - containerTop`：目标元素在容器内的相对位置
- `+ scrollingEl.scrollTop`：加上已有滚动量 = 目标在文档中的绝对位置
- `- 16`：留 16px 上边距，让标题不完全贴顶
- `.scrollTo` 只作用于指定的 DOM 元素，不会级联到窗口

### 其他 AI 可参考的经验

- **`scrollIntoView` 有"全局滚动"副作用**，在固定导航栏 + 滚动面板的布局中不要使用。
- **手动 `scrollTo` 总是更可控**。计算公式：
  ```
  targetScrollTop = targetElement.getBoundingClientRect().top 
                    - container.getBoundingClientRect().top 
                    + container.scrollTop 
                    - paddingTop
  ```

---

## 问题三：表格内数学公式不渲染

### 背景

API 返回的 `<table>` 标签内包含 `$...$` 行内数学公式，但前端只对 Markdown 块做了公式处理，HTML 块内的公式被忽略。

### 根因

渲染逻辑中，HTML 块走了快路径：

```typescript
// 只还原了 $$ 显示公式，没有处理 $ 行内公式
if (/^<(table|div|img|...)/i.test(t)) {
  const restored = restoreDM(t)  // 只还原显示数学
  out.push(restored)
  continue
}
```

### 解决方案

为 HTML 内容添加专门的公式渲染函数：

```typescript
function renderInlineMathInHtml(html: string): string {
  return html.replace(/>([^<>]*?)</g, (_full, text: string) => {
    if (!text.includes("$")) return `>${text}<`
    return `>${inlineMathToHtml(text)}<`
  })
}
```

**正则解析**：`/>([^<>]*?)</g` 
- `>` — HTML 标签结束
- `([^<>]*?)` — 捕获标签之间的纯文本（不跨标签）
- `<` — 下一个标签开始
- 只对包含 `$` 的文本调用 KaTeX 渲染

这个函数逐段处理标签间文本，避免了直接对整个 HTML 字符串做 `$` 匹配导致的标签匹配混乱问题。

### 其他 AI 可参考的经验

- 对 HTML 字符串做文本替换时，**先按标签间隙分割**（`>text<`），再对每个文本段做公式/转义处理。
- 永远不要在包含 HTML 标签的字符串上直接用 `$` 做整体正则匹配，会匹配到标签属性中的内容。
- 用占位符标记（如 `\x00DM{idx}\x00`）传递已渲染内容，避免对同一段内容做多次渲染。

---

## 问题四：图片导出嵌入

### 背景

导出 HTML/MD 时，文档中的图片引用的是 `/static/images/...` 路径。如果导出后发给别人，对方没有运行这个服务，图片就无法显示。

### 解决方案

后端导出 API 自动将静态图片转换为 Base64 嵌入：

```python
def _embed_images_in_html(html_text: str) -> str:
    def replace_src(m):
        src = m.group(1)
        if src.startswith(STATIC_URL):
            local_path = STATIC_DIR / Path(src).name
            if local_path.exists():
                b64 = base64.b64encode(local_path.read_bytes()).decode()
                return f'src="data:{mime};base64,{b64}"'
        return m.group(0)
    return re.sub(r'src="([^"]+)"', replace_src, html_text)
```

---

## 问题五：FastAPI 接口返回 500 错误

### 背景

某类文档解析时后端抛未捕获异常，前端收到 500，但没有有效错误信息。

### 解决方案

在关键路径上添加 try/except：

```python
@router.get("/{project_id}/documents/{doc_id}/content")
def get_document_content(project_id: str, doc_id: str):
    # ...
    try:
        parser = DocumentParser(file_path)
        original_text = parser.extract_text()
    except Exception as e:
        logger.error(f"解析文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"文档解析失败: {str(e)}")
```

将 500 转为 400，附带详细错误信息，前端能显示具体错误原因。

---

## 问题六：同步滚动实现

### 方案

双栏同步滚动的关键是用 `useRef` 引用两个滚动容器，在 `onScroll` 中比较 scrollTop 比例：

```typescript
// hooks/useSyncScroll.ts
const handleScroll = (source: "left" | "right") => {
  if (!syncScroll || isSyncing.current) return
  isSyncing.current = true

  const sourceEl = source === "left" ? leftRef.current : rightRef.current
  const targetEl = source === "left" ? rightRef.current : leftRef.current
  if (!sourceEl || !targetEl) return

  const ratio = sourceEl.scrollTop / (sourceEl.scrollHeight - sourceEl.clientHeight)
  targetEl.scrollTop = ratio * (targetEl.scrollHeight - targetEl.clientHeight)

  requestAnimationFrame(() => { isSyncing.current = false })
}
```

**关键技巧**：
- `isSyncing` ref 防止递归触发：A 滚动 → 更新 B → B 触发 scroll 事件 → 更新 A...
- 用 `requestAnimationFrame` 而不是 `setTimeout`，确保在下一帧前释放锁
- 用**比例**（0~1）而不是绝对值同步，因为左右内容长度不同

---

## 问题七：DeepSeek API 翻译失败的根因与修复

### 背景

用户报告翻译功能完全失败。点击翻译后持续报错，永远拿不到结果。

### 排查过程

#### 第一步：直接测试 DeepSeek API

用 Python requests 直接调用 DeepSeek Chat Completions API：

```python
requests.post("https://api.deepseek.com/v1/chat/completions", json={
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "将以下内容翻译为中文：Hello World"}],
    "temperature": 0.3,
    "max_tokens": 4096
})
```

**结果：200 OK，返回"你好，世界"。API 本身完全正常。**

#### 第二步：对比参考脚本

用户提供了已验证可用的参考脚本 `D:\pythontest\translation\translators\deepseek_translate.py`，对比发现关键差异：

| 对比项 | 参考脚本 ✅ | 本项目 ❌ |
|--------|----------|---------|
| `max_tokens` | **4096** | 16384 |
| 消息结构 | **只有 user role** | system + user |
| 系统提示词 | **无** | 50 行术语对照表，每次调用都带 |
| 单次输入大小 | 一段话 (~500 字) | 最多 18000 字 |
| API 响应时间 | 2-5 秒/段 | 30-60 秒/块 |

### 根因分析

翻译失败的根因**不是 DeepSeek API 本身的问题**，而是本项目 `translator.py` 的 API 调用方式与 DeepSeek API 的最佳实践不符：

1. **巨型系统提示词（50 行术语表）**：每次 API 调用都带上 50 行 `角色: system, 内容: 你是一位专业的学术论文翻译专家...` 的术语对照表。这增加了约 900 tokens 的输入开销，每次调用都要额外处理。

2. **`max_tokens=16384` 过大**：DeepSeek 推荐的翻译场景用 `4096` 即可。更大的 `max_tokens` 意味着模型生成更谨慎、更慢。

3. **大块内容聚合（18000 字/块）**：将多个段落合并成 18000 字的大块，每块的 DeepSeek 处理时间 30-60 秒。配合系统提示词，单次 API 调用约 5000-7000 input tokens + ~2000 output tokens。

4. **HTTP 超时级联**：120KB 文档 ≈ 7-8 个大块，总处理时间 4-8 分钟。Next.js 开发服务器代理层在此类长连接中产生 `ECONNRESET` / `socket hang up`。

### 修复方案

完全按照参考脚本的调用方式重写 `translator.py`：

#### 改动一：移除 system message，合并到 user prompt

```python
# ❌ 修复前：system + user 分离，system 带 50 行术语表
data = {
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT_50_LINES},
        {"role": "user", "content": "请翻译以下段落"}
    ],
    "max_tokens": 16384
}

# ✅ 修复后：只有 user role，术语表精简为 prompt 内嵌示例
TRANSLATE_PROMPT = """请将以下英文学术论文段落翻译成流畅、专业的中文。要求：
1. 保持专业术语准确，例如：
   - Dynamic Movement Primitives → 动态运动原语
   - reinforcement learning → 强化学习
2. 保持原文的段落结构和格式
3. 数学公式、变量名保持原样

英文原文：
{text}

请直接输出中文翻译："""

data = {
    "messages": [
        {"role": "user", "content": prompt}
    ],
    "max_tokens": 4096
}
```

#### 改动二：减小 chunk 大小

```python
# 修复前
MAX_SINGLE_CHUNK = 18000  # 大块 → 单个 API 调用 30-60 秒

# 修复后  
MAX_SINGLE_CHUNK = 6000   # 中块 → 单个 API 调用 10-20 秒
```

#### 改动三：异步翻译 + 轮询（架构优化）

```python
# POST /translate → 立即返回 202
threading.Thread(target=run_translation, daemon=True).start()
return {"data": {"status": "translating", "progress": 0}}

# GET /translate/status → 轮询进度
def get_translation_status(project_id, doc_id):
    job = _translation_jobs.get(f"{project_id}:{doc_id}")
    return {"data": job}
```

前端每 2 秒轮询一次，实时显示进度百分比。

#### 验证结果

对 120KB 的 PDF 论文进行实际翻译测试：

```
[1] status=translating, progress=18%
[2] status=translating, progress=22%
...
[61] status=completed, progress=100%
SUCCESS length=54678 tokens=67772
First 200: # 动态运动原语：学习运动行为的吸引子模型
Auke Jan Ijspeert
auke.ijspeert@epfl.ch
洛桑联邦理工学院，瑞士洛桑 CH-1015
```

翻译成功完成，54,678 字符的中文译文，专业术语翻译准确。

### 其他 AI 可参考的经验

1. **不要给 DeepSeek API 带巨型 system prompt**。术语表应精简为 user prompt 中的 inline 示例（2-3 个例子足够模型理解风格）。

2. **`max_tokens=4096` 对于段落翻译足够**。16384 只会让模型生成更慢、更犹豫。

3. **翻译 API 必须异步**。一篇论文 3-10 万词，逐段调用 LLM API，总时间 5-15 分钟。HTTP 连接不可能保持这么久。

4. **参考已验证能工作的脚本**来调整 API 调用参数，而不是自己猜测。DeepSeek API 的 `deepseek-v4-flash` 模型名是有效的，不需要强行改为 `deepseek-chat`。

---

## 问题八：进度条硬编码与翻译缓存加载失败

### 背景

用户反馈：
1. 翻译进度条永远显示 60%，不随实际进度变化
2. 翻译结果刷新页面后丢失，需要重新翻译

### 根因分析

#### 问题 1：进度条硬编码

```typescript
// DualPaneReader.tsx
<div className="absolute inset-y-0 left-0 bg-accent-500 rounded-full animate-pulse-soft" style={{ width: "60%" }} />
```

进度条宽度被硬编码为 `"60%"`，不会随 `translationResult.progress` 变化。

#### 问题 2：翻译缓存无法加载（最严重）

```python
# projects.py 中 save_translation 调用错误
storage_service.save_translation(project_id, doc_id, {
    "content": result["text"],
    "tokens_used": result["tokens"],
    "status": "completed",
    "translated_at": datetime.now(timezone.utc).isoformat(),
})
```

`save_translation` 函数签名是 `(project_id, doc_id, content: str, tokens_used: int)`，但实际传入了一个 dict。导致：
- 翻译内容被错误存储为对象
- Token 统计永远为 0
- 缓存无法被正确加载

### 修复方案

```typescript
// 修复进度条
style={{ width: `${translationResult?.progress || 0}%` }}
```

```python
// 修复 save_translation 调用
storage_service.save_translation(
    project_id, doc_id,
    content=result["text"],
    tokens_used=result["tokens"],
)
```

**数据修复**：修复存储中受影响的翻译记录，将 dict 格式转为 string 格式，并恢复正确的 Token 统计。

---

## 问题九：路由顺序错误导致 API 端点 404

### 背景

`/token-stats`、`/token-history`、`/search` 等端点全部返回 404 错误。

### 根因分析

FastAPI 路由匹配是按定义顺序进行的。`@router.get("/{project_id}")` 是一个通配路由，它放在了所有非参数路由之前，导致所有单段路径都被匹配为 `project_id` 参数。

```python
# ❌ 错误顺序
@router.get("/{project_id}")      # 这个通配路由会匹配 /token-stats、/search 等
@router.get("/token-stats")
@router.get("/token-history")
```

### 解决方案

将参数化路由移到所有非参数化路由之后：

```python
# ✅ 正确顺序
@router.get("/token-stats")
@router.get("/token-history")
@router.get("/search")
# ... 其他非参数路由 ...
@router.get("/{project_id}")      # 通配路由放在最后
```

### 经验总结

- **路由顺序很重要**：非参数化路由必须放在参数化路由之前
- **通配路由应放在末尾**：`/{param}` 这种模式会匹配几乎所有路径

---

## 问题十：Token 统计显示为零

### 背景

状态栏显示的 Token 统计永远为零。

### 根因分析

```typescript
// StatusBar.tsx
<span>Tokens: {(apiStats.todayTokens.total / 1000).toFixed(1)}K</span>
```

`todayTokens` 字段在 store 中永远是全零对象 `{0, 0, 0, 0}`，而实际统计数据存储在 `totalTokens` 中。

### 修复方案

```typescript
<span>Tokens: {(apiStats.totalTokens.total / 1000).toFixed(1)}K</span>
```

---

## 总结：关键架构决策

| 决策 | 方案 | 原因 |
|------|------|------|
| 文档渲染 | `dangerouslySetInnerHTML` + KaTeX 预渲染 | 30万字符不能走 React VDOM |
| CSS 隔离 | `.doc-content > *` 选择器 | innerHTML 内元素没有 Tailwind 类名 |
| TOC 导航 | 手动 `scrollTo()` | `scrollIntoView` 滚动窗口 |
| 导出图片 | 后端 Base64 嵌入 | 离线可用 |
| 搜索 | 后端全量遍历 | 数据量不大，不需要倒排索引 |
| 状态管理 | Zustand (单 store) | 应用规模适中，不需要 Redux |
| 翻译 | 异步并发 + WebSocket | 长耗时操作，实时进度推送 |
| 路由顺序 | 非参数路由在前，通配路由在后 | FastAPI 按顺序匹配 |

---

---
   
## 常见 Bug 检查清单

在提交代码前，检查以下常见问题：

1. **进度条**：确保使用动态值 `{progress}%` 而非硬编码
2. **路由顺序**：非参数路由必须在参数化路由之前
3. **API 调用**：检查参数是否与函数签名匹配
4. **Token 统计**：确保显示的是正确的统计字段
5. **存储格式**：确保存储的是字符串而非对象
6. **环境变量**：避免硬编码端口和 URL

---
   
## 问题十四：导出格式缺陷全面修复（`\begin{}...\end{}` 公式、HTML 非法嵌套、图片位置等）

### 背景

通过检查四个导出产物（MD/HTML/DOCX/PDF）和全部导出相关源代码，发现 9 个跨导出器的格式解析和图片缓存问题。

### 问题清单与修复

#### 修复 1：`\begin{}...\end{}` 公式环境不受保护（🔴 严重）

**问题**：所有导出器的公式保护正则只匹配 `$$`/`$`/`\[`/`\(` 定界符，遗漏了 `\begin{aligned}`、`\begin{array}`、`\begin{cases}` 等 LaTeX 环境。这些公式在 Markdown→HTML 转换时被破坏。

**修复**：在 `markdown_exporter.py`、`html_exporter.py`、`docx_exporter.py`、`translator.py` 的正则最前面添加 `\\begin\{[^}]*\}[\s\S]*?\\end\{[^}]*\}`，确保 LaTeX 环境优先匹配。

涉及的修复文件：
- `markdown_exporter.py:_protect_math` — 公式保护正则
- `html_exporter.py:_protect_math` — 公式保护正则
- `html_exporter.py:_restore_math_html` — 增加 `\begin` 还原分支
- `docx_exporter.py:_add_formatted_runs` — 内联正则
- `docx_exporter.py:_parse_content` — 行解析增加 `\begin` 处理
- `translator.py:FORMULA_BLOCK_RE` — 翻译前公式保护

#### 修复 2：HTML `<p><div>` 非法嵌套（🔴 严重）

**问题**：Python-Markdown 库将数学占位符 `@@MATH_N@@` 转换为 HTML 时包裹在 `<p>` 中，公式还原后变成 `<p><div class="math-block">...</div></p>`，违反 HTML 规范（块级元素不可嵌套在行内元素内）。

**修复**：在 `html_exporter.py:_markdown_to_html` 末尾增加后处理：
```python
html = re.sub(r'<p>\s*<div class="math-block">', r'<div class="math-block">', html)
html = re.sub(r'</div>\s*</p>', r'</div>', html)
```

#### 修复 3：Modern/Compact 主题缺少 KaTeX（🔴 严重）

**问题**：`template_manager.py` 中 Academic 和 Dark 模板有 KaTeX 脚本引用，但 Modern 和 Compact 模板缺少。使用这两个主题导出的 HTML 数学公式无法渲染。

**修复**：在 Modern 和 Compact 模板的 `<head>` 中添加 KaTeX CSS/JS CDN 引用，并在 `</body>` 前添加 `renderMathInElement` 初始化脚本。

#### 修复 4：图片位置均匀分布算法不准确（🔴 严重）

**问题**：`_enrich_translation_with_images` 按 `step = total_paras / total_images` 均匀分布图片到译文段落，完全忽略图片在原文章节中的实际位置。

**修复**：改为上下文相关算法 — 先计算每张图片在原文章节中的位置比例，再按相同比例映射到译文段落：
```python
# 计算图片在原文中的段落位置
o_ratio = img_para_idx / max(1, len(o_paras) - 1)
# 映射到译文对应位置
t_idx = int(o_ratio * (len(t_paras) - 1))
```

#### 修复 5：AssetManager 缓存清理不一致（🟡 中等）

**问题**：HTML 导出器在原文和译文图片嵌入之间调用 `clear_cache()`，这会同时清空 base64 缓存和已处理图片集合，导致翻译文本的图片需要重新编码。

**修复**：
- `collect_images` 参数 `_doc_id` 改为 `doc_id`（之前参数名加下划线表示未使用）
- 新增 `clear_processed_only()` 方法，只清除已处理集合，保留 base64 缓存
- HTML 导出器在原文/译文之间改用 `clear_processed_only()` 而非 `clear_cache()`

#### 修复 6：TemplateManager 模板文件重复写入

**问题**：每次 `TemplateManager.__init__()` 都会无条件重写所有模板文件，造成不必要的磁盘 I/O。

**修复**：引入 MD5 哈希版本检查机制：
- `_load_hashes()` / `_save_hashes()` — 从 `.template_hashes` 文件读写哈希
- `_compute_hash()` — 计算模板内容的 MD5
- 只在哈希变化或文件不存在时才写入
- 哈希变化时重新创建 Jinja2 Environment 以加载新模板

#### 修复 7：TOC 锚点生成错误（🟡 中等）

**问题**：`_generate_toc` 中使用 `str.replace("[^a-z0-9-]", "")` 清理锚点文本，但 `str.replace` 按字面字符串匹配而非正则，导致 `[^a-z0-9-]` 不被识别为字符类。

**修复**：
```python
# ❌ 修复前
anchor = text.lower().replace(" ", "-").replace("[^a-z0-9-]", "")

# ✅ 修复后
anchor = re.sub(r'[^a-z0-9-]', '', text.lower().replace(" ", "-"))
```

#### 修复 8：PDF 生成时 KaTeX 渲染等待不足（🟡 中等）

**问题**：`_pdf_generator.py` 中 `page.wait_for_timeout(1000)` 固定等待 1 秒，对于包含 200+ 图片和大量公式的大型文档，CDN 加载的 KaTeX 脚本可能在 1 秒内未完成渲染。

**修复**：用 `page.wait_for_function` 替代固定超时：
```javascript
// 检查是否有 KaTeX 脚本 + 是否有数学块 + KaTeX 是否已渲染
const hasKatex = !!document.querySelector('script[src*="katex.min.js"]');
if (!hasKatex) return true;  // 无 KaTeX → 立即继续
const hasMath = !!document.querySelector('.math-block, .math-inline');
if (!hasMath) return true;  // 无数学公式 → 立即继续
return !!document.querySelector('.katex, .katex-display');  // 等 KaTeX 渲染完成
```
超时设为 20 秒，异常时静默跳过。

#### 修复 9：Markdown 导出 HTML 标签清理过于激进（🟡 中等）

**问题**：`_strip_html_tags` 无条件剥离所有非 `br`/`hr` 的 HTML 标签，包括 `<code>`、`<pre>`、`<strong>`、`<em>` 等语义标签。

**修复**：在通用标签剥离之前，先转换语义标签为 Markdown 等价形式：
- `<pre>...</pre>` → ```` ```...``` ````
- `<code>...</code>` → `` `...` ``
- `<strong>/<b>...</b>` → `**...**`
- `<em>/<i>...</i>` → `*...*`

### 其他 AI 可参考的经验

- **公式保护必须在最前面**：当正则中有多个 `|` 分支时，`\begin{...}...\end{...}` 必须放在 `\[...\]` 之前，否则 `\[` 会提前匹配 `\begin` 中的反斜杠。
- **Markdown→HTML 转换后的 HTML 验证**：Python-Markdown 产生的 HTML 不是完全规范的，需要在关键位置（如公式块的 `<p><div>` 嵌套）做后处理。
- **模板版本管理**：当模板内嵌在 Python 源码中时，必须有机制确保磁盘缓存与代码同步。MD5 哈希比较是一个轻量级的方案。
- **Playwright PDF 的数学渲染**：`wait_for_timeout` 不可靠。用 `wait_for_function` 检测 DOM 中的 `.katex` 元素是确定 KaTeX 渲染完成的唯一可靠方法。
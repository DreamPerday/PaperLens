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

---

## 问题十五：统一文档中间层 AST / Block Schema 构建

### 背景

项目有四个导出器（MD/HTML/PDF/DOCX）和一个翻译器，每个模块都包含`各自的`独立的、重复的文档解析逻辑（公式保护、标题提取、列表解析、表格解析等）。这种 ad-hoc 解析模式导致：

1. **逻辑重复**：`_protect_math`、`_strip_html_tags`、`_parse_content` 等函数在每个导出器中独立实现
2. **解析不一致**：不同导出器对同一内容的处理结果不同（如 `\begin{aligned}` 在 HTML 中正确处理，在 DOCX 中可能被破坏）
3. **难以扩展**：添加新的导出格式需要重新实现所有解析逻辑
4. **Bug 易发**：每个导出器各自维护正则表达式，边角情况难以覆盖

### 解决方案：统一文档中间层 AST

构建了一个三层架构：

```
输入文本 (Markdown/LaTeX 混合)
      ↓
[MarkdownParser] — 解析器层
      ↓
Document AST (Block Schema) — 中间层
      ↓
[MarkdownRenderer / HTMLRenderer / DocxRenderer] — 渲染器层
      ↓
MD / HTML / DOCX / PDF 输出
```

### 架构说明

#### 1. Block Schema (`backend/app/models/block_schema.py`)

定义了完整的文档块类型层次结构：

**Block 类型**（12 种）：
| BlockType | 描述 | 关键字段 |
|-----------|------|---------|
| `heading` | ATX 标题 | `level` (1-6), `inlines` |
| `paragraph` | 文本段落 | `inlines` |
| `code_block` | 围栏代码块 | `content`, `lang` |
| `math_block` | 显示公式 | `content` (原始 LaTeX) |
| `image` | 图片块 | `content`, `meta.url` |
| `bullet_list` / `ordered_list` | 列表 | `children` (list_item) |
| `list_item` | 列表项 | `inlines` |
| `blockquote` | 块引用 | `children` (blocks) |
| `table` | 表格 | `rows`, `aligns` |
| `thematic_break` | 水平分割线 | - |
| `html_block` | 原始 HTML 块 | `content` |

**Inline 类型**（10 种）：
| InlineType | 描述 | 关键字段 |
|-----------|------|---------|
| `text` | 纯文本 | `content` |
| `bold` | **加粗** | `children` (支持嵌套) |
| `italic` | *斜体* | `children` (支持嵌套) |
| `underline` | 下划线 | `content` |
| `strikethrough` | 删除线 | `content` |
| `code` | `` 行内代码 `` | `content` |
| `math` | $行内公式$ | `content` |
| `link` | [链接](url) | `content`, `url`, `children` |
| `image` | ![图片](url) | `alt`, `url` |
| `soft_break` | 软换行 | - |

#### 2. MarkdownParser (`backend/app/services/parser/markdown_parser.py`)

行驱动的 Markdown 解析器，按优先级尝试匹配以下块类型：

1. Math Block（`\begin{}...\end{}`、`\[...\]`、`$$...$$`）
2. Fenced Code Block（` ``` ` / `~~~`）
3. ATX Heading（`# ` ~ `###### `）
4. Thematic Break（`---`、`***`、`___`）
5. Table（GFM 表格）
6. Blockquote（`> `）
7. List（`- `、`* `、`+ `、`1. `）
8. HTML Block（`<p>`、`<div>` 等块级标签）
9. Paragraph（兜底）

Inline 解析器支持嵌套（如 `**bold with *italic* inside**`），解析优先级：
- Math > Code > Image > Link > Bold > Italic > Text

#### 3. 格式渲染器

| 渲染器 | 文件 | 输出 |
|--------|------|------|
| `MarkdownRenderer` | `ast_renderer.py` | Markdown 文本（无损 round-trip） |
| `HTMLRenderer` | `html_renderer.py` | 语义化 HTML5（含 KaTeX 标记） |
| `DocxRenderer` | `docx_renderer.py` | python-docx Document 构建 |

### 重构效果

**删除的重复代码**（估计 300+ 行）：
- `docx_exporter.py:_parse_content` — 约 120 行自定义行解析逻辑
- `docx_exporter.py:_add_formatted_runs` — 约 80 行内联格式化解析
- `html_exporter.py:_protect_math` / `_restore_math_html` — 约 30 行公式正则
- `html_exporter.py:_markdown_to_html` — 约 10 行，改为 AST 通道
- `markdown_exporter.py:_protect_math` / `_restore_math` — 约 20 行公式正则
- `markdown_exporter.py:_strip_html_tags` — 约 20 行 HTML 清理

**新增的核心文件**：

```
backend/app/models/block_schema.py          — AST 核心类型定义
backend/app/services/parser/__init__.py     — 包入口
backend/app/services/parser/markdown_parser.py — 文本 → AST 解析器
backend/app/services/parser/ast_renderer.py    — AST → Markdown 渲染器
backend/app/services/parser/html_renderer.py   — AST → HTML 渲染器
backend/app/services/parser/docx_renderer.py   — AST → DOCX 渲染器
```

**修改的文件**（重构为 AST 通道）：
```
backend/app/services/export/html_exporter.py
backend/app/services/export/markdown_exporter.py
backend/app/services/export/docx_exporter.py
```

### 验证结果

通过 14 项综合测试（含学术论文场景），所有测试通过：

| 测试项 | 验证内容 |
|--------|---------|
| Heading | H1~H3 解析和渲染 |
| Inline | Bold/Italic/Code 正确解析 |
| Math | $inline$ 和 $$display$$ 及 HTML 标记 |
| LaTeX Environment | `\begin{equation}` 完整保留 |
| Lists | 有序/无序列表及嵌套 |
| Blockquote | 块引用解析 |
| Code Block | 围栏代码块及语言标识 |
| Table | GFM 表格及列对齐 |
| Thematic Break | 分割线 |
| Nested Formatting | `**bold *italic***` 嵌套解析 |
| Image/Link | 图片和链接的解析与渲染 |
| Round-trip | 二次渲染稳定性（第 2 次渲染与第 1 次 100% 一致） |
| Academic Document | 含公式、表格、列表的实际论文场景 |

### 使用示例

```python
from app.services.parser import MarkdownParser, render_to_html, render_document

parser = MarkdownParser()
doc = parser.parse(text)

# 导出为 HTML
html = render_to_html(doc)

# 导出为 Markdown（可继续编辑）
markdown = render_document(doc)

# 导出为 DOCX
from app.services.parser import DocxRenderer
docx_bytes = DocxRenderer().render(doc, title="Document")
```

---

## 问题十六：WYSIWYG 文档导出系统 — 工业级 AST + Render Pipeline 架构设计

### 0. 总体架构图

```
                     ┌─────────────┐
                     │  PDF Upload │
                     │  / OCR      │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │ PaddleOCR    │
                     │ + Layout     │
                     │   Parser     │
                     └──────┬──────┘
                            │ OCR Regions + Text
                     ┌──────▼──────┐
                     │ MarkdownParser│ ← Markdown/LaTeX 混合输入
                     │ (Python/TS   │
                     │  对齐实现)    │
                     └──────┬──────┘
                            │
                  ┌─────────▼─────────┐
                  │  Document AST     │
                  │  Block Schema     │  ← 唯一真相源
                  │  (Python ↔ TS)    │
                  └───┬──────┬────┬──┘
                      │      │    │
        ┌─────────────┤      │    └──────────────────┐
        │             │      │                        │
   ┌────▼────┐  ┌─────▼──┐ ┌▼──────────┐   ┌────────▼──────┐
   │ Web      │  │ HTML   │ │ Playwright │   │  Python        │
   │ Reader   │  │ Export │ │ PDF        │   │  DOCX / EPUB   │
   │ (React)  │  │        │ │ Generator  │   │  Export         │
   └────┬─────┘  └────┬───┘ └─────┬──────┘   └───────┬────────┘
        │             │            │                   │
        │    ┌────────┴────────────┴───────────────────┘
        │    │   Shared Renderer + Print CSS + Theme Tokens
        │    │   (一份代码，四种输出)
        └────┘
```

### 1. 统一文档 AST 架构

#### 1.1 TypeScript AST 类型定义

文件：[block-schema.ts](file:///d:/pythontest/translation-platform/frontend/src/ast/block-schema.ts)

**与 Python 端完全对齐的设计原则**：
- 类型名称、字段名、字段顺序与 [block_schema.py](file:///d:/pythontest/translation-platform/backend/app/models/block_schema.py) 完全一致
- TS 端扩展了 export-specific 类型（`CitationRef`、`OCRRegion`、`FigureMeta`、`TranslationPair` 等）
- 版本号统一管理：`DOCUMENT_AST_VERSION = "1.1.0"`

**完整 Block 类型（24 种）**：

| BlockType | 用途 | Web Reader | PDF | EPUB | DOCX |
|-----------|------|:---:|:---:|:---:|:---:|
| `heading` | 标题 H1-H6 | ✅ | ✅ | ✅ | ✅ |
| `paragraph` | 文本段落 | ✅ | ✅ | ✅ | ✅ |
| `code_block` | 代码块 | ✅ | ✅ | ✅ | ✅ |
| `math_block` | 显示公式 | ✅ | ✅ | ✅ | ✅ |
| `image` | 独立图片 | ✅ | ✅ | ✅ | ✅ |
| `bullet_list` | 无序列表 | ✅ | ✅ | ✅ | ✅ |
| `ordered_list` | 有序列表 | ✅ | ✅ | ✅ | ✅ |
| `list_item` | 列表项 | ✅ | ✅ | ✅ | ✅ |
| `blockquote` | 块引用 | ✅ | ✅ | ✅ | ✅ |
| `table` | GFM 表格 | ✅ | ✅ | ✅ | ✅ |
| `thematic_break` | 水平线 | ✅ | ✅ | ✅ | ✅ |
| `html_block` | 原始 HTML | ✅ | ✅ | ✅ | - |
| `footnote` | 脚注标记 | ✅ | ✅ | ✅ | ✅ |
| `footnote_ref` | 脚注内容 | ✅ | ✅ | ✅ | ✅ |
| `citation` | 引文标记 `[1]` | ✅ | ✅ | ✅ | ✅ |
| `citation_list` | 参考文献列表 | ✅ | ✅ | ✅ | ✅ |
| `toc` | 目录 | ✅ | ✅ | ✅ | ✅ |
| `figure` | 带标题图表 | ✅ | ✅ | ✅ | ✅ |
| `ocr_region` | OCR 区域 | ✅ | ✅ | ✅ | ✅ |
| `column_layout` | 双栏/单栏 | ✅ | ✅ | ✅ | - |
| `page_break` | 强制分页 | - | ✅ | ✅ | ✅ |

**Inline 类型（10 种）**：

| InlineType | 描述 | 嵌套支持 | 示例 |
|-----------|------|:---:|------|
| `text` | 纯文本 | - | `Hello` |
| `bold` | 加粗 | ✅ | `**bold *italic***` |
| `italic` | 斜体 | ✅ | `*italic*` |
| `underline` | 下划线 | - | `<u>` |
| `strikethrough` | 删除线 | - | `~~text~~` |
| `code` | 行内代码 | - | `` `code` `` |
| `math` | 行内公式 | - | `$E=mc^2$` |
| `link` | 超链接 | ✅ | `[text](url)` |
| `image` | 行内图片 | - | `![alt](src)` |
| `soft_break` | 软换行 | - | `<br>` |

#### 1.2 扩展 Schema

**OCR Block Schema**（`OCRRegion`）：
```typescript
interface OCRBBox {
  x: number; y: number; width: number; height: number; page: number;
}
interface OCRRegion {
  bbox: OCRBBox;
  type: "text" | "title" | "figure" | "table" | "formula" | "footer" | "header";
  confidence: number;
  text: string;
}
```

**Citation Schema**（`CitationRef`）：
```typescript
interface CitationRef {
  id: string; index: number;
  authors: string; title: string; venue: string;
  year: number; doi?: string; url?: string;
}
```

**Figure Schema**（`FigureMeta`）：
```typescript
interface FigureMeta {
  id: string; caption: string; label: string;
  width: number; height: number; src: string;
  srcType: "base64" | "url" | "file"; ocrBbox?: OCRBBox;
}
```

**Translation Schema**（`TranslationPair`）：
```typescript
interface TranslationPair {
  source: InlineNode[];
  target: InlineNode[];
  confidence: number;
}
```
每个 `Block` 可选携带 `translation?: TranslationPair`，从而实现段落级双语对照，而非整篇文档的简单拼接。

#### 1.3 AI-Friendly 设计

- **段落粒度 TranslationPair**：每个 Block 携带 `source → target` 对，支持 RAG 检索
- **Inline 级别对齐**：`InlineNode[]` 的对齐使翻译模型可以逐词/逐公式匹配
- **Confidence 字段**：翻译置信度可直接用于高亮低置信区域
- **Metadata 完整**：文档元信息（DOI、arxivId、关键词）随 AST 携带

---

### 2. Unified Renderer 架构

#### 2.1 核心原则

> **一份 AST，一套 Renderer，四种输出路径**

```
                   Document AST
                        │
            ┌───────────┼───────────┐
            │           │           │
      [BlockRenderer]   │     [Python Renderer]
      (React)           │     (Server-side)
            │           │           │
   ┌────────┴───┐       │    ┌──────┴──────┐
   │  Reader    │  Print │    │ DOCX Export │
   │  screen    │  CSS   │    │ EPUB Export │
   └────────────┘        │    └─────────────┘
                         │
                  ┌──────┴──────┐
                  │ PDF Export  │
                  │ (Playwright │
                  │  渲染 Print  │
                  │  CSS HTML)   │
                  └─────────────┘
```

#### 2.2 Block Renderer（共享组件）

文件：[block-renderer.tsx](file:///d:/pythontest/translation-platform/frontend/src/ast/block-renderer.tsx)

```tsx
<DocumentRenderer blocks={ast.blocks} mode="reader" />   // Web Reading
<DocumentRenderer blocks={ast.blocks} mode="print" />     // Print / PDF
<DocumentRenderer blocks={ast.blocks} mode="export" />    // HTML export
```

**Key design decisions**：

1. **同一个 `BlockRenderer` 组件**渲染所有 Block 类型，mode prop 控制细节
2. **Inline 渲染器独立为纯函数** `renderInlines()`，不依赖 DOM
3. **KaTeX 在组件层使用 `React.useMemo` + `dangerouslySetInnerHTML`** — 与现有 `DocumentView.tsx` 一致，但改为 Block 级别而非全文正则
4. **图片使用 `loading="lazy"`** — Reader 模式懒加载，Print 模式下浏览器自动加载全部

#### 2.3 Theme System

文件：[print.css](file:///d:/pythontest/translation-platform/frontend/src/ast/print.css)

**CSS Custom Properties 令牌系统**：

```css
:root {
  --font-body: "Inter", "Noto Sans SC", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", monospace;
  --font-math: "KaTeX_Main", "Times New Roman", serif;
  --color-text: #1a1a2e;
  --color-heading: #0f0f1a;
  --color-link: #2e6eff;
  --color-code-bg: #f1f3f6;
  --color-quote-bg: #f8f9fb;
  /* ... 50+ tokens */
}

/* Dark mode override */
:root.dark {
  --color-text: #e2e4ea;
  --color-heading: #f0f2f8;
  /* ... */
}
```

**四种模式同一套令牌**：
- `@media screen` — 正常 Web 阅读体验
- `@media print` — PDF / 打印输出
- `.dark` — 深色模式 Web Reader
- `@media (max-width: 768px)` — 移动端布局

#### 2.4 SSR / Hydration

```
Server (Next.js SSR)            Client (Hydration)
     │                               │
     │ parse(markdown) → AST         │
     │                               │
     │ <DocumentRenderer>            │ hydrate →
     │   KaTeX SSR                   │   KaTeX client-side
     │   (katex.renderToString)      │   (React.useMemo)
     │ </DocumentRenderer>           │
```

**KaTeX SSR 策略**：
- **Server side**：`katex.renderToString()` 生成 HTML 字符串（零 JS 首次渲染）
- **Client side hydration**：`React.useMemo` 缓存，公式不变不重算
- **Print mode**：浏览器直接渲染已存在的 `.katex-html` DOM，无需额外 JS

---

### 3. PDF 导出架构

#### 3.1 为什么 HTML → Chromium PDF 是最佳方案

| 方案 | 数学公式 | 中文 | 图片 | 开发成本 | 结果 |
|------|:---:|:---:|:---:|:---:|------|
| WeasyPrint | ❌ 不支持 JS/KaTeX | ✅ | ✅ | 低 | 公式丢失 |
| LaTeX→PDF | ✅ | 复杂 | ⚠️ | 极高 | 好但难自动化 |
| Canvas 截图 | ❌ 文本无法选择 | ✅ | ✅ | 中 | 模糊位图 |
| **Playwright Chromium PDF** | ✅ KaTeX SSR | ✅ | ✅ | 低 | 矢量文本+公式 |
| Puppeteer Chromium PDF | ✅ | ✅ | ✅ | 低 | 同 Playwright |

**选择 Playwright 的核心理由**：
1. **Chromium PDF 引擎**内置分页、字体嵌入、CSS print 渲染 — 印刷级排版
2. **KaTeX SSR 已预渲染为 HTML**，Chromium 直接渲染，无需 JS 执行（`wait_for_function` 检查 `.katex` 元素即可）
3. 无额外依赖：已在项目中使用，复用现有 `_pdf_generator.py`
4. 跨平台一致性：Windows/Linux/Docker 同一套代码

#### 3.2 完整 PDF Pipeline

```
AST (Python)
  │
  ▼
HTMLRenderer (server-side, Python)
  │  render_to_html(ast_doc)
  │  生成 standalone HTML with:
  │    - 内联 print.css
  │    - 内联 KaTeX CSS
  │    - 内联字体 @font-face（Inter, Noto Sans SC）
  │    - Base64 图片
  │    - <meta charset="utf-8">
  │    - <title> 元信息
  ▼
standalone HTML file
  │
  ▼
Playwright Chromium
  │  page.goto("file://...")
  │  wait_for_function("!!document.querySelector('.katex')")
  │  wait_for_timeout(500)       ← 等待 KaTeX 渲染完成
  │  page.pdf({
  │    format: "A4",
  │    print_background: true,
  │    display_header_footer: true,
  │    header_template: "...",
  │    footer_template: "Page <span class='pageNumber'></span>",
  │    margin: { top: "2.5cm", bottom: "2cm", left: "2.5cm", right: "2cm" }
  │  })
  ▼
PDF (bytes)
```

#### 3.3 Print CSS 关键规则

```css
@media print {
  @page {
    size: A4;
    margin-top: 2.5cm;
    @top-center { content: string(doctitle); }
    @bottom-center { content: counter(page); }
  }

  /* 避免公式/图表/代码被截断 */
  .math-display, .figure-block, .code-block, table {
    page-break-inside: avoid;
  }

  /* 标题后不单独分页 */
  h1, h2, h3 { page-break-after: avoid; }

  /* 长公式允许横向滚动（极少情况） */
  .math-display .katex { overflow-x: auto; }

  /* 强制颜色打印 */
  body { -webkit-print-color-adjust: exact; }
}
```

#### 3.4 字体嵌入

Chromium PDF 自动嵌入页面使用的字体。确保：
1. HTML 中通过 `@font-face` 或 `<link>` 声明字体
2. 字体文件在 `file://` 协议下可访问
3. Playwright 启动时传递 `--font-render-hinting=none`（已配置）

#### 3.5 大文档分页

- **Chromium 自动分页**：基于 A4 尺寸自动分页，无需手动计算
- **Print CSS `page-break-before/after`**：控制章节分页
- **`orphans: 2; widows: 2`**：避免孤行
- **Header/Footer**：Chromium 的 `header_template` / `footer_template` 支持 `pageNumber` / `totalPages` 占位符

#### 3.6 KaTeX SSR 渲染确认

```python
# 替代 wait_for_timeout — 等待 KaTeX DOM 确实渲染完成
page.wait_for_function(
    "document.querySelectorAll('.katex-html').length > 0 || "
    "document.querySelectorAll('.math-display').length === 0",
    timeout=10000
)
```

---

### 4. EPUB 导出架构

#### 4.1 EPUB 内部结构

```
document.epub (ZIP)
├── mimetype                  ("application/epub+zip")
├── META-INF/
│   └── container.xml
└── OEBPS/
    ├── content.opf           (metadata + spine + manifest)
    ├── toc.ncx               (NCX navigation)
    ├── nav.xhtml             (HTML5 nav for EPUB3)
    ├── css/
    │   ├── print.css         (复用！与 Web Reader 同一套)
    │   └── katex.min.css
    ├── images/
    │   └── *.png
    └── xhtml/
        ├── cover.xhtml
        ├── chapter-01.xhtml
        ├── chapter-02.xhtml
        └── ...
```

#### 4.2 HTML → EPUB Pipeline

```
Document AST
  │
  ▼
HTMLRenderer (mode="epub")
  │  与 Print 模式共用 print.css
  │  额外处理：
  │    - KaTeX CSS inline
  │    - 图片 Base64 → <img> 标签
  │    - 按 heading level=1 分章节
  │
  ▼
章节化 HTML 文件 (chapter-*.xhtml)
  │
  ▼
ebooklib (Python) 打包
  │  epub.set_metadata(...)
  │  epub.add_css(print.css)
  │  epub.add_chapter(chapter)
  │  epub.write()
  ▼
.epub 文件
```

#### 4.3 数学公式兼容

EPUB 对 KaTeX 的兼容策略：

| 方案 | Kindle | iBooks | 通用阅读器 |
|------|:---:|:---:|:---:|
| KaTeX HTML + CSS inline | ⚠️ | ✅ | ✅ |
| MathML | ✅ | ✅ | ⚠️ |
| SVG 图片（KaTeX→SVG） | ✅ | ✅ | ✅ |

**推荐策略**：**KaTeX HTML + 降级 SVG**

1. **首选**：内联 KaTeX HTML + KaTeX CSS（EPUB3 阅读器如 iBooks、Thorium 完美支持）
2. **降级**：对 Kindle 等老旧 EPUB2 阅读器，将关键公式转为 SVG 嵌入

```python
# KaTeX → SVG 降级（通过 Node.js）
import subprocess
def katex_to_svg(latex: str, display: bool = True) -> str:
    result = subprocess.run(
        ["npx", "katex", latex, "--output", "mathml" if else "html"],
        capture_output=True, text=True
    )
    return result.stdout
```

#### 4.4 CSS 适配

```css
/* EPUB 额外规则 — 附加到 print.css 之后 */
@supports (display: flex) {
  /* EPUB3 才支持的现代布局 */
  .math-display { display: flex; justify-content: center; }
}

/* Kindle 兼容 — 回退到简单布局 */
.kfx .math-display {
  text-align: center;
  page-break-inside: avoid;
}
```

#### 4.5 导航（NCX + NAV）

```xml
<!-- toc.ncx — EPUB2 兼容 -->
<navMap>
  <navPoint id="ch1" playOrder="1">
    <navLabel><text>Introduction</text></navLabel>
    <content src="xhtml/chapter-01.xhtml"/>
  </navPoint>
</navMap>

<!-- nav.xhtml — EPUB3 -->
<nav epub:type="toc">
  <ol>
    <li><a href="xhtml/chapter-01.xhtml">Introduction</a></li>
  </ol>
</nav>
```

---

### 5. DOCX 导出架构

#### 5.1 AST → python-docx 映射

| Block Type | python-docx 方法 | 样式 |
|-----------|-----------------|------|
| `heading` (level=1) | `doc.add_heading(text, level=1)` | `Heading 1` |
| `heading` (level=2) | `doc.add_heading(text, level=2)` | `Heading 2` |
| `paragraph` | `doc.add_paragraph()` | `Normal` |
| `code_block` | 手动 paragraph + Consolas font | `Code` |
| `math_block` | paragraph + italic `[ ... ]` 标记 | `Math` |
| `bullet_list` | `doc.add_paragraph(style='List Bullet')` | `List Bullet` |
| `ordered_list` | `doc.add_paragraph(style='List Number')` | `List Number` |
| `blockquote` | paragraph + `left_indent=0.5inch` | `Quote` |
| `table` | `doc.add_table(rows, cols)` | `Table Grid` |
| `figure` | `doc.add_picture(stream)` | 居中 |
| `page_break` | `doc.add_page_break()` | — |

#### 5.2 样式映射

已在 [docx_renderer.py](file:///d:/pythontest/translation-platform/backend/app/services/parser/docx_renderer.py) 中实现：
- 字体：Times New Roman 12pt（正文）/ Consolas 10pt（代码）
- 标题大小：H1=20pt, H2=18pt, H3=16pt
- 行距：正文 1.5 倍行距 / 代码单倍行距
- 页面：A4 (8.27×11.69 inches)，1英寸页边距

#### 5.3 数学公式处理

当前 DOCX 不原生支持 KaTeX/MathML，采用**回退标记**方案：

```python
# 行内公式：italic 字体 + 括号标注
run = p.add_run(f"({math_content})")
run.font.italic = True

# 显示公式：居中段落
p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
run = p.add_run(f"[ {math_content} ]")
```

**长期方案**（可选）：使用 MathML→OMML 转换（Word 原生公式格式）。

---

### 6. Web Reader 与 Export 一致性

#### 6.1 如何保证一致

```
┌─────────────────────────────────────────────┐
│         同一份代码路径                        │
│                                              │
│  AST → BlockRenderer → print.css → Output    │
│                                              │
│  mode="reader"  → screen media → Web Reader  │
│  mode="print"   → print media  → PDF         │
│  mode="export"  → inline CSS   → HTML file   │
└─────────────────────────────────────────────┘
```

#### 6.2 共享清单

| 共享资源 | 使用方式 |
|---------|---------|
| **AST types** | TS ↔ Python 字段一一对应 |
| **BlockRenderer** | 同一组件，三种 mode |
| **print.css** | 同一CSS，三种 media 查询 |
| **Typography tokens** | CSS custom properties，一处定义 |
| **KaTeX** | `katex.renderToString()` — SS/CSR/Export 同一API |
| **Image renderer** | `<img>` + `figure` 标签，不依赖 canvas |

#### 6.3 如何避免 "Web 正常 / PDF 错乱"

1. **永远不依赖运行时 JavaScript 的布局计算** — 所有布局由 CSS 控制
2. **使用 CSS `@page` 规则**统一 PDF 页面尺寸，而非 JS 动态计算
3. **测试：在浏览器 DevTools 中模拟 `@media print`** 预览 PDF 效果
4. **CI 中自动化对比**：Playwright 生成 PDF 截图 vs Web Reader 截图

---

### 7. 数学公式导出

#### 7.1 KaTeX SSR 策略

```
KaTeX LaTeX Input
      │
      ├──→ katex.renderToString() → HTML string → SSR / Client hydrate
      │
      ├──→ (alternate) katex.__renderToDomTree() → React elements
      │
      └──→ (fallback) SVG via node-katex → <img src="data:image/svg+xml;...">
```

**当前选择**：`katex.renderToString()` + `dangerouslySetInnerHTML`

#### 7.2 各格式策略

| 格式 | 策略 | 兼容性 |
|------|------|:---:|
| **Web** | `katex.renderToString()` → SSR + hydrate | ✅ 完美 |
| **PDF** | 同上 → Chromium 渲染 KaTeX HTML | ✅ 完美 |
| **EPUB** | KaTeX HTML + KaTeX CSS inline + SVG 降级 | ✅ |
| **DOCX** | Italic 文本 + `[ ... ]` 标记 | ⚠️ 可读 |
| **Markdown** | 原始 `$...$` / `$$...$$` 保留 | ✅ 完美 |

#### 7.3 长公式处理

```css
/* 溢出时横向滚动，不截断、不缩小 */
.math-display {
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
}

/* 允许 KaTeX 在特定位置换行 */
.math-display .katex { white-space: normal; }
```

#### 7.4 OCR 数学公式

PaddleOCR 输出：
- 行内公式：`$E = mc^2$` 或 `\(E = mc^2\)`
- 显示公式：`\begin{equation}...\end{equation}`

AI 翻译可以在翻译过程中保留公式占位符，翻译完成后再用 AST 重新组装。

---

### 8. OCR 与图片处理

#### 8.1 OCR Block 保留

每个 OCR 识别的区域在 AST 中保留为 `ocr_region` Block：

```typescript
{
  type: "ocr_region",
  ocrRegion: {
    bbox: { x: 100, y: 200, width: 300, height: 50, page: 3 },
    type: "figure",
    confidence: 0.95,
    text: "Figure 1: Architecture overview"
  }
}
```

#### 8.2 图片导出策略

| 场景 | 策略 |
|------|------|
| **Web Reader** | `<img src="/api/images/{doc_id}/{hash}">` + lazy loading |
| **HTML Export** | Base64 data URI（`embed_images: true`） |
| **PDF Export** | Playwright 自动渲染 `<img>`，base64 直接嵌入 |
| **EPUB Export** | 图片解码后写入 EPUB ZIP，`<img src="../images/fig1.png">` |
| **DOCX Export** | `doc.add_picture(BytesIO(base64decode(data)))` |

#### 8.3 图片压缩

```python
# Large figure → compressed JPEG for export
from PIL import Image
def compress_figure(data: bytes, max_width: int = 1200) -> bytes:
    img = Image.open(BytesIO(data))
    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()
```

---

## 问题十七：翻译后原文面板变宽挤占译文空间

### 背景

翻译/重新翻译后，原文面板宽度变宽，挤占了右侧译文面板的空间，只有重启服务器才能恢复。

### 分析

`DualPaneReader` 中左右面板用 `flex-1 min-w-0` 分配宽度。翻译完成后，面板内容从空 `<div>` 切换到完整 `DocumentView`（含 HTML 表格、KaTeX 公式）。`min-w-0` 在某些浏览器下无法压制 table/公式的固有最小宽度，内容撑开面板。

### 解决方案

**1. 面板容器从 Flexbox 改 CSS Grid**

```tsx
// 修复前：Flexbox
<div className="flex-1 flex min-h-0">

// 修复后：CSS Grid 强制 50/50
<div className="flex-1 grid grid-cols-1 lg:grid-cols-2 min-h-0">
```

移除各面板的 `flex-1`，保留 `min-w-0`。Grid 的 `1fr 1fr` 不受内容宽度影响。

**2. CSS 溢出保护**

- `.reader-panel`：`overflow-wrap: anywhere; min-width: 0`
- `.doc-content p`：`word-break: break-word`
- `.doc-content table`：`table-layout: auto`

### 关键经验

- **Flex `flex-1` + `min-w-0` 在动态内容切换时不可靠**。CSS Grid 是更安全的选择。
- **Grid 对移动端更友好**：`grid-cols-1 lg:grid-cols-2` 天然支持响应式。

---

## 问题十八：AI 翻译丢失 Markdown 格式 + 中文文本溢出

### 背景

1. AI 翻译后 Markdown 格式标记丢失（`**bold**`→`粗体`，`### heading`→纯文本）
2. 中文翻译宽度超出可视范围

### 分析

原有 `_protect_formulas()` 只保护 LaTeX，Markdown 标记裸露传给 AI。AI 翻译文本但丢弃标记符号。

中文无自然分词，CSS 只有 `.doc-content p` 有 `word-break`，其他元素溢出容器。

### 解决方案

#### Markdown 格式双层保护

八种格式保护模式（[translator.py](file:///d:/pythontest/translation-platform/backend/app/services/translator.py)）：

| 模式 | 匹配 | 策略 |
|------|------|------|
| `MD_INLINE_CODE_RE` | `` `code` `` | 替换为 `[MDC_N]` |
| `MD_ITALIC_RE` | `*italic*` | 替换为 `[MDC_N]` |
| `MD_BOLD_RE` | `**bold**` | 替换为 `[MDC_N]` |
| `MD_LINK_RE` | `[text](url)` | 替换为 `[MDC_N]` |
| `MD_CODE_BLOCK_RE` | ` ```...``` ` | 替换为 `[MDC_N]` |
| `MD_BLOCKQUOTE_PREFIX_RE` | `> quote` | 替换为 `[MDC_N]` |
| `MD_LIST_PREFIX_RE` | `- item` / `1. item` | 替换为 `[MDC_N]` |
| `MD_HEADING_PREFIX_RE` | `### heading` | 替换为 `[MDC_N]` |

保护顺序从小到大（inline code→italic→bold→links→code blocks→blockquote→lists→headings）。

**增强提示词**：12 条明确的 Markdown 保留规则。

#### 中文溢出全面 CSS 修复

为所有 `doc-content` 子元素添加 `word-break: break-word; overflow-wrap: break-word`：
`h1-h6`, `li`, `blockquote`, `code`, `pre`, `a`, `figcaption`。

### 关键经验

- **格式保护必须在公式保护之后、发送前执行**，还原时反过来。
- **占位符命名要区分**：`[FORMULA_N]` vs `[MDC_N]`，避免交叉冲突。
- **中文溢出修复要全面**，不能只修 `p`，必须覆盖所有子元素。

---

## 问题十九：AI 翻译分段逻辑重新设计 — 块感知分裂 + 完整性校验

### 背景

`split_paragraphs()` 用 `re.split(r'\n\s*\n', text)` 盲分割。HTML 表格内空行导致 `<table>` 被切碎分段传给 AI，结果标签错乱、显示损坏。翻译后无校验。

### 分析

需要三个新能力：识别不可分割的原子块、在保持原子性的前提下分块、翻译后验证数据完整性。

### 解决方案：四层防御架构

#### Layer 1 — 原子块识别

`ATOMIC_BLOCK_RE` 统一匹配 5 种原子块：

| 分组 | 类型 | 示例 |
|------|------|------|
| 1 | HTML 容器 | `<table>...</table>` |
| 2 | Fenced code | ` ```...``` ` |
| 3 | LaTeX 环境 | `\begin{aligned}...\end{aligned}` |
| 4 | 显示公式 | `$$...$$` |
| 5 | 多行引用 | `> line1\n> line2` |

`_find_atomic_blocks(text)` → `[(start, end, type), ...]`

#### Layer 2 — 块感知分裂

`_block_aware_split(text)` 核心：**占位符替换 → 分割 → 还原**

```python
# 1. 原子块 → __ATOMIC_N__
# 2. 在受保护文本上按 /\n\n+/ 分割
# 3. __ATOMIC_N__ → 原始内容
```

原子块内部空行永不触发分裂。

#### Layer 3 — 智能分块

`_smart_chunk_paragraphs` 重写，新增：

- **HTML 块检测**：`HTML_BLOCK_RE` 匹配，HTML 块单独成 chunk
- **富文本因子**：`_rich_text_factor()` 估计标记占比，有效长度 = 实际长度 × (1 - markup × 0.5)
- **公式长度补偿**：扣除公式字符
- **宽限制**：HTML 块 `NORMAL_CHUNK_MAX × 1.5`

#### Layer 4 — 完整性校验

`_validate_chunk_completeness(original, translated, idx)` 四维度：

| 维度 | 阈值 | 含义 |
|------|------|------|
| 长度比 | `trans < orig × 0.15` | issue |
| 空翻译 | `trans == 0` | issue |
| 格式标记 | 数量不匹配 | warning |
| 公式数 | 数量不匹配 | warning |
| 段落数 | 丢失超 50% | warning |

`translate_document_async` 集成校验日志。

### 测试（7 项全通过）

```
✅ 简单文本 → 3 段
✅ HTML 表格（4 行） → 完整，闭合正常
✅ 代码块 → 完整
✅ LaTeX 环境 → 完整
✅ 混合文档 → 表格/代码块分别完整
✅ $$ 内部双空行 → 不分裂
✅ 分块回归 → 段落数→chunk 数正确
```

### 关键经验

- **占位符替换法**是最简单的结构化内容保护方式：不需要自己写分段器。
- **HTML 富文本 chunk 大小**：`table`/`figure` 大多为标记字符，`_rich_text_factor()` 修正有效长度。
- **长 HTML 块单独成 chunk**：超大 table 独立处理，避免合并后超出 token 限制。

---

### 9. Print CSS 系统

完整实现文件：[print.css](file:///d:/pythontest/translation-platform/frontend/src/ast/print.css)

#### 9.1 覆盖的模块

| 模块 | CSS 类 | 关键规则 |
|------|--------|---------|
| Typography | `.document-renderer` | `--font-body`, `--line-height-body`, `text-align: justify` |
| Margin | `@page` | `margin: 2.5cm 2cm 2cm 2.5cm` |
| Font | `@font-face` (inline) | Inter, Noto Sans SC, JetBrains Mono |
| Page Size | `@page { size: A4; }` | 可切换 Letter |
| TOC | `.toc-block` | `page-break-after: always` |
| Citation | `.citation-list` | `font-size: 0.9em` |
| Figure | `.figure-block` | `max-width: 100%; page-break-inside: avoid` |
| Formula | `.math-display` | `overflow-x: auto; page-break-inside: avoid` |
| Table | `.doc-table` | `border-collapse: collapse; page-break-inside: avoid` |
| Page Break | `.page-break` | `page-break-after: always` |
| Dual Column | `.column-layout.two-column` | `column-count: 2; column-gap: 1.5em` |

#### 9.2 两种模式 CSS

```css
/* 双栏模式 — 学术论文双栏 */
.column-layout.two-column {
  column-count: 2;
  column-gap: 1.5em;
  column-rule: 1px solid var(--color-border);

  h1, h2, .math-display, .figure-block, .table-wrapper {
    column-span: all;  /* 关键元素跨栏 */
  }
}

/* 单栏模式 — A4 默认 */
.document-renderer:not(.two-column) {
  max-width: none;
}
```

---

### 10. 推荐目录结构

```
translation-platform/
├── frontend/                          # Next.js 14 App Router
│   ├── src/
│   │   ├── ast/                       # ★ AST 模块（核心共享层）
│   │   │   ├── index.ts               #    barrel export
│   │   │   ├── block-schema.ts        #    TS AST 类型定义
│   │   │   ├── block-renderer.tsx     #    Shared Block Renderer
│   │   │   └── print.css              #    Print CSS + Design Tokens
│   │   ├── renderer/                  # ★ 渲染器（新增）
│   │   │   ├── web/                   #    Web Reader 渲染器
│   │   │   │   ├── DualPaneReader.tsx
│   │   │   │   ├── DocumentView.tsx
│   │   │   │   ├── MathRenderer.tsx
│   │   │   │   └── TOC.tsx
│   │   │   ├── export/                #    Export 渲染引擎
│   │   │   │   ├── html-renderer.ts   #    AST → HTML (SSR)
│   │   │   │   ├── print-layout.tsx   #    Print 布局组件
│   │   │   │   └── epub-renderer.ts   #    AST → EPUB HTML
│   │   │   └── shared/               #    共享渲染工具
│   │   │       ├── inline-renderer.ts
│   │   │       └── math-engine.ts
│   │   ├── themes/                    # ★ 主题系统（新增）
│   │   │   ├── tokens.css             #    CSS custom properties
│   │   │   ├── academic.css           #    学术风格
│   │   │   ├── modern.css             #    现代风格
│   │   │   ├── dark.css               #    深色模式
│   │   │   └── print-overrides.css    #    打印覆盖
│   │   ├── print/                     # ★ 打印样式（新增）
│   │   │   ├── academic-print.css     #    学术打印
│   │   │   ├── a4.css                 #    A4 纸张
│   │   │   ├── letter.css             #    Letter 纸张
│   │   │   └── mobile-print.css       #    移动端打印
│   │   ├── components/                # 现有组件
│   │   │   ├── reader/               #    DualPaneReader, DocumentView, ...
│   │   │   ├── export/               #    ExportModal
│   │   │   └── ui/                   #    Button, Dialog, ...
│   │   ├── hooks/                     # useSyncScroll, useExport, ...
│   │   ├── store/                     # Zustand store
│   │   ├── types/                     # API types (Project, TranslationResult...)
│   │   ├── lib/                       # api.ts, utils.ts
│   │   └── app/                       # Next.js 路由
│   ├── tailwind.config.ts
│   └── package.json
│
├── backend/                           # FastAPI
│   ├── app/
│   │   ├── models/
│   │   │   ├── schemas.py
│   │   │   └── block_schema.py        # ★ Python AST 定义
│   │   ├── services/
│   │   │   ├── parser/                # ★ 解析器
│   │   │   │   ├── __init__.py
│   │   │   │   ├── markdown_parser.py
│   │   │   │   ├── ast_renderer.py    # AST → Markdown
│   │   │   │   ├── html_renderer.py   # AST → HTML
│   │   │   │   └── docx_renderer.py   # AST → DOCX
│   │   │   ├── export/                # ★ 导出器
│   │   │   │   ├── __init__.py
│   │   │   │   ├── html_exporter.py
│   │   │   │   ├── markdown_exporter.py
│   │   │   │   ├── pdf_exporter.py
│   │   │   │   ├── docx_exporter.py
│   │   │   │   └── epub_exporter.py   # ★ 新增
│   │   │   ├── pipeline/              # ★ 导出流水线（新增）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── export_worker.py   #   后台导出 Worker
│   │   │   │   ├── export_queue.py    #   导出任务队列
│   │   │   │   └── temp_manager.py    #   临时文件管理
│   │   │   ├── translator.py
│   │   │   └── ocr.py
│   │   ├── routes/
│   │   │   ├── export.py
│   │   │   └── projects.py
│   │   └── utils/
│   │       └── parser.py
│   └── requirements.txt
│
└── DEV_NOTES.md                       # 本文件
```

---

### 11. 技术选型推荐

#### 11.1 Frontend

| 层级 | 选型 | 理由 |
|------|------|------|
| **Renderer** | 自定义 `BlockRenderer` (React) | 完全控制→Print CSS 一致 |
| **Virtualization** | `@tanstack/react-virtual` | 大文档虚拟滚动 |
| **Theme Engine** | CSS Custom Properties + Tailwind | 零运行时开销 |
| **State** | Zustand (已有) | 轻量，与 React 解耦 |
| **Math** | KaTeX (已有) | SSR 支持，比 MathJax 快 10× |
| **SSR** | Next.js 14 Server Components (已有) | KaTeX 可服务端渲染 |

#### 11.2 Backend

| 层级 | 选型 | 理由 |
|------|------|------|
| **Export Worker** | `asyncio.create_task` / `BackgroundTasks` | 轻量，无需 Celery |
| **Queue** | `asyncio.Queue` + 内存队列 | 当前规模足够 |
| **Storage** | 本地文件系统 (已有) | 如需扩展→S3/MinIO |
| **EPUB** | `ebooklib` | Python 原生，EPUB2/3 兼容 |
| **DOCX** | `python-docx` (已有) | 成熟稳定 |
| **PDF** | Playwright (已有) | Chromium PDF 引擎 |

#### 11.3 方案对比表

| 需求 | 推荐方案 A | 替代方案 B | 不推荐 |
|------|-----------|-----------|--------|
| **PDF** | Playwright Chromium PDF | Puppeteer (API 几乎相同) | WeasyPrint (无 JS) |
| **EPUB** | ebooklib | - | 手写 XML |
| **Math (Web)** | KaTeX SSR | MathJax | Canvas 截图 |
| **Math (EPUB 降级)** | KaTeX→SVG | MathJax-node→SVG | 图片 |
| **OCR** | PaddleOCR (已有) | Tesseract | - |
| **Layout Parse** | LayoutParser | docTR | - |
| **Queue** | asyncio.Queue | Celery + Redis | - |
| **大文档导出** | 流式生成 + temp 文件 | - | 内存全量 |

---

### 12. Worker 与异步导出架构

#### 12.1 导出任务生命周期

```
用户点击"导出"
      │
      ▼
POST /api/projects/{pid}/documents/{did}/export
      │
      ▼
创建 ExportTask { id, status: "queued", progress: 0 }
      │
      ▼
加入 asyncio.Queue
      │
      ▼
ExportWorker 取任务
      │  status → "processing"
      │  progress 逐步更新 (0→100)
      │
      ├──▶ 小文档 (< 5MB): 同步返回
      │
      └──▶ 大文档: WebSocket 推送 progress
            │  WebSocket msg: { type: "progress", progress: 60 }
            │  WebSocket msg: { type: "done", download_url: "/api/..." }
            ▼
         客户端下载 / 自动触发 download
```

#### 12.2 实现骨架

```python
# backend/app/services/pipeline/export_queue.py
import asyncio
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable
from enum import Enum

class ExportStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"

@dataclass
class ExportTask:
    id: str
    status: ExportStatus
    progress: int
    result: Optional[bytes]
    error: Optional[str]
    format: str  # "pdf" | "epub" | "docx" | "md" | "html"
    project_id: str
    doc_id: str

class ExportQueue:
    def __init__(self, max_workers: int = 2):
        self._queue: asyncio.Queue[ExportTask] = asyncio.Queue()
        self._tasks: dict[str, ExportTask] = {}
        self._workers: list[asyncio.Task] = []
        self._max_workers = max_workers

    async def enqueue(self, task: ExportTask) -> ExportTask:
        self._tasks[task.id] = task
        await self._queue.put(task)
        return task

    def get_task(self, task_id: str) -> Optional[ExportTask]:
        return self._tasks.get(task_id)

    async def start(self, handler: Callable[[ExportTask], Awaitable[bytes]]):
        async def worker():
            while True:
                task = await self._queue.get()
                task.status = ExportStatus.processing
                try:
                    task.result = await handler(task)
                    task.status = ExportStatus.completed
                    task.progress = 100
                except Exception as e:
                    task.status = ExportStatus.failed
                    task.error = str(e)
                finally:
                    self._queue.task_done()

        for _ in range(self._max_workers):
            self._workers.append(asyncio.create_task(worker()))
```

#### 12.3 WebSocket 进度推送

```
Client                           Server
  │                                │
  │──── WS connect ───────────────▶│
  │                                │
  │  ◀── { type: "progress",      │
  │         progress: 30 }         │
  │                                │
  │  ◀── { type: "progress",      │
  │         progress: 80 }         │
  │                                │
  │  ◀── { type: "done",          │
  │         download_url: "/..." } │
  │                                │
```

#### 12.4 临时文件管理

```python
# backend/app/services/pipeline/temp_manager.py
import tempfile, shutil, time
from pathlib import Path

class TempManager:
    def __init__(self, base_dir: Path, ttl_seconds: int = 3600):
        self.base_dir = base_dir
        self.ttl = ttl_seconds
        self.base_dir.mkdir(exist_ok=True)

    def create(self, prefix: str, suffix: str) -> Path:
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=self.base_dir)
        return Path(path)

    async def cleanup(self):
        """删除超过 TTL 的临时文件"""
        now = time.time()
        for f in self.base_dir.glob("*"):
            if now - f.stat().st_mtime > self.ttl:
                try:
                    f.unlink()
                except OSError:
                    pass
```

#### 12.5 缓存策略

```python
CACHE_PREFIX = "export:"
CACHE_TTL = 86400  # 24 小时

# 缓存 key 计算
def cache_key(project_id: str, doc_id: str, format: str, options_hash: str) -> str:
    return f"{CACHE_PREFIX}{project_id}:{doc_id}:{format}:{options_hash}"

# 使用示例
# 如果 24 小时内相同参数导出相同文档，直接返回缓存结果
```

---

### 实现优先级与路线图

| 优先级 | 任务 | 预估影响 |
|:---:|------|------|
| P0 | TypeScript AST 类型定义 (block-schema.ts) ✅ 已完成 | 基础 |
| P0 | Shared BlockRenderer 组件 ✅ 已完成 | 渲染一致性 |
| P0 | Print CSS 系统 ✅ 已完成 | PDF/EPUB 排版 |
| P1 | `DocumentView.tsx` 迁移到 `BlockRenderer` | 消除重复解析逻辑 |
| P1 | EPUB Exporter (ebooklib) | 新格式支持 |
| P1 | Export Queue + Worker | 大文档导出不阻塞 |
| P1 | ✅ **Python 端 SSR KaTeX 渲染** | **WYSIWYG 数学公式导出** |
| P1 | ✅ **统一 Render Pipeline 修复** | **图片+公式全格式一致** |
| P2 | 数学公式 SVG 降级 (EPUB) | Kindle 兼容 |
| P2 | 虚拟滚动 (大文档阅读) | 性能 |
| P2 | CI 截图对比测试 | 防止回归 |

---

## 问题十七：WYSIWYG 导出一致性修复 — Python 端 SSR KaTeX + 全格式统一

### 诊断

**问题一：公式在 PDF/DOCX 中未渲染**

排查发现，Python 后端 `HTMLRenderer` 输出的是原始 LaTeX 标记:

```html
<!-- 旧版 HTMLRenderer 输出 -->
<span class="math-inline">\(E=mc^2\)</span>
<div class="math-block">\[\int x dx\]</div>
```

然后依赖模板中的 `<script src="katex...">` + `renderMathInElement()` **客户端 JS** 来转换。
这对 PDF（Playwright 网络依赖 + 时序不可靠）和 DOCX（根本不支持 JS）是致命的。

**问题二：图片仅在 HTML 格式显示**

PDF 导出中 Playwright 的 `wait_for_timeout(1000)` 不能可靠等待大图/网络图片加载完成。

### 修复

#### 修复 1: Python 端 SSR KaTeX 渲染服务

文件: [katex_service.py](file:///d:/pythontest/translation-platform/backend/app/services/parser/katex_service.py)

```
LaTeX 文本
    │
    ▼
subprocess.run(["node", "-e", require("katex").renderToString(...)])
    │  encoding="utf-8", errors="replace", timeout=15s
    │  cwd=项目根目录, NODE_PATH=frontend/node_modules
    ▼
真实 KaTeX HTML（含 katex-mathml、katex-html 等 class）
```

关键设计：
- 调用项目已有的 `frontend/node_modules/katex` — 与前端 `DocumentView.tsx` 使用**完全相同**的 KaTeX 版本
- `NODE_PATH` 环境变量确保 `require("katex")` 能找到模块
- 失败时 graceful fallback 为 `<pre>` 标签包裹的 LaTeX 源码

#### 修复 2: HTMLRenderer 改为 SSR 模式

文件: [html_renderer.py](file:///d:/pythontest/translation-platform/backend/app/services/parser/html_renderer.py)

已移除所有 `\(...\)` / `\[...\]` 原始 LaTeX 标记生成。
现在直接输出 KaTeX 预渲染的 HTML：

```html
<!-- 新版 HTMLRenderer 输出（SSR 模式） -->
<span class="math-inline"><span class="katex"><span class="katex-mathml">...</span>...</span></span>
<div class="math-block math-display"><span class="katex-display"><span class="katex">...</span></span></div>
```

**效果**：
- HTML 导出：打开即渲染，**不需要**浏览器端 KaTeX JS
- PDF 导出：Playwright 渲染的 HTML 中数学公式已是终态，零 JS 依赖
- EPUB 导出：XHTML 中的数学公式同样是预渲染态

#### 修复 3: 模板移除客户端 KaTeX JS

文件: [template_manager.py](file:///d:/pythontest/translation-platform/backend/app/services/export/template_manager.py)

所有 4 个模板（academic / modern / dark / compact）中:
- ✅ 保留 KaTeX CSS（`katex.min.css` CDN 链接）— 用于样式化已预渲染的 KaTeX HTML
- ❌ 移除 `katex.min.js` — 不再需要
- ❌ 移除 `auto-render.min.js` — 不再需要
- ❌ 移除所有 `renderMathInElement()` 调用 — 不再需要

**同时修复**: 移除了 academic 模板中重复的原文/译文内容块（此前渲染了两遍）。

#### 修复 4: PDF 导出图片预加载

文件: [pdf_exporter.py](file:///d:/pythontest/translation-platform/backend/app/services/export/pdf_exporter.py)

```python
# 旧: 简单等待 1000ms — 不可靠
page.wait_for_timeout(1000)

# 新: 三阶段图片加载保证
page.wait_for_load_state("networkidle", timeout=30000)   # 等待所有网络请求完成
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # 触发懒加载
page.wait_for_timeout(500)                                # 渲染缓冲
page.evaluate("window.scrollTo(0, 0)")                   # 回滚到顶部
```

#### 修复 5: DOCX 增加图像块支持

文件: [docx_renderer.py](file:///d:/pythontest/translation-platform/backend/app/services/parser/docx_renderer.py)

新增 `BlockType.image` 处理分支，将独立的图片块插入 DOCX。

### 验证结果

**24/24 测试通过**，覆盖：

| 测试组 | 项数 | 验证内容 |
|--------|:---:|---------|
| SSR KaTeX Service | 5 | `katex-mathml` 存在、`katex-display` 存在、无残留 `$` 标记 |
| HTML Renderer (SSR模式) | 12 | 所有 Block 类型正确、公式预渲染、无客户端依赖 |
| DOCX Export | 1 | 含数学公式的文档可正常导出 |
| Markdown Round-trip | 3 | 数学公式完整保留、二次渲染稳定 |
| Exporter Imports | 1 | 所有导出器可正常导入 |
| HTML (无SSR回退) | 2 | 回退模式正确输出 LaTeX 标记 |

### WYSIWYG 一致性矩阵

| 格式 | 数学公式 | 图片 | 渲染引擎 |
|------|:---:|:---:|------|
| **Web Reader** | KaTeX SSR (React) | `<img>` + base64 | `DocumentView.tsx` |
| **HTML Export** | KaTeX SSR (Python Node) ✅ | `<img>` + base64 ✅ | `HTMLRenderer(ssr_math=True)` |
| **PDF Export** | 预渲染 KaTeX HTML → Chromium ✅ | Playwright networkidle ✅ | Playwright + SSR HTML |
| **DOCX Export** | KaTeX HTML 内联 + 回退标记 | `add_picture()` ✅ | `DocxRenderer` |
| **Markdown Export** | 原始 `$...$` 保留 ✅ | Base64 data URI | `MarkdownRenderer` |
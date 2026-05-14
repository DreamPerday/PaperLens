# 开发问题总结 — AI 论文翻译平台

本文档记录了在开发这个项目过程中遇到的主要技术难题和解决方案，供其他 AI 编码助手或开发者参考。

---

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

## 问题十六：WYSIWYG 导出一致性修复 — Python 端 SSR KaTeX + 全格式统一

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

## 问题二十：Token 统计细分 — 缓存命中/未命中 + DeepSeek 价格计算

### 背景

原有 Token 统计只有一个笼统的 `tokens_used` 字段，无法区分输入/输出 token，也无法区分缓存命中/未命中。用户需要精细化的成本控制和费用预估。

### 需求

1. Token 分类：缓存命中输入、缓存未命中输入、输出、总 Token
2. DeepSeek V4 Flash 价格：
   - 输入（缓存命中）：¥0.02 / 百万 tokens
   - 输入（缓存未命中）：¥1.00 / 百万 tokens  
   - 输出：¥2.00 / 百万 tokens
3. 前端显示总价

### 解决方案

#### 后端改动

**1. `translator.py`_translate_single_chunk** — 从 DeepSeek API `usage` 对象提取细分字段：

```python
usage = result.get("usage", {})
prompt_tokens = usage.get("prompt_tokens", 0)
completion_tokens = usage.get("completion_tokens", 0)
cached_tokens = (
    usage.get("prompt_tokens_details", {})
    .get("cached_tokens", 0)
)
```

**2. `translator.py`translate_document_async** — 汇总细分 token：
```python
total_prompt_tokens = sum(r.get("prompt_tokens", 0) for r in results)
total_completion_tokens = sum(r.get("completion_tokens", 0) for r in results)
total_cached_tokens = sum(r.get("cached_tokens", 0) for r in results)
```

**3. `storage.py`save_translation** — 存储细分字段 + 项目级汇总：
```python
self.update_project(project_id, {
    "total_tokens": ...,
    "total_prompt_tokens": ...,
    "total_completion_tokens": ...,
    "total_cached_tokens": ...,
})
```

**4. `services/pricing.py`（新增）** — 价格计算引擎：
- `PRICING` 字典：模型 → 三类单价
- `calculate_cost(prompt_tokens, completion_tokens, cached_tokens, model)` 
- 计算公式：`cached/1M*0.02 + (prompt-cached)/1M*1 + completion/1M*2`

**5. API 端点返回细分**：
- `/api/stats`：增加 `prompt_tokens`、`completion_tokens`、`cached_tokens`、`cost`
- `/api/projects/token-stats`：增加同上字段 + 各项目 `cost`

#### 前端改动

**1. `types/index.ts`** — `TokenUsage` 接口：
```typescript
interface TokenUsage {
  inputCacheHit: number    // 缓存命中
  inputCacheMiss: number   // 缓存未命中
  output: number           // 输出
  total: number            // 总计
  cost: number             // 价格 (CNY)
}
```

**2. `store/index.ts`** — `refreshApiStats` 解析新字段：
- 从 API 读取 `prompt_tokens`、`completion_tokens`、`cached_tokens`
- `inputCacheMiss = prompt_tokens - cached_tokens`
- 价格直接从 API `cost` 字段获取（后端计算）

**3. `StatusBar.tsx`** — 底部状态栏同时显示 Token 总数 + 总价：
```
Tokens: 1.5M  |  ¥3.50
```

**4. `TokenStats.tsx`** — API 消耗统计面板新增四个卡片：
- 输入（未命中）：带 `¥1/百万 tokens` 标注
- 输入（缓存命中）：绿色高亮，`¥0.02/百万 tokens`
- 输出 Tokens：`¥2/百万 tokens`
- 总花费：accent 色高亮

**5. `utils.ts`** — `formatCost` 改为 ¥ 符号：`¥{cost.toFixed(4)}`

### 关键经验

- **后端计算价格**，前端只负责展示。避免前端维护定价逻辑，保证价格计算一致性。
- **DeepSeek API 的 `prompt_tokens_details.cached_tokens` 仅在缓存命中时返回**，默认值为 0。缓存未命中输入 = `prompt_tokens - cached_tokens`。
- `save_token_history` 使用默认参数值（`=0`），兼容已有不带这些字段的历史记录，向后兼容。

---

## 问题二十一：翻译进度条卡死 0% — 防卡死与鲁棒性增强

### 背景

用户反馈翻译过程中进度条一直停在 0%，实际翻译已完成大部分，但部分数据缺失。更严重的是：因为 `translatingFileId` 未释放，用户无法点"重新翻译"来重试。

### 根因分析（多个并发问题）

**Bug 1 — 后端后处理异常未被捕获**

`projects.py` 中 `_translate_task` 执行翻译后处理（保存结果、发 WebSocket done、记录 token history）时没有 try/except。如果 `save_translation` 或 `save_token_history` 中任何一步抛出异常（如文件写入失败、JSON 序列化错误），`job["status"]` 就永远卡在 `"translating"`，前端轮询永远返回 `progress: 0`。

**Bug 2 — 前端不允许重新翻译**

`store/index.ts` 中 `startTranslation` 有一个守卫：

```typescript
if (state.translatingFileId) {
  console.warn(`Translation already in progress...`)
  return  // ← 直接拒绝，无逃生路径
}
```

进度条卡死后 `translatingFileId` 永远不会被清除，导致用户完全无法重新翻译。

**Bug 3 — 前端 polling catch 无日志**

三个 `catch {}` 空块静默吞掉所有错误，导致即使 polling 本身出错（网络错误、跨域、状态码异常），开发者完全无法感知。

**Bug 4 — 无卡死检测（watchdog）**

如果 WebSocket 挂了但前端没有感知，或者后端 chunk 推送停止了，前端没有任何超时检测机制，只能永远等待。

### 解决方案

#### 修复 1：后端 try/except 包裹所有后处理逻辑

`projects.py:236-291`：

```python
try:
    if result["success"] or ...:
        job["status"] = "completed"
        storage_service.save_translation(...)
        storage_service.update_document(...)
        save_token_history(...)
        # WebSocket "done" 消息...
    else:
        job["status"] = "failed"
except Exception as e:
    logger.error(f"翻译后处理异常: job={job_id}, error={e}", exc_info=True)
    job["status"] = "failed"
    job["error"] = f"后处理异常: {str(e)}"
    job["result"] = {"text": result.get("text", ""), ...}
    storage_service.update_document(project_id, doc_id, {"status": "failed"})
```

关键：**即使后处理失败，job 状态也必须设置为 "failed"**，让前端轮询感知到并释放 `translatingFileId`。

#### 修复 2：前端允许强制重新翻译

将 `startTranslation` 中的守卫从"直接拒绝"改为"清理旧状态 + 继续"：

```typescript
if (state.translatingFileId) {
  console.warn(`Force restarting: was=${state.translatingFileId}, new=${docId}`)
  get().setTranslatingFileId(null)   // ← 释放锁
  set(s => ({ translationResult: { ...s.translationResult, status: "error", progress: 0 } }))
}
```

#### 修复 3：所有 catch 块添加 console.error

```typescript
// 之前：
} catch {}

// 之后：
} catch (e) {
  console.error("[STORE] translation poll error:", e)
}
```

#### 修复 4：Watchdog 30 秒卡死检测

```typescript
let lastProgressTime = Date.now()
let usePolling = false

// 每次收到 progress 更新时刷新
lastProgressTime = Date.now()

// 每 5 秒检查一次
const watchdogInterval = setInterval(() => {
  if (done) { clearInterval(watchdogInterval); return }
  const stallDuration = Date.now() - lastProgressTime
  if (stallDuration > 30_000) {
    if (!usePolling && ws) {
      // WS 层卡死 → 关闭 WS 切换为 polling
      ws.close()
      startPolling()
    } else {
      // polling 也卡死了 → 标记失败，释放锁
      finishWith(partialContent, 0, "error")
    }
  }
}, 5_000)
```

**两阶段降级**：
1. WebSocket 卡死 → 自动切换 HTTP polling
2. HTTP polling 也卡死 → 标记翻译失败，释放 `translatingFileId`

### 其他 AI 可参考的经验

- **任何长耗时异步任务，必须保证最终状态一致**。无论成功/失败/后处理异常，job 的 `status` 必须从 `"translating"` 转移为 `"completed"` 或 `"failed"`。用 `try/except` 包裹整个后处理逻辑是必须的。
- **前端进度追踪的"锁"必须有逃生路径**。如果 `translatingFileId` 不允许覆盖，一旦卡死用户就完全无解。要么提供"取消翻译"按钮，要么允许强制重新翻译。
- **空 catch 是调试噩梦**。polling 和 WebSocket 的 catch 块至少应包含 `console.error`，最好还能上报到监控系统。
- **Watchdog 是 WebSocket 类应用的标配**。WebSocket 的 `onclose` 不一定能捕获所有断连场景（如代理超时、防火墙静默切断），watchdog 作为兜底机制确保不会永久等待。

---
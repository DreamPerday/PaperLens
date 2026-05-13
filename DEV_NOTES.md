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

## 常见 Bug 检查清单

在提交代码前，检查以下常见问题：

1. **进度条**：确保使用动态值 `{progress}%` 而非硬编码
2. **路由顺序**：非参数路由必须在参数化路由之前
3. **API 调用**：检查参数是否与函数签名匹配
4. **Token 统计**：确保显示的是正确的统计字段
5. **存储格式**：确保存储的是字符串而非对象
6. **环境变量**：避免硬编码端口和 URL
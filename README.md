# AI 论文翻译平台 (PaperLens)

学术论文翻译与在线阅读平台，支持 PDF/DOCX 文档解析、AI 翻译、双栏对照阅读、多格式导出。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Next.js 14 (App Router) + TypeScript |
| 样式方案 | Tailwind CSS + 自定义 Design Token |
| 状态管理 | Zustand (WebSocket + HTTP 轮询双通道) |
| 数学渲染 | KaTeX (Python 服务端预渲染) |
| 图标库 | Lucide React |
| 后端框架 | FastAPI + Uvicorn |
| PDF 解析 | 外部 Layout Parsing API |
| DOCX 解析 | python-docx |
| AI 翻译 | DeepSeek API (deepseek-v4-flash) |
| 实时推送 | WebSocket + HTTP 轮询双通道 |
| PDF 导出 | Playwright (Chromium 无头浏览器) |
| 存储 | 本地 JSON 文件存储 |

## 项目结构

```
translation-platform/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 入口 + /api/stats
│   │   ├── config.py                  # 配置管理 (Pydantic Settings)
│   │   ├── models/
│   │   │   ├── block_schema.py        # 文档 AST 类型定义 (24 Block + 10 Inline)
│   │   │   └── schemas.py             # API 数据模型
│   │   ├── routes/projects.py         # API 路由 (项目/文档/翻译/导出/搜索/统计)
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── storage.py             # 存储服务 (JSON 文件数据库 + 项目/文档 CRUD)
│   │       ├── translator.py          # 翻译服务 (DeepSeek API + 异步并发)
│   │       ├── pricing.py             # 价格计算引擎 (缓存命中/未命中/输出)
│   │       ├── parser/                # AST 解析器 + 渲染器
│   │       │   ├── __init__.py
│   │       │   ├── markdown_parser.py # 文本 → AST (行驱动 Markdown 解析)
│   │       │   ├── ast_renderer.py    # AST → Markdown (无损 round-trip)
│   │       │   ├── html_renderer.py   # AST → HTML5 (含 SSR KaTeX)
│   │       │   ├── docx_renderer.py   # AST → python-docx
│   │       │   └── katex_service.py   # Subprocess Node.js KaTeX 渲染
│   │       └── export/                # 导出器
│   │           ├── __init__.py
│   │           ├── html_exporter.py   # 导出 HTML 文件
│   │           ├── markdown_exporter.py # 导出 Markdown 文件
│   │           ├── pdf_exporter.py    # 导出 PDF (Playwright)
│   │           ├── docx_exporter.py   # 导出 DOCX 文件
│   │           └── template_manager.py # HTML 导出模板管理 (4 种主题)
│   ├── storage/                       # 运行时数据
│   │   ├── projects.json              # 项目索引
│   │   ├── projects/<id>/             # 每个项目的文档/翻译数据
│   │   ├── uploads/                   # 上传的源文件
│   │   ├── static/images/             # 文档提取的图片
│   │   └── token_history/             # Token 使用历史记录
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # 主页面
│   │   │   ├── layout.tsx             # 根布局 (KaTeX CSS, 主题)
│   │   │   └── globals.css            # 全局样式 + Design Token
│   │   ├── ast/                       # AST 共享组件 (TS 侧)
│   │   │   ├── block-schema.ts        # AST 类型定义 (镜像 Python)
│   │   │   ├── block-renderer.tsx     # 共享 BlockRenderer (reader/print/export)
│   │   │   ├── print.css              # Print CSS (50+ Design Token)
│   │   │   └── index.ts               # Barrel export
│   │   ├── components/
│   │   │   ├── layout/                # Navbar, Sidebar, StatusBar
│   │   │   ├── reader/                # DualPaneReader, DocumentView, TOC, MathRenderer
│   │   │   ├── translation/           # TokenUsageDialog, TokenStats, BatchDialog, SearchDialog, CleanupDialog
│   │   │   ├── ui/                    # Button, Card, Dialog, Badge, Progress, Tooltip
│   │   │   ├── upload/                # FileUpload
│   │   │   └── settings/              # SettingsPanel
│   │   ├── hooks/                     # useTheme, useSyncScroll, useKeyboard
│   │   ├── lib/                       # api.ts, utils.ts
│   │   ├── store/index.ts             # Zustand 全局状态 (WebSocket + HTTP 轮询)
│   │   └── types/index.ts             # TypeScript 类型定义
│   ├── .env.local                     # 前端环境变量
│   ├── next.config.js                 # Next.js 配置 (API 代理)
│   └── package.json
```

## 核心功能

### 1. 文档管理
- 项目管理：创建、重命名、删除
- 文件上传：支持 PDF、DOCX、Markdown、LaTeX、TXT
- 文件操作：重命名、删除 (含右键菜单)
- 废弃文件清理：检测并删除未被引用的孤立文件

### 2. 文档解析与渲染
- **PDF**：通过外部 Layout Parsing API 提取为 Markdown + 图片
- **DOCX**：通过 python-docx 提取文本和图片
- **文档 AST 架构**：统一 Block Schema 中间层 (24 种 Block 类型、10 种 Inline 类型)
- **数学公式**：支持行内 `$...$` 和块级 `$$...$$`、`\begin{}...\end{}` 等多种 LaTeX 定界符
- **KaTeX 服务端预渲染**：Python subprocess → Node.js KaTeX，纯 HTML 输出，零客户端 JS
- **前端渲染**：`dangerouslySetInnerHTML` + KaTeX 预渲染 HTML，30 万+字符流畅渲染
- **双栏对照阅读**：原文 | 译文，支持同步/独立滚动、TOC 导航

### 3. AI 翻译
- **DeepSeek API**：`deepseek-v4-flash` 模型，段落级翻译
- **智能分块**：普通文本 3500-4500 字符，数学密集 2000-3000 字符
- **块感知分裂**：自动识别 HTML 表格/代码块/LaTeX 环境/公式为原子块，绝不截断
- **格式保护**：双层占位符保护 LaTeX 公式 (`[FORMULA_N]`) 和 Markdown 标记 (`[MDC_N]`)
- **完整性校验**：翻译后自动对比长度/段落/公式/标记数量，缺失告警
- **异步并发**：`asyncio` + `httpx.AsyncClient` + `Semaphore(10)` 并发调用
- **实时进度**：WebSocket 推送 + HTTP 轮询双通道，支持 Watchdog 卡死检测
- **自动重试**：失败自动重试 + 重新翻译锁释放
- **参考文献跳过**：自动检测 References/Bibliography 部分并跳过
- **翻译缓存**：刷新页面自动加载，不丢失结果

### 4. 导出功能
- **格式**：HTML、PDF (Playwright)、Markdown、DOCX
- **模板**：4 种主题 (academic / modern / dark / compact)
- **数学公式**：所有格式均通过 KaTeX 服务端预渲染，PDF/HTML/DOCX 一致
- **图片嵌入**：自动 Base64 嵌入，离线可用
- **PDF 增强**：三阶段图片加载、封面页、水印、目录生成
- **DOCX 增强**：图片支持、公式斜体居中、列表/引用行内格式化

### 5. Token 用量统计与定价
- **细分字段**：缓存命中输入、缓存未命中输入、输出 Token、总 Token
- **价格计算**：DeepSeek V4 Flash 定价 (¥0.02/百万 缓存命中、¥1.00/百万 缓存未命中、¥2.00/百万 输出)
- **统计视图**：4 卡片面板 (输入未命中/缓存命中/输出/总花费) + 时间范围筛选
- **历史追踪**：全部/今日/7天/30天 维度，按项目明细 + 每日历史记录
- **状态栏**：实时显示总 Token 和总费用

### 6. 搜索
- 全文档内容搜索
- 结果含上下文摘要
- 点击跳转到对应项目/文档

## 启动方式

### 后端
```bash
cd backend
pip install -r requirements.txt
# 配置 DeepSeek API Key
cp .env.example .env  # 编辑 DEEPSEEK_API_KEY
# 启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端
```bash
cd frontend
npm install
# 配置后端端口 (可选，默认 8000)
echo "NEXT_PUBLIC_API_PORT=8000" > .env.local
# 启动
npm run dev  # http://localhost:3000
```

### 环境变量

**后端** (`backend/.env`)：
```env
DEEPSEEK_API_KEY=your-api-key-here
DEEPSEEK_MODEL=deepseek-v4-flash
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
STORAGE_PATH=./storage
```

**前端** (`frontend/.env.local`)：
```env
NEXT_PUBLIC_API_PORT=8000
```

### API 代理
前端 `next.config.js` 配置了 `/api/*` → `http://localhost:8000` 的 rewrite，开发时直接访问 `localhost:3000` 即可。

## API 接口总览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects` | 项目列表 |
| POST | `/api/projects` | 创建项目 |
| GET/PUT/DELETE | `/api/projects/{id}` | 项目 CRUD |
| GET | `/api/projects/{id}/documents` | 文档列表 |
| POST | `/api/projects/{id}/documents/upload` | 上传文档 |
| PUT/DELETE | `/api/projects/{id}/documents/{doc_id}` | 文档更新/删除 |
| GET | `/api/projects/{id}/documents/{doc_id}/content` | 文档内容 (含翻译缓存) |
| POST | `/api/projects/{id}/documents/{doc_id}/translate` | 启动翻译 (异步) |
| POST | `/api/projects/{id}/documents/{doc_id}/export` | 导出 |
| GET | `/api/projects/search?q=...` | 全平台搜索 |
| GET | `/api/projects/storage/orphans` | 孤立文件列表 |
| DELETE | `/api/projects/storage/orphans` | 清理孤立文件 |
| GET | `/api/projects/token-stats` | Token 统计 (按项目 + 含价格) |
| GET | `/api/projects/token-history?days=30` | Token 使用历史 |
| GET | `/api/stats` | 平台总统计 (含价格) |
| GET | `/health` | 健康检查 |
| WS | `/api/projects/{id}/documents/{doc_id}/translate/ws` | 翻译进度 WebSocket |

## Design Token

CSS 自定义属性实现 Design Token，支持亮色/暗色一键切换：

```css
--background, --foreground       /* 主背景/前景色 */
--surface, --surface-100 ~ -900  /* 表面层级色 */
--accent, --accent-100 ~ -900    /* 主色调 (紫蓝) */
```

通过 Tailwind `@apply` 引用为 `text-surface-600`、`bg-accent-500` 等。

## 开发笔记

详细的开发问题记录和解决方案参见 [DEV_NOTES.md](./DEV_NOTES.md)，涵盖：

- 前端文档渲染性能优化 (React → dangerouslySetInnerHTML)
- TOC 导航滚动问题修复
- DeepSeek API 翻译失败排查 (system prompt 过大、chunk 过大)
- WYSIWYG 导出一致性修复 (SSR KaTeX + 全格式统一)
- 翻译进度条卡死防护 (Watchdog + try/except + 强制重翻译)
- Token 统计细分与定价
- 智能分块与完整性校验
- 等等 21 个已解决问题

## 注意事项

1. **DeepSeek API Key**：需要在 `.env` 中配置有效的 API Key，DeepSeek 模型名为 `deepseek-v4-flash`
2. **存储路径**：后端运行时会自动创建 `storage/` 目录
3. **PDF 导出**：需要安装 Playwright Chromium (`playwright install chromium`)
4. **KaTeX SSR**：依赖 `frontend/node_modules/katex`，运行前端 `npm install` 后自动安装
5. **端口配置**：前端通过 `NEXT_PUBLIC_API_PORT` 配置后端端口
6. **CORS**：后端已配置 CORS，允许前端跨域访问
7. **FFmpeg** (可选)：视频/音频处理需要配置 FFmpeg 路径
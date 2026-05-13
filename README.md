# AI 论文翻译平台 (PaperLens)

学术论文翻译与在线阅读平台，支持 PDF/DOCX 文档解析、AI 翻译、双栏对照阅读。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Next.js 14 (App Router) + TypeScript |
| 样式方案 | Tailwind CSS + 自定义 Design Token |
| 状态管理 | Zustand |
| 数学渲染 | KaTeX (服务端预渲染) |
| 图标库 | Lucide React |
| 后端框架 | FastAPI + Uvicorn |
| PDF 解析 | 外部 Layout Parsing API |
| DOCX 解析 | python-docx |
| AI 翻译 | DeepSeek API (OpenAI 兼容) |
| 实时推送 | WebSocket |
| 存储 | 本地 JSON 文件存储 |

## 项目结构

```
translation-platform/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理 (Pydantic Settings)
│   │   ├── models/schemas.py    # 数据模型
│   │   ├── routes/projects.py   # API 路由 (项目/文档/翻译/导出/搜索/清理/统计)
│   │   ├── services/
│   │   │   ├── storage.py       # 存储服务 (JSON 文件数据库)
│   │   │   └── translator.py    # 翻译服务 (DeepSeek API + 异步并发)
│   │   └── utils/parser.py      # 文档解析器 (PDF/DOCX)
│   ├── storage/                 # 运行时数据
│   │   ├── projects.json        # 项目索引
│   │   ├── projects/<id>/       # 每个项目的文档/翻译数据
│   │   ├── uploads/             # 上传的源文件
│   │   ├── static/images/       # 文档图片
│   │   └── token_history/       # Token 使用历史记录
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # 主页面
│   │   │   ├── layout.tsx       # 根布局 (KaTeX CSS, 主题)
│   │   │   └── globals.css      # 全局样式 + Design Token
│   │   ├── components/
│   │   │   ├── layout/          # Navbar, Sidebar, StatusBar
│   │   │   ├── reader/          # DualPaneReader, DocumentView, TOC, MathRenderer
│   │   │   ├── translation/     # GlossaryDialog, TokenStats, BatchDialog, SearchDialog, CleanupDialog, TokenUsageDialog
│   │   │   ├── ui/              # Button, Card, Dialog, Badge, Progress, Tooltip
│   │   │   ├── upload/          # FileUpload
│   │   │   └── settings/        # SettingsPanel
│   │   ├── hooks/               # useTheme, useSyncScroll, useKeyboard
│   │   ├── lib/                 # api.ts, utils.ts
│   │   ├── store/index.ts       # Zustand 全局状态 (WebSocket + 轮询)
│   │   └── types/index.ts       # TypeScript 类型定义
│   ├── .env.local               # 环境变量配置
│   ├── next.config.js           # Next.js 配置
│   └── package.json
```

## 核心功能

### 1. 文档管理
- 项目管理：创建、重命名、删除项目
- 文件上传：支持 PDF、DOCX、Markdown、LaTeX、TXT
- 文件操作：重命名、删除 (含右键菜单)
- 废弃文件清理：检测并删除未被引用的孤立文件

### 2. 文档解析与渲染
- **PDF**：通过外部 Layout Parsing API 提取为 Markdown + 图片
- **DOCX**：通过 python-docx 提取文本和图片
- 支持数学公式 (行内 `$...$` 和块级 `$$...$$`)、表格、图片
- KaTeX 服务端预渲染，前端 `dangerouslySetInnerHTML` 直出

### 3. AI 翻译
- 基于 DeepSeek API 的段落级翻译（`deepseek-v4-flash` 模型）
- 术语对照表 (50+ 常用学术术语)
- 智能分块翻译（普通文本 3500-4500 字符，数学密集 2000-3000 字符）
- **异步并发**：`asyncio` + `httpx.AsyncClient` + `Semaphore(10)` 并发调用
- **实时进度**：WebSocket 推送翻译进度，支持增量渲染
- **流式输出**：Chunk 级流式处理，边翻译边显示
- **自动重试**：失败自动重试机制
- **公式保护**：`[FORMULA_N]` 占位符保护数学公式不被翻译
- **参考文献跳过**：自动检测 References/Bibliography 部分并跳过
- 翻译结果缓存（刷新页面自动加载）

### 4. 阅读体验
- 双栏对照 (原文 | 译文)
- 同步/独立滚动
- 目录导航 (TOC)
- 字号调节 (12-28px)
- 全屏模式
- 深色/浅色主题

### 5. 导出功能
- 支持 HTML、PDF (HTML 模板)、Markdown 格式
- 图片自动嵌入为 Base64 (无需网络依赖)

### 6. 搜索功能
- 全文档内容搜索
- 结果含上下文摘要
- 点击直接跳转到对应项目/文档

### 7. Token 用量统计
- 按项目统计 Token 消耗
- 可视化进度条
- 总量/平均数/请求次数
- 历史记录追踪

## 启动方式

### 后端
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 配置 DeepSeek API Key
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端
```bash
cd frontend
npm install
npm run dev  # Next.js 默认 http://localhost:3000
```

### 环境变量配置

**前端** (`frontend/.env.local`)：
```env
NEXT_PUBLIC_API_PORT=8000
```

**后端** (`backend/.env`)：
```env
DEEPSEEK_API_KEY=your-api-key-here
DEEPSEEK_MODEL=deepseek-v4-flash
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
STORAGE_PATH=./storage
```

### API 代理
前端 `next.config.js` 配置了 `/api/*` -> `http://localhost:8000` 的 rewrite，开发时直接访问 `localhost:3000` 即可。

## API 接口总览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects` | 项目列表 |
| POST | `/api/projects` | 创建项目 |
| GET/PUT/DELETE | `/api/projects/{id}` | 项目 CRUD |
| GET | `/api/projects/{id}/documents` | 文档列表 |
| POST | `/api/projects/{id}/documents/upload` | 上传文档 |
| PUT/DELETE | `/api/projects/{id}/documents/{doc_id}` | 文档更新/删除 |
| GET | `/api/projects/{id}/documents/{doc_id}/content` | 文档内容（含翻译缓存） |
| POST | `/api/projects/{id}/documents/{doc_id}/translate` | 启动翻译（异步） |
| POST | `/api/projects/{id}/documents/{doc_id}/export` | 导出 |
| GET | `/api/projects/search?q=...` | 搜索 |
| GET | `/api/projects/storage/orphans` | 孤立文件列表 |
| DELETE | `/api/projects/storage/orphans` | 清理孤立文件 |
| GET | `/api/projects/token-stats` | Token 统计（按项目） |
| GET | `/api/projects/token-history?days=30` | Token 使用历史 |
| GET | `/api/stats` | 平台统计 |
| GET | `/health` | 健康检查 |
| WS | `/api/projects/{id}/documents/{doc_id}/translate/ws` | 翻译进度 WebSocket |

## Design Token

项目使用 CSS 自定义属性实现 Design Token，支持亮色/暗色一键切换：

```css
--background, --foreground       /* 主背景/前景色 */
--surface, --surface-100 ~ -900  /* 表面层级色 */
--accent, --accent-100 ~ -900    /* 主色调 (紫蓝) */
```

通过 Tailwind `@apply` 引用为 `text-surface-600`、`bg-accent-500`、`border-surface-200/50` 等。

## 性能优化亮点

1. **文档渲染**：`dangerouslySetInnerHTML` + KaTeX 预渲染，支持 30 万+字符文档流畅渲染
2. **异步翻译**：10 并发 API 调用，大幅提升翻译速度
3. **流式输出**：WebSocket 实时推送，边翻译边显示
4. **增量渲染**：Chunk 级内容组装，避免全量重渲染
5. **内存优化**：智能分块策略，数学密集内容采用更小块

## 注意事项

1. **DeepSeek API Key**：需要在 `.env` 中配置有效的 API Key
2. **存储路径**：后端运行时会自动创建 `storage/` 目录
3. **端口配置**：前端通过 `NEXT_PUBLIC_API_PORT` 环境变量配置后端端口
4. **CORS**：后端已配置 CORS，允许前端跨域访问
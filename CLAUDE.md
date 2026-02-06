# Synapse (InsightSentinel) 项目规范

## 项目简介
**Synapse** (神经突触) 是一个 7x24 小时运行的自主 AI 情报 Agent，专注于 GCR（大中华区）AI 市场情报分析。

## 文档结构规范

```
Synapse/
├── CLAUDE.md           # 本文件 - 项目规范和 Claude 使用指南
├── plan/               # 实现计划文档
│   └── current-plan.md # 当前实施计划
├── PRD/                # 产品需求文档
│   └── PRD.md          # 主 PRD 文档（包含变更历史）
├── architecture/       # 技术架构文档
│   ├── overview.md     # 架构总览
│   ├── backend.md      # 后端架构详细设计
│   ├── database.md     # 数据库 Schema 设计
│   ├── agent.md        # Agent 核心设计
│   └── crawler.md      # 爬虫系统设计
├── stitch/             # UI 原型设计 (Google Stitch 生成)
└── insightsentinel/    # 前端 React 应用
```

## 技术栈

### 前端 (已实现)
- React 19 + TypeScript
- Vite 6.2
- Tailwind CSS
- Google Gemini API

### 后端 (已实现)
- Python 3.11+ (使用 **uv** 管理环境和依赖)
- FastAPI
- PostgreSQL + pgvector (向量数据库)
- Redis (缓存/队列)
- LLM: Claude Opus 4.5 (通过 Agent Maestro 免费使用) / Gemini

### LLM 集成
- **Agent Maestro**: VS Code 扩展，通过 GitHub Copilot 订阅免费使用 Claude API
- 默认使用 `claude-opus-4.5` 模型
- 可通过 `LLM_PROVIDER` 环境变量切换到 Gemini

## Claude 使用规范

### 计划文件
- 计划文件存放在 `/Users/zhaochaoqun/Github/Synapse/plan/` 目录
- 每次更新计划时，同步更新到此目录
- Claude 内部计划文件路径: `/Users/zhaochaoqun/.claude/plans/`

### PRD 文档
- PRD 文档存放在 `/Users/zhaochaoqun/Github/Synapse/PRD/` 目录
- 主文档: `PRD/PRD.md`
- 变更历史通过 git 追踪，同时在文档内部保留重大变更记录

### 架构文档
- 架构文档存放在 `/Users/zhaochaoqun/Github/Synapse/architecture/` 目录
- 按模块拆分为多个文件，便于维护和查阅

## 核心功能

1. **Agentic Loop 多步推理** - Agent 自主完成 3-5 步任务
2. **GCR 平台真实数据** - 微信/知乎/小红书/抖音数据抓取
3. **错误自愈能力** - API 失败时自主调整策略
4. **长效记忆系统** - Vector DB + 关系型数据库，支持跨时间洞察

## 开发命令

```bash
# 前端开发
cd insightsentinel
npm install
npm run dev

# 后端开发 (使用 uv)
cd backend
uv sync                        # 安装依赖
uv run uvicorn app.main:app --reload  # 启动服务

# 或者使用 uv run 直接运行
uv run python -m uvicorn app.main:app --reload
```

## 环境配置

后端配置文件: `backend/.env`

```bash
# LLM Provider: "anthropic" (默认，通过 Agent Maestro) 或 "gemini"
LLM_PROVIDER=anthropic

# Agent Maestro (需要 VS Code + Agent Maestro 扩展运行)
AGENT_MAESTRO_URL=http://localhost:23333/api/anthropic
CLAUDE_MODEL_LIGHT=claude-opus-4.5
CLAUDE_MODEL_HEAVY=claude-opus-4.5

# Gemini (可选，仅当 LLM_PROVIDER=gemini 时需要)
GEMINI_API_KEY=your_key
```

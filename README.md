# Synapse (InsightSentinel)

神经突触 —— 寓意连接全网信息

一个 7x24 小时运行的自主 AI 情报 Agent，专注于 GCR（大中华区）AI 市场情报分析。

## 功能特点

- **Agentic Loop 多步推理** - Agent 自主完成 3-5 步任务
- **GCR 平台数据** - 微信/知乎/小红书/抖音数据抓取
- **错误自愈** - API 失败时自主调整策略
- **长效记忆** - Vector DB + 关系型数据库，支持跨时间洞察

## 技术栈

### 前端
- React 19 + TypeScript
- Vite + Tailwind CSS
- Google Gemini API

### 后端 (开发中)
- Python + FastAPI
- PostgreSQL + pgvector
- Redis

## 项目结构

```
Synapse/
├── CLAUDE.md           # 项目规范
├── plan/               # 实施计划
├── PRD/                # 产品需求文档
├── architecture/       # 技术架构文档
├── stitch/             # UI 原型 (Google Stitch)
├── insightsentinel/    # 前端 React 应用
└── backend/            # 后端 FastAPI 服务 (开发中)
```

## 快速开始

### 前端开发

```bash
cd insightsentinel
npm install
npm run dev
```

### 后端开发 (待实现)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 文档

- [PRD](./PRD/PRD.md) - 产品需求文档
- [架构总览](./architecture/overview.md) - 系统架构设计
- [实施计划](./plan/current-plan.md) - 开发计划

## License

MIT

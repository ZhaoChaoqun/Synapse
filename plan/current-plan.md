# InsightSentinel 实施计划

## 文档信息
- **版本**: v1.0
- **创建日期**: 2026-02-06
- **状态**: 待批准

---

## 1. 项目当前状态

### 已完成
- ✅ 前端 React 应用 (insightsentinel/)
  - 6 个功能组件 (Header, CommandBar, LogPanel, StatsGrid, NetworkMap)
  - Google Gemini API 集成 (geminiService.ts)
  - 843 行 TypeScript 代码
- ✅ UI 原型设计 (stitch/)
  - Mission Control Dashboard
  - Deep Dive Investigation View
  - Cross-Platform Insight Gallery
- ✅ 项目文档
  - CLAUDE.md - 项目规范
  - PRD/PRD.md - 产品需求文档
  - architecture/ - 技术架构文档

### 待实现
- ❌ 后端 FastAPI 服务
- ❌ Agentic Loop 核心
- ❌ GCR 平台爬虫
- ❌ 记忆系统
- ❌ 前后端集成

---

## 2. 实施阶段

### 阶段 1: 基础架构 (2-3 天)

**目标**: 搭建后端项目骨架

**任务清单**:
- [ ] 创建 FastAPI 项目结构
- [ ] 配置 PostgreSQL + pgvector
- [ ] 配置 Redis
- [ ] 实现基础 API 端点 (health, CORS)
- [ ] 集成 Gemini API
- [ ] 编写 Alembic 数据库迁移

**关键文件**:
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/models/base.py`

**验证方式**:
```bash
# 启动服务
uvicorn app.main:app --reload

# 测试健康检查
curl http://localhost:8000/health
```

---

### 阶段 2: Agent 核心 (3-4 天)

**目标**: 实现 Agentic Loop

**任务清单**:
- [ ] 实现 AgentState 状态管理
- [ ] 实现 Planner (任务分解)
- [ ] 实现 Executor (任务执行)
- [ ] 实现 Tool 基类与注册表
- [ ] 实现 SSE 流式响应
- [ ] 实现 LLM Router (轻量/重量模型路由)

**关键文件**:
- `backend/app/core/agent/orchestrator.py`
- `backend/app/core/agent/planner.py`
- `backend/app/core/agent/executor.py`
- `backend/app/core/tools/base.py`
- `backend/app/api/v1/endpoints/agent.py`

**验证方式**:
```bash
# 测试 Agent 执行
curl -X POST http://localhost:8000/api/v1/agent/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "Test command"}'
```

---

### 阶段 3: 爬虫系统 (3-4 天)

**目标**: 实现 GCR 平台数据抓取

**任务清单**:
- [ ] 实现爬虫基类
- [ ] 实现知乎爬虫 (优先级最高)
- [ ] 实现微信公众号爬虫 (搜狗入口)
- [ ] 实现反检测模块 (UA 轮换、指纹伪装)
- [ ] 实现代理池管理
- [ ] 实现速率限制

**关键文件**:
- `backend/app/crawlers/base.py`
- `backend/app/crawlers/zhihu/crawler.py`
- `backend/app/crawlers/wechat/crawler.py`
- `backend/app/crawlers/anti_detect/`

**验证方式**:
```python
# 测试知乎爬虫
crawler = ZhihuCrawler(...)
results = await crawler.search("DeepSeek", limit=10)
assert len(results.items) > 0
```

---

### 阶段 4: 记忆系统 (2-3 天)

**目标**: 实现长效记忆

**任务清单**:
- [ ] 实现向量存储 (pgvector)
- [ ] 实现嵌入生成
- [ ] 实现语义搜索
- [ ] 实现时间线索引
- [ ] 实现变化检测 (功能上下线)

**关键文件**:
- `backend/app/memory/vector_store.py`
- `backend/app/memory/retriever.py`
- `backend/app/memory/temporal_index.py`

**验证方式**:
```python
# 测试语义搜索
results = await memory.search("DeepSeek API pricing", limit=10)
assert len(results) > 0

# 测试时间线变化检测
changes = await memory.find_temporal_changes("DeepSeek", "聊天功能", days=90)
```

---

### 阶段 5: 高级功能 (2-3 天)

**目标**: 完善 Agent 能力

**任务清单**:
- [ ] 实现 Critic (批判性评估)
- [ ] 实现递归搜索扩展
- [ ] 实现错误自愈机制
- [ ] 实现 Token 消耗追踪
- [ ] 优化 Token 使用 (先过滤后分析)

**关键文件**:
- `backend/app/core/agent/critic.py`
- `backend/app/core/resilience/retry.py`
- `backend/app/core/llm/router.py`

**验证方式**:
```bash
# 测试错误自愈
# 故意触发 403 错误，观察日志是否显示恢复过程
```

---

### 阶段 6: 前后端集成 (1-2 天)

**目标**: 完成端到端集成

**任务清单**:
- [ ] 创建前端 API 服务 (agentService.ts)
- [ ] 修改 App.tsx 集成后端 SSE
- [ ] 实现 WebSocket 实时推送
- [ ] 更新 StatsGrid 从后端获取数据
- [ ] 更新 NetworkMap 从后端获取数据
- [ ] 端到端测试

**关键文件**:
- `insightsentinel/services/agentService.ts`
- `insightsentinel/App.tsx`

**验证方式**:
```
1. 启动后端: uvicorn app.main:app --reload
2. 启动前端: npm run dev
3. 在 CommandBar 输入命令
4. 观察 LogPanel 是否显示实时思考链路
5. 观察 StatsGrid 和 NetworkMap 是否更新
```

---

## 3. 依赖关系

```
阶段 1 (基础架构)
    │
    ├──▶ 阶段 2 (Agent 核心)
    │         │
    │         └──▶ 阶段 5 (高级功能)
    │                   │
    ├──▶ 阶段 3 (爬虫系统) ──┤
    │                       │
    └──▶ 阶段 4 (记忆系统) ──┴──▶ 阶段 6 (集成)
```

---

## 4. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| GCR 平台反爬严格 | 爬虫成功率低 | 代理池 + 降级到缓存 |
| Gemini API 限流 | Agent 响应慢 | 指数退避 + Token 优化 |
| 前后端接口不匹配 | 集成延迟 | 先定义 OpenAPI Schema |
| 向量搜索性能 | 响应时间长 | HNSW 索引 + 分页 |

---

## 5. 待确认事项

在开始实施前，需要确认以下事项：

1. **Git 仓库**: 是否需要现在创建 GitHub 仓库并提交现有代码？
2. **API Key**: 是否已有 Gemini API Key 可用于后端？
3. **代理服务**: 是否有可用的代理服务商用于爬虫？
4. **部署环境**: 是否需要准备 Docker 配置？

---

## 6. 下一步行动

1. 退出计划模式
2. 创建 GitHub 仓库
3. 提交现有代码（多个 commit 分类提交）
4. 开始阶段 1 实施

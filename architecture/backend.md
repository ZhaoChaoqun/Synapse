# 后端 API 详细设计

## 1. API 端点总览

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/agent/execute` | 执行 Agent 命令 (SSE) |
| GET | `/api/v1/agent/tasks/{task_id}` | 获取任务详情 |
| GET | `/api/v1/agent/tasks` | 获取任务列表 |
| POST | `/api/v1/intelligence/search` | 搜索情报库 |
| GET | `/api/v1/intelligence/timeline` | 获取时间线事件 |
| GET | `/api/v1/intelligence/competitors/{id}` | 获取竞品详情 |
| GET | `/api/v1/platforms/stats` | 获取平台统计 |
| GET | `/api/v1/platforms/network` | 获取知识图谱 |
| WS | `/api/v1/ws` | WebSocket 实时推送 |

---

## 2. Agent 端点

### 2.1 POST /api/v1/agent/execute

执行 Agent 命令，返回 Server-Sent Events 流。

**请求体**:
```json
{
  "command": "Monitor DeepSeek's latest developments",
  "options": {
    "platforms": ["zhihu", "wechat"],
    "time_range": "7d",
    "max_steps": 10
  }
}
```

**响应** (SSE 流):
```
event: thought
data: {"step_id": "task_001_step_1", "phase": "planning", "thought": "分析任务: 监控 DeepSeek 最新动态", "action": "decompose_task", "progress": 10}

event: thought
data: {"step_id": "task_001_step_2", "phase": "searching", "thought": "正在搜索知乎...", "action": "platform_search", "progress": 30}

event: thought
data: {"step_id": "task_001_step_3", "phase": "expanding", "thought": "发现新关键词 'DeepSeek R1'，追加搜索...", "action": "recursive_search", "progress": 50}

event: thought
data: {"step_id": "task_001_step_4", "phase": "critiquing", "thought": "正在交叉验证信息可信度...", "action": "critical_evaluation", "progress": 80}

event: thought
data: {"step_id": "task_001_step_5", "phase": "synthesizing", "thought": "生成情报摘要...", "action": "synthesize", "progress": 100}

event: complete
data: {"task_id": "task_001", "intelligence_count": 15, "total_tokens": 2500}
```

**前端集成**:
```typescript
const eventSource = new EventSource('/api/v1/agent/execute?command=...');

eventSource.addEventListener('thought', (event) => {
  const step = JSON.parse(event.data);
  addLogEntry(step);
});

eventSource.addEventListener('complete', () => {
  eventSource.close();
  refreshDashboard();
});
```

### 2.2 GET /api/v1/agent/tasks/{task_id}

获取任务详情。

**响应**:
```json
{
  "task_id": "task_001",
  "command": "Monitor DeepSeek's latest developments",
  "status": "completed",
  "thought_chain": [
    {
      "step_id": "task_001_step_1",
      "phase": "planning",
      "timestamp": "2026-02-06T10:00:00Z",
      "thought": "分析任务...",
      "action": "decompose_task",
      "observation": "分解为 4 个子任务",
      "tokens_used": 150
    }
  ],
  "result_summary": "发现 15 条相关情报，主要涉及...",
  "intelligence_count": 15,
  "total_tokens": 2500,
  "duration_ms": 45000
}
```

---

## 3. 情报端点

### 3.1 POST /api/v1/intelligence/search

搜索情报库（语义搜索）。

**请求体**:
```json
{
  "query": "DeepSeek API pricing",
  "platforms": ["zhihu", "wechat"],
  "time_range": "30d",
  "category": "product_launch",
  "min_credibility": 0.6,
  "limit": 20
}
```

**响应**:
```json
{
  "items": [
    {
      "id": "intel_001",
      "platform": "zhihu",
      "title": "DeepSeek V3 API 降价分析",
      "summary": "DeepSeek 宣布 API 价格下调 50%...",
      "author": "AI 研究员",
      "published_at": "2026-02-01T08:00:00Z",
      "sentiment": 0.8,
      "credibility_score": 0.85,
      "importance_score": 0.9,
      "mentioned_companies": ["DeepSeek", "OpenAI"],
      "keywords": ["API", "pricing", "V3"],
      "source_url": "https://zhihu.com/answer/..."
    }
  ],
  "total": 42,
  "query_tokens": 50
}
```

### 3.2 GET /api/v1/intelligence/timeline

获取时间线事件（用于检测跨时间变化）。

**查询参数**:
- `subject`: 主体名称 (如 "DeepSeek")
- `days`: 时间范围 (默认 90)

**响应**:
```json
{
  "events": [
    {
      "id": "event_001",
      "event_type": "feature_change",
      "event_date": "2026-02-01",
      "subject_name": "DeepSeek",
      "description": "DeepSeek V3 API 上线",
      "significance_score": 0.95,
      "related_event_id": null
    },
    {
      "id": "event_002",
      "event_type": "feature_change",
      "event_date": "2025-11-15",
      "subject_name": "DeepSeek",
      "description": "DeepSeek 聊天功能下线",
      "significance_score": 0.7,
      "related_event_id": "event_003"
    },
    {
      "id": "event_003",
      "event_type": "feature_change",
      "event_date": "2026-01-20",
      "subject_name": "DeepSeek",
      "description": "DeepSeek 聊天功能重新上线",
      "significance_score": 0.85,
      "related_event_id": "event_002"
    }
  ],
  "insights": [
    {
      "type": "feature_return",
      "description": "DeepSeek 聊天功能在下线 2 个月后重新上线",
      "events": ["event_002", "event_003"]
    }
  ]
}
```

---

## 4. 平台端点

### 4.1 GET /api/v1/platforms/stats

获取各平台实时统计（用于 StatsGrid 组件）。

**响应**:
```json
{
  "stats": [
    {
      "platform": "wechat",
      "display_name": "WeChat Pulse",
      "hotness_score": 88,
      "trend": 0.12,
      "trend_up": true,
      "color_theme": "green",
      "top_keywords": [
        {"keyword": "DeepSeek", "count": 156},
        {"keyword": "Kimi", "count": 98}
      ],
      "last_updated": "2026-02-06T10:30:00Z"
    },
    {
      "platform": "zhihu",
      "display_name": "Zhihu Heat",
      "hotness_score": 76,
      "trend": -0.05,
      "trend_up": false,
      "color_theme": "blue",
      "top_keywords": [...]
    }
  ]
}
```

### 4.2 GET /api/v1/platforms/network

获取知识图谱网络（用于 NetworkMap 组件）。

**查询参数**:
- `focus`: 焦点节点 (可选)
- `depth`: 展开深度 (默认 2)

**响应**:
```json
{
  "nodes": [
    {
      "id": "node_001",
      "label": "DeepSeek",
      "type": "competitor",
      "status": "active",
      "icon": "business",
      "color": "#4F46E5",
      "x": 0.5,
      "y": 0.5
    },
    {
      "id": "node_002",
      "label": "Moonshot AI",
      "type": "competitor",
      "status": "active",
      "icon": "business",
      "color": "#10B981"
    },
    {
      "id": "node_003",
      "label": "TechBrother",
      "type": "kol",
      "status": "active",
      "icon": "person",
      "color": "#F59E0B"
    }
  ],
  "edges": [
    {
      "source": "node_001",
      "target": "node_002",
      "relationship": "competes_with",
      "strength": 0.8
    },
    {
      "source": "node_003",
      "target": "node_001",
      "relationship": "covers",
      "strength": 0.6
    }
  ]
}
```

---

## 5. WebSocket 端点

### 5.1 WS /api/v1/ws

实时推送通道。

**消息类型**:

```typescript
// 订阅
{ "type": "subscribe", "topics": ["stats", "alerts"] }

// 统计更新
{ "type": "stats_update", "data": {...} }

// 实时告警
{ "type": "alert", "data": { "level": "warning", "message": "知乎爬虫被限流" } }

// Agent 思考步骤
{ "type": "thought", "task_id": "task_001", "data": {...} }
```

---

## 6. 错误响应格式

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "API rate limit exceeded",
    "details": {
      "retry_after": 60
    }
  }
}
```

**错误码**:
| 代码 | HTTP 状态码 | 描述 |
|------|-----------|------|
| `INVALID_REQUEST` | 400 | 请求参数错误 |
| `UNAUTHORIZED` | 401 | 未授权 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `RATE_LIMITED` | 429 | 请求频率过高 |
| `INTERNAL_ERROR` | 500 | 内部错误 |

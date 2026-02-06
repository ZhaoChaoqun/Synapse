# 数据库 Schema 设计

## 1. 概述

使用 PostgreSQL 作为主数据库，配合 pgvector 扩展实现向量搜索。

---

## 2. 实体关系图

```
┌───────────────────┐       ┌───────────────────┐
│ intelligence_items│       │    competitors    │
├───────────────────┤       ├───────────────────┤
│ id (PK)           │       │ id (PK)           │
│ source_platform   │       │ name              │
│ title             │       │ products (JSON)   │
│ content           │       │ funding_rounds    │
│ summary           │◀──────│ ...               │
│ mentioned_companies│       └───────────────────┘
│ credibility_score │               │
│ embedding_id      │               │
│ ...               │               ▼
└───────────────────┘       ┌───────────────────┐
        │                   │ product_features  │
        │                   ├───────────────────┤
        │                   │ id (PK)           │
        ▼                   │ competitor_id(FK) │
┌───────────────────┐       │ feature_name      │
│   agent_tasks     │       │ feature_status    │
├───────────────────┤       │ status_history    │
│ id (PK)           │       └───────────────────┘
│ command           │
│ thought_chain     │       ┌───────────────────┐
│ intelligence_ids  │       │  timeline_events  │
│ total_tokens      │       ├───────────────────┤
│ ...               │       │ id (PK)           │
└───────────────────┘       │ event_type        │
                            │ event_date        │
                            │ subject_name      │
                            │ related_event_id  │
                            └───────────────────┘
```

---

## 3. 表定义

### 3.1 情报实体表 (intelligence_items)

```sql
CREATE TABLE intelligence_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_platform VARCHAR(50) NOT NULL,  -- wechat, zhihu, xiaohongshu, douyin
    source_url TEXT,
    source_id VARCHAR(255),                 -- 平台内部 ID

    title TEXT,
    content TEXT NOT NULL,
    summary TEXT,                           -- LLM 生成的摘要

    author_name VARCHAR(255),
    author_id VARCHAR(255),
    author_followers INTEGER,

    published_at TIMESTAMP WITH TIME ZONE,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 情报分类
    category VARCHAR(100),                  -- product_launch, funding, partnership
    sentiment FLOAT,                        -- -1.0 to 1.0
    credibility_score FLOAT,                -- 0.0 to 1.0
    importance_score FLOAT,                 -- 0.0 to 1.0

    -- 关联实体（JSON 数组）
    mentioned_companies JSONB DEFAULT '[]',
    mentioned_products JSONB DEFAULT '[]',
    mentioned_persons JSONB DEFAULT '[]',
    keywords JSONB DEFAULT '[]',

    -- 向量嵌入 ID
    embedding_id VARCHAR(255),

    -- 元数据
    raw_data JSONB,
    processing_metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_intelligence_platform ON intelligence_items(source_platform);
CREATE INDEX idx_intelligence_published ON intelligence_items(published_at);
CREATE INDEX idx_intelligence_category ON intelligence_items(category);
CREATE INDEX idx_intelligence_companies ON intelligence_items USING GIN (mentioned_companies);
```

### 3.2 竞品信息表 (competitors)

```sql
CREATE TABLE competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    aliases JSONB DEFAULT '[]',             -- 别名列表

    -- 基本信息
    company_type VARCHAR(100),              -- startup, bigtech, research_lab
    founded_date DATE,
    headquarters VARCHAR(255),
    website TEXT,

    -- 产品信息
    products JSONB DEFAULT '[]',
    tech_stack JSONB DEFAULT '[]',

    -- 融资信息
    funding_rounds JSONB DEFAULT '[]',
    total_funding DECIMAL(15, 2),
    valuation DECIMAL(15, 2),

    -- 团队信息
    key_people JSONB DEFAULT '[]',
    employee_count INTEGER,

    -- 动态追踪
    last_news_at TIMESTAMP WITH TIME ZONE,
    news_frequency FLOAT,
    sentiment_trend FLOAT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3.3 产品功能追踪表 (product_features)

用于检测"功能上线/下线"变化。

```sql
CREATE TABLE product_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID REFERENCES competitors(id),
    product_name VARCHAR(255) NOT NULL,

    feature_name VARCHAR(255) NOT NULL,
    feature_description TEXT,
    feature_status VARCHAR(50) NOT NULL,    -- active, deprecated, beta, removed

    first_seen_at TIMESTAMP WITH TIME ZONE,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    removed_at TIMESTAMP WITH TIME ZONE,

    -- 状态变更历史
    status_history JSONB DEFAULT '[]',      -- [{status, timestamp, source}]

    source_intelligence_id UUID REFERENCES intelligence_items(id),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_features_status ON product_features(feature_status);
CREATE INDEX idx_features_competitor ON product_features(competitor_id);
```

### 3.4 Agent 任务记录表 (agent_tasks)

```sql
CREATE TABLE agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    command TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,            -- pending, running, completed, failed

    -- 执行过程
    thought_chain JSONB DEFAULT '[]',
    tools_used JSONB DEFAULT '[]',

    -- 结果
    result_summary TEXT,
    intelligence_ids UUID[],

    -- 统计
    total_steps INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_duration_ms INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,

    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3.5 时间线事件表 (timeline_events)

用于跨时间分析。

```sql
CREATE TABLE timeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_type VARCHAR(100) NOT NULL,       -- product_launch, feature_change, funding
    event_date DATE NOT NULL,

    subject_type VARCHAR(50) NOT NULL,      -- competitor, product, person
    subject_id UUID,
    subject_name VARCHAR(255),

    description TEXT,
    significance_score FLOAT,

    source_intelligence_ids UUID[],

    -- 用于检测"回归"变化（如功能恢复上线）
    related_event_id UUID REFERENCES timeline_events(id),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_timeline_date ON timeline_events(event_date);
CREATE INDEX idx_timeline_subject ON timeline_events(subject_type, subject_id);
```

---

## 4. 向量存储 (pgvector)

### 4.1 启用扩展

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4.2 向量表

```sql
CREATE TABLE intelligence_embeddings (
    id UUID PRIMARY KEY REFERENCES intelligence_items(id),
    embedding vector(768),  -- text-embedding-004 维度
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- HNSW 索引（近似最近邻搜索）
CREATE INDEX idx_embedding_hnsw ON intelligence_embeddings
USING hnsw (embedding vector_cosine_ops);
```

### 4.3 语义搜索查询

```sql
-- 查找最相似的 10 条情报
SELECT i.*, e.embedding <=> $1 AS distance
FROM intelligence_items i
JOIN intelligence_embeddings e ON i.id = e.id
WHERE i.source_platform = ANY($2)
  AND i.published_at > NOW() - INTERVAL '7 days'
ORDER BY e.embedding <=> $1
LIMIT 10;
```

---

## 5. Redis 数据结构

### 5.1 缓存键设计

| 键模式 | 数据类型 | 用途 | TTL |
|--------|---------|------|-----|
| `cache:search:{hash}` | String | 搜索结果缓存 | 1h |
| `cache:competitor:{id}` | String | 竞品信息缓存 | 24h |
| `tokens:task:{id}` | Hash | 任务 Token 统计 | 7d |
| `tokens:daily:{date}` | Hash | 每日 Token 统计 | 30d |
| `crawler:proxy_pool` | Sorted Set | 代理池（按成功率排序） | - |
| `crawler:proxy_failed` | Hash | 代理失败计数 | 24h |
| `crawler:rate_limit:{platform}` | String | 速率限制令牌 | 1s |

### 5.2 示例

```python
# 代理池管理
await redis.zadd("crawler:proxy_pool", {proxy_url: success_rate})
await redis.zrevrange("crawler:proxy_pool", 0, 0)  # 获取最佳代理

# Token 统计
await redis.hincrby(f"tokens:task:{task_id}", "gemini_flash:prompt", 1000)
await redis.hincrby(f"tokens:daily:2026-02-06", "gemini_flash", 5000)
```

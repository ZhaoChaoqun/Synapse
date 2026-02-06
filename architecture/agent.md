# Agent 核心设计

## 1. Agentic Loop 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT ORCHESTRATOR                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    USER COMMAND                            │  │
│  │         "Monitor DeepSeek's latest developments"           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 STEP 1: PLANNER                            │  │
│  │   [Gemini Flash] 任务分解                                   │  │
│  │   Output: TaskPlan with 3-5 sub-tasks                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│              ┌───────────────┴───────────────┐                  │
│              ▼                               ▼                  │
│  ┌─────────────────────┐         ┌─────────────────────┐       │
│  │  STEP 2a: SEARCH    │         │  STEP 2b: SCRAPE    │       │
│  │  微信/知乎/XHS/抖音  │         │  获取详细内容        │       │
│  └─────────────────────┘         └─────────────────────┘       │
│              │                               │                  │
│              └───────────────┬───────────────┘                  │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 STEP 3: RECURSIVE EXPAND                   │  │
│  │   发现新关键词？→ 自主决定是否追加搜索                        │  │
│  │   "DeepSeek R1" → 发现 "DeepSeek API 降价" → 追加           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 STEP 4: CRITIC (Critical Review)           │  │
│  │   [Gemini Pro] 交叉验证信息可信度                           │  │
│  │   - 来源可靠性评分                                          │  │
│  │   - 矛盾检测                                                │  │
│  │   - 时效性判断                                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 STEP 5: SYNTHESIZE & STORE                 │  │
│  │   生成情报摘要 → 存入记忆系统 → 推送前端                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent 状态机

### 2.1 状态枚举

```python
class AgentPhase(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    SEARCHING = "searching"
    SCRAPING = "scraping"
    EXPANDING = "expanding"      # 递归搜索
    CRITIQUING = "critiquing"   # 批判性评估
    SYNTHESIZING = "synthesizing"
    RECOVERING = "recovering"    # 错误恢复
    COMPLETED = "completed"
    FAILED = "failed"
```

### 2.2 状态转换图

```
                    ┌──────────────────────────────────────┐
                    │                                      │
                    ▼                                      │
┌──────┐      ┌──────────┐      ┌───────────┐      ┌─────────────┐
│ IDLE │ ──▶  │ PLANNING │ ──▶  │ EXECUTING │ ──▶  │ SEARCHING/  │
└──────┘      └──────────┘      └───────────┘      │ SCRAPING    │
                                      │            └─────────────┘
                                      │                   │
                                      ▼                   ▼
                               ┌─────────────┐     ┌───────────┐
                               │ RECOVERING  │ ◀── │ EXPANDING │
                               └─────────────┘     └───────────┘
                                      │                   │
                                      ▼                   ▼
                               ┌─────────────┐     ┌───────────────┐
                               │   FAILED    │     │  CRITIQUING   │
                               └─────────────┘     └───────────────┘
                                                          │
                                                          ▼
                                                   ┌───────────────┐
                                                   │ SYNTHESIZING  │
                                                   └───────────────┘
                                                          │
                                                          ▼
                                                   ┌───────────────┐
                                                   │  COMPLETED    │
                                                   └───────────────┘
```

---

## 3. 核心数据结构

### 3.1 ThoughtStep（思考步骤）

```python
class ThoughtStep(BaseModel):
    """单步思考记录，用于展示给前端"""
    step_id: str
    phase: AgentPhase
    timestamp: datetime
    thought: str              # Agent 的"想法"
    action: Optional[str]     # 执行的动作
    observation: Optional[str] # 观察到的结果
    tool_calls: List[Dict[str, Any]] = []
    tokens_used: int = 0
    duration_ms: int = 0
```

### 3.2 AgentState（Agent 状态）

```python
class AgentState(BaseModel):
    """Agent 运行状态"""
    task_id: str
    original_command: str
    current_phase: AgentPhase
    thought_chain: List[ThoughtStep] = []  # 完整思考链
    discovered_keywords: List[str] = []    # 发现的新关键词
    pending_searches: List[str] = []       # 待搜索队列
    collected_data: List[Dict] = []        # 收集的数据
    credibility_scores: Dict[str, float] = {}  # 可信度评分
    total_tokens: int = 0
    error_count: int = 0
    max_steps: int = 10
    current_step: int = 0
```

---

## 4. Orchestrator 核心实现

```python
class AgentOrchestrator:
    """Agent 编排器：协调整个 Agentic Loop"""

    async def run(
        self,
        command: str,
        stream_callback: callable = None
    ) -> AsyncGenerator[ThoughtStep, None]:
        """
        执行 Agentic Loop，流式返回思考步骤
        """
        state = AgentState(
            task_id=generate_task_id(),
            original_command=command,
            current_phase=AgentPhase.PLANNING
        )

        try:
            # Step 1: 任务规划
            async for step in self._plan(state, command):
                yield step

            # Step 2-3: 执行与递归扩展
            while state.current_step < state.max_steps:
                state.current_step += 1

                async for step in self._execute_step(state):
                    yield step

                if state.pending_searches:
                    keyword = state.pending_searches.pop(0)
                    async for step in self._expand_search(state, keyword):
                        yield step
                else:
                    break

            # Step 4: 批判性评估
            async for step in self._critique(state):
                yield step

            # Step 5: 合成结果
            async for step in self._synthesize(state):
                yield step

        except Exception as e:
            # 错误自愈
            async for step in self._recover(state, e):
                yield step
```

---

## 5. Tool 定义

### 5.1 Tool 基类

```python
class BaseTool(ABC):
    """Tool 基类"""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """返回 Tool 定义"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行 Tool"""
        pass

    def to_function_schema(self) -> Dict:
        """转换为 Gemini Function Calling 格式"""
        return {
            "name": self.definition.name,
            "description": self.definition.description,
            "parameters": {...}
        }
```

### 5.2 内置 Tools

| Tool | 功能 | 参数 |
|------|------|------|
| `platform_search` | 多平台搜索 | query, platforms, time_range |
| `memory_search` | 记忆库搜索 | query, subject, detect_changes |
| `analyze_sentiment` | 情感分析 | texts, extract_opinions |
| `competitor_lookup` | 竞品查询 | name |
| `timeline_query` | 时间线查询 | subject, days |
| `web_scrape` | 网页抓取 | url |

---

## 6. LLM 路由策略

### 6.1 双层模型

| 层级 | 模型 | 用途 | 成本 |
|------|------|------|------|
| Light | Gemini Flash | 过滤、分类、简单推理 | 低 |
| Heavy | Gemini Pro | 复杂分析、批判评估 | 高 |

### 6.2 自动路由规则

```python
# 轻量任务 → Gemini Flash
light_tasks = ["filter", "classify", "extract_keywords", "simple_qa"]

# 重量任务 → Gemini Pro
heavy_tasks = ["critical_review", "deep_analysis", "synthesis"]

# 根据内容长度
if len(content) > 5000:
    use_heavy_model()
else:
    use_light_model()
```

---

## 7. 错误自愈机制

### 7.1 错误分类

| 错误类型 | 触发条件 | 恢复策略 |
|---------|---------|---------|
| API_RATE_LIMIT | 429 响应 | 指数退避 |
| API_TIMEOUT | 请求超时 | 重试 |
| CRAWLER_BLOCKED | 403 响应 | 切换代理 |
| CRAWLER_CAPTCHA | 验证码检测 | 切换代理 + 告警 |
| NETWORK_ERROR | 网络异常 | 重试 |

### 7.2 恢复策略实现

```python
class RetryManager:
    STRATEGIES = {
        ErrorType.API_RATE_LIMIT: [ExponentialBackoffStrategy()],
        ErrorType.CRAWLER_BLOCKED: [SwitchProxyStrategy(), FallbackCrawlerStrategy()],
    }

    def get_strategy(self, error: Exception) -> RecoveryStrategy:
        error_type = self._classify_error(error)
        return self.STRATEGIES.get(error_type, [ExponentialBackoffStrategy()])[0]
```

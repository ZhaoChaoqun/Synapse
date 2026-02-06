# 爬虫系统设计

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                      Crawler Manager                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Request Queue                           │  │
│  │    [微信搜索] [知乎搜索] [小红书搜索] [抖音搜索]              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Anti-Detect Layer                        │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │  │
│  │  │ Proxy Pool  │ │ UA Rotator  │ │ Fingerprint Manager │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  Platform Crawlers                         │  │
│  │  ┌─────────┐ ┌─────────┐ ┌───────────┐ ┌─────────────┐   │  │
│  │  │ WeChat  │ │  Zhihu  │ │Xiaohongshu│ │   Douyin    │   │  │
│  │  │ Crawler │ │ Crawler │ │  Crawler  │ │   Crawler   │   │  │
│  │  └─────────┘ └─────────┘ └───────────┘ └─────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     Parser Layer                           │  │
│  │     Content Extraction → Cleaning → Normalization          │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 爬虫基类

```python
class BaseCrawler(ABC):
    """爬虫基类"""

    def __init__(
        self,
        proxy_pool: ProxyPool,
        anti_detect: AntiDetect,
        rate_limiter: RateLimiter
    ):
        self.proxy_pool = proxy_pool
        self.anti_detect = anti_detect
        self.rate_limiter = rate_limiter

    @property
    @abstractmethod
    def platform_name(self) -> str:
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        time_range: str = "7d",
        limit: int = 10
    ) -> CrawlResult:
        """搜索内容"""
        pass

    @abstractmethod
    async def get_detail(self, item_id: str) -> Dict[str, Any]:
        """获取详情"""
        pass

    async def _request_with_retry(
        self,
        url: str,
        method: str = "GET",
        max_retries: int = 3,
        **kwargs
    ) -> Any:
        """带重试和反检测的请求"""
        for attempt in range(max_retries):
            try:
                proxy = await self.proxy_pool.get()
                headers = self.anti_detect.get_headers()
                await self.rate_limiter.wait(self.platform_name)

                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method, url,
                        proxy=proxy,
                        headers=headers,
                        **kwargs
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 403:
                            await self.proxy_pool.mark_failed(proxy)
                            raise RateLimitedException()
                        else:
                            raise CrawlerException(f"HTTP {response.status}")

            except RateLimitedException:
                await asyncio.sleep(2 ** attempt)
                continue
```

---

## 3. 平台爬虫实现

### 3.1 微信公众号爬虫

**策略**: 使用搜狗微信搜索作为入口

```python
class WeChatCrawler(BaseCrawler):
    platform_name = "wechat"
    SEARCH_URL = "https://weixin.sogou.com/weixin"

    async def search(self, query: str, time_range: str = "7d", limit: int = 10):
        """搜索微信公众号文章"""
        time_param = self._convert_time_range(time_range)
        results = []
        page = 1

        while len(results) < limit:
            params = {
                "query": query,
                "type": 2,  # 文章搜索
                "page": page,
                "tsn": time_param
            }

            data = await self._request_with_retry(self.SEARCH_URL, params=params)
            items = self._parse_search_results(data)
            results.extend(items)

            if not items:
                break
            page += 1

        return CrawlResult(
            platform=self.platform_name,
            items=results[:limit],
            total_found=len(results),
            has_more=len(results) > limit
        )
```

### 3.2 知乎爬虫

**策略**: 使用知乎 API + x-zse-96 签名

```python
class ZhihuCrawler(BaseCrawler):
    platform_name = "zhihu"
    SEARCH_API = "https://www.zhihu.com/api/v4/search_v3"

    async def search(self, query: str, time_range: str = "7d", limit: int = 10):
        """搜索知乎内容"""
        params = {
            "t": "general",
            "q": query,
            "correction": 1,
            "offset": 0,
            "limit": min(limit, 20)
        }

        # 知乎需要特殊签名
        headers = self._generate_zhihu_headers(params)

        data = await self._request_with_retry(
            self.SEARCH_API,
            params=params,
            headers=headers
        )

        return CrawlResult(
            platform=self.platform_name,
            items=self._parse_zhihu_results(data),
            total_found=data.get("paging", {}).get("totals", 0),
            has_more=not data.get("paging", {}).get("is_end", True)
        )

    def _generate_zhihu_headers(self, params: dict) -> dict:
        """生成知乎 API 签名"""
        # x-zse-96 签名算法
        # ...
        pass
```

### 3.3 小红书爬虫

**策略**: Web API + X-S/X-T 签名

```python
class XiaohongshuCrawler(BaseCrawler):
    platform_name = "xiaohongshu"

    async def search(self, query: str, time_range: str = "7d", limit: int = 10):
        """搜索小红书笔记"""
        timestamp = int(time.time() * 1000)
        sign_data = self._generate_xhs_sign(query, timestamp)

        headers = {
            "X-S": sign_data["x_s"],
            "X-T": str(timestamp),
            **self.anti_detect.get_headers()
        }

        # 实现搜索逻辑
        pass
```

### 3.4 抖音爬虫

**策略**: Web API + msToken 机制

```python
class DouyinCrawler(BaseCrawler):
    platform_name = "douyin"

    async def search(self, query: str, time_range: str = "7d", limit: int = 10):
        """搜索抖音视频"""
        ms_token = await self._get_ms_token()

        params = {
            "keyword": query,
            "search_channel": "aweme_general",
            "sort_type": 0,
            "publish_time": self._convert_time_range(time_range),
            "msToken": ms_token
        }

        # 实现搜索逻辑
        pass
```

---

## 4. 反检测模块

### 4.1 代理池管理

```python
class ProxyPool:
    """代理池管理"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.proxy_key = "crawler:proxy_pool"
        self.failed_key = "crawler:proxy_failed"

    async def get(self) -> str:
        """获取最佳代理（按成功率排序）"""
        proxies = await self.redis.zrevrange(self.proxy_key, 0, 0, withscores=True)
        if proxies:
            return proxies[0][0]
        return await self._fetch_new_proxy()

    async def mark_failed(self, proxy: str):
        """标记代理失败"""
        await self.redis.zincrby(self.proxy_key, -1, proxy)
        await self.redis.hincrby(self.failed_key, proxy, 1)

        # 失败次数过多则移除
        failures = await self.redis.hget(self.failed_key, proxy)
        if int(failures or 0) > 5:
            await self.redis.zrem(self.proxy_key, proxy)

    async def mark_success(self, proxy: str):
        """标记代理成功"""
        await self.redis.zincrby(self.proxy_key, 1, proxy)
```

### 4.2 指纹伪装

```python
class AntiDetect:
    """反检测模块"""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...",
        # 更多 UA...
    ]

    def get_headers(self) -> Dict[str, str]:
        """生成随机浏览器指纹头"""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
```

### 4.3 速率限制

```python
class RateLimiter:
    """速率限制器"""

    # 各平台速率限制（请求/秒）
    LIMITS = {
        "wechat": 0.5,    # 2秒1次
        "zhihu": 1.0,     # 1秒1次
        "xiaohongshu": 0.5,
        "douyin": 0.5,
    }

    async def wait(self, platform: str):
        """等待直到可以发送请求"""
        key = f"crawler:rate_limit:{platform}"
        limit = self.LIMITS.get(platform, 1.0)

        while True:
            if await self.redis.set(key, "1", ex=int(1/limit), nx=True):
                return
            await asyncio.sleep(0.1)
```

---

## 5. 数据解析

### 5.1 通用解析器

```python
class ContentParser:
    """内容解析器"""

    def parse(self, raw_html: str, platform: str) -> ParsedContent:
        """解析原始 HTML"""
        parser = self._get_parser(platform)
        return parser.parse(raw_html)

    def normalize(self, content: ParsedContent) -> NormalizedContent:
        """标准化内容"""
        return NormalizedContent(
            title=self._clean_text(content.title),
            body=self._clean_text(content.body),
            author=content.author,
            published_at=self._parse_datetime(content.published_at),
            metrics=content.metrics,
        )

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除 HTML 标签
        # 移除特殊字符
        # 标准化空白
        pass
```

### 5.2 平台特定解析器

```python
class ZhihuParser:
    """知乎内容解析器"""

    def parse_answer(self, data: dict) -> ParsedContent:
        return ParsedContent(
            title=data.get("question", {}).get("title"),
            body=data.get("content"),
            author=data.get("author", {}).get("name"),
            published_at=data.get("created_time"),
            metrics={
                "voteup_count": data.get("voteup_count", 0),
                "comment_count": data.get("comment_count", 0),
            }
        )

class XiaohongshuParser:
    """小红书内容解析器"""

    def parse_note(self, data: dict) -> ParsedContent:
        return ParsedContent(
            title=data.get("title"),
            body=data.get("desc"),
            author=data.get("user", {}).get("nickname"),
            published_at=data.get("time"),
            metrics={
                "liked_count": data.get("liked_count", 0),
                "collected_count": data.get("collected_count", 0),
            },
            images=data.get("images", []),  # 小红书特有
        )
```

---

## 6. 错误处理

### 6.1 异常类型

```python
class CrawlerException(Exception):
    """爬虫基础异常"""
    pass

class RateLimitedException(CrawlerException):
    """被限流"""
    pass

class BlockedException(CrawlerException):
    """被封禁"""
    pass

class CaptchaException(CrawlerException):
    """遇到验证码"""
    pass

class ParseException(CrawlerException):
    """解析失败"""
    pass
```

### 6.2 重试策略

| 异常类型 | 重试次数 | 退避策略 | 额外动作 |
|---------|---------|---------|---------|
| RateLimitedException | 3 | 指数退避 | - |
| BlockedException | 2 | 切换代理 | 记录失败代理 |
| CaptchaException | 1 | 切换代理 | 发送告警 |
| ParseException | 0 | - | 记录日志 |

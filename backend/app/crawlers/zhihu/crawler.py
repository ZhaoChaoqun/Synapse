"""
Zhihu Crawler

Crawls content from Zhihu (知乎) platform.
"""

import hashlib
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

from app.crawlers.base import (
    BaseCrawler,
    CrawlItem,
    CrawlResult,
    CrawlerException,
    ParseException,
)
from app.crawlers.anti_detect import AntiDetect, ProxyPool, RateLimiter


class ZhihuCrawler(BaseCrawler):
    """
    Zhihu platform crawler.

    Supports:
    - Keyword search
    - Question/Answer detail fetching
    - Article content extraction
    """

    # API endpoints
    SEARCH_API = "https://www.zhihu.com/api/v4/search_v3"
    QUESTION_API = "https://www.zhihu.com/api/v4/questions/{qid}/feeds"
    ANSWER_API = "https://www.zhihu.com/api/v4/answers/{aid}"
    ARTICLE_API = "https://zhuanlan.zhihu.com/api/articles/{aid}"

    # Content type mappings
    CONTENT_TYPES = {
        "search_result": "mixed",
        "answer": "answer",
        "article": "article",
        "question": "question",
    }

    def __init__(
        self,
        proxy_pool: Optional[ProxyPool] = None,
        anti_detect: Optional[AntiDetect] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        super().__init__(proxy_pool, anti_detect, rate_limiter)
        self._x_zse_96_key = "101_3_3.0"  # Zhihu signature version

    @property
    def platform_name(self) -> str:
        return "zhihu"

    @property
    def display_name(self) -> str:
        return "知乎"

    async def search(
        self,
        query: str,
        time_range: str = "7d",
        limit: int = 10,
    ) -> CrawlResult:
        """
        Search Zhihu for content matching the query.

        Args:
            query: Search keywords
            time_range: Time range filter (1d, 7d, 30d, 90d)
            limit: Maximum number of results

        Returns:
            CrawlResult with search results
        """
        try:
            items = []
            offset = 0
            page_size = min(limit, 20)

            while len(items) < limit:
                # Build search URL
                params = {
                    "t": "general",
                    "q": query,
                    "correction": 1,
                    "offset": offset,
                    "limit": page_size,
                    "filter_fields": "",
                    "lc_idx": offset,
                    "show_all_topics": 0,
                    "search_source": "Normal",
                }

                url = f"{self.SEARCH_API}?{urlencode(params)}"

                # Make request with API headers
                headers = {}
                if self.anti_detect:
                    headers = self.anti_detect.get_api_headers("zhihu")

                # Add Zhihu-specific headers
                headers.update({
                    "x-requested-with": "fetch",
                    "x-zse-93": self._x_zse_96_key,
                })

                response = await self._request(url, headers=headers)

                if not isinstance(response, dict):
                    raise ParseException("Invalid response format from Zhihu search")

                # Parse search results
                data = response.get("data", [])
                if not data:
                    break

                for item in data:
                    parsed = self._parse_search_item(item, query)
                    if parsed and self._is_within_time_range(parsed, time_range):
                        items.append(parsed)
                        if len(items) >= limit:
                            break

                # Check pagination
                paging = response.get("paging", {})
                if paging.get("is_end", True):
                    break

                offset += page_size

            return CrawlResult.success(
                platform=self.platform_name,
                items=items[:limit],
                total_found=len(items),
                has_more=len(items) >= limit,
            )

        except CrawlerException:
            raise
        except Exception as e:
            return CrawlResult.failure(
                platform=self.platform_name,
                error=f"Search failed: {str(e)}"
            )

    async def get_detail(self, item_id: str) -> Optional[CrawlItem]:
        """
        Get detailed content for a Zhihu item.

        Args:
            item_id: Item ID in format "type:id" (e.g., "answer:123456", "article:789")

        Returns:
            CrawlItem with full details, or None if not found
        """
        try:
            # Parse item ID
            parts = item_id.split(":")
            if len(parts) != 2:
                return None

            item_type, type_id = parts

            if item_type == "answer":
                return await self._get_answer_detail(type_id)
            elif item_type == "article":
                return await self._get_article_detail(type_id)
            elif item_type == "question":
                return await self._get_question_answers(type_id)
            else:
                return None

        except Exception:
            return None

    async def _get_answer_detail(self, answer_id: str) -> Optional[CrawlItem]:
        """Fetch answer details."""
        url = self.ANSWER_API.format(aid=answer_id)

        headers = {}
        if self.anti_detect:
            headers = self.anti_detect.get_api_headers("zhihu")

        response = await self._request(url, headers=headers)

        if not isinstance(response, dict):
            return None

        return self._parse_answer(response)

    async def _get_article_detail(self, article_id: str) -> Optional[CrawlItem]:
        """Fetch article details."""
        url = self.ARTICLE_API.format(aid=article_id)

        headers = {}
        if self.anti_detect:
            headers = self.anti_detect.get_api_headers("zhihu")

        response = await self._request(url, headers=headers)

        if not isinstance(response, dict):
            return None

        return self._parse_article(response)

    async def _get_question_answers(self, question_id: str) -> Optional[CrawlItem]:
        """Fetch question and its top answer."""
        url = self.QUESTION_API.format(qid=question_id)

        headers = {}
        if self.anti_detect:
            headers = self.anti_detect.get_api_headers("zhihu")

        response = await self._request(url, headers=headers)

        if not isinstance(response, dict):
            return None

        # Get first answer from feed
        data = response.get("data", [])
        if data:
            first_answer = data[0].get("target", {})
            return self._parse_answer(first_answer)

        return None

    def _parse_search_item(self, item: Dict[str, Any], query: str) -> Optional[CrawlItem]:
        """Parse a search result item."""
        try:
            item_type = item.get("type")
            obj = item.get("object", {}) or item.get("highlight", {})

            if not obj:
                return None

            # Extract based on content type
            if item_type == "search_result":
                # This is a wrapper, get the actual object
                obj = item.get("object", {})
                item_type = obj.get("type", "answer")

            content_id = str(obj.get("id", ""))
            if not content_id:
                return None

            # Generate unified ID
            unified_id = f"{item_type}:{content_id}"

            # Extract content
            title = self._clean_html(obj.get("title", "") or obj.get("question", {}).get("title", ""))
            content = self._clean_html(obj.get("content", "") or obj.get("excerpt", ""))

            # Extract author
            author = obj.get("author", {}) or {}
            author_name = author.get("name", "")
            author_id = str(author.get("id", ""))

            # Extract URL
            url = obj.get("url", "")
            if not url and item_type == "answer":
                question_id = obj.get("question", {}).get("id")
                if question_id:
                    url = f"https://www.zhihu.com/question/{question_id}/answer/{content_id}"
            elif not url and item_type == "article":
                url = f"https://zhuanlan.zhihu.com/p/{content_id}"

            # Extract metrics
            metrics = {
                "voteup_count": obj.get("voteup_count", 0),
                "comment_count": obj.get("comment_count", 0),
            }

            # Extract timestamp
            created_time = obj.get("created_time") or obj.get("created")
            published_at = None
            if created_time:
                if isinstance(created_time, int):
                    published_at = datetime.fromtimestamp(created_time).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    published_at = str(created_time)

            return CrawlItem(
                id=unified_id,
                platform=self.platform_name,
                title=title or f"知乎{item_type}",
                content=content,
                summary=content[:200] if content else None,
                author_name=author_name,
                author_id=author_id,
                url=url,
                published_at=published_at,
                metrics=metrics,
                raw_data=obj,
            )

        except Exception:
            return None

    def _parse_answer(self, data: Dict[str, Any]) -> Optional[CrawlItem]:
        """Parse an answer object."""
        try:
            answer_id = str(data.get("id", ""))
            if not answer_id:
                return None

            question = data.get("question", {}) or {}
            title = question.get("title", "")

            content = self._clean_html(data.get("content", ""))
            author = data.get("author", {}) or {}

            question_id = question.get("id")
            url = f"https://www.zhihu.com/question/{question_id}/answer/{answer_id}" if question_id else ""

            created_time = data.get("created_time")
            published_at = datetime.fromtimestamp(created_time).strftime("%Y-%m-%d %H:%M:%S") if created_time else None

            return CrawlItem(
                id=f"answer:{answer_id}",
                platform=self.platform_name,
                title=title,
                content=content,
                summary=content[:200] if content else None,
                author_name=author.get("name", ""),
                author_id=str(author.get("id", "")),
                url=url,
                published_at=published_at,
                metrics={
                    "voteup_count": data.get("voteup_count", 0),
                    "comment_count": data.get("comment_count", 0),
                    "thanks_count": data.get("thanks_count", 0),
                },
                raw_data=data,
            )
        except Exception:
            return None

    def _parse_article(self, data: Dict[str, Any]) -> Optional[CrawlItem]:
        """Parse an article object."""
        try:
            article_id = str(data.get("id", ""))
            if not article_id:
                return None

            title = data.get("title", "")
            content = self._clean_html(data.get("content", ""))
            author = data.get("author", {}) or {}

            created_time = data.get("created")
            published_at = datetime.fromtimestamp(created_time).strftime("%Y-%m-%d %H:%M:%S") if created_time else None

            return CrawlItem(
                id=f"article:{article_id}",
                platform=self.platform_name,
                title=title,
                content=content,
                summary=content[:200] if content else None,
                author_name=author.get("name", ""),
                author_id=str(author.get("id", "")),
                url=f"https://zhuanlan.zhihu.com/p/{article_id}",
                published_at=published_at,
                metrics={
                    "voteup_count": data.get("voteup_count", 0),
                    "comment_count": data.get("comment_count", 0),
                    "liked_count": data.get("liked_count", 0),
                },
                raw_data=data,
            )
        except Exception:
            return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        clean = clean.replace("&nbsp;", " ")
        clean = clean.replace("&lt;", "<")
        clean = clean.replace("&gt;", ">")
        clean = clean.replace("&amp;", "&")
        clean = clean.replace("&quot;", '"')
        # Clean up whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def _is_within_time_range(self, item: CrawlItem, time_range: str) -> bool:
        """Check if item is within the specified time range."""
        if not item.published_at:
            return True  # No date info, include it

        try:
            days = self._parse_time_range(time_range)
            cutoff = datetime.now() - timedelta(days=days)

            # Parse published_at
            published = datetime.strptime(item.published_at, "%Y-%m-%d %H:%M:%S")
            return published >= cutoff
        except Exception:
            return True  # On parse error, include it

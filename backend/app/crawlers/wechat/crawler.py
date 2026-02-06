"""
WeChat Crawler

Crawls content from WeChat Official Accounts (微信公众号) via Sogou search.
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


class WeChatCrawler(BaseCrawler):
    """
    WeChat Official Accounts crawler.

    Uses Sogou WeChat search (weixin.sogou.com) to find public articles.

    Note: WeChat has strong anti-crawling measures. This crawler uses
    Sogou's public search interface which is more accessible.
    """

    # Sogou WeChat search endpoints
    SEARCH_URL = "https://weixin.sogou.com/weixin"
    ARTICLE_URL = "https://weixin.sogou.com/link"

    # Search types
    SEARCH_TYPE_ARTICLE = 2  # Article search
    SEARCH_TYPE_ACCOUNT = 1  # Account search

    def __init__(
        self,
        proxy_pool: Optional[ProxyPool] = None,
        anti_detect: Optional[AntiDetect] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        super().__init__(proxy_pool, anti_detect, rate_limiter)

    @property
    def platform_name(self) -> str:
        return "wechat"

    @property
    def display_name(self) -> str:
        return "微信公众号"

    async def search(
        self,
        query: str,
        time_range: str = "7d",
        limit: int = 10,
    ) -> CrawlResult:
        """
        Search WeChat articles via Sogou.

        Args:
            query: Search keywords
            time_range: Time range filter (1d, 7d, 30d, 90d)
            limit: Maximum number of results

        Returns:
            CrawlResult with search results
        """
        try:
            items = []
            page = 1
            page_size = 10  # Sogou default

            # Convert time_range to Sogou's inttime parameter
            inttime = self._get_inttime(time_range)

            while len(items) < limit:
                # Build search URL
                params = {
                    "type": self.SEARCH_TYPE_ARTICLE,
                    "query": query,
                    "ie": "utf8",
                    "page": page,
                }

                if inttime:
                    params["inttime"] = inttime

                url = f"{self.SEARCH_URL}?{urlencode(params)}"

                # Make request
                headers = {}
                if self.anti_detect:
                    headers = self.anti_detect.get_headers("wechat")

                response = await self._request(url, headers=headers)

                if not isinstance(response, str):
                    raise ParseException("Invalid response format from Sogou")

                # Parse HTML results
                page_items = self._parse_search_page(response, query)

                if not page_items:
                    break

                items.extend(page_items)

                # Check if we have enough items
                if len(page_items) < page_size:
                    break

                page += 1

                # Limit to 5 pages max
                if page > 5:
                    break

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
        Get detailed content for a WeChat article.

        Args:
            item_id: Article ID (Sogou link ID or direct URL hash)

        Returns:
            CrawlItem with full details, or None if not found

        Note: Getting full article content requires following Sogou's
        temporary link, which may require additional anti-detection measures.
        """
        # WeChat articles through Sogou use temporary links
        # Full content extraction requires browser automation
        # For now, return None and rely on search results' excerpts
        return None

    def _get_inttime(self, time_range: str) -> Optional[int]:
        """
        Convert time range to Sogou's inttime parameter.

        inttime values:
        - 1: 1 day
        - 2: 1 week
        - 3: 1 month
        - 4: 1 year
        """
        mapping = {
            "1d": 1,
            "7d": 2,
            "30d": 3,
            "90d": 4,
        }
        return mapping.get(time_range)

    def _parse_search_page(self, html: str, query: str) -> List[CrawlItem]:
        """Parse Sogou search result page HTML."""
        items = []

        try:
            # Find all article items (news-box elements)
            # Pattern: <div class="txt-box">...</div>
            article_pattern = r'<div class="txt-box">(.*?)</div>\s*</li>'
            article_matches = re.findall(article_pattern, html, re.DOTALL)

            # Alternative pattern for different HTML structure
            if not article_matches:
                article_pattern = r'<li[^>]*id="sogou_vr_\d+_box[^>]*"[^>]*>(.*?)</li>'
                article_matches = re.findall(article_pattern, html, re.DOTALL)

            for i, match in enumerate(article_matches):
                item = self._parse_article_item(match, i, query)
                if item:
                    items.append(item)

        except Exception:
            pass

        return items

    def _parse_article_item(self, html: str, index: int, query: str) -> Optional[CrawlItem]:
        """Parse a single article item from search results."""
        try:
            # Extract title
            title_match = re.search(r'<a[^>]*target="_blank"[^>]*>(.*?)</a>', html, re.DOTALL)
            title = ""
            url = ""
            if title_match:
                title = self._clean_html(title_match.group(1))
                # Extract URL
                url_match = re.search(r'href="([^"]+)"', title_match.group(0))
                if url_match:
                    url = url_match.group(1)

            if not title:
                return None

            # Extract content/excerpt
            content_match = re.search(r'<p class="txt-info"[^>]*>(.*?)</p>', html, re.DOTALL)
            content = ""
            if content_match:
                content = self._clean_html(content_match.group(1))

            # Extract account name (author)
            account_match = re.search(r'<a[^>]*class="account"[^>]*>(.*?)</a>', html, re.DOTALL)
            author_name = ""
            if account_match:
                author_name = self._clean_html(account_match.group(1))

            # Alternative author extraction
            if not author_name:
                account_match = re.search(r'<span class="s-p"[^>]*>(.*?)</span>', html)
                if account_match:
                    author_name = self._clean_html(account_match.group(1))

            # Extract timestamp
            time_match = re.search(r'(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)', html)
            published_at = None
            if time_match:
                date_str = time_match.group(1)
                # Normalize date format
                date_str = date_str.replace("年", "-").replace("月", "-").replace("日", "")
                try:
                    published_at = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

            # Generate unique ID based on URL or title
            item_id = hashlib.md5(f"{url or title}".encode()).hexdigest()[:16]

            return CrawlItem(
                id=f"wechat:{item_id}",
                platform=self.platform_name,
                title=title,
                content=content,
                summary=content[:200] if content else None,
                author_name=author_name,
                author_id=None,  # WeChat doesn't expose account IDs in Sogou
                url=url,
                published_at=published_at,
                metrics={},  # Sogou doesn't show article metrics
                raw_data={"html_snippet": html[:500]},
            )

        except Exception:
            return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and clean text."""
        if not text:
            return ""

        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)

        # Remove em tags from highlighting
        clean = re.sub(r'</?em>', '', clean)

        # Decode HTML entities
        clean = clean.replace("&nbsp;", " ")
        clean = clean.replace("&lt;", "<")
        clean = clean.replace("&gt;", ">")
        clean = clean.replace("&amp;", "&")
        clean = clean.replace("&quot;", '"')
        clean = clean.replace("&#39;", "'")

        # Clean up whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()

        return clean


class WeChatAccountCrawler(WeChatCrawler):
    """
    Specialized crawler for WeChat Official Account profiles.

    Inherits from WeChatCrawler but searches for accounts instead of articles.
    """

    async def search_accounts(
        self,
        query: str,
        limit: int = 10,
    ) -> CrawlResult:
        """
        Search for WeChat Official Accounts.

        Args:
            query: Account name or keywords
            limit: Maximum number of results

        Returns:
            CrawlResult with account information
        """
        try:
            items = []
            page = 1

            while len(items) < limit:
                params = {
                    "type": self.SEARCH_TYPE_ACCOUNT,
                    "query": query,
                    "ie": "utf8",
                    "page": page,
                }

                url = f"{self.SEARCH_URL}?{urlencode(params)}"

                headers = {}
                if self.anti_detect:
                    headers = self.anti_detect.get_headers("wechat")

                response = await self._request(url, headers=headers)

                if not isinstance(response, str):
                    break

                page_items = self._parse_account_page(response)

                if not page_items:
                    break

                items.extend(page_items)
                page += 1

                if page > 3:  # Limit pages
                    break

            return CrawlResult.success(
                platform=self.platform_name,
                items=items[:limit],
                total_found=len(items),
            )

        except Exception as e:
            return CrawlResult.failure(
                platform=self.platform_name,
                error=f"Account search failed: {str(e)}"
            )

    def _parse_account_page(self, html: str) -> List[CrawlItem]:
        """Parse account search results."""
        items = []

        try:
            # Find account items
            account_pattern = r'<li[^>]*class="news-box"[^>]*>(.*?)</li>'
            matches = re.findall(account_pattern, html, re.DOTALL)

            for match in matches:
                item = self._parse_account_item(match)
                if item:
                    items.append(item)

        except Exception:
            pass

        return items

    def _parse_account_item(self, html: str) -> Optional[CrawlItem]:
        """Parse a single account item."""
        try:
            # Extract account name
            name_match = re.search(r'<p class="tit"[^>]*>(.*?)</p>', html, re.DOTALL)
            name = ""
            if name_match:
                name = self._clean_html(name_match.group(1))

            if not name:
                return None

            # Extract WeChat ID
            wechat_id_match = re.search(r'微信号[：:]\s*([a-zA-Z0-9_-]+)', html)
            wechat_id = ""
            if wechat_id_match:
                wechat_id = wechat_id_match.group(1)

            # Extract description
            desc_match = re.search(r'<span class="sp-txt"[^>]*>(.*?)</span>', html, re.DOTALL)
            description = ""
            if desc_match:
                description = self._clean_html(desc_match.group(1))

            # Generate ID
            item_id = hashlib.md5(f"{name}:{wechat_id}".encode()).hexdigest()[:16]

            return CrawlItem(
                id=f"wechat_account:{item_id}",
                platform=self.platform_name,
                title=name,
                content=description,
                summary=description[:200] if description else None,
                author_name=name,
                author_id=wechat_id,
                url=None,
                published_at=None,
                metrics={},
                raw_data={"wechat_id": wechat_id},
            )

        except Exception:
            return None

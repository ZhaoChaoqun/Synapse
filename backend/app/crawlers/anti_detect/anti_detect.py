"""
Anti-Detection Module

Provides browser fingerprint randomization to avoid detection.
"""

import random
from typing import Dict, List, Optional


class AntiDetect:
    """
    Anti-detection module for crawlers.

    Provides:
    - Random User-Agent rotation
    - Browser fingerprint headers
    - Platform-specific cookie management
    """

    # Common User-Agent strings (updated for 2026)
    USER_AGENTS: List[str] = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Chrome on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Firefox on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
        # Safari on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    ]

    # Accept-Language variations
    ACCEPT_LANGUAGES: List[str] = [
        "zh-CN,zh;q=0.9,en;q=0.8",
        "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    ]

    # Platform-specific referer patterns
    REFERERS: Dict[str, List[str]] = {
        "zhihu": [
            "https://www.zhihu.com/",
            "https://www.zhihu.com/search",
            "https://www.zhihu.com/hot",
        ],
        "wechat": [
            "https://weixin.sogou.com/",
            "https://mp.weixin.qq.com/",
        ],
        "xiaohongshu": [
            "https://www.xiaohongshu.com/",
            "https://www.xiaohongshu.com/explore",
        ],
        "douyin": [
            "https://www.douyin.com/",
            "https://www.douyin.com/search",
        ],
    }

    def __init__(self):
        self._current_ua: Optional[str] = None
        self._cookie_store: Dict[str, Dict[str, str]] = {}

    def get_headers(self, platform: Optional[str] = None) -> Dict[str, str]:
        """
        Get randomized browser headers.

        Args:
            platform: Optional platform name for specific headers

        Returns:
            Dict of HTTP headers
        """
        headers = {
            "User-Agent": self._get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        # Add platform-specific referer
        if platform and platform in self.REFERERS:
            headers["Referer"] = random.choice(self.REFERERS[platform])

        return headers

    def get_api_headers(self, platform: Optional[str] = None) -> Dict[str, str]:
        """
        Get headers for API requests (JSON).

        Args:
            platform: Optional platform name

        Returns:
            Dict of HTTP headers for API requests
        """
        headers = {
            "User-Agent": self._get_user_agent(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        if platform and platform in self.REFERERS:
            headers["Referer"] = random.choice(self.REFERERS[platform])
            headers["Origin"] = self.REFERERS[platform][0].rstrip("/")

        return headers

    def _get_user_agent(self) -> str:
        """Get a random User-Agent (with some session persistence)."""
        # 70% chance to reuse current UA for session consistency
        if self._current_ua and random.random() < 0.7:
            return self._current_ua

        self._current_ua = random.choice(self.USER_AGENTS)
        return self._current_ua

    def rotate_user_agent(self) -> str:
        """Force rotation to a new User-Agent."""
        self._current_ua = random.choice(self.USER_AGENTS)
        return self._current_ua

    def get_cookies(self, platform: str) -> Dict[str, str]:
        """
        Get cookies for a platform.

        Args:
            platform: Platform name

        Returns:
            Dict of cookies
        """
        return self._cookie_store.get(platform, {})

    def set_cookies(self, platform: str, cookies: Dict[str, str]) -> None:
        """
        Store cookies for a platform.

        Args:
            platform: Platform name
            cookies: Cookies to store
        """
        if platform not in self._cookie_store:
            self._cookie_store[platform] = {}
        self._cookie_store[platform].update(cookies)

    def clear_cookies(self, platform: Optional[str] = None) -> None:
        """
        Clear cookies.

        Args:
            platform: Platform to clear, or None for all
        """
        if platform:
            self._cookie_store.pop(platform, None)
        else:
            self._cookie_store.clear()


# Global instance
_anti_detect: Optional[AntiDetect] = None


def get_anti_detect() -> AntiDetect:
    """Get the global AntiDetect instance."""
    global _anti_detect
    if _anti_detect is None:
        _anti_detect = AntiDetect()
    return _anti_detect

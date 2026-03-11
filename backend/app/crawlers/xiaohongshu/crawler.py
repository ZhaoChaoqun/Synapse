"""Playwright-based Xiaohongshu (Little Red Book) crawler with screenshot feedback."""

import asyncio
import base64
import os
import subprocess
import urllib.parse
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from .cookie_manager import CookieManager


def get_chrome_user_data_dir() -> Optional[str]:
    """Get the default Chrome user data directory based on OS."""
    system = os.uname().sysname if hasattr(os, 'uname') else 'Windows'

    if system == "Darwin":  # macOS
        path = Path.home() / "Library/Application Support/Google/Chrome"
    elif system == "Linux":
        path = Path.home() / ".config/google-chrome"
    else:  # Windows
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        path = Path(local_app_data) / "Google/Chrome/User Data"

    return str(path) if path.exists() else None


def _get_chrome_debug_port() -> Optional[int]:
    """Check if Chrome is running with remote debugging enabled and return the port."""
    try:
        result = subprocess.run(
            ["lsof", "-i", "TCP:9222", "-sTCP:LISTEN"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            return 9222
    except Exception:
        pass
    return None


def _extract_cookies_from_chrome_db() -> Optional[dict]:
    """Extract xiaohongshu cookies from Chrome's local SQLite database.

    On macOS, Chrome stores cookies in an encrypted SQLite database.
    We copy the DB file and read the cookie names/domains (unencrypted fields)
    to check if xiaohongshu session cookies exist, then use the raw encrypted
    storage state to pass to Playwright via the saved cookies approach.

    Note: This does NOT decrypt cookie values - it only checks for cookie existence.
    For actual cookie values, we use the interactive login or persistent context approach.
    """
    return None  # Cookie extraction from Chrome DB requires decryption; skip for now


class XiaohongshuCrawler:
    """Crawler for Xiaohongshu using Playwright browser automation.

    Features:
    - Real browser automation for authentic scraping
    - Cookie-based login persistence
    - Screenshot capture for real-time feedback
    - Async generator for streaming results
    - Option to reuse local Chrome login state
    """

    def __init__(
        self,
        on_screenshot: Optional[Callable[[str, str], None]] = None,
        headless: bool = True,
        use_local_chrome: bool = True,
    ):
        """Initialize the crawler.

        Args:
            on_screenshot: Callback function (message, base64_image) called when taking screenshots
            headless: Whether to run browser in headless mode
            use_local_chrome: Whether to try reusing local Chrome's login state
        """
        self.on_screenshot = on_screenshot
        self.headless = headless
        self.use_local_chrome = use_local_chrome
        self._playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def _capture_and_emit(self, message: str) -> None:
        """Take a screenshot and emit it via callback."""
        if self.page and self.on_screenshot:
            try:
                screenshot = await self.page.screenshot(type="jpeg", quality=50)
                b64_image = base64.b64encode(screenshot).decode()
                self.on_screenshot(message, b64_image)
            except Exception as e:
                print(f"Screenshot error: {e}")

    async def _check_login_status_on_page(self) -> bool:
        """Check login status by examining page elements.

        This is more reliable than just checking cookies, as cookies may be
        expired or invalid even if they exist.

        Returns:
            True if logged in, False if login modal/popup is visible or not logged in
        """
        if not self.page:
            return False

        try:
            # First check: Is login modal/popup visible? If yes, NOT logged in
            login_modal_selectors = [
                ".login-container",
                "[class*='login-modal']",
                "[class*='login-popup']",
                ".qrcode-login",
                "[class*='qrcode']",
                # Login form indicators
                "input[placeholder*='手机号']",
                "input[placeholder*='验证码']",
                "[class*='phone-login']",
                # Modal overlay with login content
                ".modal-content:has([class*='login'])",
            ]

            for selector in login_modal_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            # Login modal is visible, user is NOT logged in
                            return False
                except:
                    continue

            # Second check: Look for logged-in user indicators
            logged_in_selectors = [
                # User avatar in header
                ".user-avatar",
                "[class*='avatar']",
                # User info section
                "[class*='user-info']",
                ".side-bar .user",
                # "我" tab or user profile link
                "a[href*='/user/profile']",
                "[class*='user-name']",
            ]

            for selector in logged_in_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            # User indicator found, user IS logged in
                            return True
                except:
                    continue

            # Third check: Cookie-based fallback (less reliable)
            if self.context:
                storage = await self.context.storage_state()
                if CookieManager.is_logged_in(storage):
                    # Cookies exist, but we couldn't confirm via page elements
                    # Be conservative: if no login modal visible and cookies exist, assume logged in
                    return True

            # Default: not logged in
            return False

        except Exception as e:
            print(f"Login status check error: {e}")
            return False

    async def start(self) -> bool:
        """Start browser and load cookies.

        Attempts to reuse login state in the following order:
        1. Try to use local Chrome's cookies via persistent context (requires Chrome closed)
        2. Try to connect to Chrome via CDP if debugging port is available
        3. Try to load previously saved cookies into standalone Chromium
        4. Start with fresh browser (no login)

        Returns:
            True if logged in, False otherwise
        """
        self._playwright = await async_playwright().start()

        chrome_user_data = get_chrome_user_data_dir() if self.use_local_chrome else None
        connected = False

        if chrome_user_data:
            # Stage 1: Try persistent context (requires Chrome to be closed)
            try:
                self.context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=chrome_user_data,
                    headless=self.headless,
                    viewport={"width": 1280, "height": 800},
                    channel="chrome",
                )
                self.page = await self.context.new_page()
                connected = True
                await self._capture_and_emit("正在使用本地 Chrome 浏览器...")
            except Exception as e:
                print(f"无法使用本地 Chrome (可能正在使用中): {e}")

            # Stage 2: Try CDP connection if Chrome has remote debugging enabled
            if not connected:
                debug_port = _get_chrome_debug_port()
                if debug_port:
                    try:
                        self.browser = await self._playwright.chromium.connect_over_cdp(
                            f"http://127.0.0.1:{debug_port}"
                        )
                        contexts = self.browser.contexts
                        if contexts:
                            self.context = contexts[0]
                            self.page = await self.context.new_page()
                        else:
                            self.context = await self.browser.new_context(
                                viewport={"width": 1280, "height": 800},
                            )
                            self.page = await self.context.new_page()
                        connected = True
                        await self._capture_and_emit("已通过远程调试连接到 Chrome...")
                    except Exception as e:
                        print(f"CDP 连接失败: {e}")

        if not connected:
            # Stage 3 & 4: Fall back to standalone Chromium with saved cookies
            self.browser = await self._playwright.chromium.launch(headless=self.headless)

            storage_state = CookieManager.load_cookies()
            if storage_state:
                self.context = await self.browser.new_context(
                    storage_state=storage_state,
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
                await self._capture_and_emit("正在使用已保存的登录状态...")
            else:
                self.context = await self.browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
                await self._capture_and_emit("正在启动浏览器...")

            self.page = await self.context.new_page()

        # Visit Xiaohongshu to check login status
        await self.page.goto("https://www.xiaohongshu.com", wait_until="networkidle")
        await self._capture_and_emit("正在打开小红书...")
        await asyncio.sleep(2)

        # Check login status - use page-level detection (more reliable than cookies)
        is_logged_in = await self._check_login_status_on_page()

        if not is_logged_in:
            await self._capture_and_emit(
                "⚠️ 未登录小红书，无法获取完整内容。\n"
                "请先在本地 Chrome 浏览器中登录 xiaohongshu.com，然后关闭 Chrome 重试。\n"
                "或调用 POST /api/v1/crawler/xiaohongshu/login 进行交互式登录。"
            )
            return False

        await self._capture_and_emit("✓ 已登录小红书")
        return True

    async def search(self, query: str, limit: int = 10) -> AsyncGenerator[dict, None]:
        """Search for notes on Xiaohongshu.

        Args:
            query: Search keyword
            limit: Maximum number of results to fetch

        Yields:
            Note data dictionaries
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        # Build search URL
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded_query}&source=web_search_result_notes"

        await self.page.goto(search_url, wait_until="networkidle")
        await self._capture_and_emit(f"正在搜索 '{query}'...")
        await asyncio.sleep(3)

        # Wait for search results to load
        try:
            # Try different selectors for note items
            selectors = [
                "section.note-item",
                "[data-v-a264b01a].note-item",
                ".feeds-container .note-item",
                "a[href*='/explore/']",
            ]

            note_selector = None
            for selector in selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    note_selector = selector
                    break
                except:
                    continue

            if not note_selector:
                await self._capture_and_emit("⚠️ 未找到搜索结果")
                return

            await self._capture_and_emit("搜索结果已加载")

        except Exception as e:
            await self._capture_and_emit(f"⚠️ 加载搜索结果超时: {e}")
            return

        # Get note links
        note_links = await self.page.query_selector_all(note_selector)
        count = 0

        for i, item in enumerate(note_links[:limit]):
            try:
                # Get the href for navigation
                href = await item.get_attribute("href")
                if not href:
                    # Try to find anchor inside
                    anchor = await item.query_selector("a")
                    if anchor:
                        href = await anchor.get_attribute("href")

                if not href:
                    continue

                # Build full URL
                if href.startswith("/"):
                    note_url = f"https://www.xiaohongshu.com{href}"
                else:
                    note_url = href

                # Open note in new tab
                note_page = await self.context.new_page()
                await note_page.goto(note_url, wait_until="networkidle")
                await asyncio.sleep(2)

                count += 1

                # Extract note data
                title = ""
                author = ""
                content = ""
                likes = "0"

                # Try to get title
                title_selectors = [
                    "#detail-title",
                    ".title",
                    "h1",
                    "[class*='title']",
                ]
                for sel in title_selectors:
                    try:
                        el = await note_page.query_selector(sel)
                        if el:
                            title = await el.inner_text()
                            if title:
                                break
                    except:
                        continue

                # Try to get author
                author_selectors = [
                    ".user-name",
                    ".username",
                    "[class*='author'] .name",
                    "[class*='user'] .name",
                ]
                for sel in author_selectors:
                    try:
                        el = await note_page.query_selector(sel)
                        if el:
                            author = await el.inner_text()
                            if author:
                                break
                    except:
                        continue

                # Try to get content
                content_selectors = [
                    "#detail-desc",
                    ".note-content",
                    ".content",
                    "[class*='desc']",
                ]
                for sel in content_selectors:
                    try:
                        el = await note_page.query_selector(sel)
                        if el:
                            content = await el.inner_text()
                            if content:
                                break
                    except:
                        continue

                # Try to get likes
                likes_selectors = [
                    "[class*='like'] span",
                    ".like-count",
                    "[class*='like-wrapper'] span",
                ]
                for sel in likes_selectors:
                    try:
                        el = await note_page.query_selector(sel)
                        if el:
                            likes = await el.inner_text()
                            if likes:
                                break
                    except:
                        continue

                # Take screenshot of the note
                if self.page:
                    # Temporarily switch to note page for screenshot
                    self.page = note_page
                    await self._capture_and_emit(f"正在阅读第 {count} 篇笔记: {title[:20] if title else '未知标题'}...")

                yield {
                    "title": title or "无标题",
                    "author": author or "未知作者",
                    "content": content[:500] if content else "",  # Limit content length
                    "likes": likes,
                    "url": note_url,
                    "source": "xiaohongshu",
                }

                await note_page.close()

            except Exception as e:
                print(f"Error processing note {i}: {e}")
                continue

        await self._capture_and_emit(f"✓ 已收集 {count} 篇笔记")

    async def login_interactive(self) -> bool:
        """Open visible browser for manual login.

        Returns:
            True if login successful, False otherwise
        """
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        await page.goto("https://www.xiaohongshu.com")

        print("=" * 50)
        print("请在浏览器中登录小红书...")
        print("登录成功后，系统会自动保存 cookies")
        print("最长等待时间: 5 分钟")
        print("=" * 50)

        try:
            # Wait for login indicator (user avatar or profile element)
            # These are common indicators that user is logged in
            login_indicators = [
                ".user-avatar",
                "[class*='avatar']",
                "[class*='user-info']",
                ".side-bar .user",
            ]

            for _ in range(300):  # Check every second for 5 minutes
                await asyncio.sleep(1)
                storage = await context.storage_state()
                if CookieManager.is_logged_in(storage):
                    # Save cookies
                    CookieManager.save_cookies(storage)
                    print("✓ 登录成功，cookies 已保存")
                    await browser.close()
                    await playwright.stop()
                    return True

            print("✗ 登录超时")
            return False

        except Exception as e:
            print(f"✗ 登录失败: {e}")
            return False

        finally:
            await browser.close()
            await playwright.stop()

    async def close(self) -> None:
        """Close browser and save cookies if logged in."""
        if self.browser:
            if self.context:
                try:
                    storage = await self.context.storage_state()
                    # Only save cookies if we're actually logged in
                    # to avoid overwriting valid cookies with empty session
                    if CookieManager.is_logged_in(storage):
                        CookieManager.save_cookies(storage)
                except:
                    pass
            await self.browser.close()

        if self._playwright:
            await self._playwright.stop()

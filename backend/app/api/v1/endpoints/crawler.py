"""Crawler management endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.crawlers.xiaohongshu import CookieManager, XiaohongshuCrawler

router = APIRouter(prefix="/crawler", tags=["crawler"])


class LoginStatusResponse(BaseModel):
    """Response for login status check."""
    platform: str
    logged_in: bool
    message: str


class LoginResponse(BaseModel):
    """Response for login trigger."""
    success: bool
    message: str


@router.get("/xiaohongshu/login-status", response_model=LoginStatusResponse)
async def get_xiaohongshu_login_status():
    """Check if user is logged in to Xiaohongshu.

    Returns login status based on saved cookies.
    """
    storage = CookieManager.load_cookies()
    if storage and CookieManager.is_logged_in(storage):
        return LoginStatusResponse(
            platform="xiaohongshu",
            logged_in=True,
            message="已登录小红书",
        )
    return LoginStatusResponse(
        platform="xiaohongshu",
        logged_in=False,
        message="未登录小红书，请先登录以获取完整内容",
    )


@router.post("/xiaohongshu/login", response_model=LoginResponse)
async def trigger_xiaohongshu_login():
    """Trigger interactive login for Xiaohongshu.

    Opens a visible browser window for manual login.
    User should complete login in the browser.
    Cookies will be saved automatically upon successful login.
    """
    try:
        crawler = XiaohongshuCrawler(headless=False)
        success = await crawler.login_interactive()

        if success:
            return LoginResponse(
                success=True,
                message="登录成功，cookies 已保存",
            )
        return LoginResponse(
            success=False,
            message="登录失败或超时",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录过程出错: {str(e)}")


@router.delete("/xiaohongshu/logout", response_model=LoginResponse)
async def logout_xiaohongshu():
    """Clear saved Xiaohongshu cookies."""
    try:
        CookieManager.clear_cookies()
        return LoginResponse(
            success=True,
            message="已退出登录，cookies 已清除",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"退出登录出错: {str(e)}")

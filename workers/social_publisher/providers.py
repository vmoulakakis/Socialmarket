from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserContext, sync_playwright


class PublishError(RuntimeError):
    pass


class AssistedProvider:
    platform = "browser"
    home_url = ""
    composer_url = ""

    def __init__(self, state: dict[str, Any], *, headless: bool = True) -> None:
        self.state = state
        self.headless = headless

    def _open(self):
        manager = sync_playwright().start()
        browser = manager.chromium.launch(headless=self.headless)
        context = browser.new_context(storage_state=self.state, locale="en-US")
        return manager, browser, context

    def session_is_logged_in(self, context: BrowserContext) -> bool:
        raise NotImplementedError

    def prepare(self, payload: dict[str, Any], media_path: Path | None) -> dict[str, Any]:
        manager, browser, context = self._open()
        try:
            if not self.session_is_logged_in(context):
                raise PublishError(f"{self.platform}_session_expired")
            tags = payload.get("hashtags") or []
            caption = str(payload.get("caption") or "").strip()
            if isinstance(tags, list) and tags:
                caption = (caption + "\n" + " ".join(str(x) for x in tags)).strip()
            return {
                "status": "assisted",
                "platform": self.platform,
                "session_verified": True,
                "open_url": self.composer_url or self.home_url,
                "caption": caption,
                "media_path": str(media_path) if media_path else None,
                "tracking_url": payload.get("tracking_url"),
                "reason": "no_app_route_requires_user_final_publish",
            }
        finally:
            context.close()
            browser.close()
            manager.stop()


class InstagramProvider(AssistedProvider):
    platform = "instagram"
    home_url = "https://www.instagram.com/"
    composer_url = "https://www.instagram.com/"

    def session_is_logged_in(self, context: BrowserContext) -> bool:
        page = context.new_page()
        page.goto(self.home_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1000)
        return "/accounts/login" not in page.url and page.locator("input[name='username']").count() == 0


class TikTokProvider(AssistedProvider):
    platform = "tiktok"
    home_url = "https://www.tiktok.com/"
    composer_url = "https://www.tiktok.com/tiktokstudio/upload"

    def session_is_logged_in(self, context: BrowserContext) -> bool:
        page = context.new_page()
        page.goto(self.home_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1000)
        # TikTok changes its UI frequently; a saved session with authenticated cookies is
        # considered provisionally valid unless the page explicitly lands on a login route.
        return "/login" not in page.url


class FacebookProvider(AssistedProvider):
    platform = "facebook"
    home_url = "https://www.facebook.com/"
    composer_url = "https://www.facebook.com/"

    def session_is_logged_in(self, context: BrowserContext) -> bool:
        page = context.new_page()
        page.goto(self.home_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1000)
        return page.locator("input[name='email']").count() == 0


class LinkedInProvider(AssistedProvider):
    platform = "linkedin"
    home_url = "https://www.linkedin.com/feed/"
    composer_url = "https://www.linkedin.com/feed/?shareActive=true"

    def session_is_logged_in(self, context: BrowserContext) -> bool:
        page = context.new_page()
        page.goto(self.home_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1000)
        return "/login" not in page.url and page.locator("input[name='session_key']").count() == 0


def provider_for(platform: str, state: dict[str, Any], *, headless: bool = True) -> AssistedProvider:
    mapping = {
        "instagram": InstagramProvider,
        "tiktok": TikTokProvider,
        "facebook": FacebookProvider,
        "linkedin": LinkedInProvider,
    }
    platform = platform.lower().strip()
    if platform not in mapping:
        raise PublishError(f"unsupported_platform:{platform}")
    return mapping[platform](state, headless=headless)

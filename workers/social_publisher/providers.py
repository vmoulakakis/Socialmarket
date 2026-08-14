from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserContext, Page, sync_playwright


class PublishError(RuntimeError):
    pass


class ManualRequired(PublishError):
    pass


def _visible(locator) -> bool:
    try:
        return locator.count() > 0 and locator.first.is_visible()
    except Exception:
        return False


def _click_first(page: Page, selectors: list[str], timeout: int = 8000) -> bool:
    for selector in selectors:
        try:
            loc = page.locator(selector)
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=timeout)
                return True
        except Exception:
            continue
    return False


def _fill_first(page: Page, selectors: list[str], value: str) -> bool:
    for selector in selectors:
        try:
            loc = page.locator(selector)
            if loc.count() and loc.first.is_visible():
                node = loc.first
                try:
                    node.fill(value)
                except Exception:
                    node.click()
                    node.press("Control+A")
                    node.type(value, delay=5)
                return True
        except Exception:
            continue
    return False


class BrowserProvider:
    platform = "browser"

    def __init__(self, state: dict[str, Any], *, headless: bool = True) -> None:
        self.state = state
        self.headless = headless

    def _open(self):
        manager = sync_playwright().start()
        browser = manager.chromium.launch(headless=self.headless)
        context = browser.new_context(storage_state=self.state, locale="en-US")
        return manager, browser, context

    def verify_session(self, context: BrowserContext) -> dict[str, Any]:
        raise NotImplementedError

    def publish(self, payload: dict[str, Any], media_path: Path | None, *, dry_run: bool = False) -> dict[str, Any]:
        raise NotImplementedError


class InstagramBrowserProvider(BrowserProvider):
    platform = "instagram"

    def verify_session(self, context: BrowserContext) -> dict[str, Any]:
        page = context.new_page()
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        if "/accounts/login" in page.url or _visible(page.locator("input[name='username']")):
            raise PublishError("instagram_session_expired")
        return {"ok": True, "url": page.url}

    def publish(self, payload: dict[str, Any], media_path: Path | None, *, dry_run: bool = False) -> dict[str, Any]:
        if not media_path:
            raise PublishError("instagram_media_required")
        manager, browser, context = self._open()
        try:
            self.verify_session(context)
            if dry_run:
                return {"status": "verified", "platform": self.platform, "dry_run": True}
            page = context.new_page()
            page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1200)
            _click_first(
                page,
                [
                    "a[href='/create/select/']",
                    "[role='button']:has-text('Create')",
                    "[role='button']:has-text('Δημιουργία')",
                    "svg[aria-label='New post']",
                ],
            )
            page.wait_for_timeout(800)
            file_input = page.locator("input[type='file']")
            if not file_input.count():
                page.goto("https://www.instagram.com/create/select/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(800)
                file_input = page.locator("input[type='file']")
            if not file_input.count():
                raise PublishError("instagram_file_input_not_found")
            file_input.first.set_input_files(str(media_path))
            page.wait_for_timeout(1800)
            for _ in range(2):
                if _click_first(page, ["[role='button']:has-text('Next')", "[role='button']:has-text('Επόμενο')"]):
                    page.wait_for_timeout(900)
            caption = str(payload.get("caption") or "").strip()
            tags = payload.get("hashtags") or []
            if isinstance(tags, list) and tags:
                caption = (caption + "\n" + " ".join(str(x) for x in tags)).strip()
            if caption:
                _fill_first(
                    page,
                    [
                        "textarea[aria-label*='caption' i]",
                        "div[contenteditable='true'][aria-label*='caption' i]",
                        "div[contenteditable='true']",
                    ],
                    caption[:2200],
                )
            if payload.get("facebook_crosspost"):
                _click_first(page, ["label:has-text('Facebook')", "[role='switch'][aria-label*='Facebook' i]"])
            if not _click_first(page, ["[role='button']:has-text('Share')", "[role='button']:has-text('Κοινοποίηση')"], timeout=12000):
                raise PublishError("instagram_share_button_not_found")
            page.wait_for_timeout(3500)
            if _visible(page.locator("text=/error|try again/i")):
                raise PublishError("instagram_publish_ui_error")
            return {"status": "published", "platform": self.platform, "url": page.url}
        finally:
            context.close()
            browser.close()
            manager.stop()


class TikTokBrowserProvider(BrowserProvider):
    platform = "tiktok"

    def verify_session(self, context: BrowserContext) -> dict[str, Any]:
        page = context.new_page()
        page.goto("https://www.tiktok.com/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1200)
        if _visible(page.locator("text=/Log in/i")) and not _visible(page.locator("a[href*='/upload']")):
            raise PublishError("tiktok_session_may_be_expired")
        return {"ok": True, "url": page.url}

    def publish(self, payload: dict[str, Any], media_path: Path | None, *, dry_run: bool = False) -> dict[str, Any]:
        if not media_path:
            raise PublishError("tiktok_media_required")
        manager, browser, context = self._open()
        try:
            self.verify_session(context)
            if dry_run:
                return {"status": "verified", "platform": self.platform, "dry_run": True}
            page = context.new_page()
            page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)
            file_input = page.locator("input[type='file']")
            if not file_input.count():
                page.goto("https://www.tiktok.com/upload", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1500)
                file_input = page.locator("input[type='file']")
            if not file_input.count():
                raise PublishError("tiktok_file_input_not_found")
            file_input.first.set_input_files(str(media_path))
            page.wait_for_timeout(2500)
            caption = str(payload.get("caption") or "").strip()
            tags = payload.get("hashtags") or []
            if isinstance(tags, list) and tags:
                caption = (caption + " " + " ".join(str(x) for x in tags)).strip()
            if caption:
                _fill_first(
                    page,
                    [
                        "div[contenteditable='true'][data-e2e*='caption']",
                        "div[contenteditable='true'][aria-label*='caption' i]",
                        "div[contenteditable='true']",
                        "textarea",
                    ],
                    caption[:2200],
                )
            page.wait_for_timeout(1200)
            if not _click_first(
                page,
                [
                    "button:has-text('Post')",
                    "button:has-text('Publish')",
                    "[data-e2e='post_video_button']",
                ],
                timeout=12000,
            ):
                raise PublishError("tiktok_publish_button_not_found")
            page.wait_for_timeout(4000)
            return {"status": "published", "platform": self.platform, "url": page.url}
        finally:
            context.close()
            browser.close()
            manager.stop()


class FacebookBrowserProvider(BrowserProvider):
    platform = "facebook"

    def verify_session(self, context: BrowserContext) -> dict[str, Any]:
        page = context.new_page()
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1200)
        if _visible(page.locator("input[name='email']")):
            raise PublishError("facebook_session_expired")
        return {"ok": True, "url": page.url}

    def publish(self, payload: dict[str, Any], media_path: Path | None, *, dry_run: bool = False) -> dict[str, Any]:
        if os.getenv("SOCIAL_ENABLE_FACEBOOK_BROWSER_PUBLISH", "false").lower() not in {"1", "true", "yes"}:
            raise ManualRequired("facebook_browser_publish_disabled; prefer Instagram cross-post or enable explicitly")
        manager, browser, context = self._open()
        try:
            self.verify_session(context)
            if dry_run:
                return {"status": "verified", "platform": self.platform, "dry_run": True}
            page = context.new_page()
            target_url = str(payload.get("facebook_target_url") or "https://www.facebook.com/")
            page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            if not _click_first(
                page,
                [
                    "[role='button']:has-text(\"What's on your mind\")",
                    "[role='button']:has-text('Create post')",
                    "[role='button']:has-text('Δημιουργία δημοσίευσης')",
                ],
            ):
                raise PublishError("facebook_composer_not_found")
            page.wait_for_timeout(700)
            caption = str(payload.get("caption") or "").strip()
            if caption:
                _fill_first(page, ["div[contenteditable='true'][role='textbox']", "div[contenteditable='true']"], caption)
            if media_path:
                file_input = page.locator("input[type='file']")
                if file_input.count():
                    file_input.first.set_input_files(str(media_path))
                    page.wait_for_timeout(1200)
            if not _click_first(page, ["[role='button']:has-text('Post')", "[role='button']:has-text('Δημοσίευση')"], timeout=12000):
                raise PublishError("facebook_post_button_not_found")
            page.wait_for_timeout(3000)
            return {"status": "published", "platform": self.platform, "url": page.url}
        finally:
            context.close()
            browser.close()
            manager.stop()


class LinkedInAssistedProvider(BrowserProvider):
    platform = "linkedin"

    def verify_session(self, context: BrowserContext) -> dict[str, Any]:
        page = context.new_page()
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1000)
        if "/login" in page.url or _visible(page.locator("input[name='session_key']")):
            raise PublishError("linkedin_session_expired")
        return {"ok": True, "url": page.url}

    def publish(self, payload: dict[str, Any], media_path: Path | None, *, dry_run: bool = False) -> dict[str, Any]:
        # Deliberately fail closed: LinkedIn automation is kept user-controlled by default.
        return {
            "status": "assisted",
            "platform": self.platform,
            "open_url": "https://www.linkedin.com/feed/?shareActive=true",
            "caption": str(payload.get("caption") or ""),
            "media_path": str(media_path) if media_path else None,
            "reason": "final_publish_requires_user_action",
        }


def provider_for(platform: str, state: dict[str, Any], *, headless: bool = True) -> BrowserProvider:
    platform = platform.lower().strip()
    mapping = {
        "instagram": InstagramBrowserProvider,
        "tiktok": TikTokBrowserProvider,
        "facebook": FacebookBrowserProvider,
        "linkedin": LinkedInAssistedProvider,
    }
    if platform not in mapping:
        raise PublishError(f"unsupported_platform:{platform}")
    return mapping[platform](state, headless=headless)

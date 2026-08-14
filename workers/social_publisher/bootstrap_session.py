from __future__ import annotations

import argparse
from typing import Any

from playwright.sync_api import sync_playwright

from .common import SupabaseREST, encrypt_state


LOGIN_URLS = {
    "instagram": "https://www.instagram.com/accounts/login/",
    "tiktok": "https://www.tiktok.com/login",
    "facebook": "https://www.facebook.com/login/",
    "linkedin": "https://www.linkedin.com/login",
}


def pair(platform: str, label: str, handle: str | None) -> dict[str, Any]:
    if platform not in LOGIN_URLS:
        raise RuntimeError(f"unsupported platform: {platform}")

    print(f"Opening {platform} in a local Chromium window.")
    print("Log in normally. Complete any MFA/challenge in the browser.")
    print("No password is read or stored by this script.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(locale="en-US")
        page = context.new_page()
        page.goto(LOGIN_URLS[platform], wait_until="domcontentloaded", timeout=60000)
        input("After you are fully logged in, return to this terminal and press ENTER... ")
        state = context.storage_state()
        browser.close()

    encrypted_state, fingerprint = encrypt_state(state)
    db = SupabaseREST()
    rows = db.upsert(
        "social_session_accounts",
        {
            "platform": platform,
            "account_label": label,
            "account_handle": handle,
            "status": "paired",
            "publish_mode": "assisted",
            "auto_publish": False,
            "capabilities": {
                "session_verification": True,
                "assisted_publish": True,
                "unattended_publish": False,
            },
            "last_error": None,
        },
        on_conflict="platform,account_label",
    )
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("failed to create/update social_session_accounts")
    account = rows[0]
    db.upsert(
        "social_session_vault",
        {
            "account_id": account["id"],
            "cipher_version": "fernet-v1",
            "encrypted_state": encrypted_state,
            "state_fingerprint": fingerprint,
        },
        on_conflict="account_id",
    )
    print(f"Paired {platform} account '{label}' as {account['id']}.")
    print("The encrypted browser session is stored in Supabase; raw session data was not written to GitHub.")
    return account


def main() -> int:
    parser = argparse.ArgumentParser(description="Pair a social account without a developer app")
    parser.add_argument("platform", choices=sorted(LOGIN_URLS))
    parser.add_argument("--label", required=True, help="Friendly account name, e.g. SocialMarket Instagram")
    parser.add_argument("--handle", help="Optional @handle/page/profile name")
    args = parser.parse_args()
    pair(args.platform, args.label, args.handle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import logging
from typing import Any

from .config import Settings

logger = logging.getLogger(__name__)


class HeaderCaptureError(RuntimeError):
    """Raised when required ModeTour request headers cannot be created."""


def _build_env_headers(settings: Settings) -> dict[str, str] | None:
    if not settings.modewebapireqheader:
        return None
    return {
        "accept": settings.accept,
        "referer": settings.referer,
        "user-agent": settings.user_agent,
        "x-platform": settings.x_platform,
        "x-salespartner": settings.x_salespartner,
        "x-username": settings.x_username,
        "x-userid": settings.x_userid,
        "x-userdepartment": settings.x_userdepartment,
        "modewebapireqheader": settings.modewebapireqheader,
    }


def _load_cached_headers(settings: Settings) -> dict[str, str] | None:
    if settings.header_cache_json.strip():
        try:
            data = json.loads(settings.header_cache_json)
        except Exception:
            data = None
        if isinstance(data, dict):
            required = ("accept", "referer", "user-agent", "x-platform", "x-salespartner", "x-username", "x-userid", "x-userdepartment", "modewebapireqheader")
            if all(str(data.get(key, "")).strip() for key in required):
                return {key: str(data[key]) for key in required}

    cache_path = settings.header_cache_path
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    required = ("accept", "referer", "user-agent", "x-platform", "x-salespartner", "x-username", "x-userid", "x-userdepartment", "modewebapireqheader")
    if any(not str(data.get(key, "")).strip() for key in required):
        return None
    return {key: str(data[key]) for key in required}


def _save_cached_headers(settings: Settings, headers: dict[str, str]) -> None:
    cache_path = settings.header_cache_path
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(headers, ensure_ascii=False, indent=2), encoding="utf-8")


def capture_base_headers(settings: Settings) -> dict[str, str]:
    env_headers = _build_env_headers(settings)
    if env_headers is not None:
        logger.info("Using ModeTour headers from environment variables.")
        return env_headers

    cached_headers = _load_cached_headers(settings)
    if cached_headers is not None:
        logger.info("Using cached ModeTour headers from %s", settings.header_cache_path)
        return cached_headers

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - depends on local install
        raise HeaderCaptureError("Playwright is required to capture ModeTour headers.") from exc

    captured: dict[str, str] = {}

    def on_request(req: Any) -> None:
        nonlocal captured
        if "/Package/GetProductMaster" in req.url and req.method.upper() == "POST":
            captured = dict(req.headers)

    page_url = f"https://www.modetour.com/product-common/{settings.seed_mat_code}?type=single"
    logger.info("Capturing ModeTour headers from %s", page_url)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("request", on_request)
        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=settings.capture_timeout_ms)
        except Exception:
            logger.info("Navigation timed out while capturing headers; continuing if request data was captured.")
        page.wait_for_timeout(settings.capture_wait_ms)
        browser.close()

    modeweb = captured.get("modewebapireqheader", "")
    if not modeweb:
        raise HeaderCaptureError("Failed to capture modewebapireqheader from ModeTour page.")
    headers = {
        "accept": captured.get("accept", settings.accept),
        "referer": settings.referer,
        "user-agent": captured.get("user-agent", settings.user_agent),
        "x-platform": captured.get("x-platform", settings.x_platform),
        "x-salespartner": captured.get("x-salespartner", settings.x_salespartner),
        "x-username": captured.get("x-username", settings.x_username),
        "x-userid": captured.get("x-userid", settings.x_userid),
        "x-userdepartment": captured.get("x-userdepartment", settings.x_userdepartment),
        "modewebapireqheader": modeweb,
    }
    _save_cached_headers(settings, headers)
    return headers

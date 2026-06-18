from __future__ import annotations

import json

from app.auth import capture_base_headers
from app.config import Settings


def test_capture_headers_from_cache_json() -> None:
    headers = {
        "accept": "application/json",
        "referer": "https://www.modetour.com/",
        "user-agent": "Mozilla/5.0",
        "x-platform": "WEB",
        "x-salespartner": "false",
        "x-username": "tester",
        "x-userid": "1",
        "x-userdepartment": "qa",
        "modewebapireqheader": "encoded-header",
    }
    settings = Settings(header_cache_json=json.dumps(headers))
    assert capture_base_headers(settings) == headers

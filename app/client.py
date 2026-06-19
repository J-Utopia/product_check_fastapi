from __future__ import annotations

import concurrent.futures
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from .auth import capture_base_headers
from .config import Settings

logger = logging.getLogger(__name__)


class ModeTourApiError(RuntimeError):
    """Raised when a ModeTour API call fails."""


@dataclass(frozen=True)
class EndpointSpec:
    name: str
    path: str


class ModeTourApiClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_headers = capture_base_headers(settings)
        self._endpoints = (
            EndpointSpec("package_info", "/Package/GetPackageInfo"),
            EndpointSpec("schedule", "/Package/GetScheduleList"),
            EndpointSpec("detail", "/Package/GetProductDetailInfo"),
            EndpointSpec("hotels", "/Package/GetHotelList"),
            EndpointSpec("flight_remarks", "/Package/GetFlightRemarkList"),
            EndpointSpec("key_points", "/Package/GetProductKeyPointInfo"),
            EndpointSpec("coupons", "/Coupon/GetPackageCouponList"),
        )

    def _headers_for_product(self, product_no: str) -> dict[str, str]:
        headers = dict(self._base_headers)
        headers["x-incomming-pathname"] = f"/product-common/{product_no}?type=group"
        return headers

    def _fetch_one(self, spec: EndpointSpec, product_no: str) -> Any:
        url = f"{self._settings.base_url}{spec.path}"
        headers = self._headers_for_product(product_no)
        logger.info("Fetching %s for productNo=%s", spec.name, product_no)
        response = requests.get(
            url,
            params={"productNo": product_no},
            headers=headers,
            timeout=self._settings.request_timeout_seconds,
        )
        if not response.ok:
            raise ModeTourApiError(
                f"{spec.name} failed with status {response.status_code}: {response.text[:300]}"
            )
        data = response.json()
        if not isinstance(data, dict) or "result" not in data:
            raise ModeTourApiError(f"{spec.name} returned an unexpected response shape.")
        return data["result"]

    def fetch_all(self, product_no: str) -> dict[str, Any]:
        started_at = time.perf_counter()
        results: dict[str, Any] = {}
        max_workers = min(len(self._endpoints), 8)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_spec = {
                executor.submit(self._fetch_one, spec, product_no): spec for spec in self._endpoints
            }
            try:
                for future in concurrent.futures.as_completed(future_to_spec):
                    spec = future_to_spec[future]
                    results[spec.name] = future.result()
            except Exception:
                for future in future_to_spec:
                    future.cancel()
                raise

        elapsed = time.perf_counter() - started_at
        logger.info("Fetched %s upstream endpoints for productNo=%s in %.2fs", len(results), product_no, elapsed)
        return {spec.name: results[spec.name] for spec in self._endpoints}

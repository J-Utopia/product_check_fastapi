from __future__ import annotations

import logging
from typing import Protocol

from .client import ModeTourApiClient
from .config import Settings
from .models import InspectionEnvelope, InspectionPayload, NormalizedProduct
from .normalizer import normalize_product
from .rules import RuleEngine

logger = logging.getLogger(__name__)


class FetchClient(Protocol):
    def fetch_all(self, product_no: str) -> dict[str, object]:
        ...


REQUIRED_FIELDS = (
    "departure_date",
    "product_name",
    "schedule_days",
    "nights",
    "country_names",
)


class InspectionService:
    def __init__(self, client: FetchClient, rule_engine: RuleEngine | None = None) -> None:
        self._client = client
        self._rule_engine = rule_engine or RuleEngine()

    def run(self, group_id: str) -> InspectionEnvelope:
        raw = self._client.fetch_all(group_id)
        normalized = normalize_product(group_id, raw)
        missing = self._validate_required_fields(normalized)
        if missing:
            return InspectionEnvelope(
                status="error",
                code="DATA_FAILURE",
                message="데이터 수신 실패",
                group_id=group_id,
                meta={"missing_fields": missing},
                result=None,
            )

        validation = self._rule_engine.validate(normalized)
        summary = self._build_summary(normalized)
        return InspectionEnvelope(
            status="ok",
            code="SUCCESS",
            message="Inspection completed",
            group_id=group_id,
            meta={
                "issue_count": len(validation.issues),
                "air_segment_count": len(normalized.air_segments),
                "day_count": len(normalized.schedule_days),
                "hotel_count": len(normalized.hotels),
                "top_badges": normalized.top_badges,
                "key_point_sections": {
                    "benefits": len(normalized.special_benefits),
                    "sightseeings": len(normalized.sightseeings),
                    "hotels": len(normalized.key_point_hotels),
                    "meals": len(normalized.key_point_meals),
                    "hashtags": len(normalized.hashtags),
                    "insurance": bool(normalized.traveler_insurance_text),
                    "mileage": bool(normalized.expected_tour_mileage_text),
                },
                "coupon_count": normalized.coupon_count,
            },
            result=InspectionPayload(
                summary=summary,
                normalized=normalized,
                issues=validation.issues,
                quality=validation.quality,
            ),
        )

    def _validate_required_fields(self, product: NormalizedProduct) -> list[str]:
        missing: list[str] = []
        for field_name in REQUIRED_FIELDS:
            value = getattr(product, field_name)
            if value in (None, "", []):
                missing.append(field_name)
        return missing

    def _build_summary(self, product: NormalizedProduct) -> str:
        period = (
            f"{product.departure_date} 출발, {product.nights}박 {product.days}일"
            if product.departure_date and product.nights is not None and product.days is not None
            else "기간 정보 확인 필요"
        )
        route = ", ".join(product.city_names[:4]) if product.city_names else ", ".join(product.country_names)

        flags: list[str] = []
        if product.shopping_count is not None:
            flags.append(f"쇼핑 {product.shopping_count}회")
        if product.optional_tour_or_not:
            flags.append(f"선택관광 {'있음' if product.optional_tour_or_not == 'Y' else '없음'}")
        if product.direct_flight is not None:
            flags.append(f"{'직항' if product.direct_flight else '경유'} 항공")

        badge_text = ", ".join(product.top_badges[:4]) if product.top_badges else ""
        summary = f"{product.product_name}\n{period}\n주요 이동/방문 도시: {route}"
        if badge_text:
            summary += f"\n상단 배지: {badge_text}"
        if flags:
            summary += f"\n주요 상태: {', '.join(flags)}"
        return summary


def build_default_service(settings: Settings) -> InspectionService:
    client = ModeTourApiClient(settings)
    return InspectionService(client)

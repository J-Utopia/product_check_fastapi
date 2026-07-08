from __future__ import annotations

import logging
from typing import Protocol

from .client import ModeTourApiClient
from .config import Settings
from .models import (
    CompactDaySummary,
    CompactFlightSummary,
    CompactInspectionEnvelope,
    CompactInspectionPayload,
    CompactIssue,
    CompactNormalizedProduct,
    InspectionEnvelope,
    InspectionPayload,
    NormalizedProduct,
)
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
                "prices": {
                    "display_price_adult": normalized.display_price_adult,
                    "selling_price_adult": normalized.selling_price_adult,
                    "selling_price_child_no_bed": normalized.selling_price_child_no_bed,
                    "selling_price_child_extra_bed": normalized.selling_price_child_extra_bed,
                    "selling_price_infant": normalized.selling_price_infant,
                },
            },
            result=InspectionPayload(
                summary=summary,
                normalized=normalized,
                issues=validation.issues,
                quality=validation.quality,
            ),
        )

    def to_compact_envelope(self, envelope: InspectionEnvelope) -> CompactInspectionEnvelope:
        if envelope.result is None:
            return CompactInspectionEnvelope(
                status=envelope.status,
                code=envelope.code,
                message=envelope.message,
                group_id=envelope.group_id,
                meta=envelope.meta,
                result=None,
            )

        normalized = envelope.result.normalized
        compact_hotels = list(dict.fromkeys(hotel.hotel_name for hotel in normalized.hotels if hotel.hotel_name))
        compact_air_segments = [
            CompactFlightSummary(
                direction=segment.direction,
                flight_no=segment.flight_no,
                departure_city_name=segment.departure_city_name,
                departure_time=segment.departure_time,
                arrival_city_name=segment.arrival_city_name,
                arrival_time=segment.arrival_time,
            )
            for segment in normalized.air_segments
        ]
        compact_schedule_days = [
            CompactDaySummary(
                day_no=day.day_no,
                date=day.date,
                route_headers=day.route_headers,
                place_names=day.place_names[:8],
                highlights=[
                    item
                    for item in [
                        day.schedule_hotel_text,
                        *[event.summary for event in day.meals[:2] if event.summary],
                        *[event.summary for event in day.others[:3] if event.summary],
                    ]
                    if item
                ][:6],
            )
            for day in normalized.schedule_days
        ]
        compact_normalized = CompactNormalizedProduct(
            product_no=normalized.product_no,
            product_name=normalized.product_name,
            title=normalized.title,
            top_badges=normalized.top_badges,
            hashtags=normalized.hashtags,
            departure_date=normalized.departure_date,
            arrival_date=normalized.arrival_date,
            nights=normalized.nights,
            days=normalized.days,
            country_names=normalized.country_names,
            city_names=normalized.city_names,
            departure_airline_name=normalized.departure_airline_name,
            return_airline_name=normalized.return_airline_name,
            departure_flight=normalized.departure_flight,
            return_flight=normalized.return_flight,
            direct_flight=normalized.direct_flight,
            shopping_count=normalized.shopping_count,
            optional_tour_or_not=normalized.optional_tour_or_not,
            local_required_expense_or_not=normalized.local_required_expense_or_not,
            local_required_expense=normalized.local_required_expense,
            included_items=normalized.included_items,
            excluded_items=normalized.excluded_items,
            special_benefits=normalized.special_benefits,
            product_point_text=normalized.product_point_text[:800],
            product_point_items=normalized.product_point_items[:20],
            sightseeings=normalized.sightseeings,
            key_point_hotels=normalized.key_point_hotels,
            key_point_meals=normalized.key_point_meals,
            key_point_leader_guild=normalized.key_point_leader_guild,
            display_price_adult=normalized.display_price_adult,
            selling_price_adult=normalized.selling_price_adult,
            selling_price_child_no_bed=normalized.selling_price_child_no_bed,
            selling_price_child_extra_bed=normalized.selling_price_child_extra_bed,
            selling_price_infant=normalized.selling_price_infant,
            coupon_count=normalized.coupon_count,
            coupon_titles=normalized.coupon_titles,
            hotels=compact_hotels,
            air_segments=compact_air_segments,
            schedule_days=compact_schedule_days,
        )
        compact_issues = [
            CompactIssue(
                rule_id=issue.rule_id,
                level=issue.level,
                title=issue.title,
                message=issue.message,
                suggestion=issue.suggestion,
                evidence=[
                    evidence.model_copy(update={"value_excerpt": evidence.value_excerpt[:100]})
                    for evidence in issue.evidence[:3]
                ],
            )
            for issue in envelope.result.issues
        ]
        return CompactInspectionEnvelope(
            status=envelope.status,
            code=envelope.code,
            message=envelope.message,
            group_id=envelope.group_id,
            meta=envelope.meta,
            result=CompactInspectionPayload(
                summary=envelope.result.summary,
                normalized=compact_normalized,
                issues=compact_issues,
                quality=envelope.result.quality,
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

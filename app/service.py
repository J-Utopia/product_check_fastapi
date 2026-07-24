from __future__ import annotations

import logging
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Protocol

from .client import ModeTourApiClient
from .config import Settings
from .models import (
    CompactDaySummary,
    CompactFlightSummary,
    CompactInspectionEnvelope,
    CompactInspectionPayload,
    CompactIssue,
    CompactNormalizedProduct,
    CollectionPlanSummary,
    DeterministicResults,
    EvidenceResponse,
    InspectionEvidence,
    InspectionEnvelope,
    InspectionRequest,
    InspectionPayload,
    NormalizedProduct,
    ProductSummary,
    RuleResult,
    ScoringSummary,
    SourceSummary,
    V3InspectionResponse,
)
from .normalizer import normalize_product
from .observability import measure_payloads
from .rules import RuleEngine
from .semantic import build_semantic_packets

logger = logging.getLogger(__name__)
V3_RESPONSE_WARNING_BYTES = 60_000
MAX_TEXT_EXCERPT_CHARS = 500
MAX_LIST_ITEMS = 20


class FetchClient(Protocol):
    def fetch_all(self, product_no: str) -> dict[str, object]:
        ...

    def fetch_core(self, product_no: str) -> dict[str, object]:
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
        self._raw_cache: dict[str, dict[str, object]] = {}
        self._v3_cache: dict[str, V3InspectionResponse] = {}
        self._evidence_by_inspection_id: dict[str, dict[str, InspectionEvidence]] = {}

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
        envelope = InspectionEnvelope(
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
        compact_envelope = self.to_compact_envelope(envelope)
        metrics = measure_payloads(raw, normalized, compact_envelope)
        logger.info(
            "Inspection payload metrics group_id=%s raw_bytes=%d normalized_bytes=%d compact_bytes=%d "
            "schedule_days=%d schedule_events=%d gpt_text_chars=%d duplicate_text_count=%d",
            group_id,
            metrics.raw_bytes,
            metrics.normalized_bytes,
            metrics.compact_bytes,
            metrics.schedule_day_count,
            metrics.schedule_event_count,
            metrics.gpt_text_chars,
            metrics.duplicate_text_count,
        )
        return envelope

    def run_v3(self, request: InspectionRequest) -> V3InspectionResponse:
        if not request.force_refresh and request.group_id in self._raw_cache:
            raw = self._raw_cache[request.group_id]
        else:
            raw = self._client.fetch_core(request.group_id)
            self._raw_cache[request.group_id] = raw
        source_hash = self._source_hash(raw)
        cache_key = f"inspection:{request.group_id}:{source_hash}:2.0.0:2.0.0"
        if not request.force_refresh and cache_key in self._v3_cache:
            cached = self._v3_cache[cache_key]
            return cached.model_copy(update={"source": cached.source.model_copy(update={"cache_status": "hit"})})

        normalized = normalize_product(request.group_id, raw)
        validation = self._rule_engine.validate(normalized)
        deterministic_results = self._to_rule_results(validation.issues)
        semantic_packets = build_semantic_packets(normalized)
        inspection_id = f"insp-{request.group_id}-{source_hash[:12]}"
        response = V3InspectionResponse(
            schema_version="3.0.0",
            inspection_id=inspection_id,
            status="ok",
            group_id=request.group_id,
            product=ProductSummary(
                product_no=normalized.product_no,
                product_code=normalized.product_code,
                computed_product_code=normalized.computed_product_code,
                title=normalized.title,
                prefixes=normalized.prefixes,
                themes=normalized.themes,
                group_brief_keywords=normalized.group_brief_keywords,
                travel_period_text=normalized.travel_period_text,
                departure_date=normalized.departure_date,
                arrival_date=normalized.arrival_date,
                nights=normalized.nights,
                days=normalized.days,
                departure_airline_name=normalized.departure_airline_name,
                return_airline_name=normalized.return_airline_name,
                departure_flight=normalized.departure_flight,
                return_flight=normalized.return_flight,
                visit_cities=normalized.visit_cities,
                shopping_count=normalized.shopping_count,
                optional_tour_or_not=normalized.optional_tour_or_not,
                guide_yn=normalized.guide_yn,
                leader_yn=normalized.leader_yn,
                guide_fee={
                    "currency": normalized.guide_fee_currency,
                    "adult": normalized.guide_fee_adult,
                    "child": normalized.guide_fee_child,
                    "infant": normalized.guide_fee_infant,
                    "payment_method": "현지지불" if normalized.local_required_expense_or_not == "Y" else None,
                },
                meeting_time=normalized.meeting_time,
                meeting_place_text=self._clip(normalized.meeting_place_text),
                prices={
                    "display_price_adult": normalized.display_price_adult,
                    "before_discount_price_adult": normalized.before_discount_price_adult,
                    "selling_price_adult": normalized.selling_price_adult,
                    "selling_price_child_no_bed": normalized.selling_price_child_no_bed,
                    "selling_price_child_extra_bed": normalized.selling_price_child_extra_bed,
                    "selling_price_infant": normalized.selling_price_infant,
                    "selling_price_local_join": normalized.selling_price_local_join,
                },
            ),
            inspection_context=self._build_inspection_context(normalized),
            deterministic=DeterministicResults(
                issue_count=sum(1 for result in deterministic_results if result.status == "failed"),
                results=deterministic_results,
            ),
            semantic_packets=semantic_packets,
            scoring=ScoringSummary(
                base_score=100,
                deterministic_deduction=self._deterministic_deduction(deterministic_results),
            ),
            source=SourceSummary(
                source_hash=source_hash,
                rule_version="2.0.0",
                prompt_version="2.0.0",
                cache_status="miss",
                fetched_at=datetime.now(timezone.utc).isoformat(),
            ),
            collection_plan=CollectionPlanSummary(
                required=["package_info", "detail", "schedule", "key_points"],
                conditional=[],
                skipped=[
                    {"endpoint": "hotels", "reason": "not_required_by_active_rules_in_v3_core"},
                    {"endpoint": "flight_remarks", "reason": "not_required_by_active_rules_in_v3_core"},
                    {"endpoint": "coupons", "reason": "not_requested"},
                ],
            ),
            warnings=[],
        )
        response = self._with_size_warning(response)
        self._v3_cache[cache_key] = response
        self._store_evidence(response, normalized)
        return response

    def get_evidence(self, inspection_id: str, evidence_ids: str) -> EvidenceResponse:
        requested_ids = [value.strip() for value in evidence_ids.split(",") if value.strip()]
        stored = self._evidence_by_inspection_id.get(inspection_id, {})
        return EvidenceResponse(
            inspection_id=inspection_id,
            evidence=[stored[evidence_id] for evidence_id in requested_ids if evidence_id in stored],
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

    def _build_inspection_context(self, product: NormalizedProduct) -> dict[str, Any]:
        included_evidence_id = f"included-full-{product.product_no}"
        excluded_evidence_id = f"excluded-full-{product.product_no}"
        meeting_evidence_id = f"meeting-full-{product.product_no}"
        schedule_evidence_ids = [f"schedule-day-{day.day_no}-full" for day in product.schedule_days]
        return {
            "top_area": {
                "source_endpoints": ["GetPackageInfo", "GetProductDetailInfo"],
                "product_no": product.product_no,
                "product_code": product.product_code,
                "computed_product_code": product.computed_product_code,
                "title": product.title,
                "prefixes": product.prefixes,
                "themes": product.themes,
                "group_brief_keywords": product.group_brief_keywords,
                "display_price_adult": product.display_price_adult,
                "before_discount_price_adult": product.before_discount_price_adult,
                "icons": {
                    "period": f"{product.nights}박{product.days}일"
                    if product.nights is not None and product.days is not None
                    else None,
                    "airline": product.departure_airline_name,
                    "shopping_count": product.shopping_count,
                    "guide_fee": self._guide_fee_context(product),
                    "optional_tour_or_not": product.optional_tour_or_not,
                    "leader_yn": product.leader_yn,
                    "guide_yn": product.guide_yn,
                    "direct_flight": product.direct_flight,
                },
            },
            "main_schedule": {
                "source_endpoints": ["GetProductDetailInfo", "GetPackageInfo", "GetScheduleList"],
                "travel_period_text": product.travel_period_text,
                "nights": product.nights,
                "days": product.days,
                "departure_date": product.departure_date,
                "arrival_date": product.arrival_date,
                "departure_airline_name": product.departure_airline_name,
                "return_airline_name": product.return_airline_name,
                "departure_flight": product.departure_flight,
                "return_flight": product.return_flight,
                "departure_city": product.air_segments[0].departure_city_name if product.air_segments else None,
                "arrival_city": product.air_segments[-1].arrival_city_name if product.air_segments else None,
                "visit_cities": product.visit_cities,
                "shopping_count": product.shopping_count,
                "optional_tour_or_not": product.optional_tour_or_not,
                "guide_fee": self._guide_fee_context(product),
            },
            "prices": {
                "source_endpoints": ["GetPackageInfo", "GetProductDetailInfo"],
                "display_price_adult": product.display_price_adult,
                "before_discount_price_adult": product.before_discount_price_adult,
                "selling_price_adult": product.selling_price_adult,
                "selling_price_child_no_bed": product.selling_price_child_no_bed,
                "selling_price_child_extra_bed": product.selling_price_child_extra_bed,
                "selling_price_infant": product.selling_price_infant,
                "selling_price_local_join": product.selling_price_local_join,
                "guide_fee": self._guide_fee_context(product),
            },
            "key_points": {
                "source_endpoints": ["GetProductKeyPointInfo", "GetProductDetailInfo"],
                "product_point": {
                    "raw_text": self._clip(product.product_point_text),
                    "items": self._limit_list(product.product_point_items),
                },
                "group_special_notes": self._limit_list(product.group_brief_keywords),
                "special_benefits": self._limit_list(product.special_benefits),
                "tourism": self._limit_list(product.sightseeings),
                "golf": self._limit_list(product.key_point_golfs),
                "hotel": self._limit_list(product.key_point_hotels),
                "meal": self._limit_list(product.key_point_meals),
                "leader_guide": {
                    "text": self._clip(product.key_point_leader_guild),
                    "guide_status": product.guide_status,
                    "leader_status": product.leader_status,
                    "guide_info": product.guide_info[:5],
                },
                "insurance": self._clip(product.traveler_insurance_text),
                "mileage": self._clip(product.expected_tour_mileage_text),
                "business_guarantee": self._clip(product.business_guarantee),
                "product_score": product.product_score,
            },
            "included_excluded": {
                "source_endpoints": ["GetProductDetailInfo"],
                "included_text": self._clip(product.included_text),
                "included_evidence_id": included_evidence_id if product.included_text else None,
                "included_items": self._limit_list(product.included_items),
                "excluded_text": self._clip(product.excluded_text),
                "excluded_evidence_id": excluded_evidence_id if product.excluded_text else None,
                "excluded_items": self._limit_list(product.excluded_items),
            },
            "meeting": {
                "source_endpoints": ["GetProductDetailInfo"],
                "meeting_time": product.meeting_time,
                "meeting_place_text": self._clip(product.meeting_place_text),
                "meeting_info_text": self._clip(product.meeting_info_text),
                "meeting_evidence_id": meeting_evidence_id
                if product.meeting_place_text or product.meeting_info_text
                else None,
            },
            "daily_schedule": {
                "source_endpoints": ["GetScheduleList"],
                "day_count": len(product.schedule_days),
                "days": [self._compact_day(day, evidence_id) for day, evidence_id in zip(product.schedule_days, schedule_evidence_ids)],
                "detail_policy": "Full day details are available through /v3/inspections/{inspection_id}/evidence by evidence_id.",
            },
            "raw_text_areas": {
                "notice_text": self._clip(product.notice_text),
                "shopping_text": self._clip(product.shopping_text),
            },
        }

    def _compact_day(self, day: Any, evidence_id: str) -> dict[str, Any]:
        events = [*day.meals, *day.guides, *day.hotels, *day.transports, *day.others]
        highlights = [
            text
            for text in [
                day.schedule_hotel_text,
                *day.route_headers,
                *day.place_names[:8],
                *[event.summary for event in events if event.summary],
                *[event.place_name for event in events if event.place_name],
            ]
            if text
        ]
        return {
            "day_no": day.day_no,
            "date": day.date,
            "route_headers": self._limit_list(day.route_headers, limit=8),
            "place_names": self._limit_list(day.place_names, limit=12),
            "highlights": self._limit_list(highlights, limit=16),
            "event_count": len(events) + len(day.air),
            "has_air": bool(day.air),
            "has_hotel": bool(day.hotels or day.schedule_hotel_text),
            "evidence_id": evidence_id,
        }

    def _guide_fee_context(self, product: NormalizedProduct) -> dict[str, int | str | None]:
        return {
            "required": product.local_required_expense_or_not,
            "currency": product.guide_fee_currency,
            "adult": product.guide_fee_adult,
            "child": product.guide_fee_child,
            "infant": product.guide_fee_infant,
            "payment_method": "현지지불" if product.local_required_expense_or_not == "Y" else None,
        }

    def _clip(self, value: str, limit: int = MAX_TEXT_EXCERPT_CHARS) -> str:
        if len(value) <= limit:
            return value
        return f"{value[:limit].rstrip()} ... [상세 근거 조회 필요]"

    def _limit_list(self, values: list[str], limit: int = MAX_LIST_ITEMS) -> list[str]:
        clipped_values = [self._clip(value, limit=180) for value in values]
        if len(clipped_values) <= limit:
            return clipped_values
        return [*clipped_values[:limit], f"... 외 {len(clipped_values) - limit}개"]

    def _with_size_warning(self, response: V3InspectionResponse) -> V3InspectionResponse:
        size_bytes = len(json.dumps(response.model_dump(), ensure_ascii=False, default=str).encode("utf-8"))
        warnings = list(response.warnings)
        if size_bytes > V3_RESPONSE_WARNING_BYTES:
            warnings.append(
                f"응답 크기 {size_bytes} bytes. 상세 원문은 evidence endpoint로 조회해야 합니다."
            )
        return response.model_copy(update={"warnings": warnings})

    def _source_hash(self, raw: dict[str, object]) -> str:
        payload = json.dumps(raw, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _to_rule_results(self, issues: list[Any]) -> list[RuleResult]:
        results: list[RuleResult] = []
        for issue in issues:
            evidence = [
                InspectionEvidence(
                    evidence_id=f"{issue.rule_id}-{index + 1}",
                    source_path=item.field,
                    excerpt=item.value_excerpt,
                )
                for index, item in enumerate(issue.evidence)
            ]
            results.append(
                RuleResult(
                    rule_id=issue.rule_id,
                    status="failed",
                    level=issue.level,
                    title=issue.title,
                    message=issue.message,
                    evidence=evidence,
                    suggestion=issue.suggestion,
                    deduction=self._deduction_for_level(issue.level),
                    confidence="high" if issue.level in ("FATAL", "ERROR") else "medium",
                )
            )
        return results

    def _deduction_for_level(self, level: str) -> int:
        if level == "FATAL":
            return 25
        if level == "ERROR":
            return 10
        if level == "WARN":
            return 4
        return 0

    def _deterministic_deduction(self, results: list[RuleResult]) -> int:
        return sum(result.deduction for result in results if result.status == "failed")

    def _store_evidence(self, response: V3InspectionResponse, product: NormalizedProduct) -> None:
        evidence_by_id: dict[str, InspectionEvidence] = {}
        for result in response.deterministic.results:
            for evidence in result.evidence:
                evidence_by_id[evidence.evidence_id] = evidence
        for packet in response.semantic_packets:
            for evidence in packet.evidence:
                evidence_by_id[evidence.evidence_id] = evidence
        context = response.inspection_context
        included = context.get("included_excluded", {})
        if included.get("included_evidence_id") and product.included_text:
            evidence_by_id[str(included["included_evidence_id"])] = InspectionEvidence(
                evidence_id=str(included["included_evidence_id"]),
                source_path="included_excluded.included_text",
                excerpt=product.included_text,
            )
        if included.get("excluded_evidence_id") and product.excluded_text:
            evidence_by_id[str(included["excluded_evidence_id"])] = InspectionEvidence(
                evidence_id=str(included["excluded_evidence_id"]),
                source_path="included_excluded.excluded_text",
                excerpt=product.excluded_text,
            )
        meeting = context.get("meeting", {})
        if meeting.get("meeting_evidence_id"):
            evidence_by_id[str(meeting["meeting_evidence_id"])] = InspectionEvidence(
                evidence_id=str(meeting["meeting_evidence_id"]),
                source_path="meeting",
                excerpt=" | ".join(value for value in [product.meeting_place_text, product.meeting_info_text] if value),
            )
        for day in product.schedule_days:
            evidence_id = f"schedule-day-{day.day_no}-full"
            evidence_by_id[evidence_id] = InspectionEvidence(
                evidence_id=evidence_id,
                source_path=f"daily_schedule.days[{day.day_no}]",
                excerpt=json.dumps(day.model_dump(), ensure_ascii=False),
                day_no=day.day_no,
            )
        self._evidence_by_inspection_id[response.inspection_id] = evidence_by_id


def build_default_service(settings: Settings) -> InspectionService:
    client = ModeTourApiClient(settings)
    return InspectionService(client)

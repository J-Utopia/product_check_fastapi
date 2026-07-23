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
                title=normalized.title,
                departure_date=normalized.departure_date,
                arrival_date=normalized.arrival_date,
                nights=normalized.nights,
                days=normalized.days,
                prices={
                    "display_price_adult": normalized.display_price_adult,
                    "selling_price_adult": normalized.selling_price_adult,
                    "selling_price_child_no_bed": normalized.selling_price_child_no_bed,
                    "selling_price_child_extra_bed": normalized.selling_price_child_extra_bed,
                    "selling_price_infant": normalized.selling_price_infant,
                },
            ),
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
        self._v3_cache[cache_key] = response
        self._store_evidence(response)
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

    def _store_evidence(self, response: V3InspectionResponse) -> None:
        evidence_by_id: dict[str, InspectionEvidence] = {}
        for result in response.deterministic.results:
            for evidence in result.evidence:
                evidence_by_id[evidence.evidence_id] = evidence
        for packet in response.semantic_packets:
            for evidence in packet.evidence:
                evidence_by_id[evidence.evidence_id] = evidence
        self._evidence_by_inspection_id[response.inspection_id] = evidence_by_id


def build_default_service(settings: Settings) -> InspectionService:
    client = ModeTourApiClient(settings)
    return InspectionService(client)

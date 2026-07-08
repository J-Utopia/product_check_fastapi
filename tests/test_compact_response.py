from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import (
    DaySchedule,
    EvidenceItem,
    FlightSegment,
    HotelStay,
    InspectionEnvelope,
    InspectionPayload,
    Issue,
    NormalizedProduct,
    QualityScore,
)
from app.service import InspectionService


def build_envelope() -> InspectionEnvelope:
    normalized = NormalizedProduct(
        product_no="103293341",
        product_name="테스트 상품",
        title="테스트 일정",
        top_badges=["인기", "추천"],
        hashtags=["유럽", "여름"],
        departure_date="2026-08-01",
        arrival_date="2026-08-05",
        nights=4,
        days=5,
        country_names=["프랑스"],
        city_names=["파리", "베르사유"],
        departure_airline_name="KE",
        return_airline_name="KE",
        departure_flight="KE901",
        return_flight="KE902",
        direct_flight=True,
        air_segments=[
            FlightSegment(
                direction="outbound",
                airline="KE",
                flight_no="KE901",
                departure_city_name="서울",
                arrival_city_name="파리",
                duration="14:00",
            )
        ],
        shopping_count=1,
        optional_tour_or_not="Y",
        local_required_expense_or_not="N",
        included_text="포함사항 원문 " * 50,
        excluded_text="불포함사항 원문 " * 50,
        notice_text="무비자 안내와 일반여권 예외 안내",
        included_items=["항공", "호텔"],
        excluded_items=["개인경비"],
        shopping_text="쇼핑 안내 " * 50,
        traveler_insurance_text="보험 안내 " * 50,
        expected_tour_mileage_text="마일리지 안내 " * 50,
        display_price_adult=1000000,
        selling_price_adult=900000,
        product_point_text="핵심포인트 전신마사지 60분 포함",
        product_point_items=["전신마사지 60분 포함"],
        special_benefits=["특전1", "특전2"],
        sightseeings=["에펠탑"],
        key_point_hotels=["시내 4성급"],
        key_point_meals=["조식 포함"],
        key_point_leader_guild="인솔자 동행",
        coupon_count=2,
        coupon_titles=["얼리버드", "재구매"],
        hotels=[
            HotelStay(
                day_no=1,
                date="2026-08-01",
                hotel_name="Paris Hotel",
                city_name="파리",
                country_name="프랑스",
                hotel_note="호텔 비고 " * 20,
            )
        ],
        schedule_days=[
            DaySchedule(
                day_no=1,
                date="2026-08-01",
                route_headers=["인천", "파리"],
                place_names=["인천공항", "드골공항"],
                schedule_hotel_text="숙박 정보 " * 30,
            )
        ],
    )
    return InspectionEnvelope(
        status="ok",
        code="SUCCESS",
        message="Inspection completed",
        group_id="103293341",
        meta={"prices": {"display_price_adult": 1000000}},
        result=InspectionPayload(
            summary="검수 요약",
            normalized=normalized,
            issues=[
                Issue(
                    rule_id="rule-1",
                    level="WARN",
                    title="제목",
                    message="메시지",
                    evidence=[EvidenceItem(field="included_text", value_excerpt="긴 텍스트")],
                    suggestion="수정 필요",
                )
            ],
            quality=QualityScore(score=85, grade="B"),
        ),
    )


def test_compact_response_reduces_payload_size() -> None:
    service = InspectionService(client=None)  # type: ignore[arg-type]
    envelope = build_envelope()

    full_bytes = len(json.dumps(envelope.model_dump(), ensure_ascii=False).encode("utf-8"))
    compact = service.to_compact_envelope(envelope)
    compact_bytes = len(json.dumps(compact.model_dump(), ensure_ascii=False).encode("utf-8"))

    assert compact_bytes < full_bytes
    assert compact.result is not None
    assert compact.result.quality == envelope.result.quality
    assert compact.result.issues[0].message == envelope.result.issues[0].message
    assert compact.result.issues[0].evidence
    assert compact.result.normalized.hotels == ["Paris Hotel"]
    assert compact.result.normalized.schedule_days[0].day_no == 1
    assert compact.result.normalized.product_point_items == ["전신마사지 60분 포함"]


def test_compact_response_preserves_error_envelope() -> None:
    service = InspectionService(client=None)  # type: ignore[arg-type]
    envelope = InspectionEnvelope(
        status="error",
        code="DATA_FAILURE",
        message="데이터 수신 실패",
        group_id="103293341",
        meta={"missing_fields": ["schedule_days"]},
        result=None,
    )

    compact = service.to_compact_envelope(envelope)

    assert compact.result is None
    assert compact.code == envelope.code
    assert compact.meta == envelope.meta


def test_compact_response_handles_empty_issues() -> None:
    service = InspectionService(client=None)  # type: ignore[arg-type]
    envelope = build_envelope()
    assert envelope.result is not None
    envelope.result.issues = []

    compact = service.to_compact_envelope(envelope)

    assert compact.result is not None
    assert compact.result.issues == []
    assert compact.result.normalized.product_no == "103293341"

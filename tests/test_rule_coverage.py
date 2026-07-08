from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import DaySchedule, HotelStay, NormalizedProduct, ScheduleEvent
from app.rules import RuleEngine


def build_product() -> NormalizedProduct:
    return NormalizedProduct(
        product_no="103293341",
        product_name="장가계 4박5일 힐튼",
        title="장가계 4박5일 힐튼 마사지 60분",
        top_badges=["직항"],
        hashtags=["#힐튼"],
        departure_date="2026-10-05",
        arrival_date="2026-10-09",
        nights=4,
        days=5,
        country_names=["중국"],
        city_names=["인천", "장가계"],
        departure_airline_name="사천항공",
        return_airline_name="사천항공",
        departure_flight="3U3708",
        return_flight="3U3707",
        direct_flight=True,
        guide_yn="Y",
        shopping_count=1,
        optional_tour_or_not="N",
        local_required_expense_or_not="N",
        local_required_expense=0,
        meeting_place_text="인천공항 미팅",
        included_text="왕복항공료 및 호텔 숙박비",
        excluded_text="개인 경비",
        included_items=["왕복항공료", "호텔 숙박비"],
        excluded_items=["개인 경비"],
        traveler_insurance_text="3억원 여행자 보험",
        expected_tour_mileage_text="18490",
        display_price_adult=1849000,
        selling_price_adult=1849000,
        selling_price_child_no_bed=1849000,
        selling_price_child_extra_bed=1849000,
        selling_price_infant=150000,
        special_benefits=["전신 마사지 60분 포함"],
        sightseeings=["유리다리"],
        key_point_hotels=["힐튼 리조트"],
        key_point_meals=["버섯샤브샤브"],
        key_point_leader_guild="",
        guide_info=[],
        hotels=[
            HotelStay(day_no=1, hotel_name="장가계 블루베이 호텔"),
            HotelStay(day_no=2, hotel_name="장가계 블루베이 호텔"),
            HotelStay(day_no=3, hotel_name="장가계 블루베이 호텔"),
        ],
        schedule_days=[
            DaySchedule(
                day_no=1,
                date="2026-10-05T00:00:00",
                route_headers=["인천", "장가계"],
                place_names=["인천공항"],
                others=[
                    ScheduleEvent(
                        service_name="기타",
                        summary="전신 마사지 90분 포함",
                        detail="전신 마사지 90분 포함",
                    )
                ],
            ),
            DaySchedule(day_no=2, date="2026-10-06T00:00:00"),
            DaySchedule(day_no=3, date="2026-10-07T00:00:00"),
            DaySchedule(day_no=4, date="2026-10-08T00:00:00"),
            DaySchedule(day_no=5, date="2026-10-09T00:00:00"),
        ],
    )


def test_rule_engine_flags_point_duration_conflict() -> None:
    product = build_product()

    result = RuleEngine().validate(product)

    issue_ids = {issue.rule_id for issue in result.issues}
    assert "POINT-001" in issue_ids


def test_rule_engine_flags_hotel_claim_mismatch() -> None:
    product = build_product()

    result = RuleEngine().validate(product)

    issue_ids = {issue.rule_id for issue in result.issues}
    assert "KP-002" in issue_ids or "HOTEL-002" in issue_ids


def test_rule_engine_flags_meeting_and_guide_gaps() -> None:
    product = build_product()

    result = RuleEngine().validate(product)

    issue_ids = {issue.rule_id for issue in result.issues}
    assert "MEETING-001" in issue_ids
    assert "GUIDE-001" in issue_ids

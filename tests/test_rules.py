from __future__ import annotations

from app.models import DaySchedule, HotelStay, ScheduleEvent
from app.rules import RuleEngine
from tests.conftest import build_product


def test_rule_engine_keeps_consistent_product_clean() -> None:
    product = build_product()
    result = RuleEngine().validate(product)
    assert result.issues == []
    assert result.quality.score == 100


def test_rule_engine_flags_optional_conflict() -> None:
    day = DaySchedule(
        day_no=2,
        date="2026-06-21T00:00:00",
        others=[ScheduleEvent(service_name="선택관광 안내", summary="야경 투어 $50", detail="", place_name="")],
    )
    product = build_product(schedule_days=[build_product().schedule_days[0], day], days=2, optional_tour_or_not="N")
    result = RuleEngine().validate(product)
    assert any(issue.rule_id == "DAY-004" for issue in result.issues)


def test_rule_engine_flags_unsupported_hotel_marketing_point() -> None:
    product = build_product(
        special_benefits=["사막 일출&일몰 뷰 사막에 지어진 전면 유리형 캡슐 호텔"],
        hotels=[HotelStay(day_no=1, hotel_name="윈이리버티 호텔"), HotelStay(day_no=2, hotel_name="대초원 현대식 게르")],
    )
    result = RuleEngine().validate(product)
    assert any(issue.rule_id == "KP-004" for issue in result.issues)


def test_rule_engine_flags_unanchored_hashtag() -> None:
    product = build_product(hashtags=["#내몽고", "#인컨타라사막"])
    result = RuleEngine().validate(product)
    assert any(issue.rule_id == "KP-005" for issue in result.issues)


def test_rule_engine_flags_text_replacement_character() -> None:
    product = build_product(included_text="왕복항공권�숙박비")
    result = RuleEngine().validate(product)
    assert any(issue.rule_id == "TEXT-001" for issue in result.issues)

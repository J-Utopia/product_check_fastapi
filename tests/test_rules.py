from __future__ import annotations

from app.models import DaySchedule, ScheduleEvent
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
        others=[ScheduleEvent(service_name="선택관광 안내", summary="사막 낙타 체험 $50", detail="", place_name="")],
    )
    product = build_product(schedule_days=[build_product().schedule_days[0], day], days=2, optional_tour_or_not="N")
    result = RuleEngine().validate(product)
    assert any(issue.rule_id == "DAY-004" for issue in result.issues)


def test_rule_engine_flags_text_replacement_character() -> None:
    product = build_product(included_text="왕복항공료 � 숙박비")
    result = RuleEngine().validate(product)
    assert any(issue.rule_id == "TEXT-001" for issue in result.issues)

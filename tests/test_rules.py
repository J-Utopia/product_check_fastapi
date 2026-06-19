from __future__ import annotations

import json
from pathlib import Path

from app.models import DaySchedule, HotelStay, ScheduleEvent
from app.rules import RuleEngine
from tests.conftest import build_product


def test_rule_engine_keeps_consistent_product_clean() -> None:
    product = build_product()
    result = RuleEngine().validate(product)
    assert result.issues == []
    assert result.quality.score == 100


def test_rule_engine_flags_title_period_mismatch() -> None:
    product = build_product(title="[출발확정] 테스트상품 3박 4일")
    result = RuleEngine().validate(product)
    assert any(issue.rule_id == "TITLE-001" for issue in result.issues)


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
        special_benefits=["별채 조식&온천 포함 유리형 캡슐 호텔"],
        hotels=[HotelStay(day_no=1, hotel_name="베이뷰 호텔"), HotelStay(day_no=2, hotel_name="대초원 프리미엄 글램핑")],
    )
    result = RuleEngine().validate(product)
    assert any(issue.rule_id == "KP-004" for issue in result.issues)


def test_rule_engine_flags_unanchored_hashtag() -> None:
    product = build_product(hashtags=["#이색온천", "#알프스감성"])
    result = RuleEngine().validate(product)
    assert any(issue.rule_id == "KP-005" for issue in result.issues)


def test_rule_engine_flags_text_replacement_character() -> None:
    product = build_product(included_text="왕복항공권�숙박비")
    result = RuleEngine().validate(product)
    assert any(issue.rule_id == "TEXT-001" for issue in result.issues)


def test_validation_rule_json_files_are_valid() -> None:
    base = Path(__file__).resolve().parents[1]
    paths = sorted(base.glob("검증룰*.json"))
    assert len(paths) == 5
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data["rules"], list)
        assert data["version"] == "2026-06-19"

from __future__ import annotations

from app.models import DaySchedule, NormalizedProduct, ScheduleEvent
from app.observability import count_duplicate_texts, json_size_bytes, measure_payloads


def test_measure_payloads_counts_normal_schedule_events() -> None:
    product = NormalizedProduct(
        product_no="123456",
        product_name="테스트 상품",
        title="테스트 상품",
        schedule_days=[
            DaySchedule(
                day_no=1,
                route_headers=["서울", "부산"],
                place_names=["해운대"],
                others=[ScheduleEvent(service_name="관광", summary="해운대 관광", detail="")],
            )
        ],
    )

    metrics = measure_payloads({"package_info": {"pName": "테스트 상품"}}, product, {"ok": True})

    assert metrics.raw_bytes > 0
    assert metrics.normalized_bytes > metrics.compact_bytes
    assert metrics.schedule_day_count == 1
    assert metrics.schedule_event_count == 1
    assert metrics.gpt_text_chars > 0


def test_json_size_bytes_handles_unserializable_values_as_failure_case() -> None:
    class CustomValue:
        def __str__(self) -> str:
            return "custom-value"

    assert json_size_bytes({"value": CustomValue()}) == len('{"value": "custom-value"}'.encode("utf-8"))


def test_count_duplicate_texts_ignores_empty_edge_case() -> None:
    assert count_duplicate_texts(["", "  ", "A  B", "A B", "C"]) == 1

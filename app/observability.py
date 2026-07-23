from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PayloadMetrics:
    raw_bytes: int
    normalized_bytes: int
    compact_bytes: int
    schedule_day_count: int
    schedule_event_count: int
    gpt_text_chars: int
    duplicate_text_count: int


def json_size_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def count_duplicate_texts(values: list[str]) -> int:
    normalized = [compact_text(value) for value in values if compact_text(value)]
    counts = Counter(normalized)
    return sum(count - 1 for count in counts.values() if count > 1)


def measure_payloads(raw: dict[str, Any], normalized: Any, compact_payload: Any) -> PayloadMetrics:
    normalized_dump = normalized.model_dump() if hasattr(normalized, "model_dump") else normalized
    compact_dump = compact_payload.model_dump() if hasattr(compact_payload, "model_dump") else compact_payload
    schedule_days = getattr(normalized, "schedule_days", [])
    text_values: list[str] = []
    event_count = 0

    for day in schedule_days:
        text_values.extend(getattr(day, "route_headers", []))
        text_values.extend(getattr(day, "place_names", []))
        hotel_text = getattr(day, "schedule_hotel_text", "")
        if hotel_text:
            text_values.append(hotel_text)
        for event_group in ("meals", "guides", "hotels", "transports", "others"):
            for event in getattr(day, event_group, []):
                event_count += 1
                for attr in ("place_name", "service_name", "summary", "detail"):
                    value = getattr(event, attr, "")
                    if value:
                        text_values.append(value)

    for attr in (
        "product_name",
        "title",
        "included_text",
        "excluded_text",
        "product_point_text",
        "meeting_place_text",
        "meeting_info_text",
    ):
        value = getattr(normalized, attr, "")
        if value:
            text_values.append(value)

    return PayloadMetrics(
        raw_bytes=json_size_bytes(raw),
        normalized_bytes=json_size_bytes(normalized_dump),
        compact_bytes=json_size_bytes(compact_dump),
        schedule_day_count=len(schedule_days),
        schedule_event_count=event_count,
        gpt_text_chars=sum(len(value) for value in text_values),
        duplicate_text_count=count_duplicate_texts(text_values),
    )

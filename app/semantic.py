from __future__ import annotations

import hashlib
from typing import Iterable

from .models import InspectionEvidence, NormalizedProduct, SemanticPacket


SEMANTIC_GUARDS = {
    "SEM-POINT-001": [
        "선택관광은 포함 일정으로 인정하지 않는다.",
        "단순 경유는 관광으로 인정하지 않는다.",
        "표현 차이만으로 불일치 판정하지 않는다.",
    ],
    "SEM-TITLE-PLACE-001": [
        "도시명이 일정에 있다고 해당 관광을 수행한 것으로 자동 인정하지 않는다.",
        "동일 장소의 통용명과 공식명은 같은 대상으로 볼 수 있다.",
    ],
    "SEM-INEX-001": [
        "기본 제공과 개인 추가 구매를 구분한다.",
        "매너팁과 필수 가이드경비를 구분한다.",
    ],
    "SEM-COPY-001": [
        "더 좋은 표현이 가능하다는 이유만으로 오류 처리하지 않는다.",
        "실제 오해 가능성이 구체적으로 설명될 때만 WARN 처리한다.",
    ],
}


def _packet_id(prefix: str, product_no: str, values: Iterable[str]) -> str:
    digest = hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{product_no}-{digest}"


def _evidence(evidence_id: str, source_path: str, excerpt: str, day_no: int | None = None) -> InspectionEvidence:
    return InspectionEvidence(
        evidence_id=evidence_id,
        source_path=source_path,
        excerpt=excerpt[:180],
        day_no=day_no,
    )


def build_semantic_packets(product: NormalizedProduct) -> list[SemanticPacket]:
    packets: list[SemanticPacket] = []
    schedule_evidence: list[InspectionEvidence] = []
    for day in product.schedule_days:
        excerpts = [
            *day.route_headers,
            *day.place_names,
            day.schedule_hotel_text,
            *[event.summary for event in [*day.meals, *day.guides, *day.hotels, *day.transports, *day.others] if event.summary],
        ]
        compact = " | ".join(value for value in excerpts if value)
        if compact:
            schedule_evidence.append(
                _evidence(f"schedule-day-{day.day_no}", f"schedule.days[{day.day_no - 1}]", compact, day.day_no)
            )

    point_claims = [
        {"claim_id": f"claim-point-{index + 1}", "text": text, "source_path": "key_points.product_point_items"}
        for index, text in enumerate([*product.product_point_items[:8], *product.special_benefits[:5], *product.sightseeings[:5]])
    ]
    if point_claims:
        packets.append(
            SemanticPacket(
                packet_id=_packet_id("SEM-POINT-001", product.product_no, [claim["text"] for claim in point_claims]),
                rule_ids=["SEM-POINT-001"],
                claims=point_claims,
                evidence=schedule_evidence[:8],
                guards=SEMANTIC_GUARDS["SEM-POINT-001"],
            )
        )

    title_claims = [{"claim_id": "claim-title-1", "text": product.title, "source_path": "product.title"}]
    if product.title and schedule_evidence:
        packets.append(
            SemanticPacket(
                packet_id=_packet_id("SEM-TITLE-PLACE-001", product.product_no, [product.title]),
                rule_ids=["SEM-TITLE-PLACE-001"],
                claims=title_claims,
                evidence=schedule_evidence[:8],
                guards=SEMANTIC_GUARDS["SEM-TITLE-PLACE-001"],
            )
        )

    if product.included_text or product.excluded_text:
        packets.append(
            SemanticPacket(
                packet_id=_packet_id("SEM-INEX-001", product.product_no, [product.included_text, product.excluded_text]),
                rule_ids=["SEM-INEX-001"],
                claims=[
                    {"claim_id": "claim-included", "text": product.included_text[:300], "source_path": "included.plain_text"},
                    {"claim_id": "claim-excluded", "text": product.excluded_text[:300], "source_path": "excluded.plain_text"},
                ],
                evidence=[
                    _evidence("included-text", "included.plain_text", product.included_text),
                    _evidence("excluded-text", "excluded.plain_text", product.excluded_text),
                ],
                guards=SEMANTIC_GUARDS["SEM-INEX-001"],
            )
        )

    copy_targets = [
        product.meeting_place_text,
        product.meeting_info_text,
        product.notice_text,
        product.product_point_text,
    ]
    copy_text = " | ".join(value for value in copy_targets if value)
    if copy_text:
        packets.append(
            SemanticPacket(
                packet_id=_packet_id("SEM-COPY-001", product.product_no, [copy_text]),
                rule_ids=["SEM-COPY-001"],
                claims=[{"claim_id": "claim-copy-1", "text": copy_text[:500], "source_path": "copy_quality.targets"}],
                evidence=[_evidence("copy-quality-text", "copy_quality.targets", copy_text)],
                guards=SEMANTIC_GUARDS["SEM-COPY-001"],
            )
        )

    return packets

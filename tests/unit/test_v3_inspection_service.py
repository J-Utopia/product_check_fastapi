from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.models import InspectionRequest
from app.service import InspectionService


class FakeClient:
    def __init__(self) -> None:
        self.fetch_core_count = 0

    def fetch_all(self, product_no: str) -> dict[str, object]:
        return self._raw(product_no)

    def fetch_core(self, product_no: str) -> dict[str, object]:
        self.fetch_core_count += 1
        return self._raw(product_no)

    def _raw(self, product_no: str) -> dict[str, Any]:
        if product_no == "999999":
            long_detail = "상세 일정 설명 " * 200
            return {
                "package_info": {
                    "pName": "장기 일정 19박 20일",
                    "date": {"sdate": "2026-01-01", "edate": "2026-01-20", "night": 19, "days": 20},
                    "price": {"adult": 1000000},
                },
                "detail": {
                    "productName": "장기 일정 19박 20일",
                    "departureDate": "2026-01-01",
                    "arrivalDate": "2026-01-20",
                    "travelNight": 19,
                    "travelDays": 20,
                    "travelPeriod": "19박 20일",
                    "includedNote": "포함사항 " * 500,
                    "unincludedNote": "불포함사항 " * 500,
                    "meetingPlace2": "미팅장소 " * 500,
                },
                "schedule": {
                    "scheduleItemList": [
                        {
                            "first": day_no,
                            "date": f"2026-01-{day_no:02d}",
                            "placeHeader": [f"도시{day_no}"],
                            "otherActions": [
                                {
                                    "itiPlaceName": f"관광지{day_no}-{index}",
                                    "itiServiceName": "관광",
                                    "itiSummaryDes": f"{day_no}일차 관광 {index}",
                                    "itiDetailDes": long_detail,
                                    "itiSeq": index,
                                }
                                for index in range(8)
                            ],
                        }
                        for day_no in range(1, 21)
                    ]
                },
                "key_points": {"specialBenefits": ["장기 일정 핵심포인트"]},
            }
        return {
            "package_info": {
                "pName": "테스트 1박 2일",
                "pcode": "PKG",
                "computedProductCode": "PKG-001",
                "themes": [{"themeId": "T1", "themeName": "테마"}],
                "badges": {"prefixes": [{"title": "라이브M"}]},
                "shoppingCount": 3,
                "guideYn": "Y",
                "leaderYn": "N",
                "date": {"sdate": "2026-01-01", "edate": "2026-01-02", "night": 1, "days": 2},
                "price": {"adult": 100000},
                "beforeDicount": {"adult": 120000},
            },
            "detail": {
                "productName": "테스트 1박 2일",
                "productCode": "PKG",
                "departureDate": "2026-01-01",
                "arrivalDate": "2026-01-02",
                "travelNight": 1,
                "travelDays": 2,
                "travelPeriod": "1박 2일",
                "departureAirlineName": "테스트항공",
                "arrivalAirlineName": "테스트항공",
                "groupBriefKeyword": "#인솔자동반 #전용차량",
                "visitCities": ["서울", "부산"],
                "shoppingTimes": 3,
                "localRequiredExpenseOrNot": "Y",
                "localRequiredExpenseCall": "USD",
                "localRequiredExpense": 60,
                "localRequiredExpenseKid": 60,
                "localRequiredExpenseToddler": 0,
                "sellingPriceLandTotalAmount": 0,
                "meetingPlace": "인천공항",
                "meetingTime": "09:20",
                "includedNote": "왕복항공 포함",
                "unincludedNote": "개인경비 불포함",
            },
            "schedule": {
                "scheduleItemList": [
                    {"first": 1, "date": "2026-01-01", "placeHeader": ["서울"], "otherActions": []},
                    {"first": 2, "date": "2026-01-02", "placeHeader": ["부산"], "otherActions": []},
                ]
            },
            "key_points": {"specialBenefits": ["해운대 관광"]},
        }


def test_run_v3_returns_core_collection_plan_normal_case() -> None:
    client = FakeClient()
    service = InspectionService(client)

    response = service.run_v3(InspectionRequest(group_id="123456"))

    assert client.fetch_core_count == 1
    assert response.status == "ok"
    assert response.collection_plan.required == ["package_info", "detail", "schedule", "key_points"]
    assert len(response.collection_plan.required) == 4
    assert response.semantic_packets
    assert response.product.shopping_count == 3
    assert response.product.guide_fee == {
        "currency": "USD",
        "adult": 60,
        "child": 60,
        "infant": 0,
        "payment_method": "현지지불",
    }
    assert response.product.prices["selling_price_local_join"] == 0
    assert response.inspection_context["top_area"]["icons"]["shopping_count"] == 3
    assert response.inspection_context["main_schedule"]["visit_cities"] == ["서울", "부산"]
    assert response.inspection_context["prices"]["guide_fee"]["child"] == 60
    assert response.inspection_context["included_excluded"]["included_text"] == "왕복항공 포함"
    assert response.inspection_context["daily_schedule"]["days"][0]["day_no"] == 1


def test_run_v3_includes_text_quality_semantic_packet_normal_case() -> None:
    service = InspectionService(FakeClient())

    response = service.run_v3(InspectionRequest(group_id="123456"))
    packet = next(packet for packet in response.semantic_packets if "SEM-TEXT-001" in packet.rule_ids)

    assert packet.claims
    assert packet.evidence
    assert any("오타" in guard for guard in packet.guards)
    assert any(claim["source_path"] == "product.title" for claim in packet.claims)


def test_run_v3_cache_hit_failure_case_avoids_second_fetch() -> None:
    client = FakeClient()
    service = InspectionService(client)

    first = service.run_v3(InspectionRequest(group_id="123456"))
    second = service.run_v3(InspectionRequest(group_id="123456"))

    assert first.source.cache_status == "miss"
    assert second.source.cache_status == "hit"
    assert client.fetch_core_count == 1


def test_inspection_request_rejects_invalid_group_id_failure_case() -> None:
    with pytest.raises(ValidationError):
        InspectionRequest(group_id="MAT260119009")


def test_get_evidence_edge_case_returns_requested_ids_only() -> None:
    service = InspectionService(FakeClient())
    response = service.run_v3(InspectionRequest(group_id="123456"))
    evidence_id = response.semantic_packets[0].evidence[0].evidence_id

    evidence_response = service.get_evidence(response.inspection_id, f"{evidence_id},missing")

    assert evidence_response.inspection_id == response.inspection_id
    assert [item.evidence_id for item in evidence_response.evidence] == [evidence_id]


def test_run_v3_keeps_long_schedule_response_bounded_edge_case() -> None:
    service = InspectionService(FakeClient())

    response = service.run_v3(InspectionRequest(group_id="999999"))
    payload_size = len(json.dumps(response.model_dump(), ensure_ascii=False, default=str).encode("utf-8"))
    first_day_evidence_id = response.inspection_context["daily_schedule"]["days"][0]["evidence_id"]
    evidence_response = service.get_evidence(response.inspection_id, first_day_evidence_id)

    assert payload_size < 60_000
    assert response.inspection_context["daily_schedule"]["day_count"] == 20
    assert "itiDetailDes" not in json.dumps(response.inspection_context, ensure_ascii=False)
    assert evidence_response.evidence
    assert "상세 일정 설명" in evidence_response.evidence[0].excerpt

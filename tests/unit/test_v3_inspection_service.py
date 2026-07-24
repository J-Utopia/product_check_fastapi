from __future__ import annotations

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

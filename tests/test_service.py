from __future__ import annotations

from app.service import InspectionService


class StubClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def fetch_all(self, product_no: str) -> dict[str, object]:
        return self._payload


def test_service_returns_data_failure_for_missing_required_fields() -> None:
    payload = {
        "package_info": {"pName": "", "date": {}, "air": {}},
        "detail": {"productName": "", "departureDate": None, "arrivalDate": None},
        "schedule": {"scheduleItemList": []},
        "hotels": [],
        "flight_remarks": [],
        "key_points": {},
        "coupons": [],
    }
    envelope = InspectionService(StubClient(payload)).run("105195679")
    assert envelope.code == "DATA_FAILURE"
    assert envelope.result is None

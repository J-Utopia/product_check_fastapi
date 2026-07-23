from __future__ import annotations

from app.normalizer import normalize_product


def _raw_with_schedule_key(key: str) -> dict[str, object]:
    return {
        "package_info": {"pName": "테스트 1박 2일", "date": {"sdate": "2026-01-01", "night": 1, "days": 2}},
        "detail": {
            "productName": "테스트 1박 2일",
            "departureDate": "2026-01-01",
            "travelNight": 1,
            "travelDays": 2,
        },
        "schedule": {
            "scheduleItemList": [
                {
                    "first": 1,
                    "placeHeader": ["서울"],
                    key: [
                        {
                            "itiPlaceName": "경복궁",
                            "itiServiceName": "관광",
                            "itiSummaryDes": "경복궁 관람",
                        }
                    ],
                }
            ]
        },
    }


def test_normalize_product_reads_other_actions_normal_case() -> None:
    product = normalize_product("123456", _raw_with_schedule_key("otherActions"))

    assert product.schedule_days[0].others[0].place_name == "경복궁"


def test_normalize_product_reads_orther_actions_legacy_edge_case() -> None:
    product = normalize_product("123456", _raw_with_schedule_key("ortherActions"))

    assert product.schedule_days[0].others[0].summary == "경복궁 관람"

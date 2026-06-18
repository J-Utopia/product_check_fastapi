from __future__ import annotations

from app.normalizer import normalize_product


def test_normalizer_strips_style_noise_from_included_excluded() -> None:
    raw = {
        "package_info": {"pName": "테스트 상품", "date": {"sdate": "2026-06-20", "edate": "2026-06-24", "night": 4, "days": 5}, "air": {"countryName": "중국"}},
        "detail": {
            "productName": "테스트 상품 4박 5일",
            "departureDate": "2026-06-20",
            "arrivalDate": "2026-06-24",
            "travelNight": 4,
            "travelDays": 5,
            "includedNote": "<style>body{font-family:Pretendard;}</style><p>왕복항공료</p><p>숙박비</p>",
            "unincludedNote": "<style>.x{color:red;}</style><p>가이드/기사 경비</p>",
        },
        "schedule": {"scheduleItemList": [{"first": 1, "date": "2026-06-20T00:00:00"}]},
        "hotels": [],
        "flight_remarks": [],
        "key_points": {},
        "coupons": [{"title": "여름 쿠폰"}],
    }
    product = normalize_product("105195679", raw)
    assert product.included_items == ["왕복항공료", "숙박비"]
    assert product.excluded_items == ["가이드", "기사 경비"]
    assert product.coupon_count == 1
    assert product.coupon_titles == ["여름 쿠폰"]

from __future__ import annotations

from app.normalizer import normalize_product


def test_normalize_product_preserves_top_area_and_guide_fee_normal_case() -> None:
    product = normalize_product(
        "110954447",
        {
            "package_info": {
                "pName": "장가계 5박6일",
                "pcode": "CJE101RSA6P0F3",
                "computedProductCode": "CJE101RSA6P0F3",
                "themes": [{"themeId": "A", "themeName": "중국 패키지"}],
                "badges": {"prefixes": [{"title": "라이브M"}]},
                "shoppingCount": 3,
                "price": {"adult": 549000},
                "beforeDicount": {"adult": 599000},
            },
            "detail": {
                "productName": "장가계 5박6일",
                "travelPeriod": "4박 6일",
                "groupBriefKeyword": "#5성급호텔 #천문산",
                "visitCities": ["장가계", "원가계"],
                "shoppingTimes": 3,
                "localRequiredExpenseOrNot": "Y",
                "localRequiredExpenseCall": "$",
                "localRequiredExpense": 60,
                "localRequiredExpenseKid": 60,
                "localRequiredExpenseToddler": 0,
                "sellingPriceAdultTotalAmount": 549000,
                "sellingPriceKidETotalAmount": 549000,
                "sellingPriceToddlerTotalAmount": 28000,
                "sellingPriceLandTotalAmount": 0,
            },
            "schedule": {},
            "key_points": {},
        },
    )

    assert product.shopping_count == 3
    assert product.guide_fee_currency == "$"
    assert product.guide_fee_adult == 60
    assert product.guide_fee_child == 60
    assert product.guide_fee_infant == 0
    assert product.selling_price_local_join == 0
    assert product.before_discount_price_adult == 599000
    assert product.prefixes == ["라이브M"]
    assert product.group_brief_keywords == ["#5성급호텔", "#천문산"]
    assert product.visit_cities == ["장가계", "원가계"]


def test_normalize_product_handles_missing_guide_fee_failure_case() -> None:
    product = normalize_product(
        "123456",
        {
            "package_info": {"pName": "테스트"},
            "detail": {"productName": "테스트"},
            "schedule": {},
            "key_points": {},
        },
    )

    assert product.shopping_count is None
    assert product.guide_fee_adult is None
    assert product.guide_fee_child is None
    assert product.guide_fee_infant is None


def test_normalize_product_preserves_zero_values_edge_case() -> None:
    product = normalize_product(
        "123456",
        {
            "package_info": {"pName": "테스트", "price": {"adult": 0}, "beforeDicount": {"adult": 0}},
            "detail": {
                "productName": "테스트",
                "sellingPriceAdultTotalAmount": 0,
                "sellingPriceLandTotalAmount": 0,
                "localRequiredExpense": 0,
                "localRequiredExpenseKid": 0,
                "localRequiredExpenseToddler": 0,
            },
            "schedule": {},
            "key_points": {},
        },
    )

    assert product.display_price_adult == 0
    assert product.before_discount_price_adult == 0
    assert product.selling_price_adult == 0
    assert product.selling_price_local_join == 0
    assert product.guide_fee_adult == 0

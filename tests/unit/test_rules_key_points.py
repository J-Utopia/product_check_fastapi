from __future__ import annotations

from app.models import NormalizedProduct
from app.rules import RuleEngine


def _issue_ids(product: NormalizedProduct) -> list[str]:
    return [issue.rule_id for issue in RuleEngine().validate(product).issues]


def test_key_point_warning_is_not_raised_when_insurance_content_exists_normal_case() -> None:
    product = NormalizedProduct(
        product_no="109507118",
        product_name="동유럽 3국 8일",
        title="동유럽 3국 8일 <황금동선/3대도시 자유시간/2대야경투어>",
        traveler_insurance_text="여행자보험 가입 최대 1억원 보장",
    )

    assert "KP-001" not in _issue_ids(product)


def test_key_point_warning_is_raised_when_all_sales_points_are_empty_failure_case() -> None:
    product = NormalizedProduct(
        product_no="123456",
        product_name="테스트 상품",
        title="테스트 상품",
    )

    assert "KP-001" in _issue_ids(product)


def test_key_point_warning_is_not_raised_when_only_title_markers_exist_edge_case() -> None:
    product = NormalizedProduct(
        product_no="123456",
        product_name="동유럽 3국 8일",
        title="동유럽 3국 8일 <쉔부른궁전내부/할슈타트 마을>",
    )

    assert "KP-001" not in _issue_ids(product)

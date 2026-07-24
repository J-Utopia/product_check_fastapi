from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .models import EvidenceItem, Issue, NormalizedProduct, QualityScore


NIGHT_DAY_RE = re.compile(r"(\d+)\s*박\s*(\d+)\s*일")
TIME_RE = re.compile(r"^(\d{2}):(\d{2})$")
DURATION_RE = re.compile(r"([가-힣A-Za-z0-9\s]+?)\s*(\d{2,3})\s*분")

NO_TIP_PATTERNS = (
    "NO팁",
    "노팁",
    "NOTIP",
    "NO TIP",
    "노기사가이드경비",
    "NO기사가이드경비",
    "NO기사경비",
    "노기사경비",
    "NO가이드경비",
    "노가이드경비",
)
TIP_IGNORE_PATTERNS = ("매너팁", "호텔팁", "포터팁", "마사지팁", "식당팁")
NO_OPTION_PATTERNS = ("NO옵션", "노옵션", "NO OPTION", "NOOPTION")
NO_SHOPPING_PATTERNS = ("NO쇼핑", "노쇼핑", "NO SHOPPING", "NOSHOPPING")
MANDATORY_EXPENSE_PATTERNS = (
    "가이드경비",
    "기사경비",
    "가이드비",
    "기사비",
    "입장경비",
    "입장료",
    "필수경비",
)
OPTION_PRESENT_PATTERNS = ("선택관광", "옵션", "$", "USD", "유료")
SHOPPING_PRESENT_PATTERNS = ("쇼핑센터", "쇼핑", "구매", "매장", "특산품점")
GENERAL_PASSPORT_EXCEPTION_PATTERNS = ("일반 여권 이외", "일반여권 이외", "개인비자 필요", "중국 대사관 개별 문의")
HOTEL_MARKETING_TOKENS = (
    "호텔",
    "리조트",
    "글램핑",
    "숙박",
    "캡슐",
    "유리",
    "별채",
    "풀빌라",
    "초원",
    "온천",
    "프리미엄",
)
HOTEL_THEME_TOKENS = ("캡슐", "유리", "별채", "풀빌라", "초원", "온천", "글램핑", "프리미엄", "리조트")
TEXT_REPLACEMENT_PATTERNS = ("�", "占")
KEY_POINT_TITLE_MARKERS = ("<", ">", "#")
RULE_TEXT_LIMIT = 400


def _excerpt(value: str) -> str:
    return value[:180]


def _normalize_token(value: str) -> str:
    return re.sub(r"[\s\-_/|()<>\[\]{}:#,.'\"`~!@?$%^&*+=]+", "", value).upper()


def _contains_token(text: str, token: str) -> bool:
    normalized_token = _normalize_token(token)
    if not normalized_token:
        return False
    return normalized_token in _normalize_token(text)


def _contains_any(text: str, tokens: Iterable[str]) -> bool:
    return any(_contains_token(text, token) for token in tokens)


def _extract_title_terms(title: str) -> list[str]:
    stopwords = {
        "출발확정",
        "조기예약",
        "특가",
        "직항",
        "항공",
        "항공확정",
        "노팁",
        "노옵션",
        "노쇼핑",
        "노기사경비",
        "노가이드경비",
        "NO팁",
        "NO옵션",
        "NO쇼핑",
        "NO기사경비",
        "NO기사가이드경비",
        "NOTIP",
        "NOOPTION",
        "NOSHOPPING",
    }
    parts = [part.strip() for part in re.split(r"[<>/()+\[\]\-|]", title) if part.strip()]
    terms: list[str] = []
    normalized_stopwords = {_normalize_token(word) for word in stopwords}
    for part in parts:
        compact = part.strip()
        if len(compact) < 2:
            continue
        if _normalize_token(compact) in normalized_stopwords:
            continue
        if compact.isdigit():
            continue
        terms.append(compact)
    return terms


def _extract_meaningful_tokens(value: str) -> list[str]:
    raw_parts = re.split(r"[\s,/+|()\[\]<>-]+", value)
    tokens: list[str] = []
    for part in raw_parts:
        compact = part.strip().lstrip("#")
        if len(compact) < 2:
            continue
        if compact.isdigit():
            continue
        if compact.upper() in {"NO", "TIP", "SHOPPING", "OPTION"}:
            continue
        tokens.append(compact)
    return tokens


def _joined_day_texts(product: NormalizedProduct) -> str:
    chunks: list[str] = []
    for day in product.schedule_days:
        chunks.extend(day.route_headers)
        chunks.extend(day.place_names)
        chunks.append(day.schedule_hotel_text)
        for event in [*day.meals, *day.guides, *day.hotels, *day.transports, *day.others]:
            chunks.extend([event.place_name, event.service_name, event.summary, _rule_text(event.detail)])
    return " | ".join(chunk for chunk in chunks if chunk)


def _issue(
    rule_id: str,
    level: str,
    title: str,
    message: str,
    suggestion: str,
    evidence: list[tuple[str, str]],
) -> Issue:
    return Issue(
        rule_id=rule_id,
        level=level,  # type: ignore[arg-type]
        title=title,
        message=message,
        suggestion=suggestion,
        evidence=[EvidenceItem(field=field, value_excerpt=_excerpt(value)) for field, value in evidence],
    )


def _parse_minutes(value: str | None) -> int | None:
    if not value:
        return None
    match = TIME_RE.match(value.strip())
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def _parse_duration(value: str | None) -> int | None:
    return _parse_minutes(value)


def _compact_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _rule_text(value: str) -> str:
    compact = _compact_space(value)
    if len(compact) <= RULE_TEXT_LIMIT:
        return compact
    return compact[:RULE_TEXT_LIMIT]


def _extract_duration_claims(values: Iterable[str]) -> dict[str, set[int]]:
    claims: dict[str, set[int]] = {}
    for value in values:
        for name, minutes_text in DURATION_RE.findall(value):
            normalized_name = _compact_space(name)
            if len(normalized_name) < 2:
                continue
            claims.setdefault(normalized_name, set()).add(int(minutes_text))
    return claims


def _has_key_point_content(product: NormalizedProduct) -> bool:
    structured_values = [
        *product.special_benefits,
        *product.sightseeings,
        *product.key_point_hotels,
        *product.key_point_meals,
        *product.key_point_golfs,
        *product.product_point_items,
        *product.top_badges,
        *product.hashtags,
        product.product_point_text,
        product.key_point_leader_guild,
        product.traveler_insurance_text,
        product.expected_tour_mileage_text,
        product.business_guarantee,
        product.product_score,
        product.selling_price,
    ]
    if any(_compact_space(value) for value in structured_values):
        return True
    return any(marker in product.title for marker in KEY_POINT_TITLE_MARKERS)


def _score(issues: list[Issue]) -> QualityScore:
    score = 100
    for issue in issues:
        if issue.level == "FATAL":
            score -= 25
        elif issue.level == "ERROR":
            score -= 10
        elif issue.level == "WARN":
            score -= 4
        elif issue.level == "INFO":
            score -= 1

    score = max(score, 0)
    if score >= 95:
        grade = "A"
    elif score >= 85:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 50:
        grade = "D"
    else:
        grade = "F"
    return QualityScore(score=score, grade=grade)


@dataclass
class ValidationResult:
    issues: list[Issue]
    quality: QualityScore


class RuleEngine:
    def validate(self, product: NormalizedProduct) -> ValidationResult:
        issues: list[Issue] = []
        issues.extend(self._validate_title_and_summary(product))
        issues.extend(self._validate_included_excluded(product))
        issues.extend(self._validate_air(product))
        issues.extend(self._validate_key_points(product))
        issues.extend(self._validate_hotel_and_meeting(product))
        issues.extend(self._validate_day_logic(product))
        issues.extend(self._validate_point_consistency(product))
        issues.extend(self._validate_text_quality(product))
        return ValidationResult(issues=issues, quality=_score(issues))

    def _validate_title_and_summary(self, product: NormalizedProduct) -> list[Issue]:
        issues: list[Issue] = []
        title = product.title
        period_match = NIGHT_DAY_RE.search(title)
        if period_match and product.nights is not None and product.days is not None:
            title_nights = int(period_match.group(1))
            title_days = int(period_match.group(2))
            if title_nights != product.nights or title_days != product.days:
                issues.append(
                    _issue(
                        "TITLE-001",
                        "ERROR",
                        "제목 박수/일수 불일치",
                        "제목의 박수/일수와 API 기간 정보가 다르다.",
                        "제목 또는 기간 정보를 다시 맞춰야 한다.",
                        [("product.title", title), ("normalized.nights_days", f"{product.nights}박 {product.days}일")],
                    )
                )

        if product.days is not None and product.schedule_days and len(product.schedule_days) != product.days:
            issues.append(
                _issue(
                    "PERIOD-001",
                    "ERROR",
                    "일정 일수 불일치",
                    "상품 일수와 일정표의 실제 일차 수가 다르다.",
                    "일차 수 또는 상품 기간을 다시 확인해야 한다.",
                    [("normalized.days", str(product.days)), ("schedule.days_count", str(len(product.schedule_days)))],
                )
            )

        if _contains_any(title, NO_SHOPPING_PATTERNS) and (product.shopping_count or 0) > 0:
            issues.append(
                _issue(
                    "TITLE-002",
                    "ERROR",
                    "노쇼핑 문구 불일치",
                    "노쇼핑 문구가 있는데 쇼핑 횟수가 0보다 크다.",
                    "쇼핑 횟수 또는 제목 문구를 맞춰야 한다.",
                    [("product.title", title), ("normalized.shopping_count", str(product.shopping_count or 0))],
                )
            )

        if _contains_any(title, NO_OPTION_PATTERNS) and product.optional_tour_or_not == "Y":
            issues.append(
                _issue(
                    "TITLE-003",
                    "ERROR",
                    "노옵션 문구 불일치",
                    "노옵션 문구가 있는데 선택관광 정보가 존재한다.",
                    "선택관광 여부 또는 제목 문구를 정리해야 한다.",
                    [("product.title", title), ("normalized.optional_tour_or_not", product.optional_tour_or_not or "")],
                )
            )

        if _contains_any(title, NO_TIP_PATTERNS):
            included_has_fees = _contains_any(product.included_text, MANDATORY_EXPENSE_PATTERNS) or any(
                _contains_any(item, MANDATORY_EXPENSE_PATTERNS) for item in product.included_items
            )
            excluded_has_fees = _contains_any(product.excluded_text, MANDATORY_EXPENSE_PATTERNS) or any(
                _contains_any(item, MANDATORY_EXPENSE_PATTERNS) for item in product.excluded_items
            )
            excluded_has_ignored_tip = _contains_any(product.excluded_text, TIP_IGNORE_PATTERNS) or any(
                _contains_any(item, TIP_IGNORE_PATTERNS) for item in product.excluded_items
            )
            if excluded_has_fees and not included_has_fees and not excluded_has_ignored_tip:
                issues.append(
                    _issue(
                        "TITLE-004",
                        "ERROR",
                        "노팁/기사경비 문구 불일치",
                        "노팁 계열 문구가 있는데 불포함 항목에 필수 가이드/기사 경비가 남아 있다.",
                        "노팁, 기사경비, 가이드경비 표기를 다시 정리해야 한다.",
                        [("product.title", title), ("normalized.excluded_text", product.excluded_text)],
                    )
                )

        title_terms = _extract_title_terms(title)
        searchable = " ".join(
            [
                product.product_name,
                " ".join(product.city_names),
                " ".join(product.country_names),
                " ".join(product.hashtags),
                " ".join(product.special_benefits),
                " ".join(product.sightseeings),
                " ".join(product.key_point_hotels),
                " ".join(product.key_point_meals),
                " ".join(product.key_point_golfs),
                " ".join(product.included_items),
                " ".join(product.excluded_items),
                _joined_day_texts(product),
            ]
        )
        if title_terms:
            missing_terms = [term for term in title_terms if term not in searchable]
            if missing_terms and len(missing_terms) <= max(1, len(title_terms) // 2):
                issues.append(
                    _issue(
                        "TITLE-005",
                        "WARN",
                        "제목 핵심표현 근거 확인 필요",
                        "제목의 일부 핵심 표현이 일정표나 상단 정보에서 바로 확인되지 않는다.",
                        "제목 표현이 실제 일정 근거와 연결되는지 재확인해야 한다.",
                        [("product.title", title), ("normalized.searchable_text", searchable)],
                    )
                )

        return issues

    def _validate_included_excluded(self, product: NormalizedProduct) -> list[Issue]:
        issues: list[Issue] = []
        if not product.included_text and not product.excluded_text:
            return issues

        visa_text = f"{product.included_text} {product.excluded_text} {product.notice_text}"
        if _contains_any(visa_text, ("비자", "무비자")) and "중국" in product.country_names:
            visa_free_markers = ("무비자", "비자면제", "면제")
            visa_required_markers = ("비자필요", "비자 신청", "비자발급", "비자비용", "사전비자")
            if _contains_any(visa_text, visa_free_markers) and _contains_any(visa_text, visa_required_markers):
                if not _contains_any(visa_text, GENERAL_PASSPORT_EXCEPTION_PATTERNS):
                    issues.append(
                        _issue(
                            "DOC-001",
                            "WARN",
                            "비자 문구 충돌",
                            "비자 면제/무비자와 비자 필요 문구가 동시에 나타난다.",
                            "비자 안내를 하나의 기준으로 다시 정리해야 한다.",
                            [("normalized.excluded_text", product.excluded_text), ("normalized.notice_text", product.notice_text)],
                        )
                    )

        if _contains_any(product.included_text, NO_TIP_PATTERNS) and _contains_any(product.excluded_text, TIP_IGNORE_PATTERNS):
            issues.append(
                _issue(
                    "DOC-002",
                    "WARN",
                    "팁 표기 혼합",
                    "포함/불포함 영역에 노팁과 매너팁 계열이 함께 보인다.",
                    "선택성 팁과 필수 경비를 분리해서 표기해야 한다.",
                    [("normalized.included_text", product.included_text), ("normalized.excluded_text", product.excluded_text)],
                )
            )

        return issues

    def _validate_air(self, product: NormalizedProduct) -> list[Issue]:
        issues: list[Issue] = []
        segments = product.air_segments
        if not segments and (product.departure_flight or product.return_flight):
            issues.append(
                _issue(
                    "AIR-000",
                    "ERROR",
                    "항공 구간 누락",
                    "항공 편명은 있는데 일정표의 항공 구간이 비어 있다.",
                    "항공 구간 데이터가 누락되지 않았는지 확인해야 한다.",
                    [("normalized.departure_flight", product.departure_flight or ""), ("normalized.return_flight", product.return_flight or "")],
                )
            )
            return issues

        if len(segments) == 1 and product.direct_flight is False:
            seg = segments[0]
            issues.append(
                _issue(
                    "AIR-001",
                    "ERROR",
                    "경유 항공 구간 부족",
                    "경유로 표시되는데 항공 구간이 1개뿐이다.",
                    "경유 구간 누락 여부를 확인해야 한다.",
                    [("normalized.direct_flight", str(product.direct_flight)), ("air_segments[0].flight_no", seg.flight_no or "")],
                )
            )

        if len(segments) >= 2:
            first = segments[0]
            last = segments[-1]
            if first.departure_city_name and last.arrival_city_name and first.departure_city_name != last.arrival_city_name:
                issues.append(
                    _issue(
                        "AIR-002",
                        "ERROR",
                        "출발/리턴 도시 불일치",
                        "출발 도시와 최종 도착 도시가 서로 다르다.",
                        "실제 출발/귀국 공항과 항공편을 다시 확인해야 한다.",
                        [("air.first.departure_city_name", first.departure_city_name), ("air.last.arrival_city_name", last.arrival_city_name)],
                    )
                )

        for segment in segments:
            duration_minutes = _parse_duration(segment.duration)
            if duration_minutes is not None and duration_minutes > 18 * 60:
                issues.append(
                    _issue(
                        "AIR-003",
                        "WARN",
                        "항공 소요시간 이상치",
                        "항공 소요시간이 비정상적으로 길다.",
                        "경유 또는 대기시간 반영 방식이 맞는지 확인해야 한다.",
                        [("air.duration", segment.duration or ""), ("air.flight_no", segment.flight_no or "")],
                    )
                )
                break

        if product.departure_flight and not any(product.departure_flight in (seg.flight_no or "") for seg in segments):
            issues.append(
                _issue(
                    "AIR-004",
                    "ERROR",
                    "출국편 편명 불일치",
                    "상품 상세의 출국편과 일정표 항공 편명이 일치하지 않는다.",
                    "편명 표기 또는 항공 구간을 수정해야 한다.",
                    [("normalized.departure_flight", product.departure_flight or ""), ("schedule.air", " / ".join(seg.flight_no or "" for seg in segments))],
                )
            )

        if product.return_flight and not any(product.return_flight in (seg.flight_no or "") for seg in segments):
            issues.append(
                _issue(
                    "AIR-005",
                    "ERROR",
                    "귀국편 편명 불일치",
                    "상품 상세의 귀국편과 일정표 항공 편명이 일치하지 않는다.",
                    "편명 표기 또는 항공 구간을 수정해야 한다.",
                    [("normalized.return_flight", product.return_flight or ""), ("schedule.air", " / ".join(seg.flight_no or "" for seg in segments))],
                )
            )

        if product.direct_flight is True and any(seg.is_transit for seg in segments):
            issues.append(
                _issue(
                    "AIR-006",
                    "ERROR",
                    "직항/경유 상충",
                    "직항으로 표시되지만 일정표 항공 구간에는 경유 표시가 있다.",
                    "직항 문구 또는 항공 구간 정보를 일치시켜야 한다.",
                    [("normalized.direct_flight", str(product.direct_flight)), ("schedule.air", " / ".join(seg.flight_no or "" for seg in segments))],
                )
            )

        if product.city_names:
            title_and_flow = " ".join(
                [
                    product.title,
                    " ".join(product.hashtags),
                    " ".join(product.city_names),
                    " ".join(header for day in product.schedule_days for header in day.route_headers),
                    " ".join(place for day in product.schedule_days for place in day.place_names),
                ]
            )
            title_terms = _extract_title_terms(product.title)
            missing_geo_terms = [term for term in title_terms if term not in title_and_flow]
            if missing_geo_terms and len(missing_geo_terms) <= max(1, len(title_terms) // 2):
                issues.append(
                    _issue(
                        "AIR-007",
                        "WARN",
                        "여행도시/지명 상충 가능성",
                        "제목의 일부 도시나 지명이 일정 흐름에서 바로 확인되지 않는다.",
                        "도시명과 실제 방문 흐름의 연결 여부를 재확인해야 한다.",
                        [("product.title", product.title), ("normalized.city_names", " / ".join(product.city_names))],
                    )
                )

        return issues

    def _validate_key_points(self, product: NormalizedProduct) -> list[Issue]:
        issues: list[Issue] = []
        if not _has_key_point_content(product):
            issues.append(
                _issue(
                    "KP-001",
                    "WARN",
                    "핵심포인트 정보 부족",
                    "핵심포인트 영역에 사용할 만한 정보가 거의 없다.",
                    "스페셜 혜택, 관광, 호텔, 식사, 가이드 정보를 보강해야 한다.",
                    [("key_points", " / ".join([product.key_point_leader_guild, product.business_guarantee, product.product_score, product.selling_price]))],
                )
            )

        hotel_blob = " ".join(hotel.hotel_name for hotel in product.hotels)
        if product.key_point_hotels and product.hotels and not any(hotel_name in hotel_blob for hotel_name in product.key_point_hotels):
            issues.append(
                _issue(
                    "KP-002",
                    "WARN",
                    "핵심포인트 호텔명 불명확",
                    "핵심포인트 호텔명과 실제 호텔명이 바로 연결되지 않는다.",
                    "핵심포인트의 호텔 문구를 실제 숙박명에 맞춰야 한다.",
                    [("key_point_hotels", " / ".join(product.key_point_hotels)), ("normalized.hotels", " / ".join(hotel.hotel_name for hotel in product.hotels))],
                )
            )

        meal_blob = " ".join(ev.summary + ev.detail for day in product.schedule_days for ev in day.meals)
        if product.key_point_meals and meal_blob and not any(meal in meal_blob for meal in product.key_point_meals):
            issues.append(
                _issue(
                    "KP-003",
                    "WARN",
                    "핵심포인트 식사명 불명확",
                    "핵심포인트 식사명이 일정의 식사와 바로 연결되지 않는다.",
                    "식사 항목과 핵심포인트 설명을 맞춰야 한다.",
                    [("key_point_meals", " / ".join(product.key_point_meals)), ("schedule.meals", meal_blob)],
                )
            )

        hotel_evidence_blob = " ".join(
            [
                hotel_blob,
                " ".join(day.schedule_hotel_text for day in product.schedule_days if day.schedule_hotel_text),
                " ".join(product.key_point_hotels),
            ]
        )
        for benefit in product.special_benefits:
            if not _contains_any(benefit, HOTEL_MARKETING_TOKENS):
                continue
            benefit_tokens = [token for token in _extract_meaningful_tokens(benefit) if len(token) >= 2]
            theme_tokens = [token for token in benefit_tokens if _contains_any(token, HOTEL_THEME_TOKENS)]
            tokens_to_check = theme_tokens or benefit_tokens
            if not any(_contains_token(hotel_evidence_blob, token) for token in tokens_to_check):
                issues.append(
                    _issue(
                        "KP-004",
                        "WARN",
                        "핵심포인트 숙박 표현 근거 부족",
                        f"핵심포인트 문구 '{benefit}'를 뒷받침할 숙박 근거가 실제 호텔/일정 데이터에서 바로 확인되지 않는다.",
                        "핵심포인트 문구를 실제 숙박명에 맞게 구체화하거나, 해당 숙박 근거가 일정표에 드러나도록 조정해야 한다.",
                        [("special_benefits", benefit), ("normalized.hotels", hotel_blob)],
                    )
                )
                break

        searchable_blob = " ".join(
            [
                " ".join(product.city_names),
                " ".join(product.special_benefits),
                " ".join(product.sightseeings),
                " ".join(product.key_point_hotels),
                " ".join(product.key_point_meals),
                _joined_day_texts(product),
            ]
        )
        for hashtag in product.hashtags:
            tokens = _extract_meaningful_tokens(hashtag)
            if tokens and not any(_contains_token(searchable_blob, token) for token in tokens):
                issues.append(
                    _issue(
                        "KP-005",
                        "WARN",
                        "해시태그 근거 부족",
                        f"해시태그 '{hashtag}'를 뒷받침할 도시/관광/일정 근거가 현재 추출 데이터에서 바로 확인되지 않는다.",
                        "해시태그가 실제 방문지, 숙박지, 핵심포인트와 연결되는지 확인해야 한다.",
                        [("hashtags", hashtag), ("normalized.city_names", " / ".join(product.city_names))],
                    )
                )
                break

        if not product.traveler_insurance_text:
            issues.append(
                _issue(
                    "KP-006",
                    "INFO",
                    "보험 정보 확인 필요",
                    "여행자 보험 관련 문구가 추출 데이터에서 확인되지 않는다.",
                    "보험 안내가 실제 일정표에 있다면 API 추출 범위나 추출 위치를 다시 확인해야 한다.",
                    [("traveler_insurance_text", product.traveler_insurance_text)],
                )
            )

        if not product.expected_tour_mileage_text:
            issues.append(
                _issue(
                    "KP-007",
                    "INFO",
                    "마일리지 정보 확인 필요",
                    "예상 마일리지 문구가 추출 데이터에서 확인되지 않는다.",
                    "마일리지 항목이 실제 일정표에 있다면 API 필드 연결 여부를 확인해야 한다.",
                    [("expected_tour_mileage_text", product.expected_tour_mileage_text)],
                )
            )

        return issues

    def _validate_hotel_and_meeting(self, product: NormalizedProduct) -> list[Issue]:
        issues: list[Issue] = []

        if product.nights is not None and product.hotels:
            hotel_days = sorted({hotel.day_no for hotel in product.hotels if hotel.day_no > 0})
            if hotel_days and len(hotel_days) != product.nights:
                issues.append(
                    _issue(
                        "HOTEL-001",
                        "WARN",
                        "숙박 박수 확인 필요",
                        "예정호텔이 배정된 숙박 일차 수가 상품 박수와 다르다.",
                        "예정호텔 일차와 실제 박수를 다시 확인해야 한다.",
                        [("normalized.nights", str(product.nights)), ("normalized.hotel_days", " / ".join(str(day) for day in hotel_days))],
                    )
                )

        if product.meeting_place_text and not product.meeting_time:
            issues.append(
                _issue(
                    "MEETING-001",
                    "WARN",
                    "미팅시간 누락 가능성",
                    "미팅 장소 안내는 있으나 미팅 시간이 비어 있다.",
                    "미팅 시간 또는 장소 안내를 다시 확인해야 한다.",
                    [("normalized.meeting_place_text", product.meeting_place_text), ("normalized.meeting_time", product.meeting_time or "")],
                )
            )

        guide_blob = " ".join(
            [
                product.key_point_leader_guild,
                product.guide_status or "",
                product.leader_status or "",
                " ".join(item.get("title", "") for item in product.guide_info),
                " ".join(item.get("text", "") for item in product.guide_info),
            ]
        )
        if product.guide_yn == "Y" and not guide_blob.strip():
            issues.append(
                _issue(
                    "GUIDE-001",
                    "WARN",
                    "가이드 표기 상충",
                    "가이드 동행 정보는 있으나 핵심포인트나 상품 정보에 가이드 상태가 드러나지 않는다.",
                    "가이드 동행 여부를 핵심포인트 또는 상품 정보에 명확히 표시해야 한다.",
                    [("normalized.guide_yn", product.guide_yn or ""), ("normalized.key_point_leader_guild", product.key_point_leader_guild)],
                )
            )

        hotel_blob = " ".join(hotel.hotel_name for hotel in product.hotels if hotel.hotel_name)
        title_hotel_terms = [
            token
            for token in _extract_meaningful_tokens(product.title)
            if _contains_any(token, HOTEL_MARKETING_TOKENS)
        ]
        missing_title_hotels = [term for term in title_hotel_terms if not _contains_token(hotel_blob, term)]
        if missing_title_hotels and hotel_blob:
            issues.append(
                _issue(
                    "HOTEL-002",
                    "WARN",
                    "상품명 호텔 문구 근거 부족",
                    "상품명에 보이는 호텔/리조트 계열 문구를 실제 예정호텔에서 바로 확인하기 어렵다.",
                    "상품명의 숙박 홍보 문구가 실제 예정호텔과 연결되는지 다시 확인해야 한다.",
                    [("product.title", product.title), ("normalized.hotels", hotel_blob)],
                )
            )

        return issues

    def _validate_point_consistency(self, product: NormalizedProduct) -> list[Issue]:
        issues: list[Issue] = []

        source_claims = _extract_duration_claims(
            [
                product.title,
                product.product_point_text,
                *product.product_point_items,
                *product.special_benefits,
                *product.sightseeings,
                *product.key_point_meals,
                *product.key_point_hotels,
            ]
        )
        schedule_claims = _extract_duration_claims(
            [
                _joined_day_texts(product),
                *[day.schedule_hotel_text for day in product.schedule_days],
            ]
        )
        for source_name, source_minutes in source_claims.items():
            for schedule_name, schedule_minutes in schedule_claims.items():
                if not (
                    _contains_token(source_name, schedule_name) or _contains_token(schedule_name, source_name)
                ):
                    continue
                if source_minutes != schedule_minutes:
                    issues.append(
                        _issue(
                            "POINT-001",
                            "ERROR",
                            "핵심포인트/일정 시간 정보 상충",
                            f"핵심포인트의 '{source_name}' 소요시간과 일자별 일정의 시간이 서로 다르다.",
                            "핵심포인트와 실제 일정표의 소요시간 표기를 하나로 맞춰야 한다.",
                            [
                                ("key_points.duration", f"{source_name}: {sorted(source_minutes)}"),
                                ("schedule.duration", f"{schedule_name}: {sorted(schedule_minutes)}"),
                            ],
                        )
                    )
                    return issues

        return issues

    def _validate_day_logic(self, product: NormalizedProduct) -> list[Issue]:
        issues: list[Issue] = []
        if not product.schedule_days:
            return issues

        day_numbers = [day.day_no for day in product.schedule_days]
        if day_numbers != sorted(day_numbers) or day_numbers[0] != 1 or len(set(day_numbers)) != len(day_numbers):
            issues.append(
                _issue(
                    "DAY-001",
                    "ERROR",
                    "일차 번호 불연속",
                    "일차 번호가 1부터 순서대로 이어지지 않거나 중복된다.",
                    "Day 번호를 순서대로 다시 맞춰야 한다.",
                    [("schedule.day_numbers", " / ".join(str(x) for x in day_numbers))],
                )
            )

        dates = [day.date for day in product.schedule_days if day.date]
        if len(dates) >= 2:
            parsed = []
            for date_text in dates:
                try:
                    parsed.append(datetime.fromisoformat(date_text.replace("Z", "")))
                except ValueError:
                    continue
            if len(parsed) >= 2 and any(b <= a for a, b in zip(parsed, parsed[1:])):
                issues.append(
                    _issue(
                        "DAY-002",
                        "ERROR",
                        "일자 순서 불일치",
                        "일정표의 날짜가 일차 순서대로 증가하지 않는다.",
                        "일정 날짜 순서를 다시 맞춰야 한다.",
                        [("schedule.dates", " / ".join(dates))],
                    )
                )

        for day in product.schedule_days:
            day_text = " ".join(
                [
                    day.schedule_hotel_text,
                    " ".join(day.route_headers),
                    " ".join(day.place_names),
                    " ".join(
                        item.service_name + item.summary + _rule_text(item.detail)
                        for item in [*day.meals, *day.guides, *day.hotels, *day.transports, *day.others]
                    ),
                ]
            )
            if _contains_any(day_text, OPTION_PRESENT_PATTERNS) and product.optional_tour_or_not == "N":
                issues.append(
                    _issue(
                        "DAY-004",
                        "ERROR",
                        "선택관광 여부 충돌",
                        f"{day.day_no}일차 일정에는 선택관광 또는 유료 옵션 표현이 있는데 상품은 선택관광 없음으로 보인다.",
                        "선택관광 여부 또는 일정 문구를 다시 확인해야 한다.",
                        [("day.text", day_text), ("normalized.optional_tour_or_not", product.optional_tour_or_not or "")],
                    )
                )
                break

            if _contains_any(day_text, SHOPPING_PRESENT_PATTERNS) and (product.shopping_count or 0) == 0:
                issues.append(
                    _issue(
                        "DAY-005",
                        "ERROR",
                        "쇼핑 여부 충돌",
                        f"{day.day_no}일차 일정에는 쇼핑 표현이 있는데 상품은 쇼핑 0회로 보인다.",
                        "쇼핑 횟수 또는 일정 문구를 다시 확인해야 한다.",
                        [("day.text", day_text), ("normalized.shopping_count", str(product.shopping_count or 0))],
                    )
                )
                break

        return issues

    def _validate_text_quality(self, product: NormalizedProduct) -> list[Issue]:
        issues: list[Issue] = []
        text_targets = [
            product.included_text,
            product.excluded_text,
            product.meeting_place_text,
            product.meeting_info_text,
            " ".join(remark.remark for remark in product.flight_remarks),
            " ".join(product.coupon_titles),
        ]
        if any(any(pattern in target for pattern in TEXT_REPLACEMENT_PATTERNS) for target in text_targets if target):
            issues.append(
                _issue(
                    "TEXT-001",
                    "WARN",
                    "문자 인코딩 이상치",
                    "일부 문구에 깨진 문자나 치환 문자가 포함되어 있다.",
                    "원본 HTML 또는 API 텍스트 인코딩을 다시 확인해야 한다.",
                    [("normalized.text_targets", " | ".join(target for target in text_targets if target))],
                )
            )
        return issues

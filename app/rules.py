from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .models import EvidenceItem, FlightSegment, Issue, NormalizedProduct, QualityScore


NIGHT_DAY_RE = re.compile(r"(\d+)\s*박\s*(\d+)\s*일")
TIME_RE = re.compile(r"^(\d{2}):(\d{2})$")
NO_TIP_PATTERNS = ("NO팁", "노팁", "NOTIP", "NO TIP", "노기사가이드경비", "NO기사가이드경비", "NO기사경비", "노기사경비", "NO가이드경비", "노가이드경비")
TIP_IGNORE_PATTERNS = ("매너팁", "호텔팁", "포터팁", "마사지팁", "식당팁")
NO_OPTION_PATTERNS = ("NO옵션", "노옵션", "NO OPTION", "NOOPTION")
NO_SHOPPING_PATTERNS = ("NO쇼핑", "노쇼핑", "NO SHOPPING", "NOSHOPPING")
MANDATORY_EXPENSE_PATTERNS = ("가이드경비", "기사경비", "가이드비", "기사비", "현지경비", "현지의무경비")


def _excerpt(value: str) -> str:
    return value[:180]


def _normalize_token(value: str) -> str:
    return re.sub(r"[\s\-_/|()<>\[\]{}:#,.'\"`~!@?$%^&*+=]+", "", value).upper()


def _contains_token(text: str, token: str) -> bool:
    return _normalize_token(token) in _normalize_token(text)


def _contains_any(text: str, tokens: Iterable[str]) -> bool:
    return any(_contains_token(text, token) for token in tokens)


def _extract_title_terms(title: str) -> list[str]:
    stopwords = {
        "출발확정",
        "유류ZERO",
        "유류고정",
        "직항",
        "왕복",
        "왕복항공",
        "4박5일",
        "3박4일",
        "5일",
        "5박6일",
        "노팁",
        "노옵션",
        "노쇼핑",
        "노기사가이드경비",
        "NO기사가이드경비",
        "NO기사경비",
        "NO가이드경비",
        "NO옵션",
        "NO쇼핑",
        "no팁",
        "no옵션",
        "no쇼핑",
    }
    parts = [part.strip() for part in re.split(r"[<>/()+\[\]\-|]", title) if part.strip()]
    terms: list[str] = []
    for part in parts:
        compact = part.strip()
        if len(compact) < 2:
            continue
        if _normalize_token(compact) in {_normalize_token(word) for word in stopwords}:
            continue
        if compact.isdigit():
            continue
        terms.append(compact)
    return terms


def _joined_day_texts(product: NormalizedProduct) -> str:
    chunks: list[str] = []
    for day in product.schedule_days:
        chunks.extend(day.route_headers)
        chunks.extend(day.place_names)
        chunks.append(day.schedule_hotel_text)
        for event in [*day.meals, *day.guides, *day.hotels, *day.transports, *day.others]:
            chunks.extend([event.place_name, event.service_name, event.summary, event.detail])
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
        issues.extend(self._validate_day_logic(product))
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
                        "제목의 박수/일수와 API 기간이 다릅니다.",
                        "제목 또는 기간 정보를 정합하게 수정하세요.",
                        [("product.title", title), ("normalized.nights_days", f"{product.nights}박 {product.days}일")],
                    )
                )

        if product.days is not None and product.schedule_days and len(product.schedule_days) != product.days:
            issues.append(
                _issue(
                    "PERIOD-001",
                    "ERROR",
                    "일정 일수 불일치",
                    "상품 일수와 일정표 일차 수가 다릅니다.",
                    "일차 수 또는 상품 기간을 재확인하세요.",
                    [
                        ("normalized.days", str(product.days)),
                        ("schedule.days_count", str(len(product.schedule_days))),
                    ],
                )
            )

        if _contains_any(title, NO_SHOPPING_PATTERNS) and (product.shopping_count or 0) > 0:
            issues.append(
                _issue(
                    "TITLE-002",
                    "ERROR",
                    "노쇼핑 문구 불일치",
                    "노쇼핑 문구가 있으나 쇼핑 횟수가 0보다 큽니다.",
                    "쇼핑 횟수 또는 제목 문구를 정합하게 수정하세요.",
                    [("product.title", title), ("normalized.shopping_count", str(product.shopping_count or 0))],
                )
            )

        if _contains_any(title, NO_OPTION_PATTERNS) and product.optional_tour_or_not == "Y":
            issues.append(
                _issue(
                    "TITLE-003",
                    "ERROR",
                    "노옵션 문구 불일치",
                    "노옵션 문구가 있으나 선택관광이 존재합니다.",
                    "선택관광 여부 또는 제목 문구를 정리하세요.",
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
                        "노팁 계열 문구가 있으나 불포함 사항에 필수 가이드/기사 경비가 노출됩니다.",
                        "노팁, 기사경비, 가이드경비 표기를 함께 정리하세요.",
                        [("product.title", title), ("normalized.excluded_text", product.excluded_text)],
                    )
                )

        title_terms = _extract_title_terms(title)
        searchable = " | ".join(
            [
                product.product_name,
                " ".join(product.city_names),
                " ".join(product.country_names),
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
                        "제목 핵심지명 검증 필요",
                        "제목의 일부 핵심지명이 일정/핵심포인트/포함불포함에서 바로 확인되지 않습니다.",
                        "핵심 지명이나 테마가 실제 일정에 존재하는지 재확인하세요.",
                        [("product.title", title), ("normalized.searchable_text", searchable)],
                    )
                )

        return issues

    def _validate_included_excluded(self, product: NormalizedProduct) -> list[Issue]:
        issues: list[Issue] = []
        if not product.included_text and not product.excluded_text:
            return issues

        if _contains_any(product.excluded_text, ("비자", "여권")) and "중국" in product.country_names:
            visa_free_markers = ("무비자", "비자면제", "면제")
            visa_required_markers = ("비자필요", "비자 신청", "비자신청", "비자 발급", "비자발급", "비자비용", "유료비자")
            if _contains_any(product.excluded_text + " " + product.included_text, visa_free_markers) and _contains_any(
                product.excluded_text + " " + product.included_text, visa_required_markers
            ):
                issues.append(
                    _issue(
                        "DOC-001",
                        "WARN",
                        "비자 문구 충돌",
                        "비자 면제/무비자와 비자 필요 문구가 동시에 노출됩니다.",
                        "비자 안내를 하나의 기준으로 정리하세요.",
                        [("normalized.included_text", product.included_text), ("normalized.excluded_text", product.excluded_text)],
                    )
                )

        if _contains_any(product.included_text, NO_TIP_PATTERNS) and _contains_any(product.excluded_text, TIP_IGNORE_PATTERNS):
            issues.append(
                _issue(
                    "DOC-002",
                    "WARN",
                    "팁 표기 혼합",
                    "포함/불포함 영역에 노팁과 매너팁 계열이 섞여 있습니다.",
                    "매너팁은 안내용으로만 두고 필수 경비와 분리하세요.",
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
                    "항공 편명은 있는데 일정표 항공 구간이 비어 있습니다.",
                    "항공구간이 실제로 내려오지 않았는지 확인하세요.",
                    [("normalized.departure_flight", product.departure_flight or ""), ("normalized.return_flight", product.return_flight or "")],
                )
            )
            return issues

        if len(segments) == 1:
            seg = segments[0]
            if product.direct_flight is False:
                issues.append(
                    _issue(
                        "AIR-001",
                        "ERROR",
                        "경유 항공 구간 부족",
                        "경유로 표시되는데 일정상 항공 구간이 1개뿐입니다.",
                        "경유 구간이 누락되었는지 확인하세요.",
                        [("normalized.direct_flight", str(product.direct_flight)), ("air_segments[0].flight_no", seg.flight_no or "")],
                    )
                )

        if len(segments) >= 2:
            first = segments[0]
            last = segments[-1]
            if first.departure_city_name and last.arrival_city_name and first.departure_city_name == last.arrival_city_name:
                pass
            elif first.departure_city_name and last.arrival_city_name and first.departure_city_name != last.arrival_city_name:
                issues.append(
                    _issue(
                        "AIR-002",
                        "ERROR",
                        "출발/리턴 지역 불일치",
                        "출발 도시와 귀국 도착 도시가 서로 다릅니다.",
                        "실제 출발/귀국 공항과 항공편을 다시 확인하세요.",
                        [
                            ("air.first.departure_city_name", first.departure_city_name or ""),
                            ("air.last.arrival_city_name", last.arrival_city_name or ""),
                        ],
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
                        "항공 소요시간이 비정상적으로 깁니다.",
                        "경유/대기 시간 반영이 정확한지 확인하세요.",
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
                    "상품 상세 출국편과 일정표 항공편명이 일치하지 않습니다.",
                    "편명 표기를 맞추거나 항공 구간을 수정하세요.",
                    [("normalized.departure_flight", product.departure_flight or ""), ("schedule.air", " / ".join(seg.flight_no or "" for seg in segments))],
                )
            )

        if product.return_flight and not any(product.return_flight in (seg.flight_no or "") for seg in segments):
            issues.append(
                _issue(
                    "AIR-005",
                    "ERROR",
                    "귀국편 편명 불일치",
                    "상품 상세 귀국편과 일정표 항공편명이 일치하지 않습니다.",
                    "귀국편 표기를 맞추거나 항공 구간을 수정하세요.",
                    [("normalized.return_flight", product.return_flight or ""), ("schedule.air", " / ".join(seg.flight_no or "" for seg in segments))],
                )
            )

        if product.direct_flight is True and any(seg.is_transit for seg in segments):
            issues.append(
                _issue(
                    "AIR-006",
                    "ERROR",
                    "직항/경유 상충",
                    "직항으로 표시되지만 일정표 항공 구간에는 경유 표기가 있습니다.",
                    "직항 문구 또는 항공 구간을 정합하게 수정하세요.",
                    [("normalized.direct_flight", str(product.direct_flight)), ("schedule.air", " / ".join(seg.flight_no or "" for seg in segments))],
                )
            )

        if product.city_names:
            title_and_flow = " ".join(
                [
                    product.title,
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
                        "여행도시/지역 상충 가능성",
                        "제목의 일부 여행도시 또는 지역이 일정표 흐름에서 바로 확인되지 않습니다.",
                        "도시/지역명이 실제 일정, 호텔, 항공 중 어디에 매핑되는지 다시 확인하세요.",
                        [("product.title", product.title), ("normalized.city_names", " / ".join(product.city_names))],
                    )
                )

        return issues

    def _validate_key_points(self, product: NormalizedProduct) -> list[Issue]:
        issues: list[Issue] = []
        if not any([product.special_benefits, product.sightseeings, product.key_point_hotels, product.key_point_meals, product.key_point_golfs]):
            issues.append(
                _issue(
                    "KP-001",
                    "WARN",
                    "핵심포인트 부족",
                    "핵심포인트 탭에서 활용할 내용이 거의 없습니다.",
                    "스페셜 혜택, 관광, 호텔, 식사, 가이드 정보를 보강하세요.",
                    [("key_points", " / ".join([product.key_point_leader_guild, product.business_guarantee, product.product_score, product.selling_price]))],
                )
            )

        hotel_blob = " ".join(hotel.hotel_name for hotel in product.hotels)
        if product.key_point_hotels and product.hotels and not any(hotel_name in hotel_blob for hotel_name in product.key_point_hotels):
            issues.append(
                _issue(
                    "KP-002",
                    "WARN",
                    "핵심호텔명 재확인",
                    "핵심포인트 호텔명과 실제 호텔명 사이에 즉시 매칭되는 값이 없습니다.",
                    "호텔명이 실제 일정/호텔 API와 일치하는지 확인하세요.",
                    [("key_point_hotels", " / ".join(product.key_point_hotels)), ("normalized.hotels", " / ".join(hotel.hotel_name for hotel in product.hotels))],
                )
            )

        meal_blob = " ".join(ev.summary + ev.detail for day in product.schedule_days for ev in day.meals)
        if product.key_point_meals and meal_blob and not any(meal in meal_blob for meal in product.key_point_meals):
            issues.append(
                _issue(
                    "KP-003",
                    "WARN",
                    "핵심식사명 재확인",
                    "핵심포인트 식사명이 일정표 식사와 바로 연결되지 않습니다.",
                    "식사 항목과 핵심포인트 설명을 맞춰주세요.",
                    [("key_point_meals", " / ".join(product.key_point_meals)), ("schedule.meals", meal_blob)],
                )
            )

        return issues

    def _validate_day_logic(self, product: NormalizedProduct) -> list[Issue]:
        issues: list[Issue] = []
        if product.schedule_days:
            day_numbers = [day.day_no for day in product.schedule_days]
            if day_numbers != sorted(day_numbers) or day_numbers[0] != 1 or len(set(day_numbers)) != len(day_numbers):
                issues.append(
                    _issue(
                        "DAY-001",
                        "ERROR",
                        "일차 번호 불연속",
                        "일차 번호가 1부터 연속되지 않거나 중복됩니다.",
                        "Day 번호를 순서대로 다시 맞추세요.",
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
                            "일차 날짜가 순차 증가하지 않습니다.",
                            "일정 날짜 순서를 다시 맞추세요.",
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
                            item.service_name + item.summary + item.detail
                            for item in [*day.meals, *day.guides, *day.hotels, *day.transports, *day.others]
                        ),
                    ]
                )
                if _contains_any(day_text, NO_OPTION_PATTERNS) and product.optional_tour_or_not == "N":
                    issues.append(
                        _issue(
                            "DAY-004",
                            "ERROR",
                            "선택관광 표기 충돌",
                            f"{day.day_no}일차에 선택관광 문구가 있으나 상품상 선택관광 없음으로 보입니다.",
                            "선택관광 여부 또는 일정 문구를 다시 확인하세요.",
                            [("day.text", day_text), ("normalized.optional_tour_or_not", product.optional_tour_or_not or "")],
                        )
                    )
                    break
                if _contains_any(day_text, NO_SHOPPING_PATTERNS) and (product.shopping_count or 0) > 0:
                    issues.append(
                        _issue(
                            "DAY-005",
                            "ERROR",
                            "쇼핑 표기 충돌",
                            f"{day.day_no}일차에 노쇼핑 문구가 있으나 상품상 쇼핑 횟수가 존재합니다.",
                            "쇼핑 횟수와 일정 문구를 다시 맞추세요.",
                            [("day.text", day_text), ("normalized.shopping_count", str(product.shopping_count or 0))],
                        )
                    )
                    break

        return issues


def _parse_duration(value: str | None) -> int | None:
    if not value:
        return None
    match = re.match(r"^(\d{2}):(\d{2})$", value.strip())
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))

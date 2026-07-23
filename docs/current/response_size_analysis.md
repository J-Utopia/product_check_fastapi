# Response Size Analysis

## 현재 구현된 계측

`app/observability.py`의 `measure_payloads`가 다음 값을 계산한다.

- `raw_bytes`
- `normalized_bytes`
- `compact_bytes`
- `schedule_day_count`
- `schedule_event_count`
- `gpt_text_chars`
- `duplicate_text_count`

`InspectionService.run`은 검수 성공 시 위 값을 logging한다.

## 현재 확인된 응답 폭증 요인

- `CompactDaySummary.place_names`는 일차별 최대 8개로 절단된다.
- `CompactDaySummary.highlights`는 일차별 최대 6개로 절단된다.
- `CompactNormalizedProduct.product_point_text`는 800자로 절단된다.
- 위 방식은 크기는 줄이지만 evidence-first 압축이 아니어서 필요한 근거가 빠질 수 있다.

## 실제 수치 산출 상태

실제 모두투어 API fixture가 아직 없으므로 상품 유형별 수치는 미측정이다.

필요 fixture:

- `short_general`
- `europe_long`
- `missing_tabs`
- `no_shopping`
- `optional_tour`
- `guide_fee`

## 다음 단계

1. 실제 API 응답을 `tests/fixtures/raw/*`에 저장한다.
2. 기존 `/run-itinerary` 결과를 `tests/golden/v2_current/*.json`에 저장한다.
3. `measure_payloads` 로그를 fixture별로 수집한다.
4. 긴 일정에서 `compact_bytes`와 `gpt_text_chars`가 일정 이벤트 수에 비례해 폭증하는지 확인한다.

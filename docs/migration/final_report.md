# 최종 보고

## 추가된 실제 오류 사례

- `tests/fixtures/real_cases/real_error_case_catalog.json`에 첨부 프롬프트의 28개 신규 테스트 항목을 등록했다.
- 실제 운영 사례 원문 파일 `오류 예시 안.md`는 현재 작업 폴더와 Desktop에서 확인되지 않았다.
- 각 사례의 `source_status`는 `prompt_only`로 표시했다.

## 신규 deterministic 규칙

- 이번 단계에서는 기존 `RuleEngine` 규칙을 v3 `deterministic.results` 형식으로 변환한다.
- 모든 deterministic issue는 `status`, `evidence`, `source_path`, `suggestion`, `deduction`, `confidence`를 포함한다.
- 신규 실제 사례 규칙의 전체 handler 분리는 다음 단계 작업이다.

## 신규 semantic 규칙

- `SEM-POINT-001`
- `SEM-TITLE-PLACE-001`
- `SEM-FREETIME-001`
- `SEM-INEX-001`
- `SEM-COPY-001`

## 추가된 정규화 필드

- `otherActions`와 `ortherActions`를 모두 지원하도록 일정 기타 이벤트 호환 처리를 추가했다.
- `app/data/location_aliases.json`에 별칭 사전 초기 파일을 추가했다.

## 과검출 방지 조건

- GPTs 의미검수룰 v2에 guard를 명시했다.
- 실제 사례 카탈로그에도 `false_positive_guards`를 사례별로 포함했다.

## 자동 검수 불가 항목

- 이미지 문맥 검수는 이미지 원본 또는 URL이 없으면 `not_evaluated` 대상이다.
- 최신 비자 규정 검수는 공식 기준 데이터가 없으면 `not_evaluated` 대상이다.
- 지역/호텔/일정 복사 오류 중 의미 판단이 필요한 항목은 semantic packet 대상이다.

## 테스트 결과

```text
python -m pytest
9 passed

python -m mypy app
Success: no issues found in 12 source files
```

## 기존 결과와의 차이

- 기존 `/run-itinerary`는 유지했다.
- 신규 `/v3/inspections`와 `/v3/inspections/{inspection_id}/evidence`를 병행 추가했다.
- 실제 상품별 golden master diff는 유효한 숫자형 단체번호가 없어 생성하지 못했다.

## 추가 확인이 필요한 데이터

- 유효한 숫자형 단체번호 6종: 일반, 장기 유럽, 탭 누락, 노쇼핑, 선택관광, 가이드경비
- 실제 운영 사례 원문 `오류 예시 안.md`
- 상품 페이지 JS chunk 또는 source map
- GPTs 관리자 화면에 반영할 실제 FastAPI host URL

# Rule Inventory

현재 `app/rules.py`의 `RuleEngine` 기준이다.

| rule_id | level | 현재 성격 | 목표 분류 | 비고 |
|---|---|---|---|---|
| TITLE-001 | ERROR | 확정형 | deterministic | 제목 박수/일수 |
| PERIOD-001 | ERROR | 확정형 | deterministic | 상품 일수와 일정 일차 수 |
| TITLE-002 | ERROR | 확정형 | deterministic | 노쇼핑 |
| TITLE-003 | ERROR | 확정형 | deterministic | 노옵션 |
| TITLE-004 | ERROR | 확정형 | deterministic | 노팁/필수경비 |
| TITLE-005 | WARN | 의미 추정 | semantic | 제목 핵심표현 근거 확인 |
| DOC-001 | WARN | 확정 후보 | deterministic 또는 semantic | 비자 문구 내부 충돌만 가능 |
| DOC-002 | WARN | 확정 후보 | deterministic | 팁 표기 혼합 |
| AIR-000 | ERROR | 확정형 | deterministic | 항공 구간 누락 |
| AIR-001 | ERROR | 확정형 | deterministic | 경유 항공 구간 부족 |
| AIR-002 | ERROR | 확정형 | deterministic | 출발/리턴 도시 불일치 |
| AIR-003 | WARN | 이상치 | deterministic | 소요시간 상한 |
| AIR-004 | ERROR | 확정형 | deterministic | 출국편 편명 불일치 |
| AIR-005 | ERROR | 확정형 | deterministic | 귀국편 편명 불일치 |
| AIR-006 | ERROR | 확정형 | deterministic | 직항/경유 상충 |
| AIR-007 | WARN | 의미 추정 | semantic | 지명 상충 가능성 |
| KP-001 | WARN | 데이터 품질 | deterministic | 핵심포인트 정보 부족 |
| KP-002 | WARN | 의미 추정 | semantic | 호텔명 연결 |
| KP-003 | WARN | 의미 추정 | semantic | 식사명 연결 |
| KP-004 | WARN | 의미 추정 | semantic | 숙박 표현 근거 |
| KP-005 | WARN | 의미 추정 | semantic | 해시태그 근거 |
| KP-006 | INFO | 데이터 품질 | deterministic | 보험 정보 |
| KP-007 | INFO | 데이터 품질 | deterministic | 마일리지 |
| HOTEL-001 | WARN | 확정 후보 | deterministic | 숙박 박수 |
| MEETING-001 | WARN | 확정 후보 | deterministic | 미팅시간 |
| GUIDE-001 | WARN | 상태 비교 | deterministic | 가이드 표기 |
| HOTEL-002 | WARN | 의미 추정 | semantic | 상품명 호텔 문구 |
| POINT-001 | ERROR | 확정형 | deterministic | 시간 정보 상충 |
| DAY-001 | ERROR | 확정형 | deterministic | 일차 번호 |
| DAY-002 | ERROR | 확정형 | deterministic | 일자 순서 |
| DAY-004 | ERROR | 확정형 | deterministic | 선택관광 여부 |
| DAY-005 | ERROR | 확정형 | deterministic | 쇼핑 여부 |
| TEXT-001 | WARN | 확정형 | deterministic | 깨진 문자 |

## 추가 프롬프트 기준 신규 규칙 후보

아래 규칙은 아직 구현하지 않았고, 실제 사례 파일 `오류 예시 안.md`가 없어 case catalog를 확정할 수 없다.

- `PRICE-CHILD-001`
- `PRICE-CHILD-002`
- `LEADER-STATUS-001`
- `AIR-DURATION-001`
- `AIRLINE-CONSISTENCY-001`
- `SCHEDULE-DUP-001`
- `BENEFIT-DURATION-001`
- `BENEFIT-COUNT-001`
- `LOCATION-CONSISTENCY-001`
- `OPTIONAL-STRUCTURE-001`
- `PRODUCT-CONDITION-001`
- `AIRPORT-BENEFIT-001`
- `PRODUCT-TYPE-GUIDE-001`
- `HOTEL-NAME-001`
- `HOTEL-NIGHT-FLOW-001`
- `RETURN-DATE-001`
- `INEX-STRUCTURE-001`
- `TEXT-KO-001`
- `IMAGE-CONTEXT-001`
- `VISA-001`

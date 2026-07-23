# GPTs Duplication Analysis

## 현재 상태

- FastAPI는 legacy `/run-itinerary`를 유지하고, GPTs v2용 `/v3/inspections`를 병행 제공한다.
- GPTs 세팅용 OpenAPI는 `gpts/GPTs_OpenAPI_v2.yaml`만 사용한다.
- 기존 GPT 지침 및 검증룰 파일은 legacy 자료로 판단해 삭제했다. 현재 GPTs 세팅 산출물은 `gpts/` 폴더의 v2 파일만 사용한다.
- 첨부 프롬프트 기준으로 GPTs는 FastAPI가 이미 계산한 `issues`를 받은 뒤 검증룰 JSON과 지식 MD를 다시 적용한다.

## 중복 가능성이 높은 영역

- 제목 박수/일수
- 노쇼핑/노옵션/노팁
- 항공 직항/경유
- 포함/불포함 문구
- 핵심포인트와 일정의 의미상 구현 여부
- 문구 품질

## 목표 상태

- Python은 `deterministic.results`만 확정한다.
- GPT는 `semantic_packets`만 판단한다.
- GPT가 Python 확정 오류를 재계산하거나 번복하지 않는다.
- GPT Action 기본 호출은 단체번호당 `/v3/inspections` 1회다.
- `/evidence`는 최종 판정에 추가 excerpt가 꼭 필요할 때만 1회 호출한다.

## 현재 미구현

- 조건부 상세 evidence 정책 고도화
- GPTs 실제 관리자 화면 반영
- semantic packet builder의 규칙군 확대

## 구현 완료

- `/v3/inspections`
- `/v3/inspections/{inspection_id}/evidence`
- semantic packet builder 1차 구현
- GPTs v2 지침/의미검수룰/OpenAPI 파일 작성

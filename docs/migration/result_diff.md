# Result Diff

Phase 1에서는 기존 검수 판정 로직을 변경하지 않았다.

## 변경된 동작

- `otherActions` 일정 기타 이벤트 키를 추가 지원한다.
- 기존 `ortherActions` 키도 그대로 지원한다.
- 성공 응답 생성 시 payload metrics를 로그로 남긴다.
- API endpoint별 status/time/size metrics를 로그로 남긴다.
- 신규 `/v3/inspections` endpoint를 추가했다.
- 신규 `/v3/inspections/{inspection_id}/evidence` endpoint를 추가했다.
- v3 기본 호출은 core 4개 endpoint로 제한하고 `hotels`, `flight_remarks`, `coupons`는 skip reason을 반환한다.
- GPTs v2용 지침, OpenAPI, 의미검수룰, 출력스키마 파일을 추가했다.

## 기존 결과와 신규 결과

실제 API fixture와 golden master가 아직 없어 상품별 diff는 미작성이다.

기본 seed `MAT260119009`로 fixture 수집을 시도했으나 `GetProductDetailInfo`가 다음 오류를 반환했다.

```text
400 {"errorCode":"productNo","errorMessage":"The value 'MAT260119009' is not valid."}
```

따라서 실제 fixture/golden master 생성은 유효한 숫자형 단체번호가 필요하다.

## 사용자 승인 필요 여부

- 관찰 가능성 로그 추가: 승인 불필요
- `otherActions` 호환 지원: 누락 데이터 복구 가능성이 있는 버그 수정으로 판단
- `/v3/inspections` 추가: 기존 `/run-itinerary` 병행 유지로 기존 GPTs 동작 영향 없음
- 실제 상품별 결과 차이: fixture 수집 후 별도 확인 필요

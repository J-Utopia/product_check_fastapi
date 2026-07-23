# API Endpoint Inventory

## 현재 호출 목록

| 내부 이름 | endpoint path | 현재 호출 정책 | 프롬프트 기준 목표 정책 | 확인 상태 |
|---|---|---|---|---|
| package_info | `/Package/GetPackageInfo` | 항상 호출 | core, 항상 호출 | confirmed |
| schedule | `/Package/GetScheduleList` | 항상 호출 | core, 항상 호출 | confirmed |
| detail | `/Package/GetProductDetailInfo` | 항상 호출 | core, 항상 호출 | confirmed |
| hotels | `/Package/GetHotelList` | 항상 호출 | 조건부 호출 | confirmed |
| flight_remarks | `/Package/GetFlightRemarkList` | 항상 호출 | 조건부 호출 | confirmed |
| key_points | `/Package/GetProductKeyPointInfo` | 항상 호출 | core, 항상 호출 | confirmed |
| coupons | `/Coupon/GetPackageCouponList` | 항상 호출 | 명시 요청 시에만 호출 | confirmed |

## 현재 계측

`ModeTourApiClient._fetch_one`에서 endpoint별로 다음 값을 logging한다.

```text
endpoint
productNo
status_code
elapsed_ms
content_length
```

## 미구현 목표

- `CollectionPlan`은 `/v3/inspections` 응답에 1차 구현했다.
- endpoint registry의 `required_by_rules`, `default_enabled`
- raw fixture 저장
- 핵심 4개와 조건부 API의 부분 실패 정책
- `httpx.AsyncClient` 재사용
- 제한적 retry 및 401/403 시 헤더 1회 갱신

## v3 현재 정책

`/v3/inspections`는 기본 호출을 다음 4개로 제한한다.

```text
package_info
detail
schedule
key_points
```

아래 endpoint는 v3 기본 검수에서 skip reason과 함께 제외된다.

```text
hotels
flight_remarks
coupons
```

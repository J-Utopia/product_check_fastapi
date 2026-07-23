# Field Mapping

이 문서는 현재 코드에서 확인한 매핑만 기록한다. 실제 API fixture 또는 JS 분석으로 확인되지 않은 필드는 확정하지 않는다.

| canonical field | 현재 source 후보 | 현재 코드 위치 | 확인 상태 |
|---|---|---|---|
| `product_no` | request `group_id` | `normalize_product(product_no, raw)` | confirmed |
| `product_name` | `detail.productName`, `package_info.pName` | `normalizer.py` | confirmed |
| `title` | `detail.productName`, `package_info.pName` | `normalizer.py` | confirmed |
| `product_code` | `detail.productCode`, `package_info.pcode` | `normalizer.py` | partial |
| `computed_product_code` | `package_info.computedProductCode` | `normalizer.py` | partial |
| `top_badges` | `package_info.badges` | `normalizer.py` | partial |
| `hashtags` | `tags`, `hashTags`, `hashtags` 후보 | `normalizer.py` | partial |
| `departure_date` | `detail.departureDate`, `package_info.date.sdate` | `normalizer.py` | partial |
| `arrival_date` | `detail.arrivalDate`, `package_info.date.edate` | `normalizer.py` | partial |
| `nights` | `detail.travelNight`, `package_info.date.night` | `normalizer.py` | partial |
| `days` | `detail.travelDays`, `package_info.date.days` | `normalizer.py` | partial |
| `departure_airline_name` | `detail.departureAirlineName`, `package_info.air.airLineName` | `normalizer.py` | partial |
| `return_airline_name` | `detail.arrivalAirlineName` | `normalizer.py` | partial |
| `included_text` | `detail.includedNote` | `normalizer.py` | confirmed |
| `excluded_text` | `detail.unincludedNote` | `normalizer.py` | confirmed |
| `meeting_place_text` | `detail.meetingPlace2` | `normalizer.py` | partial |
| `meeting_info_text` | `detail.meetingInfo` | `normalizer.py` | partial |
| `display_price_adult` | `package_info.price.adult`, `adultPrice`, `priceAdult` | `normalizer.py` | partial |
| `selling_price_child_no_bed` | `detail.sellingPriceKidNTotalAmount`, `sellingPriceKidN` | `normalizer.py` | partial |
| `selling_price_child_extra_bed` | `detail.sellingPriceKidETotalAmount`, `sellingPriceKidE` | `normalizer.py` | partial |
| `schedule_days[].others` | `schedule.scheduleItemList[].otherActions`, legacy `ortherActions` | `normalizer.py` | partial |

## 확인 필요 필드

- `before_discount_price_adult`
- `selling_price_local_join`
- `fuel_surcharge_included`
- `tax_included`
- `guide_fee_currency`, `guide_fee_adult`, `guide_fee_child`, `guide_fee_infant`
- `reserved_count`, `valid_seat_count`, `minimum_departure_count`
- `leader_confirmed`, `departure_confirmed`, `price_confirmed`, `schedule_confirmed`, `hotel_confirmed`, `air_confirmed`
- `meetingPlace`, `meetingPlace2`, `meetingInfo`, `meetingTime`의 실제 우선순위

# 현재 API 검증 메모

검증 일시: 2026-06-18  
검증 대상: `https://b2c-api.modetour.com`

## 핵심 사실

- `productNo` 기반 일정표 API는 익명 GET 호출 시 `401 Unauthorized`가 발생한다.
- 모두투어 웹 페이지에서 캡처한 요청 헤더 중 `modewebapireqheader`가 포함되면 일정표 API 호출이 성공한다.
- 그룹 일정표 호출 시 `x-incomming-pathname`은 `/product-common/{productNo}?type=group` 형식으로 맞추는 것이 안전하다.

## 헤더 캡처 기준

- 시드 페이지: `https://www.modetour.com/product-common/{MAT코드}?type=single`
- 캡처 대상 요청: `POST /Package/GetProductMaster`
- 재사용 핵심 헤더:
  - `modewebapireqheader`
  - `x-platform`
  - `x-salespartner`
  - `x-username`
  - `x-userid`
  - `x-userdepartment`
  - `user-agent`
  - `accept`

## 실호출 검증 결과

샘플 `productNo`: `105195679`

- `GetPackageInfo`: `200 OK`
- `GetScheduleList`: `200 OK`
- `GetProductDetailInfo`: `200 OK`
- `GetHotelList`: `200 OK`
- `GetFlightRemarkList`: `200 OK`
- `GetProductKeyPointInfo`: `200 OK`
- `GetPackageCouponList`: `200 OK`

## 실제 확인한 중요 필드

### GetPackageInfo

- `result.pnum`
- `result.pcode`
- `result.computedProductCode`
- `result.pName`
- `result.air.countryName`
- `result.air.airLineName`
- `result.air.startAir`
- `result.date.sdate`
- `result.date.edate`
- `result.date.night`
- `result.date.days`
- `result.shoppingCount`
- `result.guideYn`
- `result.leaderYn`

### GetScheduleList

- `result.scheduleItemList[].first`
- `result.scheduleItemList[].date`
- `result.scheduleItemList[].placeHeader`
- `result.scheduleItemList[].scheduleHotel`
- `result.scheduleItemList[].listAirRouteInfo`
- `result.scheduleItemList[].listMealPlace`
- `result.scheduleItemList[].listGuidePlace`
- `result.scheduleItemList[].listHotelPlace`
- `result.scheduleItemList[].ortherActions`

### GetProductDetailInfo

- `result.productName`
- `result.departureDate`
- `result.arrivalDate`
- `result.departureFlight`
- `result.arrivalFlight`
- `result.directFlightOrNot`
- `result.meetingTime`
- `result.meetingInfo`
- `result.meetingPlace2`
- `result.includedNote`
- `result.unincludedNote`
- `result.shoppingNote`
- `result.shoppingTimes`
- `result.optionalTourOrNot`
- `result.localRequiredExpenseOrNot`
- `result.localRequiredExpense`
- `result.hotelConfirm`
- `result.flightConfirm`
- `result.departureAirlineName`
- `result.arrivalAirlineName`

### GetHotelList

- `result[].first`
- `result[].date`
- `result[].listHotelPlaceData[].placeNameK`
- `result[].listHotelPlaceData[].cityName`
- `result[].listHotelPlaceData[].countryName`
- `result[].listHotelPlaceData[].highlightDes`
- `result[].listHotelPlaceData[].contactWay`

### GetFlightRemarkList

- `result[].infoName`
- `result[].remark`

### GetProductKeyPointInfo

- `result.specialBenefits`
- `result.sightseeings`
- `result.leaderGuildStatus`
- `result.leaderStatus`
- `result.travelerInsuranceInfo`
- `result.guideInfo`

## 메모

- `ortherActions`는 실제 오탈자 필드명으로 존재했다.
- `유의 ㅣ 안내사항` 같은 표기는 실제 데이터에 존재하므로 무조건 오류로 잡으면 안 된다.
- 호텔 주소 일부는 `?`가 섞인 깨짐이 있어 텍스트 품질 검수는 보수적으로 처리해야 한다.

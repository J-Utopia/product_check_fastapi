# JS UI Mapping

실제 상품 페이지 JS chunk 또는 source map이 제공되지 않았으므로 이 문서는 현재 코드와 첨부 프롬프트 기준의 조사 항목만 기록한다. JS 확인 전에는 API 경로를 확정하지 않는다.

| 화면영역 | UI 문구/아이콘 | JS 조건 | API | JSON 경로 | 파생 규칙 | 확인 상태 |
|---|---|---|---|---|---|---|
| 상품 상단 | 상품명 | unknown | GetPackageInfo, GetProductDetailInfo | `pName`, `productName` 후보 | 제목/기간/지명 규칙 | partial |
| 상품 상단 | 인솔자 아이콘 | unknown | GetPackageInfo, GetProductDetailInfo | `leaderYn`, `leaderStatus` 후보 | LEADER-STATUS-001 | partial |
| 상품 상단 | 항공 아이콘 | unknown | GetPackageInfo, GetProductDetailInfo | `air`, `departureAirlineName` 후보 | AIRLINE-CONSISTENCY-001 | partial |
| 상품 상단 | 선택관광 | unknown | GetProductDetailInfo | `optionalTourOrNot` 후보 | OPTIONAL-STRUCTURE-001 | partial |
| 핵심포인트 | 탭 표시 | unknown | GetProductKeyPointInfo | `specialBenefits`, `sightseeings`, `hotels`, `meals` 후보 | SEM-POINT-001 | partial |
| 포함/불포함 | 포함사항 | unknown | GetProductDetailInfo | `includedNote` | INEX-STRUCTURE-001 | confirmed |
| 포함/불포함 | 불포함사항 | unknown | GetProductDetailInfo | `unincludedNote` | INEX-STRUCTURE-001 | confirmed |
| 미팅정보 | 미팅 시간/장소 | unknown | GetProductDetailInfo | `meetingPlace`, `meetingPlace2`, `meetingInfo`, `meetingTime` 후보 | MEETING-001 | partial |
| 여행 주요일정 | 항공/도시/예약인원 | unknown | GetScheduleList, GetProductDetailInfo | unknown | AIR-DURATION-001, RETURN-DATE-001 | unknown |
| 가격 | 성인/아동/유아/현지합류/가이드경비 | unknown | GetPackageInfo, GetProductDetailInfo | 일부 가격 필드 후보만 확인 | PRICE-CHILD-001, PRICE-CHILD-002 | partial |

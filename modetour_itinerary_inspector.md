## 목적

모두투어 일정표 품질 검수 GPTs 재구축용 핵심 문서

목표는 오타 검수가 아니라,

```text
여러 데이터 간 불일치를 찾는 일정표 검수 엔진 구축
```

---

# 전체 구조

```text
사용자
↓
GPTs
↓
FastAPI
↓
모두투어 API
↓
정규화 JSON
↓
검증룰(JSON)
↓
GPT 추론
↓
검수 결과
```

원칙

* FastAPI = 사실
* GPT = 판단

---

# 설계 철학

GPT는 데이터를 생성하지 않는다.

반드시

```text
실제 API 데이터
+
검증룰
```

기반으로 판단한다.

정상 구조를 오류로 만드는 것보다

오류를 놓치는 것이 낫다.

---

# 오류 생성 원칙

오류 생성 조건

```text
A 데이터
VS
B 데이터
```

2개 이상의 독립 데이터 충돌

가능

* 상단 항공 ↔ 일정표
* 호텔 ↔ 제목
* 포함 ↔ 불포함
* 미팅 ↔ 항공

금지

* 단일 문장
* 일반 상식
* 가능성만으로 오류 생성

---

# API 히스토리

## 상품 후보 조회

```text
POST
https://b2c-api.modetour.com/Package/SearchProductMaster
```

사용 목적

상품 후보 풀 확보

---

## Payload 핵심

필수

```text
areaId
searchFrom
searchTo
startingPoint
page
pageSize
```

의미 조건은 API에 넣지 않는다.

금지

```text
가족여행
힐링
자유일정
가성비
```

---

## 응답에서 사용한 필드

```text
masterCode
masterCodeId
masterProductName
descriptions
tags
price
dates
airNames
URL
```

---

# 자연어 검색 구조

```text
사용자 질문
↓
LLM 의도 분석
↓
후보 지역 결정
↓
SearchProductMaster
↓
상품 후보 확보
↓
LLM 의미 필터
↓
최종 추천
```

핵심

```text
LLM = 방향 결정

API = 후보 제공

LLM = 의미 선별
```

---

# FastAPI 역할

담당

* API 호출
* 데이터 수집
* JSON 정규화

담당하지 않음

* 추론
* 오류 판단

패키지

```text
fastapi
uvicorn
requests
```

---

# GPTs Action

Endpoint

```text
POST /run-itinerary
```

입력

```json
{
 "group_id":"..."
}
```

단체번호 입력 시

API 호출 필수

---

# GPTs 원칙

금지

* API 없이 추론
* 빈 데이터 보완
* 일반 상식 사용

필수 필드

```text
departure_date
product_name
itinerary
nights
countries
```

누락 시

```text
데이터 수신 실패
```

---

# Validation Layer

## RULE-01

제목 검증

비교

```text
title
↔ air
↔ itinerary
↔ hotel
```

검증

* 국가
* 도시
* 박수
* 동일호텔
* 노옵션
* 노쇼핑
* 자유일정

---

## RULE-02

항공 교차검증

비교

```text
상단 항공
↔ 일정표
```

검증

* 출국편
* 귀국편
* 직항
* 날짜
* 항공 블록

---

## RULE-03

포함/불포함 검증

비교

```text
포함사항
↔ 불포함
↔ 혜택
↔ 탭
↔ 일정표
```

검증

* 보험
* 식사
* 입장료
* 가이드비

---

## RULE-04

미팅 + CS 검증

비교

```text
미팅정보
↔ 항공
↔ 일정표
```

검증

* 터미널
* 시간
* 해산 방식
* 노팁
* 노쇼핑
* 선택관광

---

## RULE-05

숙박/이동 검증

비교

```text
호텔
↔ 항공
↔ 일정
```

검증

* 숙박 박수
* 도시 이동
* 국가 이동
* 자유일정

---

# 정상 구조 보호

정상

```text
노팁
+
가이드비 포함
```

정상

```text
가이드경비 포함
+
매너팁 별도
```

매너팁은 오류 근거가 아니다.

고객 오인 가능성만으로

WARN 생성 금지

---

# 재개발 시 필요한 API

상품 상세 API

일정표 API

항공 API

호텔 API

미팅 정보 API

선택관광 API

탭 정보 API

---

# 절대 변하지 않는 구조

```text
API 데이터 수집
↓
정규화
↓
교차검증
↓
정상 구조 보호
↓
결과 출력
```

엔드포인트는 바뀌어도

이 구조는 유지한다.

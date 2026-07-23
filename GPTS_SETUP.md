# GPTs v2 세팅 파일

현재 GPTs에는 legacy `지침_검증룰` 파일을 넣지 않는다.
아래 4개 파일만 사용한다.

## 1. 지침

파일:

```text
gpts/GPTs_지침_v2.md
```

GPT Builder의 Instructions 영역에 넣는다.

## 2. Action OpenAPI 스키마

파일:

```text
gpts/GPTs_OpenAPI_v2.yaml
```

GPT Builder의 Actions schema에 넣는다.

주의:

```yaml
servers:
  - url: https://YOUR_FASTAPI_HOST
```

위 URL은 실제 배포된 FastAPI 주소로 교체해야 한다.
로컬 테스트 주소는 `http://127.0.0.1:8000`이지만 GPTs Action에서는 공개 HTTPS URL이 필요하다.

## 3. 의미 검수룰

파일:

```text
gpts/GPTs_의미검수룰_v2.json
```

Knowledge 파일로 첨부한다.

## 4. 출력 스키마

파일:

```text
gpts/GPTs_출력스키마_v2.json
```

Knowledge 파일로 첨부한다.

## 사용하지 않는 파일

- `지침_검증룰/` legacy 폴더: 삭제됨
- `openapi.gpts.compact.json`: 삭제됨
- 기존 `검증룰1~5.json`, `지식_01~03.md`: v2에서는 사용하지 않음

## Action 호출 원칙

- 사용자가 숫자 단체번호를 입력하면 `runItineraryInspection` 1회 호출
- Python deterministic 결과는 재판정하지 않음
- GPT는 `semantic_packets`만 검수
- `/evidence`는 근거가 부족하고 최종 판정에 꼭 필요할 때만 호출

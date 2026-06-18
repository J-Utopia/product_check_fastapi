# FastAPI URL 안내

## 로컬 실행 URL

FastAPI는 서버를 실행해야 URL이 생긴다.

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

실행 후 접근 URL:

- `http://127.0.0.1:8010/`
- `http://127.0.0.1:8010/health`
- `http://127.0.0.1:8010/run-itinerary`
- `http://127.0.0.1:8010/docs`
- `http://127.0.0.1:8010/openapi.json`

## GPTs 연결용 URL

- GPTs Action에는 외부에서 접근 가능한 배포 URL이 필요하다.
- 현재 코드는 로컬에서 정상 동작한다.
- 실제 배포가 완료되면 `https://<배포도메인>` 형태로 `GPTs_스키마.md`의 `servers.url`을 교체하면 된다.

## 엔드포인트 역할

- `GET /` 서비스 기본 정보와 URL 확인
- `GET /health` 상태 확인
- `POST /run-itinerary` 단체번호 검수 실행
- `GET /docs` Swagger UI
- `GET /openapi.json` OpenAPI 스펙

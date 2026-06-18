# FastAPI 상시 구동 안내

GPTs가 `run-itinerary`를 호출하려면 FastAPI가 계속 떠 있어야 한다.

## 로컬 실행
```powershell
cd C:\Users\jeonuk\Desktop\Project\Python\ModewareBusiness\일정표검수
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

## 상시 구동

```powershell
cd C:\Users\jeonuk\Desktop\Project\Python\ModewareBusiness\일정표검수
uvicorn app.main:app --host 0.0.0.0 --port 8010
```

이 문서는 로컬 상시 구동 기준만 남긴다. Render 배포가 끝나면 운영 주소는 Render 쪽을 사용한다.

## 확인 URL

- `http://127.0.0.1:8010/`
- `http://127.0.0.1:8010/health`
- `http://127.0.0.1:8010/run-itinerary`
- `http://127.0.0.1:8010/docs`
- `http://127.0.0.1:8010/openapi.json`

## 주의

- GPTs Action에는 로컬 `127.0.0.1` 주소를 직접 넣을 수 없다.
- GPTs에서 직접 호출하려면 외부 공개 HTTPS 주소가 필요하다.
- 이 스크립트는 로컬 개발/검증용 상시 구동을 위한 것이다.

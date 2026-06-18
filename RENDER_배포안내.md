# Render 배포 안내

## 목적

GPTs가 호출할 수 있는 공개 HTTPS URL을 만든다.

## 배포 파일

- `render.yaml`
- `requirements.txt`
- `.python-version`

## Render 서비스 생성값

- Runtime: `Python 3`
- Branch: `main`
- Root Directory: 비움
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## 필수 환경변수

배포 후 `/health`만 확인되면 끝이 아니다.  
`/run-itinerary`가 실제로 동작하려면 인증 헤더가 필요하다.

우선순위는 아래 순서다.

1. `MODETOUR_HEADER_CACHE_JSON`
2. 개별 헤더 환경변수
3. 로컬 캐시 파일
4. Playwright 자동 캡처

Render에서는 3번과 4번이 불안정하므로 1번 또는 2번을 넣는 것이 맞다.

### 권장

- `MODETOUR_HEADER_CACHE_JSON`

값 예시:

```json
{
  "accept": "application/json, text/plain, */*",
  "referer": "https://www.modetour.com/",
  "user-agent": "Mozilla/5.0",
  "x-platform": "WEB",
  "x-salespartner": "false",
  "x-username": "...",
  "x-userid": "...",
  "x-userdepartment": "...",
  "modewebapireqheader": "..."
}
```

## 배포 후 확인

1. `GET /health`
2. `GET /openapi.json`
3. `GET /docs`
4. `POST /run-itinerary`

## 실제 판정 기준

- `health`만 되면 배포 성공이 아니다.
- `run-itinerary`가 `SUCCESS`를 반환해야 운영 가능 상태다.
- `AUTH_CAPTURE_FAILED`가 나오면 Render 환경변수 누락이다.

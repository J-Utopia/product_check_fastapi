# Render 배포 안내

## 목적

GPTs가 호출할 수 있는 공개 HTTPS URL을 만든다.

## 배포 파일

- `render.yaml`
- `requirements.txt`
- `.python-version`

## 배포 방식

1. GitHub 저장소에 코드를 올린다.
2. Render Dashboard에서 `New -> Blueprint`를 선택한다.
3. Blueprint 파일로 저장소 루트의 `render.yaml`을 지정한다.
4. Deploy를 누른다.

## 배포 후 확인

- 서비스 URL: `https://<service-name>.onrender.com`
- 상태 확인: `GET /health`
- 실행 확인: `POST /run-itinerary`

## 주의

- Render에서는 `127.0.0.1`가 아니라 `0.0.0.0`로 띄워야 한다.
- GPTs Action에는 Render가 만든 `https://...onrender.com` 주소를 넣는다.
- 인증 헤더는 가능하면 `.cache/modetour_headers.json`을 유지하거나, Render 환경변수로 주입한다.

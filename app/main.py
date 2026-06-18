from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .auth import HeaderCaptureError
from .client import ModeTourApiError
from .config import settings
from .models import RunItineraryRequest
from .service import build_default_service

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Modetour Itinerary Inspection API",
    version="2.0.0",
    description="현재 기준 모두투어 일정표 검수용 FastAPI",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url=None,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def index() -> dict[str, object]:
    return {
        "service": "Modetour Itinerary Inspection API",
        "status": "ok",
        "endpoints": {
            "health": "/health",
            "run_itinerary": "/run-itinerary",
            "docs": "/docs",
            "openapi": "/openapi.json",
        },
    }


@app.get("/openapi.json")
def openapi_json() -> dict[str, object]:
    return app.openapi()


@app.post("/run-itinerary")
def run_itinerary(request: RunItineraryRequest) -> JSONResponse:
    try:
        service = build_default_service(settings)
        envelope = service.run(request.group_id)
        return JSONResponse(status_code=200, content=envelope.model_dump())
    except HeaderCaptureError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "code": "AUTH_CAPTURE_FAILED",
                "message": "ModeTour 인증 헤더 확보 실패",
                "group_id": request.group_id,
                "meta": {"reason": str(exc)},
                "result": None,
            },
        )
    except ModeTourApiError as exc:
        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "code": "UPSTREAM_API_FAILED",
                "message": "ModeTour API 호출 실패",
                "group_id": request.group_id,
                "meta": {"reason": str(exc)},
                "result": None,
            },
        )

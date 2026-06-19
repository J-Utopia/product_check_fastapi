from __future__ import annotations

import functools
import logging
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .auth import HeaderCaptureError
from .client import ModeTourApiError
from .config import settings
from .models import InspectionEnvelope, RunItineraryRequest
from .service import InspectionService, build_default_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Modetour Itinerary Inspection API",
    version="2.0.0",
    description="모두투어 일정표 검수용 FastAPI",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url=None,
)


@functools.lru_cache(maxsize=1)
def get_service() -> InspectionService:
    logger.info("Building inspection service")
    return build_default_service(settings)


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


@app.post("/run-itinerary", response_model=InspectionEnvelope)
def run_itinerary(request: RunItineraryRequest) -> JSONResponse:
    started_at = time.perf_counter()
    try:
        service = get_service()
        envelope = service.run(request.group_id)
        logger.info("Completed inspection for group_id=%s in %.2fs", request.group_id, time.perf_counter() - started_at)
        return JSONResponse(status_code=200, content=envelope.model_dump())
    except HeaderCaptureError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "code": "AUTH_CAPTURE_FAILED",
                "message": "ModeTour 인증 헤더 정보 수집 실패",
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

#실행
#cd C:\Users\jeonuk\Desktop\Project\Python\ModewareBusiness\일정표검수
#python -m uvicorn app.main:app --reload
#브라우저 http://127.0.0.1:8000/docs 실행
from __future__ import annotations
import functools
import logging
import time
import json

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .auth import HeaderCaptureError
from .client import ModeTourApiError
from .config import settings
from .models import (
    CompactInspectionEnvelope,
    EvidenceResponse,
    InspectionEnvelope,
    InspectionRequest,
    RunItineraryRequest,
    V3InspectionResponse,
)
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


@app.post("/run-itinerary", response_model=InspectionEnvelope | CompactInspectionEnvelope)
def run_itinerary(request: RunItineraryRequest, compact: bool = True) -> JSONResponse:
    started_at = time.perf_counter()
    try:
        service = get_service()
        envelope = service.run(request.group_id)
        payload_model = service.to_compact_envelope(envelope) if compact else envelope

        payload = payload_model.model_dump()
        body_size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

        logger.info(
            "Response Size = %d bytes (%.2f KB / %.2f MB)",
            body_size,
            body_size / 1024,
            body_size / 1024 / 1024,
        )

        logger.info(
            "Completed inspection for group_id=%s compact=%s in %.2fs",
            request.group_id,
            compact,
            time.perf_counter() - started_at,
        )
        return JSONResponse(status_code=200, content=payload)
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


@app.post("/v3/inspections", response_model=V3InspectionResponse)
async def run_v3_inspection(request: InspectionRequest) -> JSONResponse:
    try:
        service = get_service()
        response = service.run_v3(request)
        return JSONResponse(status_code=200, content=response.model_dump())
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


@app.get("/v3/inspections/{inspection_id}/evidence", response_model=EvidenceResponse)
async def get_v3_inspection_evidence(inspection_id: str, evidence_ids: str) -> JSONResponse:
    service = get_service()
    response = service.get_evidence(inspection_id, evidence_ids)
    return JSONResponse(status_code=200, content=response.model_dump())

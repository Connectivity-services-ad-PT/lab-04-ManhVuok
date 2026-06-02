import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


SERVICE_NAME = os.getenv("SERVICE_NAME", "access-gate")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")

CARD_PATTERN = r"^RFID-[0-9]{4}-[0-9]{3}$"
GATE_PATTERN = r"^GATE-[0-9]{2}$"

PROBLEM_BASE = "https://campus.local/errors"


app = FastAPI(
    title="FIT4110 Lab 04 - Access Gate Service",
    version=SERVICE_VERSION,
    description=(
        "Dockerized Access Gate API aligned with the Lab 03 OpenAPI/Postman contract "
        "(team-gate). Provides RFID access logs, gate status, card info and business events."
    ),
)


# --------------------------------------------------------------------------- #
# Enums / models                                                              #
# --------------------------------------------------------------------------- #
class Direction(str, Enum):
    IN = "IN"
    OUT = "OUT"


class AccessStatus(str, Enum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"


class GateMode(str, Enum):
    NORMAL = "NORMAL"
    LOCKDOWN = "LOCKDOWN"
    MAINTENANCE = "MAINTENANCE"
    EMERGENCY_OPEN = "EMERGENCY_OPEN"


class HolderType(str, Enum):
    STUDENT = "STUDENT"
    LECTURER = "LECTURER"
    STAFF = "STAFF"
    VISITOR = "VISITOR"


class CardStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class HealthResponse(BaseModel):
    status: str
    service: str
    time: str


# --------------------------------------------------------------------------- #
# In-memory seed data (matches the Lab 03 contract examples)                   #
# --------------------------------------------------------------------------- #
ACCESS_LOGS: List[Dict] = [
    {
        "logId": "0196fb3d-4ad7-7d1e-9f49-5d5148d2babc",
        "cardId": "RFID-2026-001",
        "gateId": "GATE-01",
        "direction": "IN",
        "status": "ALLOWED",
        "timestamp": "2026-05-26T07:30:00Z",
        "operatorNote": None,
    },
    {
        "logId": "0196fb3d-4ad7-7d1e-9f49-5d5148d2babd",
        "cardId": "RFID-2026-002",
        "gateId": "GATE-02",
        "direction": "OUT",
        "status": "DENIED",
        "timestamp": "2026-05-26T07:35:00Z",
        "operatorNote": "Thẻ hết hạn",
    },
]

GATES: Dict[str, Dict] = {
    "GATE-01": {
        "gateId": "GATE-01",
        "gateName": "Cổng chính A",
        "mode": "NORMAL",
        "isOnline": True,
        "lastHeartbeat": "2026-05-26T08:00:00Z",
        "errorMessage": None,
    },
    "GATE-02": {
        "gateId": "GATE-02",
        "gateName": "Cổng phụ B",
        "mode": "MAINTENANCE",
        "isOnline": False,
        "lastHeartbeat": "2026-05-26T06:00:00Z",
        "errorMessage": "Đang bảo trì",
    },
}

CARDS: Dict[str, Dict] = {
    "RFID-2026-001": {
        "cardId": "RFID-2026-001",
        "holderName": "Nguyen Van A",
        "holderType": "STUDENT",
        "status": "ACTIVE",
        "issuedAt": "2026-01-15T00:00:00Z",
        "expiresAt": "2027-01-15T00:00:00Z",
        "suspendedReason": None,
    },
    "RFID-2026-002": {
        "cardId": "RFID-2026-002",
        "holderName": "Tran Thi B",
        "holderType": "LECTURER",
        "status": "SUSPENDED",
        "issuedAt": "2025-09-01T00:00:00Z",
        "expiresAt": "2026-09-01T00:00:00Z",
        "suspendedReason": "Báo mất thẻ",
    },
}


# --------------------------------------------------------------------------- #
# Problem+json helpers                                                         #
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    problem_type: str = "about:blank",
    errors: Optional[List[Dict]] = None,
) -> Dict:
    problem: Dict = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    if errors is not None:
        problem["errors"] = errors
    return problem


def problem_response(problem: Dict, headers: Optional[Dict] = None) -> JSONResponse:
    return JSONResponse(
        status_code=problem["status"],
        content=problem,
        media_type="application/problem+json",
        headers=headers,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = build_problem(
            status_code=exc.status_code,
            title="HTTP Error",
            detail=str(exc.detail),
            instance=str(request.url.path),
        )
    problem.setdefault("type", "about:blank")
    problem.setdefault("status", exc.status_code)
    problem.setdefault("instance", str(request.url.path))
    return problem_response(problem, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(p) for p in err.get("loc", [])),
            "code": err.get("type", "validation_error"),
            "message": err.get("msg", "Invalid value"),
        }
        for err in exc.errors()
    ]
    first = errors[0]["message"] if errors else "Request validation error"
    return problem_response(
        build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Dữ liệu không hợp lệ",
            detail=first,
            instance=str(request.url.path),
            problem_type=f"{PROBLEM_BASE}/validation",
            errors=errors,
        )
    )


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    instance = "/"
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Chưa xác thực",
                detail="Thiếu Bearer token",
                instance=instance,
                problem_type=f"{PROBLEM_BASE}/unauthorized",
                errors=[],
            ),
        )
    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Chưa xác thực",
                detail="Bearer token không hợp lệ",
                instance=instance,
                problem_type=f"{PROBLEM_BASE}/unauthorized",
                errors=[],
            ),
        )


def not_found(detail: str, instance: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=build_problem(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Không tìm thấy",
            detail=detail,
            instance=instance,
            problem_type=f"{PROBLEM_BASE}/not-found",
            errors=[],
        ),
    )


# --------------------------------------------------------------------------- #
# Endpoints                                                                    #
# --------------------------------------------------------------------------- #
@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME, time=now_iso())


@app.get("/access/logs/recent", dependencies=[Depends(verify_bearer_token)])
def recent_access_logs(
    cursor: Optional[str] = Query(default=None, min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
) -> Dict:
    items = ACCESS_LOGS[:limit]
    return {"items": items, "nextCursor": None, "hasMore": False}


@app.get("/access/logs/{logId}", dependencies=[Depends(verify_bearer_token)])
def get_access_log(logId: str) -> Dict:
    for log in ACCESS_LOGS:
        if log["logId"] == logId:
            return log
    raise not_found(f"Log quẹt thẻ {logId} không tồn tại", f"/access/logs/{logId}")


@app.get("/gates/{gateId}/status", dependencies=[Depends(verify_bearer_token)])
def gate_status(
    gateId: str = Path(..., pattern=GATE_PATTERN),
) -> Dict:
    gate = GATES.get(gateId)
    if gate is None:
        raise not_found(f"Cổng {gateId} không tồn tại", f"/gates/{gateId}/status")
    return gate


@app.get("/cards/{cardId}", dependencies=[Depends(verify_bearer_token)])
def card_info(
    cardId: str = Path(..., pattern=CARD_PATTERN),
) -> Dict:
    card = CARDS.get(cardId)
    if card is None:
        raise not_found(f"Thẻ {cardId} không tồn tại", f"/cards/{cardId}")
    return card


@app.post(
    "/events",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
)
async def create_event(request: Request) -> Dict:
    instance = "/events"
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_problem(
                status_code=status.HTTP_400_BAD_REQUEST,
                title="Dữ liệu không hợp lệ",
                detail="Body không phải JSON hợp lệ",
                instance=instance,
                problem_type=f"{PROBLEM_BASE}/validation",
                errors=[],
            ),
        )

    if not isinstance(payload, dict):
        raise _bad_event("Body phải là JSON object", instance)

    event_type = payload.get("eventType")
    if event_type == "GATE_SCAN":
        missing = [f for f in ("gateId", "cardId") if not payload.get(f)]
        if missing:
            raise _bad_event(
                f"GATE_SCAN thiếu field bắt buộc: {', '.join(missing)}", instance, missing
            )
    elif event_type == "CARD_STATUS_CHANGE":
        missing = [f for f in ("cardId", "newStatus") if not payload.get(f)]
        if missing:
            raise _bad_event(
                f"CARD_STATUS_CHANGE thiếu field bắt buộc: {', '.join(missing)}",
                instance,
                missing,
            )
    else:
        raise _bad_event(
            "eventType phải là GATE_SCAN hoặc CARD_STATUS_CHANGE", instance, ["eventType"]
        )

    return {"eventId": f"EVT-{uuid.uuid4()}"}


def _bad_event(detail: str, instance: str, fields: Optional[List[str]] = None) -> HTTPException:
    errors = [{"field": f, "code": "REQUIRED", "message": "Field bắt buộc"} for f in (fields or [])]
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=build_problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Dữ liệu không hợp lệ",
            detail=detail,
            instance=instance,
            problem_type=f"{PROBLEM_BASE}/validation",
            errors=errors,
        ),
    )

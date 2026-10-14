from __future__ import annotations

import ipaddress
import base64
import secrets
from typing import Iterable

from fastapi import Request
from fastapi.responses import JSONResponse

from app.security.config import AuthConfig
from app.security.session import COOKIE_NAME, verify

NO_STORE = {"Cache-Control": "no-store, private", "Pragma": "no-cache"}
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
PUBLIC_API = {("POST", "/api/auth/login")}
PUBLIC_HEALTH = {"/health", "/healthz/live", "/healthz/ready"}


def error(request: Request, status: int, code: str, fields: Iterable[str] = (), headers: dict[str, str] | None = None) -> JSONResponse:
    messages = {
        "AUTHENTICATION_FAILED": "שם המשתמש או הסיסמה אינם נכונים",
        "AUTHENTICATION_REQUIRED": "נדרשת התחברות",
        "SESSION_MISSING": "נדרשת התחברות",
        "SESSION_INVALID": "החיבור אינו תקף",
        "SESSION_EXPIRED": "תוקף החיבור פג",
        "CSRF_INVALID": "אימות הבקשה נכשל",
        "ORIGIN_FORBIDDEN": "מקור הבקשה אינו מורשה",
        "CLIENT_NOT_FOUND": "הלקוח לא נמצא",
    }
    response_headers = dict(NO_STORE)
    if headers:
        response_headers.update(headers)
    return JSONResponse(
        status_code=status,
        headers=response_headers,
        content={
            "schema_version": "RTDIR_TRANSPORT_ERROR_V1",
            "code": code,
            "message": messages.get(code, "לא ניתן להשלים את הבקשה"),
            "field_paths": sorted(set(fields), key=lambda item: item.encode("utf-8")),
            "request_id": getattr(request.state, "request_id", "unavailable"),
        },
    )


def header_values(request: Request, name: str) -> list[str]:
    target = name.lower().encode("ascii")
    return [value.decode("latin-1") for key, value in request.scope.get("headers", []) if key.lower() == target]


def canonical_client_ip(request: Request) -> str | None:
    values = header_values(request, "x-real-ip")
    if len(values) != 1:
        return None
    raw = values[0]
    if raw != raw.strip() or "," in raw or len(raw) > 64 or "%" in raw:
        return None
    try:
        parsed = ipaddress.ip_address(raw)
    except ValueError:
        return None
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped:
        parsed = parsed.ipv4_mapped
    return parsed.compressed


def exact_header(request: Request, name: str) -> str | None:
    values = header_values(request, name)
    return values[0] if len(values) == 1 else None


def is_internal_health(request: Request) -> bool:
    return (
        request.method == "GET"
        and request.url.path == "/healthz/ready"
        and exact_header(request, "host") is not None
        and exact_header(request, "host").lower() == "healthcheck.railway.app"
    )


def is_spa_path(path: str) -> bool:
    if path in {"/", "/login", "/clients", "/clients/new", "/fixation/input", "/fixation/result", "/fixation/history"}:
        return True
    parts = [segment for segment in path.split("/") if segment]
    if len(parts) >= 2 and parts[0] == "clients" and parts[1].isdigit() and int(parts[1]) > 0:
        if len(parts) == 2:
            return True
        if len(parts) == 3 and parts[2] in {
            "employment-history", "pension-products", "legacy-conversion-history",
            "professional-sources", "planning-input", "retirement-income-readiness",
            "grants", "actual-capitalizations",
        }:
            return True
        if len(parts) == 4 and parts[2] == "fixation" and parts[3] in {"workspace", "input", "result", "history"}:
            return True
        if len(parts) == 5 and parts[2:4] == ["fixation", "runs"] and parts[4]:
            return True
    return len(parts) == 3 and parts[:2] == ["fixation", "runs"] and bool(parts[2])


def is_public_path(method: str, path: str) -> bool:
    if (method, path) in PUBLIC_API or path in PUBLIC_HEALTH:
        return True
    if method not in {"GET", "HEAD"}:
        return False
    if is_spa_path(path):
        return True
    if path.startswith("/assets/"):
        return True
    return False


def validate_edge(request: Request, config: AuthConfig) -> tuple[str | None, JSONResponse | None]:
    client_ip = canonical_client_ip(request)
    proto = exact_header(request, "x-forwarded-proto")
    forwarded_host = exact_header(request, "x-forwarded-host")
    host = exact_header(request, "host")
    if client_ip is None or proto != "https" or forwarded_host is None or host is None:
        return None, error(request, 400, "EDGE_REQUEST_INVALID")
    if forwarded_host.lower() != config.public_authority or host.lower() != config.public_authority:
        return None, error(request, 400, "EDGE_REQUEST_INVALID")
    return client_ip, None


def validate_origin(request: Request, config: AuthConfig) -> JSONResponse | None:
    origin = exact_header(request, "origin")
    if origin != config.public_origin:
        return error(request, 403, "ORIGIN_FORBIDDEN")
    return None


def validate_session(request: Request, config: AuthConfig) -> JSONResponse | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return error(request, 401, "SESSION_MISSING")
    payload, session_error = verify(config, token)
    if session_error:
        return error(request, 401, session_error)
    request.state.auth_session = payload
    request.state.trusted_professional_actor = payload["actor_id"]
    return None


def validate_csrf(request: Request) -> JSONResponse | None:
    values = header_values(request, "x-rtdir-csrf")
    expected = request.state.auth_session["csrf"]
    def decode(value: object) -> bytes | None:
        if not isinstance(value, str) or len(value) != 43 or "=" in value:
            return None
        try:
            raw = base64.b64decode(value + "=", altchars=b"-_", validate=True)
        except (ValueError, TypeError):
            return None
        if len(raw) != 32 or base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") != value:
            return None
        return raw

    supplied = decode(values[0]) if len(values) == 1 else None
    bound = decode(expected)
    if supplied is None or bound is None or not secrets.compare_digest(supplied, bound):
        return error(request, 403, "CSRF_INVALID")
    return None

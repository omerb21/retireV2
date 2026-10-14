from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.security.config import AuthConfig
from app.security.transport import (
    NO_STORE, UNSAFE, error, exact_header, is_internal_health, is_public_path,
    validate_csrf, validate_edge, validate_origin, validate_session,
)
from app.security.session import COOKIE_NAME


class RTDIRSecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config: AuthConfig):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next):
        request.state.request_id = secrets.token_urlsafe(18)
        if not self.config.production:
            return await call_next(request)
        internal_health = is_internal_health(request)
        if not internal_health:
            client_ip, rejected = validate_edge(request, self.config)
            if rejected:
                return rejected
            request.state.client_ip = client_ip
        if request.method == "OPTIONS" and not internal_health:
            origin = exact_header(request, "origin")
            requested_method = exact_header(request, "access-control-request-method")
            raw_headers = exact_header(request, "access-control-request-headers") or ""
            headers = {item.strip().lower() for item in raw_headers.split(",") if item.strip()}
            if origin != self.config.public_origin or requested_method not in {"GET", "POST", "PUT", "DELETE", "OPTIONS"} or not headers.issubset({"content-type", "x-rtdir-csrf"}):
                return error(request, 403, "ORIGIN_FORBIDDEN")
            return Response(status_code=204, headers={
                "Access-Control-Allow-Origin": self.config.public_origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, X-RTDIR-CSRF",
                "Access-Control-Max-Age": "600",
                **NO_STORE,
            })
        public = internal_health or is_public_path(request.method, request.url.path)
        if request.url.path == "/api/auth/login":
            rejected = validate_origin(request, self.config)
            if rejected:
                return rejected
        elif not public:
            is_logout = request.url.path == "/api/auth/logout"
            if is_logout:
                rejected = validate_origin(request, self.config)
                if rejected:
                    return rejected
            rejected = validate_session(request, self.config)
            if rejected:
                if is_logout:
                    rejected = error(request, 401, "AUTHENTICATION_REQUIRED")
                    rejected.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="lax")
                return rejected
            if request.method in UNSAFE:
                rejected = validate_csrf(request) if is_logout else validate_origin(request, self.config) or validate_csrf(request)
                if rejected:
                    return rejected
            elif exact_header(request, "origin") not in {None, self.config.public_origin}:
                return error(request, 403, "ORIGIN_FORBIDDEN")
        response = await call_next(request)
        if response.status_code == 404 and "endpoint" not in request.scope:
            response = error(request, 404, "ROUTE_NOT_FOUND")
        elif response.status_code == 405:
            response = error(request, 405, "METHOD_NOT_ALLOWED")
        if request.url.path.startswith("/api/") or not public or request.url.path in {"/", "/login"}:
            response.headers.update(NO_STORE)
        if not internal_health and exact_header(request, "origin") == self.config.public_origin:
            response.headers["Access-Control-Allow-Origin"] = self.config.public_origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["X-Request-ID"] = request.state.request_id
        return response

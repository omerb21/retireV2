from __future__ import annotations

import hmac
import json
import unicodedata
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response

from app.db.session import get_session_factory
from app.security.rate_limit import (
    RateLimitUnavailable, cleanup_batch, finalize, login_buckets, malformed_buckets, precheck,
)
from app.security.session import COOKIE_NAME, SESSION_SECONDS, issue, public_dto
from app.security.transport import error

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _valid_username(value: object) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 128
        and len(value.encode("utf-8")) <= 512
        and value == value.strip(" \t\r\n")
        and not any(unicodedata.category(char) == "Cc" for char in value)
    )


def _valid_password(value: object) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 1024
        and len(value.encode("utf-8")) <= 4096
        and not any(unicodedata.category(char) == "Cc" for char in value)
    )


def _store(request: Request):
    try:
        return get_session_factory()()
    except Exception as exc:
        raise RateLimitUnavailable("rate-limit database unavailable") from exc


def _malformed_attempt(request: Request) -> Response | None:
    db = _store(request)
    try:
        wait = finalize(db, malformed_buckets(request.app.state.auth_config, request.state.client_ip), success=False)
    finally:
        db.close()
    if wait:
        return error(request, 429, "LOGIN_RATE_LIMITED", headers={"Retry-After": str(wait)})
    return None


@router.post("/login")
async def login(request: Request):
    config = request.app.state.auth_config
    if not request.app.state.rate_limiter_ready:
        return error(request, 503, "AUTH_RATE_LIMIT_UNAVAILABLE")
    content_type = request.headers.get("content-type", "")
    media, _, parameters = content_type.partition(";")
    valid_charset = not parameters or parameters.strip().lower() in {"charset=utf-8", "charset=\"utf-8\""}
    if media.strip().lower() != "application/json" or not valid_charset:
        return error(request, 415, "LOGIN_CONTENT_TYPE_UNSUPPORTED")
    body = await request.body()
    if len(body) > 8192:
        return error(request, 413, "LOGIN_BODY_TOO_LARGE")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        try:
            limited = _malformed_attempt(request)
        except RateLimitUnavailable:
            return error(request, 503, "AUTH_RATE_LIMIT_UNAVAILABLE")
        return limited or error(request, 400, "REQUEST_JSON_INVALID")
    fields = []
    if not isinstance(payload, dict):
        fields = ["/"]
    else:
        extras = set(payload) - {"username", "password"}
        fields.extend("/" + name.replace("~", "~0").replace("/", "~1") for name in extras)
        if "username" not in payload or not _valid_username(payload.get("username")):
            fields.append("/username")
        if "password" not in payload or not _valid_password(payload.get("password")):
            fields.append("/password")
    if fields:
        try:
            limited = _malformed_attempt(request)
        except RateLimitUnavailable:
            return error(request, 503, "AUTH_RATE_LIMIT_UNAVAILABLE")
        return limited or error(request, 422, "LOGIN_REQUEST_INVALID", fields)
    username, password = payload["username"], payload["password"]
    buckets = login_buckets(config, username, request.state.client_ip)
    try:
        db = _store(request)
    except RateLimitUnavailable:
        request.app.state.rate_limiter_ready = False
        return error(request, 503, "AUTH_RATE_LIMIT_UNAVAILABLE")
    try:
        cleanup_batch(db)
        wait = precheck(db, buckets)
    except RateLimitUnavailable:
        request.app.state.rate_limiter_ready = False
        return error(request, 503, "AUTH_RATE_LIMIT_UNAVAILABLE")
    finally:
        db.close()
    if wait:
        return error(request, 429, "LOGIN_RATE_LIMITED", headers={"Retry-After": str(wait)})
    username_matches = hmac.compare_digest(username.encode("utf-8"), config.username.encode("utf-8"))
    verifier = config.password_hash if username_matches else config.dummy_password_hash
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, VerificationError
    hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)
    password_matches = False
    try:
        password_matches = hasher.verify(verifier, password)
    except (VerifyMismatchError, VerificationError):
        password_matches = False
    success = bool(username_matches and password_matches)
    try:
        db = _store(request)
    except RateLimitUnavailable:
        request.app.state.rate_limiter_ready = False
        return error(request, 503, "AUTH_RATE_LIMIT_UNAVAILABLE")
    try:
        wait = finalize(db, buckets, success=success)
    except RateLimitUnavailable:
        request.app.state.rate_limiter_ready = False
        return error(request, 503, "AUTH_RATE_LIMIT_UNAVAILABLE")
    finally:
        db.close()
    if wait:
        return error(request, 429, "LOGIN_RATE_LIMITED", headers={"Retry-After": str(wait)})
    if not success:
        return error(request, 401, "AUTHENTICATION_FAILED")
    token, session = issue(config)
    response = Response(
        content=json.dumps(public_dto(session), ensure_ascii=False, separators=(",", ":")),
        media_type="application/json",
    )
    response.set_cookie(
        COOKIE_NAME,
        token,
        secure=True,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=SESSION_SECONDS,
        expires=datetime.fromtimestamp(session["exp"], timezone.utc),
    )
    return response


@router.get("/session")
def session_status(request: Request):
    if not request.app.state.auth_config.production:
        return {
            "schema_version": "RTDIR_AUTHENTICATED_SESSION_V1",
            "authenticated": True,
            "actor_id": "development-professional",
            "expires_at": "2999-12-31T23:59:59Z",
            "csrf_token": "A" * 43,
        }
    return public_dto(request.state.auth_session)


@router.post("/logout", status_code=204)
def logout(request: Request):
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="lax")
    return response

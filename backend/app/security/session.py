from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import secrets
from typing import Any

from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer

from app.security.config import AuthConfig

COOKIE_NAME = "__Host-retire_v2_session"
SESSION_SECONDS = 28_800
SESSION_CONTRACT = "RTDIR_SESSION_V1"
SESSION_SALT = "RTDIR_SESSION_COOKIE_V1"


class _CanonicalJSON:
    @staticmethod
    def dumps(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

    @staticmethod
    def loads(value: str) -> Any:
        return json.loads(value)


def _serializer(config: AuthConfig) -> URLSafeTimedSerializer:
    if config.session_secret is None:
        raise RuntimeError("session secret unavailable")
    return URLSafeTimedSerializer(
        config.session_secret,
        salt=SESSION_SALT,
        serializer=_CanonicalJSON,
        signer_kwargs={"key_derivation": "hmac", "digest_method": hashlib.sha256},
    )


def _random32() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")


def _is_token32(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 43 or "=" in value:
        return False
    try:
        raw = base64.urlsafe_b64decode(value + "=")
    except Exception:
        return False
    return len(raw) == 32 and base64.urlsafe_b64encode(raw).decode().rstrip("=") == value


def issue(config: AuthConfig, *, now: int | None = None) -> tuple[str, dict[str, Any]]:
    issued = int(datetime.now(timezone.utc).timestamp()) if now is None else now
    payload = {
        "contract": SESSION_CONTRACT,
        "actor_id": config.actor_id,
        "iat": issued,
        "exp": issued + SESSION_SECONDS,
        "nonce": _random32(),
        "csrf": _random32(),
    }
    return _serializer(config).dumps(payload), payload


def verify(config: AuthConfig, token: str, *, now: int | None = None) -> tuple[dict[str, Any] | None, str | None]:
    current = int(datetime.now(timezone.utc).timestamp()) if now is None else now
    try:
        payload = _serializer(config).loads(token, max_age=SESSION_SECONDS)
    except SignatureExpired:
        return None, "SESSION_EXPIRED"
    except BadData:
        return None, "SESSION_INVALID"
    expected = {"contract", "actor_id", "iat", "exp", "nonce", "csrf"}
    if not isinstance(payload, dict) or set(payload) != expected:
        return None, "SESSION_INVALID"
    iat, exp = payload.get("iat"), payload.get("exp")
    if (
        payload.get("contract") != SESSION_CONTRACT
        or payload.get("actor_id") != config.actor_id
        or isinstance(iat, bool)
        or not isinstance(iat, int)
        or isinstance(exp, bool)
        or not isinstance(exp, int)
        or exp != iat + SESSION_SECONDS
        or iat > current + 60
        or not _is_token32(payload.get("nonce"))
        or not _is_token32(payload.get("csrf"))
    ):
        return None, "SESSION_INVALID"
    if current >= exp:
        return None, "SESSION_EXPIRED"
    return payload, None


def public_dto(payload: dict[str, Any]) -> dict[str, Any]:
    expires = datetime.fromtimestamp(payload["exp"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": "RTDIR_AUTHENTICATED_SESSION_V1",
        "authenticated": True,
        "actor_id": payload["actor_id"],
        "expires_at": expires,
        "csrf_token": payload["csrf"],
    }

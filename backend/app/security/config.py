from __future__ import annotations

from dataclasses import dataclass
import base64
import os
import unicodedata
from urllib.parse import urlsplit

def _secret(name: str, value: str | None) -> bytes:
    if value is None or len(value) != 43 or "=" in value:
        raise RuntimeError(f"{name} is invalid")
    try:
        decoded = base64.urlsafe_b64decode(value + "=")
    except Exception as exc:
        raise RuntimeError(f"{name} is invalid") from exc
    if len(decoded) != 32 or base64.urlsafe_b64encode(decoded).decode().rstrip("=") != value:
        raise RuntimeError(f"{name} is invalid")
    return decoded


def valid_actor(value: object) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 128
        and value == value.strip(" \t\r\n")
        and not any(unicodedata.category(char) == "Cc" for char in value)
    )


def _origin(value: str | None) -> tuple[str, str]:
    if (
        not value
        or not value.isascii()
        or value.endswith("/")
        or "," in value
        or "*" in value
    ):
        raise RuntimeError("AUTH_PUBLIC_ORIGIN is invalid")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("AUTH_PUBLIC_ORIGIN is invalid")
    return value, parsed.netloc.lower()


def _phc(name: str, value: str | None) -> str:
    from argon2 import extract_parameters
    from argon2.low_level import Type
    if not value:
        raise RuntimeError(f"{name} is invalid")
    try:
        parameters = extract_parameters(value)
    except Exception as exc:
        raise RuntimeError(f"{name} is invalid") from exc
    if not (
        parameters.type is Type.ID
        and parameters.version == 19
        and parameters.time_cost == 3
        and parameters.memory_cost == 65536
        and parameters.parallelism == 4
        and parameters.hash_len == 32
        and parameters.salt_len >= 16
    ):
        raise RuntimeError(f"{name} is invalid")
    return value


@dataclass(frozen=True)
class AuthConfig:
    production: bool
    public_origin: str | None = None
    public_authority: str | None = None
    username: str | None = None
    password_hash: str | None = None
    dummy_password_hash: str | None = None
    actor_id: str | None = None
    session_secret: bytes | None = None
    rate_limit_secret: bytes | None = None

    @classmethod
    def from_env(cls) -> "AuthConfig":
        production = os.getenv("APP_ENV") == "production"
        if not production:
            return cls(production=False)
        if os.getenv("AUTH_INGRESS_MODE") != "railway_public_edge":
            raise RuntimeError("AUTH_INGRESS_MODE is invalid")
        if os.getenv("WEB_CONCURRENCY") != "1":
            raise RuntimeError("WEB_CONCURRENCY is invalid")
        if os.getenv("RAILWAY_DEPLOYMENT_OVERLAP_SECONDS") != "0":
            raise RuntimeError("RAILWAY_DEPLOYMENT_OVERLAP_SECONDS is invalid")
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url.startswith(("postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://")):
            raise RuntimeError("DATABASE_URL is invalid")
        origin, authority = _origin(os.getenv("AUTH_PUBLIC_ORIGIN"))
        username = os.getenv("AUTH_USERNAME")
        if (
            not isinstance(username, str)
            or not 1 <= len(username) <= 128
            or len(username.encode("utf-8")) > 512
            or username != username.strip(" \t\r\n")
            or any(unicodedata.category(c) == "Cc" for c in username)
        ):
            raise RuntimeError("AUTH_USERNAME is invalid")
        actor = os.getenv("AUTH_ACTOR_ID")
        if not valid_actor(actor):
            raise RuntimeError("AUTH_ACTOR_ID is invalid")
        password_hash = _phc("AUTH_PASSWORD_HASH", os.getenv("AUTH_PASSWORD_HASH"))
        dummy_hash = _phc("AUTH_DUMMY_PASSWORD_HASH", os.getenv("AUTH_DUMMY_PASSWORD_HASH"))
        if password_hash == dummy_hash:
            raise RuntimeError("AUTH_DUMMY_PASSWORD_HASH is invalid")
        return cls(
            production=True,
            public_origin=origin,
            public_authority=authority,
            username=username,
            password_hash=password_hash,
            dummy_password_hash=dummy_hash,
            actor_id=actor,
            session_secret=_secret("AUTH_SESSION_SECRET_B64", os.getenv("AUTH_SESSION_SECRET_B64")),
            rate_limit_secret=_secret("AUTH_RATE_LIMIT_SECRET_B64", os.getenv("AUTH_RATE_LIMIT_SECRET_B64")),
        )

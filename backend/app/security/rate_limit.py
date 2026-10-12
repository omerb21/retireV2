from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac
import math
from typing import Iterable

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.security.config import AuthConfig

TABLE = "rtdir_login_rate_limit_buckets"
THRESHOLDS = {"USER": 5, "IP": 20, "GLOBAL": 200}
MAX_COUNT = 2_147_483_647


class RateLimitUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Bucket:
    key: str
    kind: str


def bucket(config: AuthConfig, kind: str, value: str | None = None) -> Bucket:
    if config.rate_limit_secret is None or kind not in THRESHOLDS:
        raise RateLimitUnavailable("rate limiter is not configured")
    raw = b"RTDIR_LOGIN_LIMIT_V1\0" + kind.encode("ascii")
    if value is not None:
        raw += b"\0" + value.encode("utf-8")
    return Bucket(hmac.new(config.rate_limit_secret, raw, hashlib.sha256).hexdigest(), kind)


def login_buckets(config: AuthConfig, username: str, ip: str) -> list[Bucket]:
    return sorted(
        [bucket(config, "GLOBAL"), bucket(config, "USER", username), bucket(config, "IP", ip)],
        key=lambda item: item.key,
    )


def malformed_buckets(config: AuthConfig, ip: str) -> list[Bucket]:
    return sorted([bucket(config, "GLOBAL"), bucket(config, "IP", ip)], key=lambda item: item.key)


def _prepare(db: Session, buckets: Iterable[Bucket]) -> tuple[datetime, list[dict]]:
    dialect = db.get_bind().dialect.name
    if dialect != "postgresql":
        raise RateLimitUnavailable("PostgreSQL is required")
    now = db.execute(text("SELECT transaction_timestamp()")) .scalar_one()
    ordered = list(buckets)
    for item in ordered:
        db.execute(text(f"""
            INSERT INTO {TABLE}
              (bucket_key,bucket_kind,window_started_at,failure_count,locked_until,updated_at)
            VALUES (:key,:kind,:now,0,NULL,:now)
            ON CONFLICT (bucket_key) DO NOTHING
        """), {"key": item.key, "kind": item.kind, "now": now})
    rows = db.execute(text(f"""
        SELECT bucket_key,bucket_kind,window_started_at,failure_count,locked_until,updated_at
        FROM {TABLE} WHERE bucket_key IN :keys ORDER BY bucket_key FOR UPDATE
    """).bindparams(bindparam("keys", expanding=True)), {"keys": [item.key for item in ordered]}).mappings().all()
    if len(rows) != len(ordered):
        raise RateLimitUnavailable("bucket store incomplete")
    expected = {item.key: item.kind for item in ordered}
    normalized = []
    for row in rows:
        data = dict(row)
        if expected.get(data["bucket_key"]) != data["bucket_kind"]:
            raise RateLimitUnavailable("bucket kind mismatch")
        count = data["failure_count"]
        if count > 0 and now >= data["window_started_at"] + timedelta(seconds=900):
            db.execute(text(f"UPDATE {TABLE} SET failure_count=0,locked_until=NULL,window_started_at=:now,updated_at=:now WHERE bucket_key=:key"), {"now": now, "key": data["bucket_key"]})
            data.update(failure_count=0, locked_until=None, window_started_at=now, updated_at=now)
        normalized.append(data)
    return now, normalized


def retry_after(rows: list[dict], now: datetime) -> int:
    remaining = [math.ceil((row["locked_until"] - now).total_seconds()) for row in rows if row["locked_until"] and row["failure_count"] >= THRESHOLDS[row["bucket_kind"]]]
    return max(1, min(900, max(remaining))) if remaining else 0


def precheck(db: Session, buckets: list[Bucket]) -> int:
    try:
        now, rows = _prepare(db, buckets)
        wait = retry_after(rows, now)
        db.commit()
        return wait
    except Exception as exc:
        db.rollback()
        if isinstance(exc, RateLimitUnavailable):
            raise
        raise RateLimitUnavailable("rate limiter precheck failed") from exc


def finalize(db: Session, buckets: list[Bucket], *, success: bool) -> int:
    try:
        now, rows = _prepare(db, buckets)
        wait = retry_after(rows, now)
        if wait:
            db.commit()
            return wait
        if success:
            for row in rows:
                if row["bucket_kind"] in {"USER", "IP"} or (row["bucket_kind"] == "GLOBAL" and row["failure_count"] == 0):
                    db.execute(text(f"DELETE FROM {TABLE} WHERE bucket_key=:key"), {"key": row["bucket_key"]})
        else:
            for row in rows:
                count = row["failure_count"]
                anchor = now if count == 0 else row["window_started_at"]
                new_count = MAX_COUNT if count >= MAX_COUNT else count + 1
                locked = new_count >= THRESHOLDS[row["bucket_kind"]]
                db.execute(text(f"""
                    UPDATE {TABLE}
                    SET window_started_at=:anchor,
                        failure_count=CASE WHEN failure_count >= 2147483647 THEN 2147483647 ELSE failure_count + 1 END,
                        locked_until=CASE WHEN :locked THEN :anchor + INTERVAL '900 seconds' ELSE NULL END,
                        updated_at=:now
                    WHERE bucket_key=:key
                """), {"anchor": anchor, "locked": locked, "now": now, "key": row["bucket_key"]})
            rows = db.execute(text(f"SELECT bucket_key,bucket_kind,window_started_at,failure_count,locked_until,updated_at FROM {TABLE} WHERE bucket_key IN :keys").bindparams(bindparam("keys", expanding=True)), {"keys": [row["bucket_key"] for row in rows]}).mappings().all()
            wait = retry_after([dict(row) for row in rows], now)
        db.commit()
        return wait
    except Exception as exc:
        db.rollback()
        if isinstance(exc, RateLimitUnavailable):
            raise
        raise RateLimitUnavailable("rate limiter mutation failed") from exc


def cleanup_batch(db: Session) -> int:
    try:
        keys = db.execute(text(f"""
            SELECT bucket_key FROM {TABLE}
            WHERE updated_at < transaction_timestamp() - INTERVAL '1800 seconds'
            ORDER BY updated_at,bucket_key FOR UPDATE SKIP LOCKED LIMIT 64
        """)).scalars().all()
        if keys:
            db.execute(text(f"DELETE FROM {TABLE} WHERE bucket_key IN :keys").bindparams(bindparam("keys", expanding=True)), {"keys": list(keys)})
        db.commit()
        return len(keys)
    except Exception as exc:
        db.rollback()
        raise RateLimitUnavailable("rate limiter cleanup failed") from exc

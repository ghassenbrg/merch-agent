from __future__ import annotations

import hmac
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.settings import AppSettings, get_settings


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_RATE_LIMITS: dict[str, deque[float]] = defaultdict(deque)


def clear_rate_limit_state() -> None:
    _RATE_LIMITS.clear()


def _bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token.strip()
    return request.headers.get("x-merch-agent-token", "").strip()


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    host = forwarded_for or (request.client.host if request.client else "unknown")
    return f"{host}:{request.method}:{request.url.path}"


def _rate_limited(request: Request, settings: AppSettings, now: float | None = None) -> bool:
    if request.url.path.startswith("/api") and request.method in UNSAFE_METHODS:
        limit = settings.write_rate_limit_per_minute
    elif request.url.path.startswith("/api"):
        limit = settings.rate_limit_per_minute
    else:
        return False

    current = now or time.monotonic()
    window_start = current - 60
    hits = _RATE_LIMITS[_client_key(request)]
    while hits and hits[0] < window_start:
        hits.popleft()
    if len(hits) >= limit:
        return True
    hits.append(current)
    return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response


class AccessControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        if _rate_limited(request, settings):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )

        if request.method in UNSAFE_METHODS and request.url.path.startswith("/api"):
            origin = request.headers.get("origin")
            if origin and origin not in settings.allowed_origins:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Origin is not allowed for write requests."},
                )

        protected_path = request.url.path.startswith("/api") or request.url.path == "/health/ready"
        if settings.auth_required and protected_path and request.method != "OPTIONS":
            token = _bearer_token(request)
            if not token or not hmac.compare_digest(token, settings.api_token):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "API authentication required."},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return await call_next(request)

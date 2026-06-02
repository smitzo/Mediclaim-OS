"""Minimal in-process observability for local development and demos."""

from __future__ import annotations

import time
import uuid
from collections import Counter
from typing import Awaitable, Callable

from fastapi import Request, Response


REQUEST_COUNTER: Counter[str] = Counter()
ERROR_COUNTER: Counter[str] = Counter()
LATENCY_TOTAL_MS: Counter[str] = Counter()


async def request_metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    route_key = f"{request.method} {request.url.path}"
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        ERROR_COUNTER[route_key] += 1
        raise
    finally:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        REQUEST_COUNTER[route_key] += 1
        LATENCY_TOTAL_MS[route_key] += elapsed_ms

    response.headers["X-Request-ID"] = request_id
    return response


def metrics_snapshot() -> dict[str, object]:
    return {
        "requests": dict(REQUEST_COUNTER),
        "errors": dict(ERROR_COUNTER),
        "latency_total_ms": dict(LATENCY_TOTAL_MS),
    }

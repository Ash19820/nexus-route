import time
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("gateway.access")
logging.basicConfig(level=logging.INFO, format="%(message)s")

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Skip spamming access logs on health check
        if request.url.path == "/health":
            return response

        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "tier_initial": response.headers.get("x-gateway-initial-tier"),
            "tier_resolved": response.headers.get("x-gateway-resolved-tier"),
            "similarity_score": float(response.headers.get("x-gateway-score")) if response.headers.get("x-gateway-score") else None,
            "router_latency_ms": float(response.headers.get("x-gateway-latency-ms")) if response.headers.get("x-gateway-latency-ms") else None
        }

        logger.info(json.dumps(log_data))
        return response

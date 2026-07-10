import logging

from fastapi import FastAPI, Request, Header, HTTPException
import hmac
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings
from app.core.upload_limits import RequestSizeLimit
from app.core.observability import metrics_snapshot, request_metrics_middleware, readiness


def configure_logging() -> None:
    """Configure application-wide logging once at startup."""
    level_name = (settings.log_level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    for name in ("httpx", "httpcore", "urllib3", "google", "botocore", "boto3"):
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


configure_logging()

app = FastAPI(
    title="Claim Processing Pipeline",
    description=(
        "AI-powered medical claim PDF processing using LangGraph multi-agent orchestration. "
        "Segregates, extracts, and aggregates data from multi-page claim documents."
    ),
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(RequestValidationError)
async def safe_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Request fields do not match the API schema."})


@app.exception_handler(Exception)
async def safe_internal_error(request: Request, exc: Exception):
    logging.getLogger(__name__).error("Request failed (%s)", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Request could not be completed."})

app.middleware("http")(request_metrics_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestSizeLimit)
app.include_router(router, prefix="/api")


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Claim Processing Pipeline",
        "status": "running",
        "version": "1.0",
        "docs": "/docs",
    }


@app.get("/health/live", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


@app.get("/metrics", tags=["Health"])
async def metrics(authorization: str | None = Header(default=None)):
    if settings.app_env == "production" and (not settings.metrics_token or not hmac.compare_digest(authorization or "", "Bearer "+settings.metrics_token)):
        raise HTTPException(status_code=401, detail="Monitoring authentication required.")
    return metrics_snapshot()


@app.get("/health/ready", tags=["Health"])
async def ready():
    checks = readiness()
    return JSONResponse(status_code=200 if all(value == "ok" for value in checks.values()) else 503, content={"status": "ready" if all(value == "ok" for value in checks.values()) else "unavailable", "checks": checks})

from fastapi import FastAPI
from app.core.logger import get_logger
from app.core.logging_config import setup_logging
from app_v2.routers.check import router as check_router

setup_logging(level="INFO", include_time=False, leading_newline=True)
logger = get_logger(__name__)

app = FastAPI(
    title="Elara Tutor V1 API",
    description="Contract-first backend for step validation checks",
    version="0.1.0",
)

app.include_router(check_router)


@app.get("/health")
async def health() -> dict[str, str]:
    logger.info("Health check requested")
    return {"status": "ok"}

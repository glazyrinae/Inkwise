"""Ручка для мониторинга: /health, без префикса /api."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.settings.config import config

router = APIRouter(tags=["service"])


class HealthResponse(BaseModel):
    """Ответ /health."""

    api_status: Literal["ok"] = Field(description="Процесс отвечает")
    service: str = Field(description="Имя сервиса из конфига")
    version: str = Field(description="Версия сервиса")
    debug: bool = Field(description="Режим отладки")


@router.get("/health")
async def health() -> HealthResponse:
    """Сервис отвечает."""
    return HealthResponse(
        api_status="ok",
        service=config.app.title,
        version=config.app.version,
        debug=config.app.debug,
    )

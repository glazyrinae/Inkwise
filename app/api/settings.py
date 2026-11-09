"""Ручки настроек: язык интерфейса; у книги — оформление ссылок и MCP-сервер проверки
орфографии."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.service.book import settings
from app.service.language import t
from app.service.sources import styles
from app.settings.config import config

router = APIRouter(tags=["settings"])


class Interface(BaseModel):
    """Как говорить с человеком: язык интерфейса из настроек приложения."""

    language: Literal["ru", "en"] = Field(
        description="Язык интерфейса", examples=["en"]
    )


class SettingsView(settings.Settings):
    """Настройки книги и из чего в них выбирать."""

    styles: dict[str, str] = Field(
        description="Правила оформления ссылок: ключ → название",
        examples=[{"gost-r-7.0.5-2008": "ГОСТ Р 7.0.5–2008"}],
    )


@router.get("/interface")
def read_interface() -> Interface:
    """Язык интерфейса: оболочка берёт его, когда загружается страница."""
    return Interface(language=config.app.language)


@router.get("/book/settings")
def read_settings() -> SettingsView:
    """Настройки книги; оформление ссылок — уже выбранное или по умолчанию."""
    current = settings.read()
    return SettingsView(
        style=styles.chosen(),
        mcp_url=current.mcp_url,
        styles={key: style.title for key, style in styles.STYLES.items()},
    )


@router.put("/book/settings")
def edit_settings(new: settings.Settings) -> settings.Settings:
    """Сохраняет настройки книги: по ним оформляются новые сноски."""
    if new.style is not None and new.style not in styles.STYLES:
        raise HTTPException(status_code=422, detail=t("Нет такого оформления ссылок"))
    settings.save(new)
    return new

"""Ручки настроек книги: оформление ссылок и MCP-сервер проверки орфографии."""

from fastapi import APIRouter, HTTPException
from pydantic import Field

from app.service.book import settings
from app.service.sources import styles

router = APIRouter(tags=["settings"])


class SettingsView(settings.Settings):
    """Настройки книги и из чего в них выбирать."""

    styles: dict[str, str] = Field(
        description="Правила оформления ссылок: ключ → название",
        examples=[{"gost-r-7.0.5-2008": "ГОСТ Р 7.0.5–2008"}],
    )


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
        raise HTTPException(status_code=422, detail="Нет такого оформления ссылок")
    settings.save(new)
    return new

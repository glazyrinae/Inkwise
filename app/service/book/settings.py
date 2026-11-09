"""Настройки книги: их меняют в оболочке, файл лежит в корне книги."""

from pydantic import BaseModel, Field

from app.service.book import paths
from app.settings.config import config


class Settings(BaseModel):
    """Настройки книги; пока поле не меняли, в нём null."""

    style: str | None = Field(
        default=None,
        description="Оформление ссылок: ключ правила; null — ГОСТ",
        examples=["gost-r-7.0.5-2008"],
    )
    mcp_url: str | None = Field(
        default=None,
        description="MCP-сервер проверки орфографии; null — не подключён",
        examples=["http://host.docker.internal:9000/mcp"],
    )


def read() -> Settings:
    """Настройки книги; файла ещё нет — все поля пустые."""
    file = paths.root() / config.book.settings_file
    if not file.is_file():
        return Settings()
    return Settings.model_validate_json(file.read_bytes())


def save(settings: Settings) -> None:
    """Записывает настройки книги."""
    file = paths.root() / config.book.settings_file
    paths.replace(file, settings.model_dump_json(indent=2).encode())

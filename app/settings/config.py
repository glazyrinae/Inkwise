"""Настройки приложения: значения — из config.toml, секреты — из окружения."""

from pathlib import Path

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class AppSettings(BaseModel):
    """Сервис: название, версия, режим отладки, уровень логов и свои имена хоста."""

    title: str
    version: str
    debug: bool
    log_level: str
    hosts: list[str]


class BookSettings(BaseModel):
    """Книга: папка в контейнере, шаблон текста блока, данные источников, файл
    настроек, папка источников и файл вида в блоке, публикация, корзина, файл и папка
    плагинов, библиотека.

    library — папка, где лежат книги-источники; её путь compose берёт из LIBRARY_DIR.
    """

    root: Path
    chapter_template: str
    sources_file: str
    settings_file: str
    sources: str
    kind_file: str
    document: str
    trash: str
    plugins_file: str
    plugin_files: str
    library: Path


class WebSettings(BaseModel):
    """Скачивание веб-страниц: ожидание ответа сайта и как api ему представляется."""

    timeout: int = Field(gt=0)
    user_agent: str = Field(min_length=1)


class OfficeSettings(BaseModel):
    """ONLYOFFICE Docs: адреса, общий с ним секрет JWT и имя автора.

    public_url — адрес для браузера, его собирает compose из OFFICE_PORT. internal_url
    и api_url — адреса внутри сети compose: api → office и office → api. Секрет —
    в .env.
    """

    public_url: str
    internal_url: str
    api_url: str
    jwt_secret: SecretStr = Field(min_length=1)
    timeout: int = Field(gt=0)
    author: str = Field(min_length=1)


class SpellingSettings(BaseModel):
    """Проверка орфографии: сколько ждать ответа MCP-сервера."""

    timeout: int = Field(gt=0)


class PluginsSettings(BaseModel):
    """Плагины: папка в контейнере, куда compose монтирует PLUGINS_DIR."""

    root: Path


class FontsSettings(BaseModel):
    """Шрифты для office: папка в контейнере, куда compose монтирует FONTS_DIR, и
    сколько ждать office и Google Fonts."""

    root: Path
    timeout: int = Field(gt=0)


class Config(BaseSettings):
    """Настройки: значения в config.toml, переменные окружения их переопределяют.

    Значений по умолчанию в коде нет, и без нужного ключа сервис падает на старте,
    а не на первом запросе. Секрет в config.toml не кладём, он приходит только
    из окружения: OFFICE__JWT_SECRET.
    """

    model_config = SettingsConfigDict(
        toml_file=Path(__file__).with_name("config.toml"),
        env_nested_delimiter="__",
    )

    app: AppSettings
    book: BookSettings
    web: WebSettings
    office: OfficeSettings
    spelling: SpellingSettings
    plugins: PluginsSettings
    fonts: FontsSettings

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Окружение важнее config.toml.

        Файл .env сам не читаем, его передаёт docker compose.
        """
        return (env_settings, TomlConfigSettingsSource(settings_cls))


config = Config()

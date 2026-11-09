"""Приложение FastAPI: uvicorn app.main:app — сервис api в docker-compose.yml."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api import (
    blocks,
    health,
    library,
    materials,
    office,
    plugins,
    quotes,
    settings,
    sources,
    spelling,
    transfer,
)
from app.service.office.formats import UnsupportedFileError
from app.service.plugins import PluginError
from app.settings.config import config

# Оболочка — статика без сборки: страница, скрипты и стили
WEB_DIR = Path(__file__).with_name("web")

# Ошибки сервисов, которые оболочка показывает человеку: код ответа и что случилось.
# Сервис кладёт в исключение, о чём оно: путь, имя файла
ERRORS: dict[type[Exception], tuple[int, str]] = {
    FileNotFoundError: (404, "Не найдено"),
    FileExistsError: (409, "Уже есть"),
    PermissionError: (403, "Нет доступа"),
    UnsupportedFileError: (415, "Редактор не открывает"),
    PluginError: (500, "Ошибка плагина"),
}


class Shell(StaticFiles):
    """Файлы оболочки: браузер сверяет их с api при каждой загрузке страницы.

    Без Cache-Control браузер сам решает, что скрипт ещё свежий, и после обновления
    оболочки берёт старый модуль из кеша — с новой страницей он падает. no-cache не
    запрещает кеш: неизменённый файл api отдаёт ответом 304 без тела.
    """

    def file_response(self, *args: Any, **kwargs: Any) -> Response:
        """Файл, как его отдаёт StaticFiles, с заголовком no-cache."""
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


def create_app() -> FastAPI:
    """Приложение FastAPI; логи только в консоль, их собирает docker compose logs."""
    logging.basicConfig(
        level=config.app.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    application = FastAPI(
        title=config.app.title,
        version=config.app.version,
        debug=config.app.debug,
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=config.app.hosts)
    for error, (status, text) in ERRORS.items():
        application.add_exception_handler(error, _answer(status, text))
    for module in (
        blocks,
        materials,
        sources,
        quotes,
        library,
        settings,
        spelling,
        office,
        plugins,
        transfer,
    ):
        application.include_router(module.router, prefix="/api")
    application.include_router(health.router)
    # Последней: статика в корне забрала бы себе все пути, подключённые после неё
    application.mount("/", Shell(directory=WEB_DIR, html=True), name="web")
    return application


def _answer(status: int, text: str) -> Callable[[Request, Exception], JSONResponse]:
    """Ответ на ошибку сервиса: «Не найдено: 01-Введение/книга.pdf»."""

    def answer(request: Request, error: Exception) -> JSONResponse:
        subject = error.args[0] if error.args else ""
        if isinstance(error, OSError) and error.filename:
            # Ошибка самой ОС: в ней полный путь в контейнере, человеку хватит имени.
            # У symlink и rename нужный файл — второй: куда, а не откуда
            subject = Path(error.filename2 or error.filename).name
        return JSONResponse({"detail": f"{text}: {subject}"}, status_code=status)

    return answer


app = create_app()

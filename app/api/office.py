"""Ручки ONLYOFFICE: файл для редактора, конфиг, приём сохранённого файла и скрипт
содержания собранной книги."""

from typing import Annotated, Any, Literal

import jwt
from fastapi import APIRouter, Body, Header, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from app.service.book import paths
from app.service.office import builder, callback, editor

router = APIRouter(tags=["office"])


class EditorResponse(BaseModel):
    """Скрипт редактора и конфиг для new DocsAPI.DocEditor в оболочке."""

    api_js: str = Field(description="Адрес api.js на office")
    config: dict[str, Any] = Field(description="Конфиг редактора, подписанный JWT")


class OfficeAnswer(BaseModel):
    """Ответ на callback office: 0 — принято."""

    error: Literal[0]


# По этой ссылке office скачивает файл, открывая его в редакторе (document.url)
@router.get("/files/{path:path}", response_class=FileResponse)
def read_file(path: str) -> FileResponse:
    """Файл книги по пути от её корня."""
    return FileResponse(paths.find(path))


@router.get("/office/config")
def editor_config(path: str) -> EditorResponse:
    """Всё, чтобы открыть файл книги в редакторе: скрипт ONLYOFFICE и конфиг."""
    return EditorResponse(api_js=editor.api_js(), config=editor.config_for(path))


# По этой ссылке office скачивает скрипт, которым заполняет содержание собранной книги
@router.get("/office/builder", response_class=PlainTextResponse)
def builder_script(path: str) -> str:
    """Скрипт Document Builder: заполнить содержание в файле книги."""
    paths.find(path)
    return builder.script(path)


@router.post("/office/callback")
async def office_callback(
    path: str,
    body: Annotated[dict[str, Any], Body()],
    authorization: Annotated[str | None, Header()] = None,
    opened: str = "",
) -> OfficeAnswer:
    """Office сообщает о документе; сохранённый файл api записывает в книгу.

    opened — когда текст открыли. Пустое у текстов, открытых до того, как время
    открытия появилось в адресе callback.

    Ответ {"error": 0} office ждёт на любой callback, иначе покажет ошибку.
    """
    try:
        await callback.save(path, opened, body, authorization)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Подпись office неверна") from None
    return OfficeAnswer(error=0)

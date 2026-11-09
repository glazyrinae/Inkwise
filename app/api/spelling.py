"""Ручки проверки орфографии: подключение к MCP-серверу и сама проверка — заглушка."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.service import spelling
from app.service.book import settings
from app.service.language import t

router = APIRouter(tags=["spelling"])


class SpellingRequest(BaseModel):
    """Текст блока на проверку."""

    text: str = Field(description="Выделенный текст или весь текст блока")


@router.get("/spelling/tools")
async def read_tools(url: str) -> list[str]:
    """Инструменты MCP-сервера по адресу: так оболочка проверяет подключение."""
    try:
        return await spelling.tools(url)
    except spelling.ServerError as error:
        raise HTTPException(
            status_code=502, detail=t("MCP-сервер не подключился: {error}", error=error)
        ) from None


@router.post("/spelling", status_code=501)
async def check_spelling(request: SpellingRequest) -> None:
    """Заглушка проверки: доводит текст до MCP-сервера, но ещё не проверяет его.

    Отвечает 501 с пояснением: дошёл ли текст и отвечает ли сервер. Проверку сделаем,
    когда выберем сервер и его инструмент.
    """
    url = settings.read().mcp_url
    if not url:
        raise HTTPException(
            status_code=409,
            detail=t(
                "MCP-сервер не подключён: кнопка «Проверка орфографии» слева внизу"
            ),
        )
    try:
        tools = await spelling.tools(url)
    except spelling.ServerError as error:
        raise HTTPException(
            status_code=502, detail=t("MCP-сервер не отвечает: {error}", error=error)
        ) from None
    raise HTTPException(
        status_code=501,
        detail=t(
            "Проверка орфографии ещё не сделана. Текст дошёл: {count} знаков; "
            "MCP-сервер отвечает, его инструменты: {tools}",
            count=len(request.text),
            tools=", ".join(tools) or t("нет"),
        ),
    )

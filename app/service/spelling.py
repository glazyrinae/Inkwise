"""Проверка орфографии через MCP-сервер.

Сервер подключают в оболочке, его адрес лежит в настройках книги. Пока сделано только
подключение: список инструментов показывает, что сервер отвечает по протоколу MCP. Какой
инструмент звать и как показывать исправления, решим, когда выберем сервер.
"""

import anyio
from mcp import Client

from app.service.language import t
from app.settings.config import config


class ServerError(Exception):
    """MCP-сервер не ответил или ответил не по протоколу."""


async def tools(url: str) -> list[str]:
    """Названия инструментов MCP-сервера: так проверяем, что он отвечает.

    Raises:
        ServerError: сервер не ответил за [spelling] timeout секунд или ответил ошибкой.
    """
    try:
        with anyio.fail_after(config.spelling.timeout):
            async with Client(url) as client:
                result = await client.list_tools()
    # Здесь только обращение к серверу, и любая его ошибка значит одно: подключиться
    # не вышло. Человеку нужна причина, а не трассировка
    except Exception as error:
        raise ServerError(_reason(error)) from error
    return [tool.name for tool in result.tools]


def _reason(error: BaseException) -> str:
    """Причина ошибки: клиент MCP заворачивает её в ExceptionGroup, бывает и дважды."""
    while isinstance(error, BaseExceptionGroup):
        error = error.exceptions[0]
    if isinstance(error, TimeoutError):
        return t("не ответил за {seconds} с", seconds=config.spelling.timeout)
    return f"{type(error).__name__}: {error}"

"""Сохранённый файл от ONLYOFFICE: office присылает ссылку на него в callback.

Ctrl+S — сразу (статус 6), закрыли файл — примерно через 10 секунд (статус 2).
"""

import logging
from pathlib import Path
from typing import Any

import httpx
import jwt

from app.service.book import changes, paths, trash
from app.settings.config import config

logger = logging.getLogger(__name__)

# Статусы callback, с которыми office присылает готовый файл: 2 — документ закрыли
# с изменениями, 6 — сохранили по Ctrl+S, не закрывая (customization.forcesave)
SAVED = {2, 6}


async def save(
    path: str, opened: str, body: dict[str, Any], authorization: str | None
) -> None:
    """Записывает в книгу файл, который office прислал в callback. opened — когда
    текст открыли, как trash.stamp().

    Тело берём из подписи office: без неё кто угодно подсунул бы свою ссылку.

    Raises:
        jwt.InvalidTokenError: подписи нет или она чужая.
    """
    data = _signed_body(body, authorization)
    if data["status"] not in SAVED:
        return
    # Ссылку office строит от адреса, по которому его открыл браузер, а из контейнера
    # api он доступен по внутреннему. Так же делает официальный коннектор ONLYOFFICE
    # для Nextcloud
    url = data["url"].replace(config.office.public_url, config.office.internal_url, 1)
    async with httpx.AsyncClient(timeout=config.office.timeout) as client:
        response = await client.get(url)
    response.raise_for_status()
    file = _file(path, opened)
    if file is None:
        logger.warning("Не сохранил %s: файла нет ни в книге, ни в корзине", path)
        return
    paths.replace(file, response.content)


def _file(path: str, opened: str) -> Path | None:
    """Куда записать текст: блок могли унести в корзину, переименовать или
    переставить, пока текст был открыт, — тогда правки идут за ним.

    Корзину смотрим первой: на месте унесённого блока может быть уже другой с тем же
    путём — например, после импорта книги.
    """
    trashed = trash.find(path, since=opened)
    if trashed:
        return trashed
    for where in (path, changes.moved(path)):
        try:
            return paths.find(where)
        except FileNotFoundError:
            pass
    return None


def _signed_body(body: dict[str, Any], authorization: str | None) -> dict[str, Any]:
    """Тело callback из JWT: из поля token или из заголовка Authorization.

    В заголовке office кладёт тело в обёртку {"payload": ...}.
    """
    token = body.get("token") or (authorization or "").removeprefix("Bearer ")
    secret = config.office.jwt_secret.get_secret_value()
    claims: dict[str, Any] = jwt.decode(token, secret, algorithms=["HS256"])
    return claims.get("payload", claims)

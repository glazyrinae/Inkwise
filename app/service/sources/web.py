"""Веб-страница как источник: api скачивает её сам и находит в ней данные для ссылки.

Заглавие, авторов, сайт и дату находит trafilatura. Копию текста для блока собирает
web_copy.py.
"""

import datetime
from urllib.parse import unquote

import httpx
import trafilatura

from app.service.language import t
from app.service.sources.description import heading
from app.service.sources.models import WebPage
from app.settings.config import config


class PageError(Exception):
    """Сайт не отдал страницу."""


def download(url: str) -> tuple[str, bytes]:
    """Страница по адресу: адрес после переадресаций и HTML.

    Raises:
        PageError: сайт не ответил, ответил ошибкой или отдал не веб-страницу.
    """
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=config.web.timeout,
            headers={"User-Agent": config.web.user_agent},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        # Своё пояснение у сайта бывает длинным: Википедия пишет о политике для роботов
        status = error.response.status_code
        raise PageError(
            t(
                "сайт ответил {status} {reason}",
                status=status,
                reason=httpx.codes.get_reason_phrase(status),
            )
        ) from error
    except httpx.HTTPError as error:
        raise PageError(
            t("сайт не ответил ({reason})", reason=type(error).__name__)
        ) from error
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type:
        raise PageError(
            t(
                "по адресу не веб-страница, а файл {type}: скачай его и подключи "
                "как книгу",
                type=content_type,
            )
        )
    return readable(str(response.url)), response.content


def readable(url: str) -> str:
    """Адрес, как его показывает браузер: «/wiki/Ссылка», а не «/wiki/%D0%A1…».

    Запрос после «?» не трогаем: в нём закодированный «&» — часть значения.
    """
    path, mark, query = url.partition("?")
    return unquote(path) + mark + query


def recognize(url: str, page: bytes | None) -> WebPage:
    """Данные, какие нашлись на странице; дата обращения — сегодня.

    page — HTML страницы; None — сайт её не отдал, данные впишут в форме. Тогда
    заглавие — из конца адреса: «…/wiki/Библиографическая_ссылка».
    """
    metadata = trafilatura.extract_metadata(page, default_url=url) if page else None
    hostname = httpx.URL(url).host
    today = datetime.date.today().strftime("%d.%m.%Y")
    if not metadata:
        last = url.partition("?")[0].rstrip("/").rsplit("/", 1)[-1]
        return WebPage(
            kind="web",
            authors=[],
            title=last.replace("_", " ") or hostname,
            site=hostname,
            year="",
            url=url,
            accessed=today,
        )
    # Авторов trafilatura отдаёт строкой: «Антон Соколов; Иван Петров»
    authors = [name for name in (metadata.author or "").split(";") if name.strip()]
    return WebPage(
        kind="web",
        authors=[heading(name, surname_first=False) for name in authors],
        title=metadata.title or hostname,
        site=metadata.sitename or hostname,
        year=(metadata.date or "")[:4],
        url=url,
        accessed=today,
    )

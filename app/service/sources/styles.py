"""Оформление ссылок: по какому правилу api собирает сноску из данных источника.

Правило выбирают в настройках книги. Пока оно одно — ГОСТ Р 7.0.5–2008. Другое,
например западное, — ещё одна запись в STYLES: название и функция сноски. Уже
вставленные сноски смена правила не трогает, по нему оформляются новые.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.service.book import settings
from app.service.sources.description import INITIAL
from app.service.sources.models import Book, Source, WebPage

GOST = "gost-r-7.0.5-2008"


@dataclass(frozen=True)
class Style:
    """Правило оформления: название для настроек и сноска по нему."""

    title: str
    # Сноска на страницы файла (первая, последняя — с 1); у веб-страницы страниц нет
    footnote: Callable[[Source, tuple[int, int] | None], str]


def footnote(source: Source, pages: tuple[int, int] | None = None) -> str:
    """Сноска по правилу из настроек книги."""
    return STYLES[chosen()].footnote(source, pages)


def chosen() -> str:
    """Правило из настроек книги; пока его не выбирали — ГОСТ."""
    return settings.read().style or GOST


def gost_head(source: Source) -> str:
    """Начало сноски по ГОСТ: заголовок с авторами и заглавие.

    Одного–трёх авторов ставим в заголовок, при четырёх и более ссылка начинается
    с заглавия: «Введение в … / Г. Джеймс [и др.]». Сайт веб-страницы — за «//».
    Ещё по этому началу плагин находит сноски, вставленные без поля с ключом источника.
    """
    title = source.title
    if isinstance(source, WebPage):
        title += " [Электронный ресурс]"
    if len(source.authors) > 3:
        head = f"{title} / {_initials_first(source.authors[0])} [и др.]"
    else:
        head = " ".join([", ".join(source.authors), title]).strip()
    if isinstance(source, WebPage) and source.site:
        head += f" // {source.site}"
    return head


def _gost(source: Source, pages: tuple[int, int] | None) -> str:
    """Подстрочная ссылка по ГОСТ Р 7.0.5–2008.

    «Ангелакос Д. Антипаттерны PostgreSQL… – СПб. : Питер, 2026. – С. 101.»
    «Соколов А. Статья [Электронный ресурс] // Хабр. – 2026. – URL: https://… (дата
    обращения: 06.11.2026).»
    """
    if isinstance(source, Book):
        output = (
            f"{source.place or '[Б. м.]'} : {source.publisher or '[б. и.]'}, "
            f"{source.year or '[б. г.]'}"
        )
        areas = [gost_head(source), source.edition, output, _gost_pages(source, pages)]
    else:
        access = f"URL: {source.url}"
        if source.accessed:
            access += f" (дата обращения: {source.accessed})"
        areas = [gost_head(source), source.year, access]
    # Области описания разделяет «. – »; точку после сокращения («испр.») не удваиваем
    text = ""
    for area in filter(None, areas):
        if text:
            text += " – " if text.endswith((".", "!", "?")) else ". – "
        text += area
    return f"{text}."


def _gost_pages(source: Book, pages: tuple[int, int] | None) -> str:
    """«С. 100» или «С. 100–101»: печатные номера — страницы файла минус сдвиг."""
    if not pages:
        return ""
    first, last = (page - source.page_offset for page in pages)
    return f"С. {first}" if first == last else f"С. {first}–{last}"


def _initials_first(author: str) -> str:
    """«Джеймс Г.» → «Г. Джеймс»: так автор стоит в сведениях об ответственности."""
    words = author.split()
    initials = [word for word in words if INITIAL.fullmatch(word)]
    return " ".join([*initials, *(word for word in words if word not in initials)])


# Правила по ключу из настроек книги; ключ хранится в файле настроек
STYLES = {GOST: Style(title="ГОСТ Р 7.0.5–2008", footnote=_gost)}

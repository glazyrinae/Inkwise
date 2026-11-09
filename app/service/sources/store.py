"""Подтверждённые данные источников — файл источников в корне книги.

Распознанное человек проверяет в форме, подтверждённое лежит здесь: одна запись на
источник, общая для всех блоков, куда он подключён. Ключ записи — путь книги на диске
или адрес веб-страницы, см. key.
"""

import html
import re
from pathlib import Path

from pydantic import TypeAdapter

from app.service.book import paths
from app.service.sources.models import Source
from app.settings.config import config

SOURCES = TypeAdapter(dict[str, Source])
# Адрес веб-страницы в её копии: так копию пишет web_copy.py
CANONICAL = re.compile(r'<link rel="canonical" href="([^"]+)">')


def key(file: Path) -> str:
    """Ключ источника — в файле источников и в поле сноски.

    У книги это её путь на диске. У копии веб-страницы — адрес страницы: копию можно
    переименовать, а одна страница может лежать в нескольких блоках.
    """
    if file.suffix == ".html" and file.is_file():
        with file.open(encoding="utf-8", errors="replace") as copy:
            canonical = CANONICAL.search(copy.read(4096))
        if canonical:
            return html.unescape(canonical.group(1))
    return str(file)


def saved(source_key: str) -> Source | None:
    """Подтверждённые данные источника; None — их ещё не подтверждали."""
    return _read().get(source_key)


def save(source_key: str, source: Source) -> None:
    """Запоминает подтверждённые данные источника: их возьмут другие блоки и сноски."""
    sources = _read()
    sources[source_key] = source
    paths.replace(_file(), SOURCES.dump_json(sources, indent=2))


def link_name(source: Source, suffix: str) -> str:
    """Имя ссылки в папке блока — первый автор и заглавие, как в начале сноски.

    «Ангелакос Д. Антипаттерны PostgreSQL и как их избежать.pdf»
    """
    stem = " ".join([*source.authors[:1], source.title])
    # «/» в имени файла нельзя, а файлы с точкой в начале дерево не показывает
    stem = re.sub(r"[/\\]", "-", stem).lstrip(". ")
    # Имя файла в Linux — не длиннее 255 байт, а буква кириллицы — это два байта
    limit = 255 - len(suffix.encode())
    if len(stem.encode()) > limit:
        cut = stem.encode()[: limit - len("…".encode())].decode(errors="ignore")
        stem = cut.rsplit(" ", 1)[0] + "…"
    return stem + suffix


def _read() -> dict[str, Source]:
    file = _file()
    return SOURCES.validate_json(file.read_bytes()) if file.is_file() else {}


def _file() -> Path:
    return paths.root() / config.book.sources_file

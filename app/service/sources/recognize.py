"""Данные книги для ссылки — из самой книги; человек проверит их в форме.

В русских книгах на обороте титула стоит готовое описание, см. description.py. Нет
описания — берём свойства файла (Title, Author): их заполняют английские издательства.
Нет и их — остаётся имя файла.
"""

import logging
import re
from collections import Counter
from pathlib import Path

from app.service.sources import bookfile, description
from app.service.sources.models import Book

logger = logging.getLogger(__name__)

# Год книги без описания: «© 2025 Packt Publishing», «Copyright © 2001 by …»
COPYRIGHT_YEAR = re.compile(r"(?:©|Copyright)\s*(?:by\s+)?((?:19|20)\d{2})")
# Авторы в свойствах файла: «Valliappa Lakshmanan;Hannes Hapke;», «A and B»
AUTHORS = re.compile(r";|,| and ")
# Мусор в свойствах: логин сборщика («arist», «user»), имя файла вместо названия
JUNK_AUTHOR = re.compile(r"^\w+$")
JUNK_TITLE = re.compile(r"\.\w{2,4}$|^untitled$", re.IGNORECASE)
# Номер страницы с края колонтитула: «101», «[ 88 ]», «4.2. Партиции   101»,
# «102   Глава 4»
PAGE_NUMBER = re.compile(r"^\[?\s*(\d{1,4})\s*\]?(?:\s|$)|\s(\d{1,4})$")


def from_file(file: Path) -> Book:
    """Данные, какие нашлись в самой книге; чего нет — допишут в форме."""
    source = Book(
        authors=[],
        title=file.stem.replace("_", " "),
        edition="",
        place="",
        publisher="",
        year="",
        page_offset=0,
    )
    if file.suffix.lower() not in bookfile.READABLE:
        return source
    try:
        book = bookfile.read(file)
        pages = range(book.page_count)
        # Описание — на обороте титула, у некоторых издательств — на последних страницах
        edges = [book.text(index) for index in dict.fromkeys([*pages[:8], *pages[-3:]])]
        described = [parsed for text in edges if (parsed := description.parse(text))]
        result = described[0] if described else _from_properties(book, edges, source)
        result.page_offset = _page_offset(book)
        return result
    except bookfile.READ_ERRORS as error:
        # Нечитаемый файл не мешает подключить книгу: данные впишут в форме
        logger.warning("Не прочитал книгу %s: %s", file, error)
        return source


def _from_properties(book: bookfile.BookFile, edges: list[str], source: Book) -> Book:
    """Свойства файла: их заполняют английские издательства; год — из «©» у ISBN."""
    author = book.author.strip(" ;")
    authors = (
        [
            description.heading(name, surname_first=False)
            for name in AUTHORS.split(author)
            if name.strip()
        ]
        if author and not JUNK_AUTHOR.match(author)
        else []
    )
    title = bookfile.LAYOUT_JUNK.sub("", book.title).strip()
    copyright_page = next((text for text in edges if "ISBN" in text), "")
    return source.model_copy(
        update={
            "authors": authors,
            "title": title if title and not JUNK_TITLE.search(title) else source.title,
            "year": max(COPYRIGHT_YEAR.findall(copyright_page), default=""),
        }
    )


def _page_offset(book: bookfile.BookFile) -> int:
    """На сколько номер страницы в файле больше печатного.

    Берём метку страницы PDF, а без меток — число с края колонтитула на страницах из
    середины книги: какой сдвиг чаще всего, тот и верный.
    """
    middle = range(
        book.page_count // 3, min(book.page_count, book.page_count // 3 + 15)
    )
    votes: Counter[int] = Counter()
    for index in middle:
        label = book.label(index)
        if label.isdigit():
            return index + 1 - int(label)
        lines = [line.strip() for line in book.text(index).splitlines() if line.strip()]
        for line in lines[:3] + lines[-3:]:
            if number := PAGE_NUMBER.search(line):
                votes[index + 1 - int(number.group(1) or number.group(2))] += 1
    offset, count = votes.most_common(1)[0] if votes else (0, 0)
    # Совпадений меньше, чем на половине страниц, — это не номера, а числа из текста
    return offset if count >= len(middle) // 2 else 0

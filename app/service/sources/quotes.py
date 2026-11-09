"""Цитата для текста блока: текст из книги без следов вёрстки и его страницы."""

import re
from pathlib import Path

from app.service.sources import bookfile


def quote(text: str) -> str:
    """Цитата для вставки в текст: в кавычках, без переносов строк и слов из вёрстки.

    Пустой текст — пустая цитата: в скане выделить нечего, вставляем только сноску.
    """
    if not text.strip():
        return ""
    text = bookfile.LAYOUT_JUNK.sub("", text)
    # Слово, перенесённое на другую строку: «партициони-\nрования»
    text = re.sub(r"(?<=[а-яёa-z])-\s*\n\s*(?=[а-яёa-z])", "", text)
    text = " ".join(text.split())
    # Точку в конце цитаты по правилам набора ставят за кавычками и знаком сноски:
    # «…данных»¹. Многоточие и сокращение («т. п.») не трогаем
    if text.endswith(".") and not re.search(r"\.\.$|\s\w{1,2}\.$", text):
        text = text[:-1]
    return f"«{text}»"


def pages(file: Path, text: str, page: int) -> tuple[int, int]:
    """Страницы файла (с 1), где начинается и кончается цитата.

    Просмотрщик сообщает только текущую страницу, а видно бывает и две, и цитата может
    перейти на следующую. Поэтому ищем начало и конец цитаты на текущей странице и на
    соседних; не нашли — верим просмотрщику.
    """
    letters = _letters(text)
    if file.suffix.lower() not in {".pdf", ".djvu"} or not letters:
        return page, page
    book = bookfile.read(file)
    nearby = [p for p in (page, page + 1, page - 1) if 1 <= p <= book.page_count]
    texts = {p: _letters(book.text(p - 1)) for p in nearby}
    first = next((p for p in nearby if letters[:30] in texts[p]), page)
    last = next(
        (p for p in sorted(nearby) if p >= first and letters[-30:] in texts[p]), first
    )
    return first, last


def _letters(text: str) -> str:
    """Только буквы и цифры: так текст страницы сравним с выделенным в просмотрщике.

    Пробелы, переносы строк и слов, кавычки у них расходятся, а буквы — нет.
    """
    return re.sub(r"[\W_]", "", text.lower())

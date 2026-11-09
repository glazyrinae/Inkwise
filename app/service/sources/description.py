"""Библиографическое описание на обороте титула русской книги (ГОСТ Р 7.0.4).

  Ангелакос Джимми                                   ← заголовок: авторы
  А64                                                ← авторский знак
  Антипаттерны PostgreSQL и как их избежать. — СПб.: Питер, 2026. — 272 с.

Рядом стоят УДК, ББК и ISBN. Описание — готовые данные для сноски, их и разбираем.
"""

import re

from app.service.sources.bookfile import LAYOUT_JUNK
from app.service.sources.models import Book

# Авторский знак стоит в начале строки; в распознанном скане бывает «0-96» вместо «О96»
AUTHOR_SIGN = re.compile(r"(?m)^[ \t]*[А-ЯЁ0]-?\d{2,3}\b")
# Выходные данные: «— СПб.: Питер, 2026», «– М.: ДМК Пресс, 2021»
OUTPUT = re.compile(
    r"[–—-]\s*(?P<place>[А-ЯЁA-Z][\w. -]{0,25}?)\s*:\s*"
    r"(?P<publisher>[^,:]{2,60}?),\s*(?P<year>(?:1[89]|20)\d{2})"
)
# Конец заглавия: « / пер. с англ.», «. – 2-е изд.», «шк.— 3-е изд.», выходные данные
TITLE_END = re.compile(r"\s/\s|\.?\s*[–—-]\s*$|\.\s*[–—]\s|\.\s-\s")
# Заголовок в одной строке с заглавием: «Аристов Евгений. PostgreSQL 14…»
INLINE_HEADING = re.compile(
    r"^([А-ЯЁ][а-яё-]+ (?:[А-ЯЁ]\.(?: ?[А-ЯЁ]\.)?|[А-ЯЁ][а-яё]+\.)) (.+)"
)
# Автор в заголовке — хотя бы два слова: «Ангелакос Джимми», «Харенслак Б.»
NAME = re.compile(r"^[А-ЯЁA-Z]\S+ [А-ЯЁA-Z]")
# Авторы в сведениях об ответственности, если распознавание скана испортило заголовок:
# «Изучаем LangChain / М. Ошин, Н. Кампос. –»
RESPONSIBILITY = re.compile(r"\s/\s([А-ЯЁA-Z]\.\s?[^/–—]+?)(?:\.\s+[–—-]|$)")
EDITION = re.compile(r"[–—-]\s*(\d+-е\s[^–—]*?изд[^–—]*?)\.?\s*[–—-]")
# По ГОСТ издательство пишут без кавычек и без формы собственности
LEGAL_FORM = re.compile(r"^(?:ООО|ТОО|АО|ЗАО|ОАО)\s+")
# Инициал: «Б.», «Дж.»
INITIAL = re.compile(r"\w{1,2}\.")


def parse(text: str) -> Book | None:
    """Данные книги из описания на странице; None — описания на ней нет."""
    text = LAYOUT_JUNK.sub("", text)
    output = OUTPUT.search(text)
    signs = list(AUTHOR_SIGN.finditer(text, 0, output.start())) if output else []
    if not output or not signs or "ISBN" not in text:
        return None
    sign = signs[-1]
    # Описание переносится по строкам как придётся: склеиваем его в одну
    record = " ".join(text[sign.end() : output.start() + 1].split())
    lines = [line.strip() for line in text[: sign.start()].splitlines() if line.strip()]
    authors = lines[-1] if lines else ""
    if not NAME.match(authors) and (inline := INLINE_HEADING.match(record)):
        authors, record = inline.groups()
    names, surname_first = authors.split(","), True
    if not NAME.match(names[0].strip()):
        responsibility = RESPONSIBILITY.search(record)
        names = responsibility.group(1).split(",") if responsibility else []
        surname_first = False
    title = TITLE_END.split(record, maxsplit=1)[0].strip(" .")
    if not title:
        return None
    edition = EDITION.search(f"{record} –")
    publisher = " ".join(output["publisher"].replace("«", "").replace("»", "").split())
    return Book(
        authors=[heading(name, surname_first) for name in names if name.strip()],
        title=title,
        edition=edition.group(1).strip(" .") if edition else "",
        place=output["place"].strip(),
        publisher=LEGAL_FORM.sub("", publisher),
        year=output["year"],
        page_offset=0,
    )


def heading(name: str, surname_first: bool) -> str:
    """Автор в форме заголовка по ГОСТ: «Фамилия И. О.».

    «Ангелакос Джимми» → «Ангелакос Д.», «Victor Dibia» → «Dibia V.»,
    «де Руйтер Дж.» — как есть.
    """
    words = name.replace(".", ". ").split()
    if not surname_first:
        words = [words[-1], *words[:-1]]
    # Частицы со строчной буквы («де», «ван») — часть фамилии
    start = 0
    while start < len(words) - 1 and words[start].islower():
        start += 1
    initials = [
        word if INITIAL.fullmatch(word) else f"{word[0]}."
        for word in words[start + 1 :]
    ]
    return " ".join([*words[: start + 1], *initials])

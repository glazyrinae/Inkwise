"""Копия веб-страницы в папке блока: из неё цитируют, как из книги.

Текст статьи из страницы достаёт trafilatura: меню, реклама и прочая обвязка сайта
в копию не попадают. Копию открывает тот же просмотрщик, что и книги. Ещё копия хранит
текст таким, каким он был в дату обращения из сноски.
"""

import html
import re

import trafilatura

from app.service.language import t
from app.service.sources.models import WebPage

# Копия — HTML: его открывает просмотрщик ONLYOFFICE
SUFFIX = ".html"
# Тело статьи в HTML от trafilatura
BODY = re.compile(r"<body>(.*)</body>", re.DOTALL)
# Адрес страницы стоит в копии как canonical: по нему store.key узнаёт страницу
COPY = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="canonical" href="{url}">
</head>
<body>
<p><i>{note}</i></p>
{article}
</body>
</html>
"""
NO_TEXT = (
    "<p>Текст страницы сохранить не удалось. Открой её по адресу выше; сноску на неё "
    "ставит правый клик → «Сноска на эту страницу».</p>"
)


def copy(source: WebPage, page: bytes | None) -> str:
    """Копия страницы для просмотрщика: адрес и дата обращения, под ними текст статьи.

    page — HTML страницы; None — сайт её не отдал, в копии будет только адрес.
    """
    article = (
        trafilatura.extract(
            page,
            url=source.url,
            output_format="html",
            include_formatting=True,
            include_links=True,
            include_tables=True,
            # Картинки по ссылкам на сайт просмотрщик стал бы скачивать при открытии
            include_images=False,
        )
        if page
        else None
    )
    body = BODY.search(article) if article else None
    text = body.group(1) if body else t(NO_TEXT)
    if "<h1" not in text:
        text = f"<h1>{html.escape(source.title)}</h1>\n{text}"
    url = html.escape(source.url)
    note = t(
        "Копия страницы {link}, дата обращения {accessed}",
        link=f'<a href="{url}">{url}</a>',
        accessed=html.escape(source.accessed),
    )
    return COPY.format(
        title=html.escape(source.title), url=url, note=note, article=text
    )

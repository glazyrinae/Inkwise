"""Ручки данных источника для формы: книга в блоке и веб-страница."""

from pathlib import PurePath

from fastapi import APIRouter
from pydantic import AnyHttpUrl, BaseModel, Field

from app.service.book import materials, paths
from app.service.sources import recognize, store, styles, web, web_copy
from app.service.sources.models import Source, WebPage

router = APIRouter(tags=["sources"])

# Страница файла, для которой форма показывает пример сноски
SAMPLE_PAGE = 101


class SourceView(BaseModel):
    """Данные источника для формы и что из них получится: имя ссылки и сноска."""

    source: Source = Field(description="Данные книги или веб-страницы")
    link: str = Field(
        description="Имя ссылки на книгу или копии страницы в папке блока",
        examples=["Ландау Л. Д. Механика.djvu"],
    )
    page: int | None = Field(
        description="Страница файла в примере сноски; у веб-страницы страниц нет",
        examples=[SAMPLE_PAGE],
    )
    footnote: str = Field(
        description="Пример сноски по правилу из настроек книги",
        examples=["Ландау Л. Д. Механика. – М. : Наука, 1988. – С. 100."],
    )
    warning: str | None = Field(
        description="Что не получилось: например, сайт не отдал страницу",
        examples=["Сайт ответил 403 Forbidden: данные впиши сам"],
    )


@router.get("/book/source")
def read_book_source(path: str) -> SourceView:
    """Данные книги или веб-страницы из блока — для формы правки."""
    file = paths.find(path)
    source = store.saved(store.key(file)) or recognize.from_file(file)
    return view(source, file.suffix)


@router.put("/book/source")
def edit_book_source(path: str, source: Source) -> str:
    """Сохраняет исправленные данные источника и называет ссылку по ним.

    В ответе — новый путь ссылки или копии страницы.
    """
    file = paths.find(path)
    renamed = materials.rename(path, store.link_name(source, file.suffix))
    # Ключ данных у ссылки на книгу и у копии страницы прежний, а файл, лежащий в самой
    # главе, переименование переносит
    store.save(store.key(paths.find(renamed)), source)
    return renamed


@router.get("/web/source", tags=["web"])
def read_web_source(url: AnyHttpUrl) -> SourceView:
    """Данные веб-страницы для формы: подтверждённые раньше или найденные на ней.

    Сайт не отдал страницу — форма всё равно откроется: данные впишут сами.
    """
    address, warning = web.readable(str(url)), None
    try:
        address, page = web.download(address)
    except web.PageError as error:
        page, warning = None, f"Страница не скачалась: {error}. Данные впиши сам."
    source = store.saved(address) or web.recognize(address, page)
    return view(source, web_copy.SUFFIX, warning)


@router.post("/sources/preview")
def preview_source(source: Source, path: str) -> SourceView:
    """Имя ссылки и пример сноски, пока данные правят в форме.

    Из пути книги нужно только расширение — для имени ссылки; у веб-страницы
    path — её адрес, а копия всегда .html.
    """
    return view(source, PurePath(path).suffix)


def view(source: Source, suffix: str, warning: str | None = None) -> SourceView:
    """Данные для формы, имя ссылки и пример сноски; suffix — расширение книги."""
    if isinstance(source, WebPage):
        return SourceView(
            source=source,
            link=store.link_name(source, web_copy.SUFFIX),
            page=None,
            footnote=styles.footnote(source),
            warning=warning,
        )
    return SourceView(
        source=source,
        link=store.link_name(source, suffix),
        page=SAMPLE_PAGE,
        footnote=styles.footnote(source, (SAMPLE_PAGE, SAMPLE_PAGE)),
        warning=warning,
    )

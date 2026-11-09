"""Ручка цитаты: текст, выделенный в книге, превращается в цитату со сноской."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.service.book import paths
from app.service.sources import quotes, recognize, store, styles
from app.service.sources.models import Book

router = APIRouter(tags=["sources"])


class QuoteRequest(BaseModel):
    """Текст, выделенный в книге."""

    path: str = Field(
        description="Ссылка на книгу в блоке: путь от корня книги",
        examples=["01-Введение/Ландау Л. Д. Механика.djvu"],
    )
    page: int | None = Field(
        ge=1,
        description="Страница файла, с 1; null — у просмотрщика страниц нет: "
        "веб-страница, EPUB",
        examples=[101],
    )
    text: str = Field(
        description="Выделенный текст; пусто — нужна только сноска на страницу"
    )


class Quote(BaseModel):
    """Что вставить в текст: цитату и сноску к ней.

    source и pages плагин кладёт в поле сноски: по ним сноску потом находят.
    """

    quote: str = Field(
        description="Цитата в кавычках, без переносов из вёрстки; пусто — только сноска"
    )
    footnote: str = Field(
        description="Сноска по правилу из настроек книги",
        examples=["Ландау Л. Д. Механика. – М. : Наука, 1988. – С. 100."],
    )
    source: str = Field(
        description="Ключ источника: путь книги на диске или адрес страницы",
        examples=["/home/user/Книги/Ландау.djvu"],
    )
    pages: tuple[int, int] | None = Field(
        description="Первая и последняя страницы файла; у веб-страницы — null",
        examples=[[101, 102]],
    )


@router.post("/book/quote")
def make_quote(request: QuoteRequest) -> Quote:
    """Цитата из источника для текста блока: в кавычках, со сноской на него.

    У книги сноска — на страницу цитаты; у веб-страницы и у книги, где просмотрщик не
    знает страниц, — без страниц.
    """
    file = paths.find(request.path)
    key = store.key(file)
    source = store.saved(key) or recognize.from_file(file)
    pages = (
        quotes.pages(file, request.text, request.page)
        if isinstance(source, Book) and request.page
        else None
    )
    return Quote(
        quote=quotes.quote(request.text),
        footnote=styles.footnote(source, pages),
        source=key,
        pages=pages,
    )

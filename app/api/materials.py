"""Ручки материалов блока: книга с диска, копия веб-страницы, удаление из блока."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.service import library
from app.service.book import materials, paths
from app.service.sources import store, styles, web, web_copy
from app.service.sources.models import Book, WebPage

router = APIRouter(tags=["book"])


class BookLink(BaseModel):
    """Книга с диска и её данные из формы."""

    path: str = Field(
        description="Полный путь книги на диске",
        examples=["/home/user/Книги/Ландау.djvu"],
    )
    source: Book = Field(description="Данные книги, подтверждённые в форме")


class Material(BaseModel):
    """Материал блока перед удалением: что удалится и как найти сноски на него."""

    link: bool = Field(description="Ссылка на книгу: удалится она, а не книга")
    source: str = Field(
        description="Ключ источника в поле сноски: путь книги или адрес страницы",
        examples=["/home/user/Книги/Ландау.djvu"],
    )
    head: str | None = Field(
        description="Начало старых сносок, вставленных без поля; null — данных нет",
        examples=["Ландау Л. Д. Механика"],
    )


@router.post("/book/books", status_code=201)
def add_book(block: str, link: BookLink) -> str:
    """Подключает к блоку книгу с диска и запоминает её данные.

    Ссылку называем по данным книги: первый автор и заглавие. В ответе — путь ссылки
    от корня книги.
    """
    file = library.find(link.path)
    name = store.link_name(link.source, file.suffix)
    path = materials.add_link(block, file, name)
    store.save(store.key(file), link.source)
    return path


@router.post("/book/web", tags=["web"], status_code=201)
def add_web_page(block: str, source: WebPage) -> str:
    """Подключает к блоку веб-страницу и запоминает её данные.

    В папку блока ложится копия текста страницы с именем «первый автор + заглавие».
    Сайт не отдал страницу — в копии будет только адрес. В ответе — путь копии от
    корня книги.
    """
    try:
        _, page = web.download(source.url)
    except web.PageError:
        page = None
    name = store.link_name(source, web_copy.SUFFIX)
    path = materials.add_copy(block, name, web_copy.copy(source, page))
    store.save(source.url, source)
    return path


@router.get("/book/material")
def read_material(path: str) -> Material:
    """Материал блока перед удалением: ссылка ли это и как найти сноски на него.

    Работает и для ссылки на перенесённую книгу: её тоже надо уметь убрать.
    """
    key = store.key(paths.target(path))
    source = store.saved(key)
    return Material(
        link=paths.in_book(path).is_symlink(),
        source=key,
        # Старые сноски вставлены ещё без поля, и все — по ГОСТ
        head=styles.gost_head(source) if source else None,
    )


@router.delete("/book/files", status_code=204)
def remove_file(path: str) -> None:
    """Убирает материал из блока: ссылку на книгу или файл; книга остаётся на месте.

    Сноски на него из текста блока удаляет плагин в редакторе, до этого вызова.
    """
    materials.remove(path)

"""Ручки дерева книги: блоки — разделы, введение, заключение и другие; публикация."""

from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints

from app.service.book import blocks, changes, document, trash
from app.service.book.blocks import Block
from app.service.office import builder

router = APIRouter(tags=["book"])

# Название станет именем папки и текста блока: без «/» и «\», не скрытое, без нулевого
# байта. Такое имя не уведёт за пределы книги
Title = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^[^./\\\x00][^/\\\x00]*$",
    ),
]


class BlockCreate(BaseModel):
    """Новый блок книги."""

    kind: blocks.Kind = Field(
        description="Раздел, введение, заключение, титульный лист или свой блок",
        examples=["section"],
    )
    title: Title | None = Field(
        description="Название раздела или своего блока; у остальных null — своё",
        examples=["Методы испытаний"],
    )


class BlockRename(BaseModel):
    """Новое название блока."""

    title: Title = Field(description="Название", examples=["Методы испытаний"])


class BlockOrder(BaseModel):
    """Новый порядок блоков: после перетаскивания в дереве."""

    order: list[str] = Field(
        description="Все блоки книги, папки по порядку",
        examples=[["02-Введение", "01-Титульный лист", "03-Методы испытаний"]],
    )


class Book(BaseModel):
    """Дерево книги для оболочки."""

    # Модуль blocks здесь не виден: поле с тем же именем закрывает его
    blocks: list[Block] = Field(description="Блоки по порядку")
    document: str | None = Field(
        description="Публикация; null — её ещё не собирали",
        examples=["Публикация.docx"],
    )


@router.get("/book")
def read_book() -> Book:
    """Блоки книги по порядку: источники, у разделов — заголовки; публикация."""
    return Book(blocks=blocks.tree(), document=document.path())


@router.post("/book/blocks", status_code=201)
def add_block(block: BlockCreate) -> blocks.Block:
    """Новый блок там, где ему место по ГОСТ: папка с номером и текст с заголовком."""
    try:
        return changes.add(block.kind, block.title)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.patch("/book/blocks", status_code=204)
def rename_block(path: str, block: BlockRename) -> None:
    """Переименовывает блок: его папку и текст."""
    changes.rename(path, block.title)


@router.put("/book/blocks/order", status_code=204)
def reorder_blocks(order: BlockOrder) -> None:
    """Расставляет блоки в новом порядке: номера в именах папок по порядку."""
    try:
        changes.reorder(order.order)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.delete("/book/blocks", status_code=204)
def remove_block(path: str) -> None:
    """Уносит блок со всеми материалами в корзину книги."""
    trash.put(path)


@router.post("/book/document")
def build_document() -> str:
    """Собирает публикацию заново: содержание, тексты блоков по порядку, источники."""
    try:
        return document.build()
    except builder.BuilderError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Публикация собрана, но без содержания: {error}",
        ) from None


@router.delete("/book/document", status_code=204)
def remove_document() -> None:
    """Удаляет публикацию."""
    document.remove()

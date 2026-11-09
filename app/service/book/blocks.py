"""Блоки книги — папки в её корне: разделы, введение, заключение, титульный лист и свои
блоки, например «Реферат» или «Приложение А».

В папке блока его текст, названный как блок («02-Введение/Введение.docx»), и папка
источников: ссылки на книги, копии веб-страниц. Порядок задаёт номер в начале имени
папки, вид блока — файл вида в ней; без файла это раздел. Разделы нумеруются по порядку:
1, 2, 3. Подразделы, пункты и подпункты — заголовки в тексте раздела, см. headings.py.
Добавить, переименовать и переставить — changes.py, удалить — trash.py.
"""

import math
import re
from pathlib import Path, PurePosixPath
from typing import Literal, get_args

from pydantic import BaseModel, Field

from app.service.book import headings, paths
from app.service.book.headings import Heading
from app.settings.config import config

# Номер в начале имени папки, «01-Введение»: по нему блоки идут по порядку
NUMBER = re.compile(r"^(\d+)-")

Kind = Literal["section", "introduction", "conclusion", "title_page", "custom"]
KINDS: tuple[Kind, ...] = get_args(Kind)


class Block(BaseModel):
    """Блок книги для дерева в оболочке."""

    path: str = Field(
        description="Папка от корня книги", examples=["02-Методы испытаний"]
    )
    kind: Kind = Field(
        description="Раздел, введение, заключение, титульный лист или свой блок",
        examples=["section"],
    )
    number: int | None = Field(
        description="Номер раздела: 1, 2, 3; у остальных блоков null", examples=[1]
    )
    title: str = Field(description="Название", examples=["Методы испытаний"])
    text: str | None = Field(
        description="Текст — его правят; null — в папке его нет",
        examples=["02-Методы испытаний/Методы испытаний.docx"],
    )
    materials: list[str] = Field(
        description="Источники блока: ссылки на книги, копии веб-страниц, другие файлы",
        examples=[["02-Методы испытаний/источники/Ландау Л. Д. Механика.djvu"]],
    )
    # Модуль headings здесь не виден: поле с тем же именем закрывает его
    headings: list[Heading] = Field(
        description="Подразделы, пункты и подпункты в тексте раздела по порядку"
    )


def tree() -> list[Block]:
    """Блоки книги по порядку; у разделов — номера и заголовки в тексте."""
    blocks = []
    sections = 0
    for folder in folders():
        kind = kind_of(folder)
        sections += kind == "section"
        blocks.append(block(folder, kind, sections if kind == "section" else None))
    return blocks


def block(folder: Path, kind: Kind, number: int | None) -> Block:
    """Блок в папке folder."""
    text = folder / text_name(folder.name)
    found = sources(folder)
    # Ссылку показываем, даже если книгу перенесли: иначе она молча пропала бы из блока
    materials = sorted(
        entry
        for entry in (found.iterdir() if found.is_dir() else ())
        if (entry.is_file() or entry.is_symlink())
        and not entry.is_dir()
        and not paths.hidden(entry.name)
    )
    has_text = text.is_file()
    return Block(
        path=paths.relative(folder),
        kind=kind,
        number=number,
        title=title(folder.name),
        text=paths.relative(text) if has_text else None,
        materials=[paths.relative(entry) for entry in materials],
        headings=headings.read(text) if has_text and kind == "section" else [],
    )


def folders() -> list[Path]:
    """Папки блоков по номеру в имени, без номера — в конце.

    Служебные папки (корзина) и ссылки на папки — не блоки.
    """
    found = [
        entry
        for entry in paths.root().iterdir()
        if entry.is_dir() and not entry.is_symlink() and not paths.hidden(entry.name)
    ]
    return sorted(found, key=_order)


def kind_of(folder: Path) -> Kind:
    """Вид блока из файла в его папке; без файла — раздел."""
    file = folder / config.book.kind_file
    kind = file.read_text(encoding="utf-8").strip() if file.is_file() else "section"
    return next((known for known in KINDS if known == kind), "section")


def is_text(path: str) -> bool:
    """Текст ли это блока: его правят, остальные файлы открывают на просмотр."""
    file = PurePosixPath(path)
    return len(file.parts) == 2 and file.name == text_name(file.parent.name)


def sources(folder: Path) -> Path:
    """Папка источников блока; её нет, пока к блоку ничего не подключили."""
    return folder / config.book.sources


def title(folder_name: str) -> str:
    """Название блока — имя папки без номера."""
    return NUMBER.sub("", folder_name, count=1)


def text_name(folder_name: str) -> str:
    """Имя текста блока: как его название."""
    return f"{title(folder_name)}.docx"


def _order(folder: Path) -> tuple[float, str]:
    number = NUMBER.match(folder.name)
    return (int(number.group(1)) if number else math.inf, folder.name)

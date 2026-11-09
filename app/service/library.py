"""Книги на диске: окно выбора книги ходит по папкам библиотеки.

Библиотека — часть диска, которую compose открывает api только на чтение (LIBRARY_DIR
в .env, по умолчанию домашняя папка). Книги могут лежать в ней где угодно.
"""

from pathlib import Path

from pydantic import BaseModel, Field

from app.service.office import formats
from app.settings.config import config


class Folder(BaseModel):
    """Папка в окне выбора книги."""

    path: str = Field(description="Полный путь папки", examples=["/home/user/Книги"])
    parent: str | None = Field(
        description="Папка выше; null — это корень библиотеки, выше подняться нельзя"
    )
    folders: list[str] = Field(description="Подпапки", examples=[["Физика"]])
    books: list[str] = Field(
        description="Файлы, которые откроет редактор", examples=[["Ландау.djvu"]]
    )


def browse(path: str | None) -> Folder:
    """Подпапки и книги папки библиотеки, без скрытых; без path — корень библиотеки.

    Raises:
        FileNotFoundError: папки нет или она за пределами библиотеки.
        PermissionError: папку нельзя прочитать.
    """
    root = config.book.library.resolve()
    folder = Path(path).resolve() if path else root
    if not folder.is_relative_to(root) or not folder.is_dir():
        raise FileNotFoundError(path)
    entries = sorted(
        (entry for entry in folder.iterdir() if not entry.name.startswith(".")),
        key=lambda entry: entry.name.casefold(),
    )
    return Folder(
        path=str(folder),
        parent=None if folder == root else str(folder.parent),
        folders=[entry.name for entry in entries if entry.is_dir()],
        books=[
            entry.name
            for entry in entries
            if entry.is_file() and formats.can_open(entry.name)
        ],
    )


def find(path: str) -> Path:
    """Книга в библиотеке по полному пути.

    Raises:
        FileNotFoundError: файла нет или он за пределами библиотеки.
        formats.UnsupportedFileError: такой файл редактор не откроет.
    """
    file = Path(path).resolve()
    if not file.is_relative_to(config.book.library.resolve()) or not file.is_file():
        raise FileNotFoundError(path)
    if not formats.can_open(file.name):
        raise formats.UnsupportedFileError(file.name)
    return file

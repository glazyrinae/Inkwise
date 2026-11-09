"""Пути в книге: оболочка называет файлы и блоки путём от корня книги.

Путь проверяем, не переходя по ссылкам: «..» не должен увести из книги. Ссылка на книгу
в папке блока ведёт в библиотеку — туда можно, но только читать.
"""

import os
from pathlib import Path

from app.settings.config import config


def root() -> Path:
    """Корень книги."""
    return config.book.root.resolve()


def in_book(path: str) -> Path:
    """Путь в книге как есть: ссылку на книгу не заменяет её целью.

    Raises:
        FileNotFoundError: путь уводит за пределы книги.
    """
    local = Path(os.path.normpath(root() / path))
    if not local.is_relative_to(root()):
        raise FileNotFoundError(path)
    return local


def target(path: str) -> Path:
    """Куда ведёт путь: у ссылки — книга на диске, даже если книгу перенесли.

    Raises:
        FileNotFoundError: путь уводит за пределы книги.
    """
    return in_book(path).resolve()


def find(path: str) -> Path:
    """Файл книги; у ссылки на книгу — сама книга в библиотеке.

    Raises:
        FileNotFoundError: файла нет, путь уводит за пределы книги или ссылка ведёт
            за пределы библиотеки.
    """
    file = target(path)
    allowed = file.is_relative_to(root()) or file.is_relative_to(
        config.book.library.resolve()
    )
    if not allowed or not file.is_file():
        raise FileNotFoundError(path)
    return file


def block(path: str) -> Path:
    """Папка блока книги: раздела, введения и других — папка в корне книги.

    Raises:
        FileNotFoundError: такой папки нет, она не в корне книги, это ссылка или скрытая
            папка — например, корзина.
    """
    folder = in_book(path)
    if folder.parent != root() or hidden(folder.name):
        raise FileNotFoundError(path)
    if folder.is_symlink() or not folder.is_dir():
        raise FileNotFoundError(path)
    return folder


def relative(path: Path) -> str:
    """Путь от корня книги: так файлы и блоки знает оболочка."""
    return path.relative_to(root()).as_posix()


def hidden(name: str) -> bool:
    """Служебное имя: скрытое (корзина, наш временный файл, блокировка LibreOffice)
    или «~$» Word."""
    return name.startswith((".", "~$"))


def replace(file: Path, data: bytes) -> None:
    """Записывает файл через временный рядом: сбой записи не испортит прежний."""
    temporary = file.with_name(f".{file.name}.tmp")
    temporary.write_bytes(data)
    temporary.replace(file)

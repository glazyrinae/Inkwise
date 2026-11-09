"""Корзина книги: скрытая папка в её корне, куда «✕» уносит блок со всем, что в нём.

Папка блока получает имя из времени удаления и пути блока:
«2026-11-06 10-15-03 02-Методы испытаний». По нему блок находят и возвращают на место
руками. Книги по ссылкам остаются на диске. В именах старых копий — путь главы с
параграфами через «›»: «… 01-Введение › 02-Цели».
"""

from datetime import datetime
from pathlib import Path, PurePosixPath

from app.service.book import paths
from app.settings.config import config

# Путь в имени папки — через «›»: «/» в имени папки нельзя
SEPARATOR = " › "


def put(path: str) -> None:
    """Уносит блок в корзину.

    Raises:
        FileNotFoundError: такого блока нет.
    """
    folder = paths.block(path)
    folder.rename(_trash() / f"{stamp()} {path.replace('/', SEPARATOR)}")


def put_book() -> None:
    """Уносит в корзину всю книгу: блоки, данные источников, настройки, публикацию.

    Блоки получают там такие же имена, как от «✕»: правки текста, открытого в этот
    момент, лягут в его копию в корзине.
    """
    trash = _trash()
    now = stamp()
    for entry in paths.root().iterdir():
        if entry != trash:
            entry.rename(trash / f"{now} {entry.name}")


def find(path: str, since: str) -> Path | None:
    """Файл блока в самой свежей копии блока в корзине; None — его там нет.

    Нужен, когда office сохраняет текст, открытый в момент удаления блока: правки не
    пропадут, а лягут в корзину вместе с ним. since — когда текст открыли, как stamp():
    копия, унесённая в корзину раньше, — другой блок с тем же путём. Пустое — любая.
    """
    trash = paths.root() / config.book.trash
    if not trash.is_dir():
        return None
    parts = PurePosixPath(path).parts
    found = []
    for folder in trash.iterdir():
        # Имя папки — время удаления и путь блока
        removed = " ".join(folder.name.split(" ")[:2])
        deleted = tuple(folder.name.split(" ", 2)[-1].split(SEPARATOR))
        file = folder.joinpath(*parts[len(deleted) :])
        fits = parts[: len(deleted)] == deleted and file != folder and file.is_file()
        if fits and removed >= since:
            found.append(file)
    # Имя папки начинается со времени удаления: самая свежая копия — последняя по имени
    return max(found, default=None)


def stamp() -> str:
    """Время для имени папки в корзине: «2026-11-06 10-15-03». Строки в таком виде
    сравниваются так же, как время."""
    return datetime.now().strftime("%Y-%m-%d %H-%M-%S")


def _trash() -> Path:
    trash = paths.root() / config.book.trash
    trash.mkdir(exist_ok=True)
    return trash

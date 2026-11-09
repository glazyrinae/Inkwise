"""Источники блока — файлы в его папке источников: ссылки на книги, копии страниц."""

from pathlib import Path

from app.service.book import blocks, paths


def add_link(block: str, file: Path, name: str) -> str:
    """Подключает к блоку книгу с диска: в папке источников появляется ссылка на неё.

    Сама книга остаётся на месте. В ответе — путь ссылки от корня книги.

    Raises:
        FileNotFoundError: такого блока нет.
        FileExistsError: в блоке уже есть файл с таким именем.
    """
    link = _sources(block) / name
    link.symlink_to(file)
    return paths.relative(link)


def add_copy(block: str, name: str, text: str) -> str:
    """Кладёт в папку источников блока новый файл с текстом; в ответе — его путь.

    Raises:
        FileNotFoundError: такого блока нет.
        FileExistsError: в блоке уже есть файл с таким именем.
    """
    file = _sources(block) / name
    # «x» — только новый файл: чужой с тем же именем не перезапишем
    with file.open("x", encoding="utf-8") as copy:
        copy.write(text)
    return paths.relative(file)


def remove(path: str) -> None:
    """Убирает материал из блока: ссылку на книгу или файл. Книга по ссылке остаётся.

    Raises:
        FileNotFoundError: такого файла в блоке нет или путь уводит за пределы книги.
        PermissionError: это текст блока — он удаляется только вместе с блоком.
    """
    file = paths.in_book(path)
    if file.parent == paths.root() or not (file.is_file() or file.is_symlink()):
        raise FileNotFoundError(path)
    if blocks.is_text(path):
        raise PermissionError(path)
    file.unlink()


def rename(path: str, name: str) -> str:
    """Переименовывает материал; в ответе — его новый путь от корня книги.

    Raises:
        FileNotFoundError: файла нет или путь уводит за пределы книги.
        FileExistsError: рядом уже есть файл с таким именем.
    """
    paths.find(path)
    current = paths.in_book(path)
    renamed = current.with_name(name)
    if renamed == current:
        return path
    # rename молча заменил бы другой файл с тем же именем
    if renamed.exists() or renamed.is_symlink():
        raise FileExistsError(name)
    current.rename(renamed)
    return paths.relative(renamed)


def _sources(block: str) -> Path:
    """Папка источников блока; создаём, когда подключают первый.

    Raises:
        FileNotFoundError: такого блока нет.
    """
    folder = blocks.sources(paths.block(block))
    folder.mkdir(exist_ok=True)
    return folder

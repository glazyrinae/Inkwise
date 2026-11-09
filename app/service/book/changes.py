"""Новые блоки книги, переименование и перестановка.

Номер в имени папки задаёт порядок блоков, поэтому новый блок в середине книги и
перестановка переименовывают папки соседей. Блок office может ещё держать открытым:
правки он пришлёт по старому пути. Поэтому api помнит переименования, пока работает, —
см. moved().

Текст блока на диске здесь не меняется: открытый в office текст office потом
перезаписал бы. Заголовок и номер раздела в тексте ставит плагин, когда текст открыт.
"""

from pathlib import Path

from app.service.book import blocks, paths, texts
from app.service.language import t
from app.settings.config import config

# Название в имени папки у блоков, которые не называют сами
TITLES: dict[blocks.Kind, str] = {
    "introduction": "Введение",
    "conclusion": "Заключение",
    "title_page": "Титульный лист",
}

# Переименования по порядку: (старый путь, новый) от корня книги
_moves: list[tuple[str, str]] = []


def add(kind: blocks.Kind, title: str | None) -> blocks.Block:
    """Новый блок с текстом там, где ему место по ГОСТ 7.32; потом его можно перетащить.

    title — название раздела или своего блока; у введения, заключения и титульного
    листа название своё. Введение, заключение и титульный лист — по одному на книгу.

    Raises:
        ValueError: у раздела или своего блока нет названия.
        FileExistsError: такой блок в книге уже есть.
    """
    title = t(TITLES[kind]) if kind in TITLES else title
    if not title:
        raise ValueError(t("Нужно название"))
    current = blocks.folders()
    kinds = [blocks.kind_of(folder) for folder in current]
    if kind in TITLES and kind in kinds:
        raise FileExistsError(title)
    index = _place(kind, kinds)
    _arrange([*current[:index], None, *current[index:]])
    folder = paths.root() / f"{index + 1:02d}-{title}"
    folder.mkdir()
    if kind != "section":
        (folder / config.book.kind_file).write_text(kind, encoding="utf-8")
    sections = kinds[:index].count("section") + 1
    texts.create(
        folder / blocks.text_name(folder.name),
        title=None if kind == "title_page" else title,
        number=sections if kind == "section" else None,
    )
    return blocks.block(folder, kind, sections if kind == "section" else None)


def rename(path: str, title: str) -> None:
    """Новое название блока: номер в имени папки прежний, текст называется как блок.

    Raises:
        FileNotFoundError: такого блока нет.
        FileExistsError: в книге уже есть блок с таким именем.
    """
    folder = paths.block(path)
    number = blocks.NUMBER.match(folder.name)
    renamed = folder.with_name(f"{number.group(0) if number else ''}{title}")
    if renamed == folder:
        return
    # rename молча заменил бы пустую папку с тем же именем
    if renamed.exists():
        raise FileExistsError(renamed.name)
    folder.rename(renamed)
    _remember(folder, renamed)
    text = renamed / blocks.text_name(folder.name)
    if text.is_file():
        text.rename(renamed / blocks.text_name(renamed.name))
        _remember(text, renamed / blocks.text_name(renamed.name))


def reorder(order: list[str]) -> None:
    """Расставляет блоки в порядке order: номера в именах папок — 01, 02 и дальше.

    Raises:
        ValueError: в order не все блоки книги — дерево в оболочке устарело.
    """
    current = blocks.folders()
    if sorted(order) != sorted(paths.relative(folder) for folder in current):
        raise ValueError(t("Блоки книги изменились: обнови страницу"))
    _arrange([paths.block(path) for path in order])


def moved(path: str) -> str:
    """Где теперь файл, если с тех пор его блок переименовали или переставили."""
    for old, new in _moves:
        if path == old or path.startswith(f"{old}/"):
            path = new + path[len(old) :]
    return path


def _place(kind: blocks.Kind, kinds: list[blocks.Kind]) -> int:
    """Место нового блока среди блоков kinds, как в ГОСТ 7.32: титульный лист в
    начале, введение перед разделами, раздел после разделов, заключение за ними, свой
    блок в конце."""
    sections = [i for i, found in enumerate(kinds) if found == "section"]
    if kind == "title_page":
        return 0
    if kind == "introduction":
        return _first(kinds, ("section", "conclusion"))
    if kind in ("section", "conclusion") and sections:
        return sections[-1] + 1
    if kind == "section":
        return _first(kinds, ("conclusion",))
    return len(kinds)


def _first(kinds: list[blocks.Kind], wanted: tuple[blocks.Kind, ...]) -> int:
    """Место первого блока из видов wanted; таких нет — конец книги."""
    return next((i for i, found in enumerate(kinds) if found in wanted), len(kinds))


def _arrange(order: list[Path | None]) -> None:
    """Номера папок блоков по порядку: 01, 02 и дальше; None — место нового блока.

    Переименовываем через временные скрытые имена: два блока с одним названием могут
    поменяться номерами.
    """
    targets = [
        (folder, folder.with_name(f"{number:02d}-{blocks.title(folder.name)}"))
        for number, folder in enumerate(order, start=1)
        if folder is not None
    ]
    moving = [(folder, target) for folder, target in targets if folder != target]
    for folder, _ in moving:
        folder.rename(folder.with_name(f".{folder.name}"))
    for folder, target in moving:
        folder.with_name(f".{folder.name}").rename(target)
        _remember(folder, target)


def _remember(old: Path, new: Path) -> None:
    _moves.append((paths.relative(old), paths.relative(new)))

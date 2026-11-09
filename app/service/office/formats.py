"""Какие файлы открывает редактор ONLYOFFICE и в каком из своих редакторов."""

from pathlib import PurePath

# Расширение → тип редактора ONLYOFFICE. Полный список форматов — в образе office:
# document-formats/onlyoffice-docs-formats.json
EDITOR_TYPES = {
    "docx": "word",
    "doc": "word",
    "odt": "word",
    "rtf": "word",
    "txt": "word",
    "md": "word",
    "html": "word",
    "epub": "word",
    "fb2": "word",
    "pdf": "pdf",
    "djvu": "pdf",
    "xlsx": "cell",
    "pptx": "slide",
}


class UnsupportedFileError(Exception):
    """Файл такого типа редактор не открывает."""


def can_open(name: str) -> bool:
    """Откроет ли редактор файл с таким именем."""
    return extension(name) in EDITOR_TYPES


def extension(name: str) -> str:
    """Расширение без точки, строчными: «Книга.PDF» → «pdf»."""
    return PurePath(name).suffix.removeprefix(".").lower()

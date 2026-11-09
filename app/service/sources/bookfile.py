"""Текст книги-файла: PDF, EPUB и FB2 читает PyMuPDF, DJVU — утилиты djvulibre."""

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pymupdf

# Что читаем: DJVU — утилитой djvutxt, остальное — PyMuPDF
READABLE = {".pdf", ".epub", ".fb2", ".djvu"}
# Файл не прочитался: битый или djvulibre не справилась
READ_ERRORS = (pymupdf.FileDataError, subprocess.SubprocessError)
# Следы вёрстки в тексте страниц: мягкие переносы и управляющие символы, у Питера
# перед заглавием стоит невидимый BEL
LAYOUT_JUNK = re.compile(r"\N{SOFT HYPHEN}\s*|[\x00-\x08\x0e-\x1f\x7f]")


@dataclass
class BookFile:
    """Открытая книга: число страниц, текст и печатный номер страницы, свойства."""

    page_count: int
    # Текст страницы по её номеру с 0
    text: Callable[[int], str]
    # Печатный номер из меток страниц PDF; "" — меток нет
    label: Callable[[int], str]
    title: str = ""
    author: str = ""


def read(file: Path) -> BookFile:
    """Открывает книгу из READABLE.

    Raises:
        pymupdf.FileDataError, subprocess.SubprocessError: файл не прочитался.
    """
    if file.suffix.lower() == ".djvu":
        return _read_djvu(file)
    document = pymupdf.open(file)
    metadata = document.metadata or {}
    has_labels = document.is_pdf and bool(document.get_page_labels())
    return BookFile(
        page_count=document.page_count,
        text=lambda index: document[index].get_text(),
        label=lambda index: document[index].get_label() if has_labels else "",
        title=metadata.get("title") or "",
        author=metadata.get("author") or "",
    )


def _read_djvu(file: Path) -> BookFile:
    """DJVU читаем djvutxt из пакета djvulibre-bin: PyMuPDF этот формат не открывает."""
    page_count = int(_run("djvused", "-e", "n", str(file)))
    return BookFile(
        page_count=page_count,
        text=lambda index: _run("djvutxt", f"--page={index + 1}", str(file)),
        label=lambda index: "",
    )


def _run(*command: str) -> str:
    return subprocess.run(
        command, capture_output=True, text=True, check=True, timeout=30
    ).stdout

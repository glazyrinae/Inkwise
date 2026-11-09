"""Текст нового блока книги: копия шаблона или пустой документ, заголовки по ГОСТ."""

import shutil
from pathlib import Path

import docx
from docx.document import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm

from app.service import plugins
from app.service.book import headings, paths
from app.settings.config import config

# Язык нового текста — язык интерфейса: по нему редактор проверяет орфографию
SPELLING = {"ru": "ru-RU", "en": "en-US"}


def create(file: Path, title: str | None = None, number: int | None = None) -> None:
    """Новый текст: копия шаблона, без шаблона — пустой документ.

    Заголовки в нём нумеруются сами, раздел — с номера number. title — заголовок в
    начале текста: с номером у раздела, без номера у введения и других блоков. Без title
    текст пустой — например, титульный лист.

    Raises:
        plugins.PluginError: плагин оформления упал.
    """
    template = _template()
    if template:
        shutil.copyfile(template, file)
    else:
        _blank(file)
    document = docx.Document(str(file))
    _language(document)
    headings.number(document, number or 1)
    # Абзац, в котором пишут текст: в пустом документе python-docx абзацев нет
    if not document.paragraphs:
        document.add_paragraph()
    if title:
        headings.title(document, title, numbered=number is not None)
    document.save(str(file))


def _template() -> Path | None:
    """Шаблон: от включённого плагина оформления, иначе свой шаблон в корне книги;
    None — шаблона нет."""
    chosen = plugins.template()
    if chosen:
        return chosen
    book = paths.root() / config.book.chapter_template
    return book if book.is_file() else None


def _blank(file: Path) -> None:
    """Пустой текст на листе A4. У python-docx по умолчанию американский Letter."""
    document = docx.Document()
    section = document.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    document.save(str(file))


def _language(document: Document) -> None:
    """Язык текста по умолчанию — язык интерфейса. С чужим языком проверка
    орфографии в редакторе подчёркивала бы весь текст: у python-docx и шаблонов
    по умолчанию английский или русский."""
    defaults = document.styles.element.xpath("w:docDefaults/w:rPrDefault/w:rPr")
    if not defaults:
        return
    language = defaults[0].find(qn("w:lang"))
    if language is None:
        language = OxmlElement("w:lang")
        defaults[0].append(language)
    language.set(qn("w:val"), SPELLING[config.app.language])

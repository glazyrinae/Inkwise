"""Таблица в публикации не рвётся между страницами, если умещается на одной.

Office держит таблицу целиком, когда строки не делятся, а каждая строка, кроме
последней, держится со следующей. С ней держится и абзац над таблицей — подпись. Но
таблицу длиннее страницы с такой связкой office 10.0 переносит на новую страницу, а
подпись оставляет одну на пустой странице перед ней. Поэтому высоту таблицы оцениваем по
тексту и картинкам в ячейках. У длинной таблицы с подписью держится только первая
строка, а дальше таблица переходит на следующие страницы как обычно.
"""

import math

from docx.document import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.oxml.table import CT_Row, CT_Tc
from docx.shared import Emu, Mm

# Высота строки текста 12 пт через один интервал в ячейке, пт: так office в шаблонах
LINE = 14.6
# Средняя ширина буквы Times New Roman 12 пт, пт
LETTER = 6
# Поля ячейки слева и справа вместе, пт
PADDING = 6
# Целиком держим таблицу не выше этой доли страницы: оценка высоты грубая
SHARE = 0.75
# Ширина текста для ячейки, у которой своей ширины в файле нет: её доля в строке
TEXT_WIDTH = Mm(160)


def keep_whole(document: Document) -> None:
    """Таблицы документа не рвутся между страницами, подпись над таблицей — с ней."""
    page = _page_height(document)
    for table in document.element.body.iter(qn("w:tbl")):
        rows = table.findall(qn("w:tr"))
        for row in rows:
            properties = row.get_or_add_trPr()
            if properties.find(qn("w:cantSplit")) is None:
                properties.insert(0, OxmlElement("w:cantSplit"))
        fits = _height(rows) <= SHARE * page
        for row in rows[:-1] if fits else rows[:1]:
            for paragraph in row.iter(qn("w:p")):
                paragraph.get_or_add_pPr().keepNext_val = True
        caption = table.getprevious()
        if caption is not None and caption.tag == qn("w:p"):
            caption.get_or_add_pPr().keepNext_val = True


def _page_height(document: Document) -> float:
    """Высота текста на странице, пт; без размеров страницы в файле — A4, поля 20 мм."""
    section = document.sections[0]
    height, top, bottom = section.page_height, section.top_margin, section.bottom_margin
    if height is None or top is None or bottom is None:
        return Mm(257).pt
    return Emu(height - top - bottom).pt


def _height(rows: list[CT_Row]) -> float:
    """Примерная высота строк таблицы, пт: по самой высокой ячейке каждой строки."""
    height = 0.0
    for row in rows:
        cells = row.findall(qn("w:tc"))
        share = Emu(TEXT_WIDTH // max(len(cells), 1))
        height += max((_cell_height(cell, share) for cell in cells), default=LINE)
    return height


def _cell_height(cell: CT_Tc, fallback: Emu) -> float:
    """Примерная высота ячейки, пт: строки текста и картинки."""
    width = (cell.width or fallback).pt - PADDING
    letters = max(math.floor(width / LETTER), 1)
    lines = sum(
        max(math.ceil(len("".join(paragraph.xpath(".//w:t/text()"))) / letters), 1)
        for paragraph in cell.iter(qn("w:p"))
    )
    pictures = sum(Emu(int(size)).pt for size in cell.xpath(".//wp:extent/@cy"))
    return lines * LINE + pictures

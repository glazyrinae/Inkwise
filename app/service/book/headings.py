"""Заголовки в тексте раздела по ГОСТ 7.32–2017: раздел, подраздел, пункт, подпункт.

Номера «1», «1.1», «1.1.1», «1.1.1.1» ставит сам редактор: стили «Heading 1»…«Heading 4»
связаны с многоуровневым списком Word. Добавили или удалили подраздел — номера ниже
пересчитались, а в собранной книге нумерация разделов идёт подряд. У заголовка без
номера — введения, заключения, своего блока — номер списка отключён в самом абзаце.
"""

import re
from copy import deepcopy
from pathlib import Path

import docx
from docx.document import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, RGBColor
from docx.styles.style import ParagraphStyle
from docx.text.paragraph import Paragraph
from pydantic import BaseModel, Field

# Раздел, подраздел, пункт, подпункт
LEVELS = 4
# Абзацный отступ по ГОСТ: с него начинается и заголовок раздела
INDENT = Cm(1.25)
# Стиль заголовка: «Heading 1» … «Heading 9»; Word пишет имя с маленькой буквы
HEADING = re.compile(r"heading ([1-9])", re.IGNORECASE)


class Heading(BaseModel):
    """Подраздел, пункт или подпункт в тексте раздела."""

    level: int = Field(
        description="2 — подраздел, 3 — пункт, 4 — подпункт", examples=[2]
    )
    text: str = Field(
        description="Название без номера", examples=["Стендовые испытания"]
    )


def number(document: Document, start: int) -> None:
    """Нумерует заголовки «Heading 1»…«Heading 4»: раздел с номера start, ниже — «1.1».

    Заголовки чёрные, как весь текст по ГОСТ. Шаблон может отключить нумерацию —
    номером списка 0 в стиле «Heading 1», как в APA: тогда заголовки без номеров.
    """
    styles = [style(document, f"Heading {level}") for level in range(1, LEVELS + 1)]
    if styles[0].element.xpath("w:pPr/w:numPr/w:numId[@w:val='0']"):
        return
    numbering = document.part.numbering_part.element
    abstract_id = _next_id(numbering.xpath("w:abstractNum/@w:abstractNumId"), 0)
    num_id = _next_id(numbering.xpath("w:num/@w:numId"), 1)
    levels = "".join(
        f'<w:lvl w:ilvl="{level}">'
        f'<w:start w:val="{start if level == 0 else 1}"/><w:numFmt w:val="decimal"/>'
        f'<w:pStyle w:val="{heading.style_id}"/><w:suff w:val="space"/>'
        f'<w:lvlText w:val="{".".join(f"%{n}" for n in range(1, level + 2))}"/>'
        f'<w:lvlJc w:val="left"/>'
        f'<w:pPr><w:ind w:left="0" w:firstLine="{_indent(heading)}"/></w:pPr></w:lvl>'
        for level, heading in enumerate(styles)
    )
    abstract = parse_xml(
        f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{abstract_id}">'
        f'<w:multiLevelType w:val="multilevel"/>{levels}</w:abstractNum>'
    )
    # Все abstractNum по схеме идут раньше num
    first_num = numbering.find(qn("w:num"))
    if first_num is None:
        numbering.append(abstract)
    else:
        first_num.addprevious(abstract)
    numbering.append(
        parse_xml(
            f'<w:num {nsdecls("w")} w:numId="{num_id}">'
            f'<w:abstractNumId w:val="{abstract_id}"/></w:num>'
        )
    )
    for level, heading in enumerate(styles):
        numbered = heading.element.get_or_add_pPr().get_or_add_numPr()
        numbered.get_or_add_ilvl().val = level
        numbered.get_or_add_numId().val = num_id
        heading.font.color.rgb = RGBColor(0, 0, 0)


def title(document: Document, text: str, numbered: bool) -> None:
    """Заголовок блока, «Heading 1», — перед первым абзацем текста. Без номера — по
    центру прописными, как заголовок структурного элемента по ГОСТ: «ВВЕДЕНИЕ».
    """
    first = document.paragraphs[0]
    paragraph = first.insert_paragraph_before(text, style(document, "Heading 1"))
    if not numbered:
        unnumbered(paragraph)


def unnumbered(paragraph: Paragraph) -> None:
    """Заголовок без номера, как у структурного элемента по ГОСТ: по центру прописными,
    «ВВЕДЕНИЕ». Номер списка из стиля отключён в самом абзаце."""
    paragraph.text = paragraph.text.upper()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # Отступ первой строки из стиля сдвинул бы заголовок с середины строки
    paragraph.paragraph_format.first_line_indent = 0
    paragraph._p.get_or_add_pPr().get_or_add_numPr().get_or_add_numId().val = 0


def read(file: Path) -> list[Heading]:
    """Подразделы, пункты и подпункты в тексте раздела по порядку."""
    found = []
    for paragraph in docx.Document(str(file)).paragraphs:
        name = paragraph.style.name if paragraph.style else None
        match = HEADING.fullmatch(name or "")
        level = int(match.group(1)) if match else 0
        if 1 < level <= LEVELS and paragraph.text.strip():
            found.append(Heading(level=level, text=paragraph.text.strip()))
    return found


def style(document: Document, name: str) -> ParagraphStyle:
    """Стиль абзаца по имени, как его показывает Word: «Heading 1».

    Office пишет в файл имя «Heading 1», Word — «heading 1», а по имени python-docx
    находит только второе. Стиль, которого в шаблоне нет, берём из пустого документа
    python-docx.
    """
    for found in document.styles:
        if isinstance(found, ParagraphStyle) and found.name == name:
            return found
    element = deepcopy(docx.Document().styles[name].element)
    document.styles.element.append(element)
    return ParagraphStyle(element)


def _indent(heading: ParagraphStyle) -> int:
    """Отступ первой строки заголовка с номером, twips: из стиля, если шаблон его задал,
    иначе абзацный по ГОСТ. Отступ номера списка сильнее стиля и сдвинул бы, например,
    заголовок по центру."""
    own = heading.paragraph_format.first_line_indent
    return INDENT.twips if own is None else own.twips


def _next_id(taken: list[str], first: int) -> int:
    return max((int(value) + 1 for value in taken), default=first)

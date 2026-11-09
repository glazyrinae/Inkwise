"""Шаблон по оформлению образца: пустой документ со стилями Word. Набор и имена стилей —
как у «Научной статьи», значения — из образца, а чего в нём нет — от основного текста.

Шрифт, кегль, интервал, отступ и выравнивание основного текста лежат в свойствах
документа по умолчанию, а не в стиле «Normal»: только так текст в таблице берёт свой
кегль из стиля таблицы. Имена стилей — те, по которым их ищет ONLYOFFICE: подпись он
вставляет стилем «Caption», сноску — «footnote text», таблицу — «Table Grid».
"""

from dataclasses import replace

import docx
from docx.document import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.section import Section
from docx.shared import Mm

from .style import Style, Text

# Стили, без которых документ Word не обходится: их оставляем из пустого документа
KEEP = {"Normal", "DefaultParagraphFont", "TableNormal", "NoList"}
TWIPS = 1440 / 25.4  # twips в миллиметре
NO_INDENT = '<w:ind w:left="0" w:firstLine="0"/>'
BORDER = '<w:{side} w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
ALIGNMENT = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
}


def document(style: Style) -> Document:
    """Шаблон: лист, поля, свойства текста по умолчанию, стили, номер страницы."""
    result = docx.Document()
    section = result.sections[0]
    width, height = style.page
    top, right, bottom, left = style.margins
    section.page_width, section.page_height = Mm(width), Mm(height)
    section.top_margin, section.right_margin = Mm(top), Mm(right)
    section.bottom_margin, section.left_margin = Mm(bottom), Mm(left)
    styles = result.styles.element
    for element in styles.findall(qn("w:style")):
        if element.get(qn("w:styleId")) not in KEEP:
            styles.remove(element)
    # «Normal» пустой: основной текст берёт свойства документа по умолчанию
    normal = styles.get_by_id("Normal")
    for properties in normal.findall(qn("w:pPr")) + normal.findall(qn("w:rPr")):
        normal.remove(properties)
    defaults = styles.find(qn("w:docDefaults"))
    defaults.addprevious(parse_xml(_defaults(style.body)))
    styles.remove(defaults)
    for xml in _styles(style, round((width - right - left) * TWIPS)):
        styles.append(parse_xml(xml))
    if style.page_number:
        _page_number(section, *style.page_number)
    return result


def _styles(style: Style, text_width: int) -> list[str]:
    """Стили шаблона: заголовки, содержание, начало статьи, рисунок и подписи, формула,
    сноски, список источников, колонтитулы, таблица."""
    body = style.body
    flat = replace(body, indent=0, line=1, before=0, after=0)
    caption = style.figure or replace(flat, align="center")
    footnote = style.footnote or replace(body, size=max(10, body.size - 4), line=1)
    contents = style.contents or replace(body, indent=0, align="left")
    references = style.references or body
    # Формула: выше и ниже — свободная строка основного текста
    space = round(body.size * body.line * 20)
    return [
        *(
            _heading(level, heading, body, style.numbered)
            for level, heading in enumerate(_levels(style), start=1)
        ),
        # «СОДЕРЖАНИЕ» в само содержание не входит; отточие и номер страницы в
        # строках содержания ставит сам office
        _paragraph(
            "TOCHeading",
            "TOC Heading",
            f'<w:spacing w:after="240"/>{NO_INDENT}<w:jc w:val="center"/>'
            '<w:outlineLvl w:val="9"/>',
            based_on="Heading1",
        ),
        *(
            _paragraph(
                f"TOC{level}",
                f"toc {level}",
                _spacing(contents)
                + f'<w:ind w:left="{(level - 1) * 284}" w:firstLine="0"/>'
                + '<w:jc w:val="left"/>',
                _run(contents, body),
            )
            for level in range(1, 4)
        ),
        # Заготовки начала статьи: УДК, название, авторы, аннотация
        _paragraph("UDC", "УДК", f'<w:spacing w:after="120"/>{NO_INDENT}'),
        _paragraph(
            "Title",
            "Title",
            f'<w:keepNext/><w:spacing w:after="120"/>{NO_INDENT}<w:jc w:val="center"/>',
            "<w:b/><w:bCs/><w:caps/>",
        ),
        _paragraph(
            "Authors",
            "Авторы",
            f'<w:keepNext/><w:spacing w:after="120"/>{NO_INDENT}<w:jc w:val="center"/>',
            "<w:i/><w:iCs/>",
        ),
        _paragraph(
            "Abstract",
            "Аннотация",
            '<w:spacing w:after="120" w:line="240" w:lineRule="auto"/>',
            _size(max(10, body.size - 2)),
        ),
        # Рисунок держится вместе с подписью под ним
        _paragraph(
            "Figure",
            "Рисунок",
            f'<w:keepNext/>{_spacing(flat)}{NO_INDENT}<w:jc w:val="center"/>',
        ),
        _text_style("Caption", "Caption", caption, body),
        # Подпись таблицы — над таблицей и держится вместе с ней
        _text_style(
            "TableCaption",
            "Подпись таблицы",
            style.table or replace(caption, align="left"),
            body,
            keep_next=True,
        ),
        _paragraph(
            "Formula",
            "Формула",
            f'<w:tabs><w:tab w:val="center" w:pos="{text_width // 2}"/>'
            f'<w:tab w:val="right" w:pos="{text_width}"/></w:tabs>'
            f'<w:spacing w:before="{space}" w:after="{space}"/>{NO_INDENT}'
            '<w:jc w:val="left"/>',
        ),
        _text_style("FootnoteText", "footnote text", footnote, body),
        f'<w:style {nsdecls("w")} w:type="character" w:styleId="FootnoteReference">'
        '<w:name w:val="footnote reference"/>'
        '<w:basedOn w:val="DefaultParagraphFont"/>'
        '<w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>',
        # Запись в списке источников: его собирает writer в конце публикации
        _text_style("Bibliography", "Bibliography", references, body),
        _paragraph("Header", "Header", f"{_spacing(flat)}{NO_INDENT}"),
        _paragraph("Footer", "Footer", f"{_spacing(flat)}{NO_INDENT}"),
        _table(flat),
    ]


def _levels(style: Style) -> list[Text]:
    """Заголовки четырёх уровней: раздел, подраздел, пункт, подпункт. Уровни, которых
    нет в образце, — как последний найденный; заголовков нет совсем — полужирный
    основной текст."""
    found = style.headings or [replace(style.body, bold=True)]
    return [found[min(level, len(found) - 1)] for level in range(4)]


def _heading(level: int, text: Text, body: Text, numbered: bool) -> str:
    """Заголовок уровня level. Номер ставит writer, привязывая нумерацию Word к стилям;
    номер списка 0 в стиле раздела отключает её, если в образце номеров нет."""
    off = not numbered and level == 1
    numbering = '<w:numPr><w:numId w:val="0"/></w:numPr>' if off else ""
    return _paragraph(
        f"Heading{level}",
        f"Heading {level}",
        f"<w:keepNext/><w:keepLines/>{numbering}{_spacing(text)}{_indent(text)}"
        f'<w:jc w:val="{text.align}"/><w:outlineLvl w:val="{level - 1}"/>',
        _run(text, body),
    )


def _text_style(
    style_id: str, name: str, text: Text, body: Text, keep_next: bool = False
) -> str:
    """Стиль абзаца с оформлением text."""
    keep = "<w:keepNext/>" if keep_next else ""
    return _paragraph(
        style_id, name, keep + _paragraph_properties(text), _run(text, body)
    )


def _defaults(body: Text) -> str:
    """Свойства текста по умолчанию — основной текст, на русском языке."""
    # Всё оформление шрифта основного текста: и шрифт, и кегль
    marks = _run(body, replace(body, font="", size=0))
    return f"""<w:docDefaults {nsdecls("w")}>
      <w:rPrDefault><w:rPr>{marks}
        <w:lang w:val="ru-RU" w:eastAsia="ru-RU" w:bidi="ar-SA"/>
      </w:rPr></w:rPrDefault>
      <w:pPrDefault><w:pPr>{_paragraph_properties(body)}</w:pPr></w:pPrDefault>
    </w:docDefaults>"""


def _paragraph_properties(text: Text) -> str:
    return f'{_spacing(text)}{_indent(text)}<w:jc w:val="{text.align}"/>'


def _spacing(text: Text) -> str:
    return (
        f'<w:spacing w:before="{round(text.before * 20)}" '
        f'w:after="{round(text.after * 20)}" w:line="{round(text.line * 240)}" '
        'w:lineRule="auto"/>'
    )


def _indent(text: Text) -> str:
    """Отступ первой строки или выступ, как у записи в списке литературы."""
    twips = round(abs(text.indent) * TWIPS)
    if text.indent < 0:
        return f'<w:ind w:left="{twips}" w:hanging="{twips}"/>'
    return f'<w:ind w:left="0" w:firstLine="{twips}"/>'


def _run(text: Text, body: Text) -> str:
    """Свойства шрифта, которыми text отличается от основного текста body."""
    parts = []
    if text.font != body.font:
        parts.append(
            f'<w:rFonts w:ascii="{text.font}" w:hAnsi="{text.font}" '
            f'w:eastAsia="{text.font}" w:cs="{text.font}"/>'
        )
    if text.bold:
        parts.append("<w:b/><w:bCs/>")
    if text.italic:
        parts.append("<w:i/><w:iCs/>")
    if text.caps:
        parts.append("<w:caps/>")
    if text.size != body.size:
        parts.append(_size(text.size))
    return "".join(parts)


def _size(points: float) -> str:
    half = round(points * 2)
    return f'<w:sz w:val="{half}"/><w:szCs w:val="{half}"/>'


def _table(text: Text) -> str:
    """Стиль новой таблицы: сетка 0,5 пт, текст с одинарным интервалом без отступа."""
    borders = "".join(
        BORDER.format(side=side)
        for side in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    return (
        f'<w:style {nsdecls("w")} w:type="table" w:styleId="TableGrid">'
        '<w:name w:val="Table Grid"/><w:basedOn w:val="TableNormal"/>'
        f'<w:pPr>{_spacing(text)}{NO_INDENT}<w:jc w:val="left"/></w:pPr>'
        f"<w:tblPr><w:tblBorders>{borders}</w:tblBorders>"
        '<w:tblCellMar><w:left w:w="57" w:type="dxa"/>'
        '<w:right w:w="57" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>'
    )


def _paragraph(
    style_id: str, name: str, ppr: str, rpr: str = "", based_on: str = "Normal"
) -> str:
    """Стиль абзаца; после него Enter даёт обычный текст."""
    return (
        f'<w:style {nsdecls("w")} w:type="paragraph" w:styleId="{style_id}">'
        f'<w:name w:val="{name}"/><w:basedOn w:val="{based_on}"/>'
        f'<w:next w:val="Normal"/><w:qFormat/>'
        f"<w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>"
    )


def _page_number(section: Section, place: str, align: str) -> None:
    """Номер страницы в колонтитуле, как в образце. Свой колонтитул шаблона writer
    оставляет как есть: номер вверху — значит, внизу свой пустой колонтитул, иначе
    writer поставил бы номер и туда."""
    part = section.header if place == "top" else section.footer
    paragraph = part.paragraphs[0]
    paragraph.alignment = ALIGNMENT[align]
    for content in (
        '<w:fldChar w:fldCharType="begin"/>',
        '<w:instrText xml:space="preserve"> PAGE </w:instrText>',
        '<w:fldChar w:fldCharType="separate"/>',
        '<w:fldChar w:fldCharType="end"/>',
    ):
        paragraph._p.append(parse_xml(f"<w:r {nsdecls('w')}>{content}</w:r>"))
    if place == "top":
        section.footer.is_linked_to_previous = False

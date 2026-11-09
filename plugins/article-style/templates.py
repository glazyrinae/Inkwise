"""Собирает шаблоны оформления плагина в templates/: один файл на требования.

Запуск из корня проекта: uv run python plugins/article-style/templates.py

Требования: российские — научная статья и отчёт по ГОСТ 7.32–2017, западные — APA,
7-е издание. Шаблон — пустой документ со стилями Word. Шрифт, интервал, абзацный
отступ и выравнивание основного текста лежат в свойствах документа по умолчанию, а не в
стиле «Normal». По иерархии стилей Word стиль таблицы сильнее этих свойств, но слабее
стиля абзаца: только так текст в ячейках сам становится 12 пт, с одинарным интервалом и
без отступа.

Имена стилей — те, по которым их ищет ONLYOFFICE: подпись он вставляет стилем «Caption»,
сноску — «footnote text», новую таблицу — «Table Grid». Свои стили названы одинаково во
всех требованиях: смена требований не меняет имена. Шаблон можно поправить и в
редакторе, но этот скрипт перезапишет правку.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import docx
from docx.document import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Mm


@dataclass(frozen=True)
class Russian:
    """Российские требования: поля и кегль подписей."""

    margins: tuple[float, float, float, float]  # мм: верхнее, правое, нижнее, левое
    caption: int  # кегль подписей рисунков и таблиц, пт


# Ключи — как в settings.preset.choices в plugin.json
RUSSIAN = {
    "article": Russian(margins=(20, 20, 20, 20), caption=12),
    "gost-7.32": Russian(margins=(20, 15, 20, 30), caption=14),
}
# APA: поля 1 дюйм со всех сторон
APA_MARGINS = (25.4, 25.4, 25.4, 25.4)

# Стили, без которых документ Word не обходится: их оставляем из пустого документа
KEEP = {"Normal", "DefaultParagraphFont", "TableNormal", "NoList"}
BOLD = "<w:b/><w:bCs/>"
SINGLE = '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
NO_INDENT = '<w:ind w:firstLine="0"/>'
CENTER = f'{NO_INDENT}<w:jc w:val="center"/>'
BORDER = '<w:{side} w:val="single" w:sz="4" w:space="0" w:color="000000"/>'


def russian(preset: Russian) -> Document:
    """Шаблон по российским требованиям: Times New Roman 14 пт, полуторный интервал,
    отступ 1,25 см, по ширине; заголовки с номерами, их ставит writer."""
    return _document(
        preset.margins,
        _defaults(size=14, line=360, indent=709, align="both"),
        lambda width: _russian_styles(preset, width),
    )


def apa() -> Document:
    """Шаблон APA, 7-е издание: Times New Roman 12 пт, двойной интервал, отступ
    1,27 см, по левому краю; заголовки без номеров."""
    return _document(
        APA_MARGINS, _defaults(size=12, line=480, indent=720, align="left"), _apa_styles
    )


def _document(
    margins: tuple[float, float, float, float],
    defaults: str,
    styles_for: Callable[[int], list[str]],
) -> Document:
    """Пустой документ A4 с полями margins, свойствами текста по умолчанию defaults и
    стилями styles_for(ширина текста в twips)."""
    document = docx.Document()
    section = document.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    top, right, bottom, left = (Mm(margin) for margin in margins)
    section.top_margin, section.right_margin = top, right
    section.bottom_margin, section.left_margin = bottom, left
    text_width = Mm(210 - margins[1] - margins[3]).twips

    styles = document.styles.element
    for style in styles.findall(qn("w:style")):
        if style.get(qn("w:styleId")) not in KEEP:
            styles.remove(style)
    # «Normal» пустой: основной текст берёт свойства документа по умолчанию
    normal = styles.get_by_id("Normal")
    for properties in normal.findall(qn("w:pPr")) + normal.findall(qn("w:rPr")):
        normal.remove(properties)
    old_defaults = styles.find(qn("w:docDefaults"))
    old_defaults.addprevious(parse_xml(defaults))
    styles.remove(old_defaults)
    for style in styles_for(text_width):
        styles.append(parse_xml(style))
    return document


def _defaults(size: int, line: int, indent: int, align: str) -> str:
    """Свойства текста по умолчанию: Times New Roman size пт, интервал line (240 —
    одинарный), абзацный отступ indent в twips, выравнивание align."""
    return f"""<w:docDefaults {nsdecls("w")}>
      <w:rPrDefault><w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"
                  w:eastAsia="Times New Roman" w:cs="Times New Roman"/>
        <w:sz w:val="{size * 2}"/><w:szCs w:val="{size * 2}"/>
        <w:lang w:val="ru-RU" w:eastAsia="ru-RU" w:bidi="ar-SA"/>
      </w:rPr></w:rPrDefault>
      <w:pPrDefault><w:pPr>
        <w:spacing w:after="0" w:line="{line}" w:lineRule="auto"/>
        <w:ind w:firstLine="{indent}"/>
        <w:jc w:val="{align}"/>
      </w:pPr></w:pPrDefault>
    </w:docDefaults>"""


def _russian_styles(preset: Russian, text_width: int) -> list[str]:
    """Стили по российским требованиям."""
    caption = (
        f'<w:sz w:val="{preset.caption * 2}"/><w:szCs w:val="{preset.caption * 2}"/>'
    )
    return [
        # Номер и отступ заголовка ставит writer, привязывая нумерацию Word к стилям.
        # Полужирные — только разделы и подразделы (ГОСТ 7.32, 6.1.1), пункты и
        # подпункты обычным шрифтом
        *(
            _paragraph(
                f"Heading{level}",
                f"Heading {level}",
                "<w:keepNext/><w:keepLines/>"
                '<w:spacing w:before="240" w:after="120"/>'
                f'<w:jc w:val="left"/><w:outlineLvl w:val="{level - 1}"/>',
                BOLD if level <= 2 else "",
            )
            for level in range(1, 5)
        ),
        *_contents(),
        # Начало статьи: УДК, название, авторы, аннотация и ключевые слова
        _paragraph(
            "UDC", "УДК", f'<w:spacing w:after="120"/>{NO_INDENT}<w:jc w:val="left"/>'
        ),
        _paragraph(
            "Title",
            "Title",
            f'<w:keepNext/><w:spacing w:after="120"/>{CENTER}',
            f"{BOLD}<w:caps/>",
        ),
        _paragraph(
            "Authors",
            "Авторы",
            f'<w:keepNext/><w:spacing w:after="120"/>{CENTER}',
            "<w:i/><w:iCs/>",
        ),
        _paragraph(
            "Abstract",
            "Аннотация",
            '<w:spacing w:after="120" w:line="240" w:lineRule="auto"/>',
            '<w:sz w:val="24"/><w:szCs w:val="24"/>',
        ),
        # Рисунок держится вместе с подписью под ним
        _paragraph(
            "Figure",
            "Рисунок",
            '<w:keepNext/><w:spacing w:before="120" w:line="240" w:lineRule="auto"/>'
            + CENTER,
        ),
        # «Рисунок 1 — Название»: под рисунком, по центру, без точки в конце
        _paragraph(
            "Caption",
            "Caption",
            f'<w:spacing w:after="120" w:line="240" w:lineRule="auto"/>{CENTER}',
            caption,
        ),
        # «Таблица 1 — Название»: над таблицей, слева без отступа, держится вместе с ней
        _paragraph(
            "TableCaption",
            "Подпись таблицы",
            '<w:keepNext/><w:spacing w:before="120" w:after="0"/><w:jc w:val="left"/>',
            based_on="Caption",
        ),
        # Выше и ниже формулы — не меньше одной свободной строки (ГОСТ 7.32, 6.8.1)
        _formula(text_width, space=480),
        *_footnotes(),
        _paragraph("Header", "Header", SINGLE + CENTER),
        _paragraph("Footer", "Footer", SINGLE + CENTER),
        # Таблица: сетка 0,5 пт
        _table("top", "left", "bottom", "right", "insideH", "insideV"),
    ]


def _apa_styles(text_width: int) -> list[str]:
    """Стили APA, 7-е издание. Интервал везде двойной, отбивок до и после нет."""
    keep = "<w:keepNext/><w:keepLines/>"
    left = f'{NO_INDENT}<w:jc w:val="left"/>'
    return [
        # Заголовки без номеров: номер списка 0 у раздела отключает нумерацию writer.
        # Уровень 1 — по центру, 2 — слева, 3 — слева курсивом, 4 — с отступа
        _paragraph(
            "Heading1",
            "Heading 1",
            f'{keep}<w:numPr><w:numId w:val="0"/>'
            f'</w:numPr>{CENTER}<w:outlineLvl w:val="0"/>',
            BOLD,
        ),
        _paragraph(
            "Heading2", "Heading 2", f'{keep}{left}<w:outlineLvl w:val="1"/>', BOLD
        ),
        _paragraph(
            "Heading3",
            "Heading 3",
            f'{keep}{left}<w:outlineLvl w:val="2"/>',
            f"{BOLD}<w:i/><w:iCs/>",
        ),
        _paragraph(
            "Heading4",
            "Heading 4",
            f'{keep}<w:jc w:val="left"/><w:outlineLvl w:val="3"/>',
            BOLD,
        ),
        *_contents(),
        # Титульная страница: название полужирным по центру, под ним авторы
        _paragraph("Title", "Title", f"<w:keepNext/>{CENTER}", BOLD),
        _paragraph("Authors", "Авторы", CENTER),
        # Аннотация — один абзац без отступа; заголовок «Abstract» — уровня 1
        _paragraph("Abstract", "Аннотация", NO_INDENT),
        _paragraph("Figure", "Рисунок", SINGLE + CENTER),
        # «Figure 1» и «Table 1» — полужирным слева над рисунком или таблицей,
        # название — следующей строкой курсивом
        _paragraph("Caption", "Caption", f"<w:keepNext/>{left}", BOLD),
        _paragraph("TableCaption", "Подпись таблицы", "", based_on="Caption"),
        _formula(text_width, space=0),
        *_footnotes(),
        # Номер страницы по APA — вверху справа
        _paragraph("Header", "Header", f'{SINGLE}{NO_INDENT}<w:jc w:val="right"/>'),
        _paragraph("Footer", "Footer", SINGLE + CENTER),
        # Таблица без вертикальных линий: линии над таблицей, под шапкой и под таблицей
        _table(
            "top",
            "bottom",
            first_row=f"<w:tcBorders>{BORDER.format(side='bottom')}</w:tcBorders>",
        ),
    ]


def _contents() -> list[str]:
    """Заголовок «СОДЕРЖАНИЕ» — в само содержание не входит — и строки содержания:
    отточие и номер страницы в них ставит сам office."""
    return [
        _paragraph(
            "TOCHeading",
            "TOC Heading",
            f'<w:spacing w:after="240"/>{CENTER}<w:outlineLvl w:val="9"/>',
            based_on="Heading1",
        ),
        *(
            _paragraph(
                f"TOC{level}",
                f"toc {level}",
                f'<w:ind w:left="{(level - 1) * 284}" w:firstLine="0"/>'
                '<w:jc w:val="left"/>',
            )
            for level in range(1, 4)
        ),
    ]


def _formula(text_width: int, space: int) -> str:
    """Формула по центру, её номер «(1)» у правого поля: Tab, формула, Tab, номер;
    space — отбивка сверху и снизу, twips."""
    return _paragraph(
        "Formula",
        "Формула",
        f'<w:tabs><w:tab w:val="center" w:pos="{text_width // 2}"/>'
        f'<w:tab w:val="right" w:pos="{text_width}"/></w:tabs>'
        f'<w:spacing w:before="{space}" w:after="{space}"/>{NO_INDENT}'
        '<w:jc w:val="left"/>',
    )


def _footnotes() -> list[str]:
    """Сноска: 10 пт, одинарный интервал, с абзацного отступа — и по ГОСТ 7.32 (6.7.4),
    и по APA; знак сноски — надстрочный."""
    return [
        _paragraph(
            "FootnoteText",
            "footnote text",
            SINGLE,
            '<w:sz w:val="20"/><w:szCs w:val="20"/>',
        ),
        f'<w:style {nsdecls("w")} w:type="character" w:styleId="FootnoteReference">'
        '<w:name w:val="footnote reference"/>'
        '<w:basedOn w:val="DefaultParagraphFont"/>'
        '<w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>',
    ]


def _table(*sides: str, first_row: str = "") -> str:
    """Стиль новой таблицы: линии 0,5 пт по сторонам sides, текст 12 пт с одинарным
    интервалом и без отступа; first_row — свойства ячеек шапки."""
    borders = "".join(BORDER.format(side=side) for side in sides)
    head = (
        f'<w:tblStylePr w:type="firstRow"><w:tcPr>{first_row}</w:tcPr></w:tblStylePr>'
        if first_row
        else ""
    )
    return (
        f'<w:style {nsdecls("w")} w:type="table" w:styleId="TableGrid">'
        '<w:name w:val="Table Grid"/><w:basedOn w:val="TableNormal"/>'
        f'<w:pPr>{SINGLE}{NO_INDENT}<w:jc w:val="left"/></w:pPr>'
        '<w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
        f"<w:tblPr><w:tblBorders>{borders}</w:tblBorders>"
        '<w:tblCellMar><w:left w:w="57" w:type="dxa"/>'
        f'<w:right w:w="57" w:type="dxa"/></w:tblCellMar></w:tblPr>{head}</w:style>'
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


if __name__ == "__main__":
    folder = Path(__file__).with_name("templates")
    folder.mkdir(exist_ok=True)
    templates = {key: russian(preset) for key, preset in RUSSIAN.items()}
    templates["apa-7"] = apa()
    for key, template in templates.items():
        template.save(str(folder / f"{key}.docx"))

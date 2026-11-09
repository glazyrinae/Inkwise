"""Оформление образца в документе Word. Свойства складываем, как сам Word: свойства
документа по умолчанию, стиль со стилями, на которых он основан, свойства в абзаце и в
куске текста. Так видно и оформление стилями, и набранное прямо в тексте.

Основной текст — оформление, которым набрано больше всего знаков. Заголовки — по стилю
«Heading N» или по уровню структуры. Подписи, содержание и список источников — по
стилю или по словам, как в PDF.
"""

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import docx
from docx.document import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement
from docx.shared import Length

from .pdf import FIGURE, NUMBER, REFERENCES, SINGLE, TABLE
from .style import Style, Text, interval, sheet

MM = 25.4 / 1440  # миллиметров в twip
ALIGN = {"both": "both", "distribute": "both", "center": "center", "right": "right"}
ALIGN |= {"end": "right", "left": "left", "start": "left"}
# Свойства по умолчанию самого Word, если документ их не задал. Шрифт без имени Word
# и office показывают как Times New Roman, office и не пишет его в файл
WORD = {"font": "Times New Roman", "size": 10.0, "bold": False, "italic": False}
WORD |= {"caps": False}
WORD |= {"align": "left", "indent": 0.0, "line": (240, "auto"), "before": 0.0}
WORD |= {"after": 0.0}

Properties = dict[str, Any]


def read(path: Path) -> Style:
    """Оформление образца в документе Word.

    Raises:
        ValueError: это не документ Word .docx или в нём нет основного текста.
    """
    try:
        document = docx.Document(str(path))
    except (PackageNotFoundError, KeyError, ValueError):
        raise ValueError("Файл не открылся как документ Word .docx") from None
    styles = _Styles(document)
    # Оформление по видам абзацев; вес — число знаков, как в PDF
    kinds: dict[str, Counter[Text]] = defaultdict(Counter)
    numbered = inside_references = False
    for element, text in _paragraphs(document.element.body):
        kind = styles.kind(element, text)
        look = styles.text(element)
        if kind.startswith("heading "):
            # Заголовок без номера среди нумерованных — «ВВЕДЕНИЕ»: он оформлен иначе
            with_number = styles.numbered(element) or bool(NUMBER.match(text))
            numbered = numbered or with_number
            kind += "" if with_number else " без номера"
            inside_references = bool(REFERENCES.fullmatch(text.strip(" .:")))
        elif inside_references:
            kind = "references"
        elif REFERENCES.fullmatch(text.strip(" .:")):
            inside_references = True
            continue
        kinds[kind][look] += len(text)
    for look in _footnotes(document, styles):
        kinds["footnote"][look] += 1
    body = _common(kinds["body"])
    if body is None:
        raise ValueError("В документе Word не нашлось основного текста")
    notes = []
    sections = document.sections
    if any(section._sectPr.xpath("w:cols[@w:num > 1]") for section in sections):
        notes.append("Образец набран в колонки, шаблон — в одну")
    section = sections[0]
    # Без размеров в документе Word берёт A4 и поля 2 см
    page = (_mm(section.page_width, 210), _mm(section.page_height, 297))
    margins = (
        _mm(section.top_margin, 20),
        _mm(section.right_margin, 20),
        _mm(section.bottom_margin, 20),
        _mm(section.left_margin, 20),
    )
    headings = [
        _common(kinds[f"heading {level}"])
        or _common(kinds[f"heading {level} без номера"])
        for level in range(1, 5)
    ]
    return Style(
        page=sheet(*page),
        margins=margins,
        body=body,
        headings=[heading for heading in headings if heading],
        numbered=numbered,
        figure=_common(kinds["figure"]),
        table=_common(kinds["table"]),
        footnote=_common(kinds["footnote"]),
        page_number=_page_number(document, styles),
        contents=_common(kinds["contents"]),
        references=_common(kinds["references"]),
        notes=notes,
    )


class _Styles:
    """Свойства абзаца и текста, как их складывает Word."""

    def __init__(self, document: Document) -> None:
        root = document.styles.element
        self.by_id = {
            style.get(qn("w:styleId")): style for style in root.findall(qn("w:style"))
        }
        self.theme = _theme(document)
        self.defaults: Properties = dict(WORD)
        defaults = root.find(qn("w:docDefaults"))
        if defaults is not None:
            paragraph = defaults.find(f"{qn('w:pPrDefault')}/{qn('w:pPr')}")
            run = defaults.find(f"{qn('w:rPrDefault')}/{qn('w:rPr')}")
            self.defaults |= _paragraph(paragraph) | self._run(run)
        # Стиль абзаца по умолчанию — тот, что у абзаца без стиля, обычно «Normal»
        self.normal = "Normal"
        for style_id, style in self.by_id.items():
            paragraph = style.get(qn("w:type")) == "paragraph"
            if paragraph and style.get(qn("w:default")) in ("1", "true"):
                self.normal = style_id

    def paragraph(self, element: BaseOxmlElement) -> Properties:
        """Свойства абзаца с его стилем; name — имя стиля строчными."""
        own = element.find(qn("w:pPr"))
        style = own.find(qn("w:pStyle")) if own is not None else None
        style_id = style.get(qn("w:val")) if style is not None else self.normal
        found = dict(self.defaults)
        for parent in self._chain(style_id):
            found |= _paragraph(parent.find(qn("w:pPr")))
            found |= self._run(parent.find(qn("w:rPr")))
        found |= _paragraph(own)
        found["name"] = self._name(style_id)
        return found

    def text(self, element: BaseOxmlElement) -> Text:
        """Оформление абзаца: свойства абзаца и самого длинного куска текста в нём."""
        found = self.paragraph(element)
        runs = [run for run in element.iter(qn("w:r")) if _run_text(run).strip()]
        if runs:
            longest = max(runs, key=lambda run: len(_run_text(run)))
            properties = longest.find(qn("w:rPr"))
            style = properties.find(qn("w:rStyle")) if properties is not None else None
            if style is not None:
                for parent in self._chain(style.get(qn("w:val"))):
                    found |= self._run(parent.find(qn("w:rPr")))
            found |= self._run(properties)
        return _text(found)

    def kind(self, element: BaseOxmlElement, text: str) -> str:
        """Что это за абзац: body, heading N, figure, table, contents, title."""
        found = self.paragraph(element)
        name = found["name"]
        if name.startswith("heading ") and name[8:].isdigit():
            return f"heading {name[8:]}"
        if "outline" in found and found["outline"] < 9:
            return f"heading {found['outline'] + 1}"
        if name.startswith("toc "):
            return "contents"
        if TABLE.match(text):
            return "table"
        if name == "caption" or FIGURE.match(text):
            return "figure"
        if name in ("title", "subtitle", "toc heading"):
            return "title"
        return "body"

    def numbered(self, element: BaseOxmlElement) -> bool:
        """У абзаца номер списка Word — в стиле или в нём самом."""
        return bool(self.paragraph(element).get("numbered"))

    def _name(self, style_id: str) -> str:
        """Имя стиля строчными, как его пишет Word: «heading 1»."""
        style = self.by_id.get(style_id)
        name = style.find(qn("w:name")) if style is not None else None
        return name.get(qn("w:val"), "").lower() if name is not None else ""

    def _chain(self, style_id: str | None) -> list[BaseOxmlElement]:
        """Стиль и стили, на которых он основан, от самого общего."""
        chain: list[BaseOxmlElement] = []
        while style_id and style_id in self.by_id and len(chain) < 20:
            style = self.by_id[style_id]
            chain.append(style)
            based = style.find(qn("w:basedOn"))
            style_id = based.get(qn("w:val")) if based is not None else None
        return chain[::-1]

    def _run(self, element: BaseOxmlElement | None) -> Properties:
        """Свойства текста из w:rPr: шрифт, кегль, начертание."""
        found: Properties = {}
        if element is None:
            return found
        fonts = element.find(qn("w:rFonts"))
        if fonts is not None:
            # Шрифт темы сильнее названного: так решает Word
            theme = fonts.get(qn("w:asciiTheme")) or fonts.get(qn("w:hAnsiTheme"))
            name = fonts.get(qn("w:ascii")) or fonts.get(qn("w:hAnsi"))
            if theme:
                found["font"] = self.theme[
                    "major" if theme.startswith("major") else "minor"
                ]
            elif name:
                found["font"] = name
        size = element.find(qn("w:sz"))
        if size is not None:
            found["size"] = int(size.get(qn("w:val"))) / 2
        for tag, key in (("w:b", "bold"), ("w:i", "italic"), ("w:caps", "caps")):
            mark = element.find(qn(tag))
            if mark is not None:
                found[key] = mark.get(qn("w:val"), "true") not in ("0", "false", "off")
        return found


def _paragraph(element: BaseOxmlElement | None) -> Properties:
    """Свойства абзаца из w:pPr: интервалы, отступ, выравнивание, уровень, номер."""
    found: Properties = {}
    if element is None:
        return found
    spacing = element.find(qn("w:spacing"))
    if spacing is not None:
        line = spacing.get(qn("w:line"))
        if line:
            found["line"] = (int(line), spacing.get(qn("w:lineRule"), "auto"))
        for side in ("before", "after"):
            value = spacing.get(qn(f"w:{side}"))
            if value is not None:
                found[side] = int(value) / 20
    indent = element.find(qn("w:ind"))
    if indent is not None:
        hanging = indent.get(qn("w:hanging"))
        first = indent.get(qn("w:firstLine"))
        if hanging is not None:
            found["indent"] = -int(hanging) * MM
        elif first is not None:
            found["indent"] = int(first) * MM
    align = element.find(qn("w:jc"))
    if align is not None:
        found["align"] = ALIGN.get(align.get(qn("w:val")), "left")
    outline = element.find(qn("w:outlineLvl"))
    if outline is not None:
        found["outline"] = int(outline.get(qn("w:val")))
    number = element.find(f"{qn('w:numPr')}/{qn('w:numId')}")
    if number is not None:
        found["numbered"] = number.get(qn("w:val")) != "0"
    return found


def _text(found: Properties) -> Text:
    line, rule = found["line"]
    size = found["size"]
    # Точный интервал — в twips, «множитель» — в 240-х долях одинарного
    ratio = line / 240 if rule == "auto" else line / 20 / (SINGLE * size)
    return Text(
        font=found["font"],
        size=size,
        bold=found["bold"],
        italic=found["italic"],
        caps=found["caps"],
        align=found["align"],
        indent=round(found["indent"], 1),
        line=interval(ratio),
        before=round(found["before"]),
        after=round(found["after"]),
    )


def _paragraphs(root: BaseOxmlElement) -> list[tuple[BaseOxmlElement, str]]:
    """Абзацы с текстом по порядку, кроме абзацев в таблицах."""
    found = []
    for element in root.iter(qn("w:p")):
        if any(parent.tag == qn("w:tbl") for parent in element.iterancestors()):
            continue
        text = "".join(_run_text(run) for run in element.iter(qn("w:r"))).strip()
        if text:
            found.append((element, text))
    return found


def _footnotes(document: Document, styles: _Styles) -> list[Text]:
    """Оформление абзацев в сносках."""
    try:
        part = document.part.part_related_by(RT.FOOTNOTES)
    except KeyError:
        return []
    root = parse_xml(part.blob)
    notes = [
        note
        for note in root.findall(qn("w:footnote"))
        if int(note.get(qn("w:id"), "0")) > 0
    ]
    return [styles.text(element) for note in notes for element, _ in _paragraphs(note)]


def _page_number(document: Document, styles: _Styles) -> tuple[str, str] | None:
    """Где номер страницы: колонтитул с полем PAGE и его выравнивание."""
    section = document.sections[0]
    for place, part in (("top", section.header), ("bottom", section.footer)):
        if part.is_linked_to_previous:
            continue
        for element in part._element.iter(qn("w:p")):
            codes = [code.text or "" for code in element.iter(qn("w:instrText"))]
            fields = element.iter(qn("w:fldSimple"))
            codes += [field.get(qn("w:instr"), "") for field in fields]
            if any("PAGE" in code.upper() for code in codes):
                return place, styles.text(element).align.replace("both", "left")
    return None


def _common(texts: Counter[Text]) -> Text | None:
    """Самое частое оформление; None — таких абзацев нет."""
    return texts.most_common(1)[0][0] if texts else None


def _mm(length: Length | None, default: float) -> float:
    """Размер в миллиметрах с точностью до десятой; не задан — default."""
    return round(length.mm, 1) if length is not None else default


def _theme(document: Document) -> dict[str, str]:
    """Шрифты темы документа: основной (minor) и для заголовков (major)."""
    fonts = {"minor": "", "major": ""}
    try:
        part = document.part.part_related_by(RT.THEME)
    except KeyError:
        return fonts
    root = parse_xml(part.blob)
    drawing = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    for kind in fonts:
        latin = root.find(f".//{drawing}{kind}Font/{drawing}latin")
        if latin is not None:
            fonts[kind] = latin.get("typeface", "")
    return fonts


def _run_text(run: BaseOxmlElement) -> str:
    return "".join(text.text or "" for text in run.iter(qn("w:t")))

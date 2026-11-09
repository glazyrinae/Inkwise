"""Оформление образца в PDF. Стилей в PDF нет, есть строки текста на страницах: шрифт,
кегль, жирность и где строка стоит. Оформление угадываем по ним.

Основной текст — шрифт и кегль, которыми набрано больше всего знаков. Левое поле —
самое левое частое начало его строк, абзацный отступ — следующее за ним, правое поле —
где кончаются строки внутри абзацев, интервал — шаг между строками. Заголовки — строки
крупнее, жирнее или прописными либо с номером «1.1»; уровень — по номеру, а без номеров
— по размеру. Подписи, содержание и список источников узнаём по словам: «Рисунок 1»,
«СОДЕРЖАНИЕ», «СПИСОК ЛИТЕРАТУРЫ».

Высоту считаем по базовым линиям строк: рамку строки PDF разных программ рисуют
по-разному. Первая строка на странице стоит базовой линией на высоте букв ниже верхнего
поля: добавку межстрочного интервала и Word, и LibreOffice дают под строкой.
"""

import itertools
import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pymupdf

from .style import Style, Text, interval, sheet

# Оформление видно по первым страницам, а большой PDF читался бы долго
PAGES = 40
MM = 25.4 / 72  # миллиметров в пункте
# Одинарный интервал Word — около 1,15 кегля, высота букв над базовой линией — около
# 0,9 кегля: так у Times New Roman и Arial
SINGLE = 1.15
ASCENT = 0.9
# Шрифты с теми же размерами букв. LibreOffice и программы без шрифтов Microsoft
# ставят их вместо оригинала, а автор набирал оригиналом
ORIGINALS = {
    "Liberation Serif": "Times New Roman",
    "Liberation Sans": "Arial",
    "Liberation Mono": "Courier New",
    "Tinos": "Times New Roman",
    "Arimo": "Arial",
    "Cousine": "Courier New",
    "Carlito": "Calibri",
    "Caladea": "Cambria",
}
FIGURE = re.compile(r"(рисунок|рис\.|figure|fig\.)\s*[\dА-ЯA-Z]", re.IGNORECASE)
TABLE = re.compile(r"(таблица|табл\.|table)\s*[\dА-ЯA-Z]", re.IGNORECASE)
# Номер заголовка: «1», «1.2», «1.2.3.» — не год и не число из текста
NUMBER = re.compile(r"(\d{1,2}(?:\.\d{1,2})*)\.?\s+[^\d\s]")
CONTENTS = re.compile(r"содержание|оглавление|(table of )?contents", re.IGNORECASE)
REFERENCES = re.compile(
    r"список\s+(использованных\s+|использованной\s+)?(источников|литературы)"
    r"|литература|библиографический\s+список|references|bibliography",
    re.IGNORECASE,
)
# Начало записи в списке источников: «1. », «[1] »
ENTRY = re.compile(r"\[?\d{1,3}[\].)]\s")
PAGE_NUMBER = re.compile(r"\d{1,4}")

# Вид строки: шрифт, кегль, полужирный, курсив
Look = tuple[str, float, bool, bool]
# Вид заголовка: вид строки, прописными ли, выравнивание, отступ, глубина номера
Kind = tuple[Look, bool, str, float, int]


@dataclass(frozen=True)
class Line:
    """Строка на странице: шрифт, кегль и начертание — самого длинного куска в ней."""

    page: int
    text: str
    font: str
    size: float
    bold: bool
    italic: bool
    x0: float
    x1: float
    baseline: float

    @property
    def look(self) -> Look:
        """Вид строки: шрифт, кегль, начертание."""
        return self.font, self.size, self.bold, self.italic


def read(path: Path) -> Style:
    """Оформление образца в PDF.

    Raises:
        ValueError: это не PDF или в нём почти нет текста — например, скан.
    """
    try:
        pdf = pymupdf.open(path)
    except pymupdf.FileDataError:
        raise ValueError("Файл не открылся как PDF") from None
    with pdf:
        width, height = pdf[0].rect.width, pdf[0].rect.height
        lines, replaced = _lines(pdf)
        notes = [f"Прочитаны первые {PAGES} страниц"] if pdf.page_count > PAGES else []
    for font in sorted(replaced):
        notes.append(f"{font} в PDF — замена {ORIGINALS[font]}, в шаблоне оригинал")
    if len(lines) < 20:
        raise ValueError(
            "В PDF почти нет текста — это скан или картинки? Нужен PDF с текстом или "
            "документ Word"
        )
    return _Sample(lines, width, height).style(notes)


class _Sample:
    """Строки образца и то, что видно по основному тексту: поля, интервал, отступ."""

    def __init__(self, lines: list[Line], width: float, height: float) -> None:
        self.width, self.height = width, height
        # Колонтитулы — номер страницы и строки, повторённые на одном месте у края
        # листа, — не текст
        edge = [line for line in lines if not 0.07 < line.baseline / height < 0.93]
        repeated = Counter((line.text, round(line.baseline)) for line in edge)
        self.furniture = [
            line
            for line in lines
            if PAGE_NUMBER.fullmatch(line.text)
            or (line in edge and repeated[(line.text, round(line.baseline))] >= 3)
        ]
        self.lines = [line for line in lines if line not in self.furniture]
        self.pages: dict[int, list[Line]] = defaultdict(list)
        for line in sorted(self.lines, key=lambda line: (line.page, line.baseline)):
            self.pages[line.page].append(line)
        signs = Counter[Look]()
        for line in self.lines:
            signs[line.look] += len(line.text)
        self.look = signs.most_common(1)[0][0]
        self.font, self.size, self.bold, self.italic = self.look
        self.body = [line for line in self.lines if line.look == self.look]
        self.left, self.indent = self._starts()
        self.step = _median(self._steps(self.body), self.size * SINGLE)
        inner = self._inner()
        ends = [line.x1 for line in inner or self.body]
        at_edge = sum(end > _quantile(ends, 0.9) - 3 for end in ends)
        self.justified = bool(inner) and at_edge >= 0.6 * len(ends)
        # Текст слева до правого поля не доходит: поле — по самым длинным строкам
        self.right = _quantile(ends, 0.9 if self.justified else 0.98)
        # Поля по страницам, которые абзац продолжает со страницы перед ней: она
        # заполнена до низа, а эта начинается без отбивки, которая бывает у заголовка
        continued = {
            number
            for number, page in self.pages.items()
            if page[0].look == self.look and abs(page[0].x0 - self.left) < 3
        }
        firsts = [self.pages[number][0].baseline for number in continued]
        anyway = [page[0].baseline for page in self.pages.values()]
        self.top = _median(firsts or anyway, 0) - ASCENT * self.size
        lasts = [
            page[-1].baseline
            for number, page in self.pages.items()
            if number + 1 in continued and page[-1].look == self.look
        ]
        # Строка занимает шаг: от верха букв вниз, добавка интервала — под буквами.
        # Полной страницы нет — низ поля не виден
        self.bottom = max(lasts) - ASCENT * self.size + self.step if lasts else 0.0

    def style(self, notes: list[str]) -> Style:
        """Оформление образца целиком."""
        top = _margin(self.top)
        bottom = _margin(self.height - self.bottom) if self.bottom else top
        if not self.bottom:
            notes.append("Нижнее поле по образцу не видно — взято, как верхнее")
        # Нижнее поле видно с точностью до строки: последняя строка страницы стоит не
        # вплотную к нему, а то и строкой выше — так переносят абзацы. Чаще всего оно
        # равно верхнему
        if top - 2 <= bottom <= top + 1.5 * self.step * MM:
            bottom = top
        headings, numbered = self._headings()
        if sum(line.x0 > self.width / 2 for line in self.body) > 0.25 * len(self.body):
            notes.append("Образец набран в две колонки, шаблон — в одну")
        if re.search(r"OCR|GlyphLess", self.font):
            notes.append(
                "Текст в PDF — распознанный скан: шрифт и размеры, наверное, неверны"
            )
        return Style(
            page=sheet(self.width * MM, self.height * MM),
            margins=(top, _margin(self.width - self.right), bottom, _margin(self.left)),
            body=Text(
                font=self.font,
                size=self.size,
                bold=self.bold,
                italic=self.italic,
                align="both" if self.justified else "left",
                indent=_millimeters(self.indent),
                line=self._interval(self.step, self.size),
                after=self._paragraph_spacing(),
            ),
            headings=headings,
            numbered=numbered,
            figure=self._caption(FIGURE),
            table=self._caption(TABLE),
            footnote=self._footnote(),
            page_number=self._page_number(),
            contents=self._contents(),
            references=self._references(),
            notes=notes,
        )

    def _starts(self) -> tuple[float, float]:
        """Левое поле и абзацный отступ, пт. Поле — самое левое из частых начал строк
        основного текста, отступ — самое частое начало правее поля."""
        starts = Counter(_even(line.x0) for line in self.body)
        enough = max(3, 0.05 * len(self.body))
        frequent = [start for start, count in starts.items() if count >= enough]
        left = min(frequent) if frequent else starts.most_common(1)[0][0]
        indents = [
            (count, start)
            for start, count in starts.items()
            if 3 < start - left < 60 and count >= enough
        ]
        indent = max(indents)[1] if indents else left
        # Точное место — по строкам, а не по округлённому до 2 пт
        exact = {
            place: _median(
                [line.x0 for line in self.body if _even(line.x0) == place], place
            )
            for place in (left, indent)
        }
        return exact[left], exact[indent] - exact[left]

    def _inner(self) -> list[Line]:
        """Строки основного текста внутри абзацев: за ними на странице идёт строка
        того же абзаца, от левого поля. Если текст по ширине, они кончаются у правого
        поля."""
        found = []
        for page in self.pages.values():
            for line, after in itertools.pairwise(page):
                same = line.look == after.look == self.look
                if same and abs(after.x0 - self.left) < 3:
                    found.append(line)
        return found

    def _headings(self) -> tuple[list[Text], bool]:
        """Заголовки по уровням и есть ли у них номера.

        Уровень — по номеру «1.2»; заголовки без номеров, как «ВВЕДЕНИЕ», тогда не в
        счёт. Номеров нет совсем — уровни по размеру: крупнее, жирнее, прописными —
        выше. Вид, который встретился один раз, — не заголовок, а, например, название
        на титульном листе.
        """
        groups: dict[Kind, list[Line]] = defaultdict(list)
        for line in self._heading_lines():
            number = NUMBER.match(line.text)
            depth = len(number[1].split(".")) if number else 0
            align, indent = self._align(line)
            groups[(line.look, _caps(line.text), align, indent, depth)].append(line)
        groups = {kind: group for kind, group in groups.items() if len(group) >= 2}
        levels: dict[int, Kind] = {}
        for kind, group in groups.items():
            depth = kind[4]
            rival = levels.get(depth)
            if 0 < depth <= 4 and (rival is None or len(group) > len(groups[rival])):
                levels[depth] = kind
        if levels:
            ordered = [levels[depth] for depth in sorted(levels)]
        else:
            ordered = sorted(groups, key=_prominence)[:4]
        texts = [self._text(groups[kind], kind[2], kind[3]) for kind in ordered]
        return texts, bool(levels)

    def _heading_lines(self) -> list[Line]:
        """Строки, похожие на заголовок: крупнее, жирнее, прописными или короткие с
        номером «1.1», не в строке таблицы. Заголовок в две строки — одна строка."""
        found: list[Line] = []
        for line in self.lines:
            number = NUMBER.match(line.text)
            stronger = line.look != self.look and (
                line.size > self.size + 0.4
                or (line.bold and not self.bold)
                or _caps(line.text)
            )
            # Пункт «1.1.1» бывает набран как основной текст: его видно по номеру
            short = line.x1 < self.right - 0.2 * (self.right - self.left)
            numbered = number is not None and "." in number[1] and short
            heading = (
                (stronger or numbered)
                and line.size >= self.size - 0.5
                and len(line.text) <= 150
                and any(char.isalpha() for char in line.text)
                and not FIGURE.match(line.text)
                and not TABLE.match(line.text)
                and not self._in_row(line)
            )
            previous = found[-1] if found else None
            continued = (
                previous is not None
                and previous.page == line.page
                and previous.look == line.look
                and 0 < line.baseline - previous.baseline <= 1.2 * self.step
            )
            if heading and not continued:
                found.append(line)
        return found

    def _caption(self, pattern: re.Pattern[str]) -> Text | None:
        """Подпись рисунка или таблицы: строки, которые начинаются с «Рисунок 1»."""
        found = [
            line
            for line in self.lines
            if pattern.match(line.text) and line.size <= self.size + 0.5
        ]
        if not found:
            return None
        places = Counter(self._align(line) for line in found)
        align, indent = places.most_common(1)[0][0]
        return self._text(found, align, indent)

    def _footnote(self) -> Text | None:
        """Сноски: мелкие строки под основным текстом страницы."""
        found = []
        for lines in self.pages.values():
            ends = [line.baseline for line in lines if line.look == self.look]
            below = [
                line
                for line in lines
                if line.baseline > max(ends, default=0) and line.size < self.size - 0.4
            ]
            # Сноска начинается с номера: мелкий текст без номеров — не сноски
            if any(line.text[:1].isdigit() for line in below):
                found += below
        if len(found) < 2:
            return None
        starts = [line.x0 - self.left for line in found if line.text[:1].isdigit()]
        align = "both" if self.justified else "left"
        text = self._text(found, align, _median(starts, 0))
        step = _median(self._steps(found), 0)
        return replace(text, line=self._interval(step, text.size))

    def _page_number(self) -> tuple[str, str] | None:
        """Номер страницы: число одно в строке выше или ниже поля текста."""
        found = Counter[tuple[str, str]]()
        middle = (self.left + self.right) / 2
        for line in self.furniture:
            if not PAGE_NUMBER.fullmatch(line.text):
                continue
            if line.baseline < self.top:
                place = "top"
            elif line.baseline > (self.bottom or self.height / 2):
                place = "bottom"
            else:
                continue
            if abs((line.x0 + line.x1) / 2 - middle) < 15:
                found[(place, "center")] += 1
            elif line.x1 > self.right - 15:
                found[(place, "right")] += 1
            elif line.x0 < self.left + 15:
                found[(place, "left")] += 1
        if not found:
            return None
        position, count = found.most_common(1)[0]
        return position if count >= 2 else None

    def _contents(self) -> Text | None:
        """Строки содержания: под словом «СОДЕРЖАНИЕ», с номером страницы в конце."""
        title = self._title(CONTENTS)
        if title is None:
            return None
        found = [
            line
            for line in self.pages[title.page]
            if line.baseline > title.baseline
            and line.size <= self.size + 0.5
            and (re.search(r"\d\s*$", line.text) or "...." in line.text)
        ]
        return self._text(found, "left", 0) if len(found) >= 3 else None

    def _references(self) -> Text | None:
        """Запись в списке источников: строки под его заголовком до следующего
        заголовка. Отступ — насколько первая строка записи с номером правее остальных
        строк; меньше нуля — левее, это выступ."""
        title = self._title(REFERENCES)
        if title is None:
            return None
        headings = set(self._heading_lines())
        found = []
        for line in itertools.chain.from_iterable(self.pages.values()):
            if (line.page, line.baseline) <= (title.page, title.baseline):
                continue
            if line in headings:
                break
            found.append(line)
        if len(found) < 3:
            return None
        indent = self._entry_indent(found)
        at_edge = sum(line.x1 > self.right - 3 for line in found)
        align = "both" if at_edge >= 0.4 * len(found) else "left"
        return self._text(found, align, indent)

    def _entry_indent(self, lines: list[Line]) -> float:
        """Отступ записи в списке источников, пт: строки начинаются в двух местах, и
        начало записи там, где строки чаще начинаются с номера или заглавной буквы.
        Записи в одну строку — отступ от левого поля."""
        places = [
            place
            for place, _ in Counter(_even(line.x0) for line in lines).most_common(2)
        ]

        def starts(place: float) -> float:
            here = [line for line in lines if _even(line.x0) == place]
            first = [
                line
                for line in here
                if ENTRY.match(line.text) or line.text[:1].isupper()
            ]
            return len(first) / len(here)

        def exact(place: float) -> float:
            return _median(
                [line.x0 for line in lines if _even(line.x0) == place], place
            )

        if len(places) == 1:
            shift = exact(places[0]) - self.left
            return shift if shift > 3 else 0.0
        first, other = sorted(places, key=starts, reverse=True)
        return exact(first) - exact(other)

    def _text(self, lines: list[Line], align: str, indent: float) -> Text:
        """Оформление строк lines: самое частое начертание, отбивки над и под ними."""
        looks = Counter(line.look for line in lines)
        font, size, bold, italic = looks.most_common(1)[0][0]
        caps = sum(_caps(line.text) for line in lines) > len(lines) / 2
        before, after = [], []
        for line in lines:
            page = self.pages[line.page]
            index = page.index(line)
            if index > 0:
                before.append(line.baseline - page[index - 1].baseline - self.step)
            if index + 1 < len(page):
                after.append(page[index + 1].baseline - line.baseline - self.step)
        return Text(
            font=font,
            size=size,
            bold=bold,
            italic=italic,
            caps=caps,
            align=align,
            indent=_millimeters(indent),
            line=self._interval(self.step, self.size),
            before=_spacing(before),
            after=_spacing(after),
        )

    def _align(self, line: Line) -> tuple[str, float]:
        """Выравнивание строки и её отступ, пт: по центру, с абзацного отступа или
        слева."""
        middle = (self.left + self.right) / 2
        if abs((line.x0 + line.x1) / 2 - middle) < 6 and line.x0 > self.left + 6:
            return "center", 0.0
        if self.indent and abs(line.x0 - self.left - self.indent) < 4:
            return "left", self.indent
        return "left", 0.0

    def _in_row(self, line: Line) -> bool:
        """Строка в ряду с другими на той же высоте — ячейка таблицы, а не заголовок."""
        return any(
            other is not line
            and abs(other.baseline - line.baseline) < 2
            and (other.x1 < line.x0 or other.x0 > line.x1)
            for other in self.pages[line.page]
        )

    def _title(self, pattern: re.Pattern[str]) -> Line | None:
        """Строка-заголовок вроде «СОДЕРЖАНИЕ»: только эти слова в строке."""
        for line in self.lines:
            if pattern.fullmatch(line.text.strip(" .:")):
                return line
        return None

    def _paragraph_spacing(self) -> float:
        """Отбивка после абзаца основного текста, пт: на сколько промежуток перед
        абзацем больше шага строк. Абзац начинается с отступа, а без отступа его видно
        только по этому промежутку."""
        gaps, starts = [], []
        for page in self.pages.values():
            for previous, line in itertools.pairwise(page):
                if previous.look == self.look == line.look:
                    gap = line.baseline - previous.baseline - self.step
                    gaps.append(gap)
                    if self.indent and abs(line.x0 - self.left - self.indent) < 4:
                        starts.append(gap)
        if self.indent:
            return _spacing(starts)
        wider = [gap for gap in gaps if gap > 2]
        return _spacing(wider) if len(wider) >= 0.1 * len(gaps) else 0.0

    @staticmethod
    def _steps(lines: list[Line]) -> list[float]:
        """Шаг между соседними на странице строками из lines."""
        pages: dict[int, list[Line]] = defaultdict(list)
        for line in lines:
            pages[line.page].append(line)
        steps = []
        for page in pages.values():
            page.sort(key=lambda line: line.baseline)
            for previous, line in itertools.pairwise(page):
                step = line.baseline - previous.baseline
                if 0.8 * line.size < step < 3 * line.size:
                    steps.append(step)
        return steps

    @staticmethod
    def _interval(step: float, size: float) -> float:
        """Межстрочный интервал по шагу строк; шага нет — одинарный."""
        return interval(step / (SINGLE * size)) if step else 1.0


def _lines(pdf: pymupdf.Document) -> tuple[list[Line], set[str]]:
    """Строки текста первых страниц и шрифты-замены, встреченные в них. Строку по
    ширине PDF бывает пишет по словам — их склеиваем по базовой линии внутри блока.
    Вертикальный текст пропускаем. Шрифт-замену сразу меняем на оригинал."""
    lines = []
    replaced = set()
    for number in range(min(PAGES, pdf.page_count)):
        for block in pdf[number].get_text("dict")["blocks"]:
            rows: dict[float, list[dict[str, Any]]] = defaultdict(list)
            for line in block.get("lines", []):
                spans = [span for span in line["spans"] if span["text"].strip()]
                if spans and line["dir"] == (1, 0):
                    rows[round(spans[0]["origin"][1])] += spans
            for baseline, spans in rows.items():
                spans.sort(key=lambda span: span["bbox"][0])
                main = max(spans, key=lambda span: len(span["text"].strip()))
                name = main["font"]
                family = _family(name)
                if family in ORIGINALS:
                    replaced.add(family)
                lines.append(
                    Line(
                        page=number,
                        text=" ".join(span["text"].strip() for span in spans),
                        font=ORIGINALS.get(family, family),
                        size=round(main["size"] * 2) / 2,
                        bold=bool(main["flags"] & 16) or "Bold" in name,
                        italic=bool(main["flags"] & 2) or "Italic" in name,
                        x0=spans[0]["bbox"][0],
                        x1=spans[-1]["bbox"][2],
                        baseline=baseline,
                    )
                )
    return lines, replaced


def _family(name: str) -> str:
    """Семейство шрифта по имени в PDF: «ABCDEF+TimesNewRomanPS-BoldMT» → «Times New
    Roman». Перед «+» — метка подмножества, после «-» или «,» — начертание."""
    name = re.split(r"[-,]", name.split("+", 1)[-1])[0]
    name = re.sub(r"(PSMT|PS|MT)$", "", name)
    return re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", name).strip()


def _prominence(kind: Kind) -> tuple[float, bool, bool]:
    """Порядок заголовков без номеров: крупнее, жирнее, прописными — выше."""
    (_, size, bold, _), caps, *_ = kind
    return -size, not bold, not caps


def _caps(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    return len(letters) >= 4 and all(char.isupper() for char in letters)


def _even(value: float) -> float:
    """С точностью до 2 пт: начала строк на одном месте расходятся на доли пункта."""
    return 2 * round(value / 2)


def _median(values: Iterable[float], default: float) -> float:
    values = list(values)
    return statistics.median(values) if values else default


def _quantile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def _spacing(gaps: list[float]) -> float:
    """Отбивка, пт: обычный промежуток, если он заметен, иначе ноль."""
    value = _median(gaps, 0)
    return float(round(value)) if value >= 3 else 0.0


def _millimeters(points: float) -> float:
    """Отступ в миллиметрах с точностью до половины: PDF даёт его с погрешностью."""
    return round(points * MM * 2) / 2


def _margin(points: float) -> float:
    """Поле в миллиметрах: круглое, если до него меньше 1,5 мм."""
    millimeters = points * MM
    rounded = 5 * round(millimeters / 5)
    return float(rounded) if abs(millimeters - rounded) < 1.5 else round(millimeters, 1)

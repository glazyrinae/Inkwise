"""Оформление, прочитанное в образце. Кегль и отбивки — в пунктах, лист, поля и отступы
— в миллиметрах. Чего в образце не нашлось — None: шаблон возьмёт это от основного
текста."""

from dataclasses import dataclass, field

ALIGN = {"left": "слева", "center": "по центру", "right": "справа", "both": "по ширине"}
PLACE = {"top": "вверху", "bottom": "внизу"}
# Обычные межстрочные интервалы Word
INTERVALS = (1.0, 1.15, 1.5, 2.0)
# Листы: A4, Letter, A5 — ширина и высота, мм
SHEETS = ((210.0, 297.0), (215.9, 279.4), (148.0, 210.0))


@dataclass(frozen=True)
class Text:
    """Оформление абзаца."""

    font: str
    size: float
    bold: bool = False
    italic: bool = False
    caps: bool = False
    # Выравнивание, как его называет Word: left, center, right, both — по ширине
    align: str = "left"
    # Отступ первой строки; меньше нуля — выступ, как у записи в списке литературы
    indent: float = 0
    # Межстрочный интервал: 1 — одинарный, 1.5 — полуторный
    line: float = 1
    before: float = 0
    after: float = 0


@dataclass(frozen=True)
class Style:
    """Оформление образца."""

    page: tuple[float, float]  # ширина и высота листа
    margins: tuple[float, float, float, float]  # верхнее, правое, нижнее, левое
    body: Text
    headings: list[Text]  # уровни заголовков, с первого
    numbered: bool  # у заголовков номера «1», «1.1»
    figure: Text | None = None  # подпись рисунка
    table: Text | None = None  # подпись таблицы
    footnote: Text | None = None
    page_number: tuple[str, str] | None = None  # top или bottom и выравнивание
    contents: Text | None = None  # строка содержания
    references: Text | None = None  # запись в списке источников
    notes: list[str] = field(default_factory=list)  # что ещё заметить в образце

    def summary(self) -> str:
        """Что прочитано в образце: по строке на элемент оформления."""
        width, height = self.page
        top, right, bottom, left = (_number(margin) for margin in self.margins)
        lines = [
            f"Лист {_number(width)}×{_number(height)} мм, поля: верхнее {top}, "
            f"правое {right}, нижнее {bottom}, левое {left} мм",
            f"Текст: {describe(self.body)}",
        ]
        numbers = "с номерами «1.1»" if self.numbered else "без номеров"
        for level, heading in enumerate(self.headings, start=1):
            lines.append(f"Заголовок {level}: {describe(heading, self.body)}")
        if self.headings:
            lines.append(f"Заголовки {numbers}")
        missing = []
        parts = {
            "подпись рисунка": self.figure,
            "подпись таблицы": self.table,
            "сноски": self.footnote,
            "содержание": self.contents,
            "список источников": self.references,
        }
        for name, text in parts.items():
            if text:
                lines.append(f"{name.capitalize()}: {describe(text, self.body)}")
            else:
                missing.append(name)
        if self.page_number:
            place, align = self.page_number
            lines.append(f"Номер страницы: {PLACE[place]} {ALIGN[align]}")
        else:
            missing.append("номер страницы")
        if not self.headings:
            missing.insert(0, "заголовки")
        if missing:
            lines.append(f"Не нашлось, взято от основного текста: {', '.join(missing)}")
        return "\n".join([*lines, *self.notes])


def describe(text: Text, body: Text | None = None) -> str:
    """Оформление словами; у элемента — только то, чем он отличается от основного
    текста body."""
    parts = []
    if body is None or text.font != body.font:
        parts.append(text.font)
    parts.append(f"{_number(text.size)} пт")
    parts += [name for name, on in _marks(text) if on]
    if body is None or text.line != body.line:
        parts.append(f"интервал {_number(text.line)}")
    if text.indent > 0:
        parts.append(f"отступ {_number(text.indent / 10)} см")
    elif text.indent < 0:
        parts.append(f"выступ {_number(-text.indent / 10)} см")
    parts.append(ALIGN[text.align])
    return ", ".join(parts)


def _marks(text: Text) -> list[tuple[str, bool]]:
    return [
        ("полужирный", text.bold),
        ("курсив", text.italic),
        ("прописные", text.caps),
    ]


def _number(value: float) -> str:
    """Число по-русски: «1,25», без лишних нулей."""
    return f"{round(value, 2):g}".replace(".", ",")


def interval(ratio: float) -> float:
    """Межстрочный интервал: ближний из обычных или с точностью до 0,05."""
    nearest = min(INTERVALS, key=lambda value: abs(value - ratio))
    return nearest if abs(nearest - ratio) < 0.1 else round(ratio * 20) / 20


def sheet(width: float, height: float) -> tuple[float, float]:
    """Лист в миллиметрах: A4, Letter или A5, если он из них, иначе как есть."""
    for size in SHEETS:
        if abs(size[0] - width) < 1 and abs(size[1] - height) < 1:
            return size
    return round(width, 1), round(height, 1)

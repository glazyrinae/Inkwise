"""Оформление, прочитанное в образце. Кегль и отбивки — в пунктах, лист, поля и отступы
— в миллиметрах. Чего в образце не нашлось — None: шаблон возьмёт это от основного
текста."""

from dataclasses import dataclass, field

from app.settings.config import config

from .words import t

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
            t(
                "Лист {width}×{height} мм, поля: верхнее {top}, правое {right}, нижнее "
                "{bottom}, левое {left} мм",
                width=_number(width),
                height=_number(height),
                top=top,
                right=right,
                bottom=bottom,
                left=left,
            ),
            t("Текст: {look}", look=describe(self.body)),
        ]
        for level, heading in enumerate(self.headings, start=1):
            look = describe(heading, self.body)
            lines.append(t("Заголовок {level}: {look}", level=level, look=look))
        if self.headings:
            numbered = self.numbered
            lines.append(
                t("Заголовки с номерами «1.1»")
                if numbered
                else t("Заголовки без номеров")
            )
        missing = []
        parts = {
            "Подпись рисунка": self.figure,
            "Подпись таблицы": self.table,
            "Сноски": self.footnote,
            "Содержание": self.contents,
            "Список источников": self.references,
        }
        for name, text in parts.items():
            if text:
                look = describe(text, self.body)
                lines.append(t("{part}: {look}", part=t(name), look=look))
            else:
                missing.append(t(name).lower())
        if self.page_number:
            place, align = self.page_number
            lines.append(
                t(
                    "Номер страницы: {place} {align}",
                    place=t(PLACE[place]),
                    align=t(ALIGN[align]),
                )
            )
        else:
            missing.append(t("Номер страницы").lower())
        if not self.headings:
            missing.insert(0, t("Заголовки").lower())
        if missing:
            found = ", ".join(missing)
            lines.append(
                t("Не нашлось, взято от основного текста: {parts}", parts=found)
            )
        return "\n".join([*lines, *self.notes])


def describe(text: Text, body: Text | None = None) -> str:
    """Оформление словами; у элемента — только то, чем он отличается от основного
    текста body."""
    parts = []
    if body is None or text.font != body.font:
        parts.append(text.font)
    parts.append(t("{size} пт", size=_number(text.size)))
    parts += [t(name) for name, on in _marks(text) if on]
    if body is None or text.line != body.line:
        parts.append(t("интервал {line}", line=_number(text.line)))
    if text.indent > 0:
        parts.append(t("отступ {indent} см", indent=_number(text.indent / 10)))
    elif text.indent < 0:
        parts.append(t("выступ {indent} см", indent=_number(-text.indent / 10)))
    parts.append(t(ALIGN[text.align]))
    return ", ".join(parts)


def _marks(text: Text) -> list[tuple[str, bool]]:
    return [
        ("полужирный", text.bold),
        ("курсив", text.italic),
        ("прописные", text.caps),
    ]


def _number(value: float) -> str:
    """Число без лишних нулей: «1,25» по-русски, «1.25» по-английски."""
    text = f"{round(value, 2):g}"
    return text.replace(".", ",") if config.app.language == "ru" else text


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

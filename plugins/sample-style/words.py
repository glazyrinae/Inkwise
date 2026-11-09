"""Строки плагина на языке интерфейса: что прочитано в образце и почему он не читается.

Строки в коде — по-русски, они же ключи перевода, как в ядре (app/service/language.py).
Язык — из настроек приложения: плагин работает внутри api.
"""

from app.settings.config import config

EN: dict[str, str] = {
    "слева": "left",
    "по центру": "centered",
    "справа": "right",
    "по ширине": "justified",
    "вверху": "at the top",
    "внизу": "at the bottom",
    "полужирный": "bold",
    "курсив": "italic",
    "прописные": "all caps",
    "{size} пт": "{size} pt",
    "интервал {line}": "line spacing {line}",
    "отступ {indent} см": "first-line indent {indent} cm",
    "выступ {indent} см": "hanging indent {indent} cm",
    "Лист {width}×{height} мм, поля: верхнее {top}, правое {right}, нижнее {bottom}, "
    "левое {left} мм": (
        "Page {width}×{height} mm, margins: top {top}, right {right}, bottom {bottom}, "
        "left {left} mm"
    ),
    "Текст: {look}": "Body text: {look}",
    "Заголовок {level}: {look}": "Heading {level}: {look}",
    "Заголовки с номерами «1.1»": "Headings numbered «1.1»",
    "Заголовки без номеров": "Headings without numbers",
    "Подпись рисунка": "Figure caption",
    "Подпись таблицы": "Table caption",
    "Сноски": "Footnotes",
    "Содержание": "Contents",
    "Список источников": "References",
    "Номер страницы": "Page number",
    "Заголовки": "Headings",
    "{part}: {look}": "{part}: {look}",
    "Номер страницы: {place} {align}": "Page number: {place}, {align}",
    "Не нашлось, взято от основного текста: {parts}": (
        "Not found, taken from the body text: {parts}"
    ),
    "Файл не открылся как PDF": "The file did not open as a PDF",
    "Прочитаны первые {pages} страниц": "The first {pages} pages were read",
    "{font} в PDF — замена {original}, в шаблоне оригинал": (
        "{font} in the PDF replaces {original}, the template uses the original"
    ),
    "В PDF почти нет текста — это скан или картинки? Нужен PDF с текстом или документ "
    "Word": (
        "The PDF has almost no text — is it a scan or images? A PDF with text or a "
        "Word document is needed"
    ),
    "Нижнее поле по образцу не видно — взято, как верхнее": (
        "The bottom margin is not visible in the sample — taken equal to the top one"
    ),
    "Образец набран в две колонки, шаблон — в одну": (
        "The sample is set in two columns, the template uses one"
    ),
    "Текст в PDF — распознанный скан: шрифт и размеры, наверное, неверны": (
        "The PDF text is a recognized scan: the font and sizes are probably wrong"
    ),
    "Файл не открылся как документ Word .docx": "The file did not open as a Word .docx",
    "В документе Word не нашлось основного текста": (
        "No body text was found in the Word document"
    ),
    "Образец набран в колонки, шаблон — в одну": (
        "The sample is set in columns, the template uses one"
    ),
}


def t(text: str, **values: object) -> str:
    """Строка на языке интерфейса, со значениями на местах {имя}."""
    if config.app.language == "en":
        text = EN.get(text, text)
    return text.format(**values) if values else text

"""Язык интерфейса: сообщения api, названия новых блоков и заголовки публикации.

Строки в коде — по-русски, они же ключи перевода: t("Нужно название"). На языке en
api берёт перевод из EN, а строку без перевода отдаёт как есть. Значения подставляются
по именам: t("Плагин больше {size} МБ", size=50). Перевод оболочки — app/web/js/en.js,
плагины переводят свои строки сами, см. PLUGINS.md.
"""

from app.settings.config import config

EN: dict[str, str] = {
    # Ошибки сервисов: «Не найдено: 01-Введение/книга.pdf»
    "Не найдено": "Not found",
    "Уже есть": "Already exists",
    "Нет доступа": "Access denied",
    "Редактор не открывает": "The editor cannot open",
    "Ошибка плагина": "Plugin error",
    # Блоки и публикация
    "Введение": "Introduction",
    "Заключение": "Conclusion",
    "Титульный лист": "Title page",
    "Нужно название": "A title is required",
    "Блоки книги изменились: обнови страницу": (
        "The book's blocks have changed: reload the page"
    ),
    "Публикация.docx": "Publication.docx",
    "СОДЕРЖАНИЕ": "CONTENTS",
    "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ": "REFERENCES",
    "Публикация собрана, но без содержания: {error}": (
        "The publication is compiled, but without a table of contents: {error}"
    ),
    "office ответил ошибкой {code}": "office answered with error {code}",
    "office не ответил ({reason})": "office did not answer ({reason})",
    # Экспорт и импорт
    "Нужен документ Word .docx": "A Word .docx document is required",
    "Это не документ Word .docx": "This is not a Word .docx document",
    "В файле нет книги Inkwise: импортировать можно только публикацию, собранную в "
    "Inkwise": (
        "There is no Inkwise book in the file: only a publication compiled in Inkwise "
        "can be imported"
    ),
    "Книга в файле испорчена": "The book in the file is damaged",
    "Книгу в файле записала другая версия Inkwise": (
        "The book in the file was written by another version of Inkwise"
    ),
    # Редактор
    "Автор": "Author",
    "Закрыть": "Close",
    # Источники
    "Страница не скачалась: {error}. Данные впиши сам.": (
        "The page did not download: {error}. Fill in the data yourself."
    ),
    "сайт ответил {status} {reason}": "the site answered {status} {reason}",
    "сайт не ответил ({reason})": "the site did not answer ({reason})",
    "по адресу не веб-страница, а файл {type}: скачай его и подключи как книгу": (
        "the address is not a web page but a {type} file: download it and attach it "
        "as a book"
    ),
    "Копия страницы {link}, дата обращения {accessed}": (
        "Copy of the page {link}, accessed {accessed}"
    ),
    "<p>Текст страницы сохранить не удалось. Открой её по адресу выше; сноску на неё "
    "ставит правый клик → «Сноска на эту страницу».</p>": (
        "<p>The text of the page could not be saved. Open it at the address above; "
        "right-click → «Footnote to this page» adds a footnote to it.</p>"
    ),
    "Нет такого оформления ссылок": "There is no such citation style",
    # Проверка орфографии
    "MCP-сервер не подключился: {error}": "The MCP server did not connect: {error}",
    "MCP-сервер не подключён: кнопка «Проверка орфографии» слева внизу": (
        "No MCP server is connected: use the «Spell checking» button at the bottom left"
    ),
    "MCP-сервер не отвечает: {error}": "The MCP server does not answer: {error}",
    "Проверка орфографии ещё не сделана. Текст дошёл: {count} знаков; MCP-сервер "
    "отвечает, его инструменты: {tools}": (
        "Spell checking is not done yet. The text arrived: {count} characters; the MCP "
        "server answers, its tools: {tools}"
    ),
    "нет": "none",
    "не ответил за {seconds} с": "did not answer in {seconds} s",
    # Плагины и шрифты
    "Нужен архив .zip": "A .zip archive is required",
    "Это не архив .zip": "This is not a .zip archive",
    "Плагин больше {size} МБ": "The plugin is larger than {size} MB",
    "В архиве должна быть одна папка плагина: латиница, цифры и «-»": (
        "The archive must hold one plugin folder: Latin letters, digits and «-»"
    ),
    "В папке {folder} архива нет plugin.json": (
        "The {folder} folder of the archive has no plugin.json"
    ),
    "У плагина {folder} нет plugin.json": "The {folder} plugin has no plugin.json",
    "У плагина нет настройки {key} = {value}": (
        "The plugin has no setting {key} = {value}"
    ),
    "У плагина нет настройки-файла {key}": "The plugin has no file setting {key}",
    "Нужен файл {types}": "A {types} file is required",
    "Шрифта нет ни в office, ни в Google Fonts: {fonts}. Его файлы .ttf или .otf "
    "можно положить в папку шрифтов Inkwise (FONTS_DIR), office поставит их сам, — "
    "и загрузить образец снова": (
        "The font is neither in office nor in Google Fonts: {fonts}. Put its .ttf or "
        ".otf files into the Inkwise fonts folder (FONTS_DIR), office installs them by "
        "itself, and upload the sample again"
    ),
    "Office не отдал список шрифтов": "Office did not return its font list",
    "Google Fonts не отдал каталог шрифтов": "Google Fonts did not return its catalog",
    "Google Fonts не отдал шрифт {name}": "Google Fonts did not return the {name} font",
    "У шрифта {name} в Google Fonts нет файлов TTF": (
        "The {name} font has no TTF files in Google Fonts"
    ),
}


def t(text: str, **values: object) -> str:
    """Строка на языке интерфейса, со значениями на местах {имя}."""
    if config.app.language == "en":
        text = EN.get(text, text)
    return text.format(**values) if values else text

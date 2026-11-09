"""Публикация — собранная книга по ГОСТ 7.32–2017: титульный лист, содержание, тексты
блоков по порядку, в конце список использованных источников; номер страницы — внизу по
центру. Каждая из этих частей — с новой страницы, таблица между страницами не рвётся.

В скрытой части публикации — вся книга: публикация и есть экспорт, см. transfer.py.

Тексты склеивает docxcompose: он переносит стили, сноски и картинки каждого текста.
Заголовки уже в текстах: раздел, подраздел, пункт, подпункт со стилями «Heading 1»…
«Heading 4». Их номера в публикации идут подряд — нумерацию стилей задаёт сама
публикация, см. headings.py. Строки содержания с номерами страниц заполняет office, см.
office/builder.py.
"""

import io
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import docx
from docx.document import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.oxml import serialize_part_xml
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm
from docx.text.paragraph import Paragraph
from docxcompose.composer import Composer  # type: ignore[import-untyped]

from app.service.book import blocks, headings, paths, tables, texts, transfer
from app.service.office import builder
from app.service.sources import store, styles
from app.settings.config import config

# Код поля сноски: «ADDIN WRITER_CITATION {"source": …, "pages": …}»
CITATION = re.compile(r"WRITER_CITATION\s*(\{[^{}]*\})")
INSTRUCTION = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}instrText"
# Поле содержания: разделы, подразделы и пункты; строка ведёт к заголовку
CONTENTS = r'TOC \o "1-3" \h \z \u'
# Абзацный отступ по ГОСТ
INDENT = Cm(1.25)
# Стиль записи в списке источников, если он есть в шаблоне; имя — как в Word
BIBLIOGRAPHY = "Bibliography"
# Источник на латинице: в списке иностранные идут после русских
LATIN = re.compile(r"\W*[A-Za-z]")
# Что видно в абзаце без текста: картинка, формула, знак сноски, поле, разрыв раздела
VISIBLE = (
    ".//w:drawing | .//w:pict | .//w:object | .//m:oMath | .//w:footnoteReference"
    " | .//w:fldChar | .//w:sectPr"
)


def build() -> str:
    """Собирает публикацию заново поверх прежней; в ответе — её путь от корня книги.

    Raises:
        builder.BuilderError: office не заполнил содержание — публикация собрана без
            него.
    """
    file = paths.root() / config.book.document
    texts.create(file)
    composer = Composer(docx.Document(str(file)))
    document = composer.doc
    # От шаблона в публикации стили, размер страницы, поля и колонтитулы, но не текст
    document.element.body.clear_content()
    book = [block for block in blocks.tree() if block.text]
    # Титульный лист — первая страница: перед содержанием и без номера страницы
    title_pages = [block for block in book if block.kind == "title_page"]
    keys: set[str] = set()
    for number, block in enumerate(title_pages):
        _append(composer, block, keys, new_page=number > 0)
    _contents(document, after_title_page=bool(title_pages))
    for block in book:
        if block.kind != "title_page":
            _append(composer, block, keys, new_page=True)
    _sources_list(document, keys)
    tables.keep_whole(document)
    _page_numbers(document, skip_first=bool(title_pages))
    output = io.BytesIO()
    composer.save(output)
    paths.replace(file, output.getvalue())
    path = paths.relative(file)
    try:
        paths.replace(file, builder.fill_contents(path))
    finally:
        # Книгу кладём в готовую публикацию, когда office её уже пересохранил: так
        # скрытая часть не зависит от office. Без содержания публикация тоже
        # импортируется
        paths.replace(file, transfer.embed(file.read_bytes()))
    return path


def path() -> str | None:
    """Путь публикации, если её уже собирали."""
    file = paths.root() / config.book.document
    return paths.relative(file) if file.is_file() else None


def remove() -> None:
    """Удаляет публикацию: её всегда можно собрать снова."""
    (paths.root() / config.book.document).unlink(missing_ok=True)


def _contents(document: Document, after_title_page: bool) -> None:
    """«СОДЕРЖАНИЕ» и поле содержания: строки с номерами страниц заполнит office.

    Заголовок самого содержания в содержание не входит: у него стиль «TOC Heading»,
    как в Word, — заголовок первого уровня, но с уровнем основного текста.
    """
    title = document.add_paragraph(
        "СОДЕРЖАНИЕ", headings.style(document, "TOC Heading")
    )
    headings.unnumbered(title)
    title.paragraph_format.page_break_before = after_title_page
    _field(document.add_paragraph(), CONTENTS)


def _append(
    composer: Composer, block: blocks.Block, keys: set[str], new_page: bool
) -> None:
    """Текст блока; в keys — ключи его источников: подключённых и из сносок."""
    text = paths.find(block.text or "")
    source = docx.Document(str(text))
    _trim(source)
    if new_page:
        _new_page(source)
    _footnote_styles(source, composer.doc)
    composer.append(source)
    keys.update(_cited(text))
    keys.update(store.key(paths.target(material)) for material in block.materials)


def _trim(document: Document) -> None:
    """Убирает пустые абзацы в конце текста: следующий блок всё равно начнётся с новой
    страницы, а они могли бы перейти на свою и оставить её пустой. После таблицы в
    конце текста такой абзац есть всегда: без него Word таблицу не заканчивает.
    """
    body = document.element.body
    for element in reversed(list(body)):
        if element.tag == qn("w:sectPr"):
            continue
        text = "".join(element.xpath(".//w:t/text()")).strip()
        if element.tag != qn("w:p") or text or element.xpath(VISIBLE):
            return
        body.remove(element)


def _new_page(document: Document) -> None:
    """Текст начинается с новой страницы: разрыв перед первым абзацем.

    Разрыв — свойство абзаца, а не пустой абзац с разрывом: тот сдвинул бы заголовок
    на строку вниз. Перед таблицей в начале текста встаёт пустой абзац с разрывом.
    """
    first = document.element.body[0]
    if first.tag != qn("w:p"):
        paragraph = OxmlElement("w:p")
        first.addprevious(paragraph)
        first = paragraph
    first.get_or_add_pPr().pageBreakBefore_val = True


def _footnote_styles(source: Document, document: Document) -> None:
    """Стили в сносках текста source — под id тех же стилей в публикации.

    docxcompose переносит сноски, но стили в них не переименовывает. Если стиль
    «footnote text» в публикации уже есть под другим id, сноска ссылается на
    несуществующий стиль, и office оформляет её как обычный текст.
    """
    try:
        part = source.part.rels.part_with_reltype(RT.FOOTNOTES)
    except KeyError:
        return
    names = {style.style_id: style.name for style in source.styles}
    ids = {style.name: style.style_id for style in document.styles}
    notes = parse_xml(part.blob)
    for element in notes.iter(qn("w:pStyle"), qn("w:rStyle")):
        style_id = ids.get(names.get(element.get(qn("w:val"))))
        if style_id:
            element.set(qn("w:val"), style_id)
    part._blob = serialize_part_xml(notes)


def _cited(text: Path) -> list[str]:
    """Ключи источников из сносок текста."""
    with zipfile.ZipFile(text) as archive:
        if "word/footnotes.xml" not in archive.namelist():
            return []
        root = ElementTree.fromstring(archive.read("word/footnotes.xml"))
    # Код поля office может разбить на несколько кусков: склеиваем их
    code = "".join(element.text or "" for element in root.iter(INSTRUCTION))
    return [json.loads(match)["source"] for match in CITATION.findall(code)]


def _sources_list(document: Document, keys: set[str]) -> None:
    """Список использованных источников: все, что подключены к блокам, и все, на какие
    есть сноски. Без страниц, по алфавиту: сначала русские, потом иностранные.

    Источник без подтверждённых данных — например, файл, положенный в папку источников
    снаружи, — в список не попадает: описать его не из чего. Запись оформлена стилем
    «Bibliography», если он есть в шаблоне, иначе — с абзацного отступа.
    """
    entries = {styles.footnote(source) for key in keys if (source := store.saved(key))}
    if not entries:
        return
    # Заголовок первого уровня без номера: с новой страницы и в содержании
    heading = document.add_paragraph(
        "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", headings.style(document, "Heading 1")
    )
    headings.unnumbered(heading)
    heading.paragraph_format.page_break_before = True
    named = [found for found in document.styles if found.name == BIBLIOGRAPHY]
    style = named[0] if named else None
    for number, entry in enumerate(sorted(entries, key=_alphabetical), start=1):
        paragraph = document.add_paragraph(f"{number}. {entry}", style)
        if style is None:
            paragraph.paragraph_format.first_line_indent = INDENT


def _alphabetical(entry: str) -> tuple[bool, str]:
    """По алфавиту: сначала русские источники, потом иностранные. Регистр не важен,
    «ё» стоит вместе с «е»."""
    return bool(LATIN.match(entry)), entry.casefold().replace("ё", "е")


def _page_numbers(document: Document, skip_first: bool) -> None:
    """Номер страницы внизу по центру, без точки — по ГОСТ. skip_first — на первой
    странице, титульном листе, номера нет, но страница в счёте.

    Свой нижний колонтитул шаблона оставляем как есть: его оформил человек.
    """
    section = document.sections[0]
    section.different_first_page_header_footer = skip_first
    footer = section.footer
    if footer.is_linked_to_previous:
        paragraph = footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _field(paragraph, "PAGE")


def _field(paragraph: Paragraph, code: str) -> None:
    """Поле Word без значения: значение посчитает редактор."""
    for content in (
        '<w:fldChar w:fldCharType="begin"/>',
        f'<w:instrText xml:space="preserve"> {code} </w:instrText>',
        '<w:fldChar w:fldCharType="separate"/>',
        '<w:fldChar w:fldCharType="end"/>',
    ):
        paragraph._p.append(parse_xml(f"<w:r {nsdecls('w')}>{content}</w:r>"))

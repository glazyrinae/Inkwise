"""Экспорт и импорт книги. Экспорт — сама публикация: обычный документ Word, а в его
скрытой части customXml лежит вся папка книги как есть. В customXml Word хранит и свой
список литературы, поэтому при пересохранении в Word часть остаётся.

Внутри — тексты блоков, копии веб-страниц, данные источников, настройки книги. Корзины
и самой публикации там нет. Книги из библиотеки внутрь не кладём: от ссылки на книгу —
только путь. Книга откроется, если лежит по тому же пути, то есть на том же рабочем
месте. На другом ссылка останется в блоке и в списке источников, но не откроется.

Импорт берёт книгу из скрытой части, а не из текста публикации: правки, внесённые в
файл в Word, в книгу не вернутся. В файле без скрытой части книги нет — это ошибка.
"""

import base64
import io
import os
import re
import uuid
import zipfile
from pathlib import PurePosixPath
from xml.etree import ElementTree

import docx
from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part

from app.service.book import paths, trash
from app.settings.config import config

# По пространству имён импорт отличает книгу от других частей customXml
NAMESPACE = "urn:writer:book"
BOOK = f"{{{NAMESPACE}}}book"
FILE = f"{{{NAMESPACE}}}file"
LINK = f"{{{NAMESPACE}}}link"
# Версия устройства скрытой части: изменится оно — импорт узнает старые файлы
VERSION = "1"
# Части customXml в документе: customXml/item1.xml, customXml/item2.xml…
CUSTOM_XML = re.compile(r"customXml/item\d+\.xml")
BROKEN = "Книга в файле испорчена"


def embed(publication: bytes) -> bytes:
    """Кладёт книгу в скрытую часть публикации."""
    document = docx.Document(io.BytesIO(publication))
    package = document.part.package
    partname = package.next_partname("/customXml/item%d.xml")
    item = Part(partname, CT.XML, _pack(), package)
    # Свойства части с её id: так часть customXml записывает сам Word
    properties = Part(
        PackURI(f"/customXml/itemProps{item.partname.idx}.xml"),
        CT.OFC_CUSTOM_XML_PROPERTIES,
        _properties(),
        package,
    )
    item.relate_to(properties, RT.CUSTOM_XML_PROPS)
    document.part.relate_to(item, RT.CUSTOM_XML)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def restore(file: bytes) -> None:
    """Заменяет книгу книгой из публикации; прежняя книга целиком уходит в корзину.

    Raises:
        ValueError: в файле нет книги writer или она испорчена.
    """
    entries = _entries(_book(file))
    trash.put_book()
    root = paths.root()
    for path, content in entries:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            target.symlink_to(content)
        else:
            target.write_bytes(content)
    # Публикация — сам файл: чтобы посмотреть книгу, собирать её заново не нужно
    (root / config.book.document).write_bytes(file)


def _pack() -> bytes:
    """Папка книги — XML: файл целиком в base64, у ссылки на книгу — её путь."""
    root = paths.root()
    book = ElementTree.Element(BOOK, version=VERSION)
    # Ссылка на папку попадает в files, а не в folders: внутрь неё walk не заходит
    for folder, folders, files in root.walk():
        if folder == root:
            folders[:] = [name for name in folders if name != config.book.trash]
            files = [name for name in files if name != config.book.document]
        for name in sorted(files):
            entry = folder / name
            path = entry.relative_to(root).as_posix()
            if entry.is_symlink():
                ElementTree.SubElement(book, LINK, path=path, target=os.readlink(entry))
            else:
                data = base64.b64encode(entry.read_bytes()).decode()
                ElementTree.SubElement(book, FILE, path=path).text = data
    return ElementTree.tostring(book, encoding="utf-8", xml_declaration=True)


def _properties() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<ds:datastoreItem ds:itemID="{{{str(uuid.uuid4()).upper()}}}"'
        ' xmlns:ds="http://schemas.openxmlformats.org/officeDocument/2006/customXml">'
        f'<ds:schemaRefs><ds:schemaRef ds:uri="{NAMESPACE}"/></ds:schemaRefs>'
        "</ds:datastoreItem>"
    ).encode()


def _book(file: bytes) -> ElementTree.Element:
    """Книга из скрытой части публикации.

    Raises:
        ValueError: это не документ .docx или в нём нет книги writer.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file)) as package:
            for name in package.namelist():
                if CUSTOM_XML.fullmatch(name):
                    part = ElementTree.fromstring(package.read(name))
                    if part.tag == BOOK:
                        return part
    except zipfile.BadZipFile:
        raise ValueError("Это не документ Word .docx") from None
    except ElementTree.ParseError:
        raise ValueError(BROKEN) from None
    raise ValueError(
        "В файле нет книги GOSTwriter: импортировать можно только публикацию, "
        "собранную в GOSTwriter"
    )


def _entries(book: ElementTree.Element) -> list[tuple[PurePosixPath, bytes | str]]:
    """Файлы книги с содержимым и ссылки на книги с путём, ссылки — последними.

    Путь из файла проверяем: он не уводит из книги, в корзину и не идёт через ссылку.
    Иначе ссылка на чужую папку дала бы записать файл куда угодно.

    Raises:
        ValueError: другая версия книги или книга испорчена.
    """
    if book.get("version") != VERSION:
        raise ValueError("Книгу в файле записала другая версия GOSTwriter")
    entries: dict[PurePosixPath, bytes | str] = {}
    for element in book:
        written = element.get("path", "")
        path = PurePosixPath(written)
        unsafe = (
            str(path) != written
            or not path.parts
            or path.is_absolute()
            or ".." in path.parts
            or path.parts[0] == config.book.trash
        )
        if unsafe or path in entries or element.tag not in (FILE, LINK):
            raise ValueError(BROKEN)
        try:
            entries[path] = (
                element.get("target", "")
                if element.tag == LINK
                else base64.b64decode(element.text or "", validate=True)
            )
        except ValueError:
            raise ValueError(BROKEN) from None
    links = {path for path, content in entries.items() if isinstance(content, str)}
    if any(links & set(path.parents) for path in entries):
        raise ValueError(BROKEN)
    return sorted(entries.items(), key=lambda entry: isinstance(entry[1], str))

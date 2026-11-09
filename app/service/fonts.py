"""Шрифты для office. Office знает шрифты системы, свои и шрифты из папки custom-fonts:
туда compose монтирует папку шрифтов writer (FONTS_DIR). Шрифт, которого в office нет,
api скачивает из Google Fonts в эту папку. Office замечает новый файл и пересобирает
список шрифтов, см. deploy/office/fonts-watch.sh. При этом перезапускаются его службы,
и открытые тексты переподключаются сами.

В Google Fonts открытые шрифты. Шрифты Microsoft — Times New Roman, Arial, Calibri и
другие — в office уже есть.
"""

import json
import re
import zipfile
from pathlib import Path
from typing import Any

import docx
import httpx
from docx.oxml import parse_xml
from docx.oxml.ns import qn

from app.service.book import paths
from app.settings.config import config

# Список шрифтов office: строки «["Times New Roman",0,0,…]» в его AllFonts.js
OFFICE_FONT = re.compile(r'^\["([^"]+)",', re.MULTILINE)
CATALOG = "https://fonts.google.com/metadata/fonts"
CSS = "https://fonts.googleapis.com/css"
# Начертания, как в Word: обычное, курсив, полужирное, полужирный курсив
STYLES = ("400", "400i", "700", "700i")
# Начертание в CSS Google Fonts: «font-style: italic; font-weight: 700; src: url(…)».
# У шрифтов с осью ширины, например Noto Sans, между ними ещё «font-stretch: normal;»,
# поэтому до src пропускаем всё, что есть в том же @font-face
FACE = re.compile(
    r"font-style: (\w+);\s*font-weight: (\d+);[^}]*?src: url\((\S+?\.ttf)\)"
)
SIDES = ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia")


class FontError(Exception):
    """Шрифта нет ни в office, ни в Google Fonts, или они не ответили."""


def install(template: Path) -> list[str]:
    """Ставит в office шрифты стилей шаблона, которых в нём нет; в ответе — скачанные.

    Имя шрифта в шаблоне приводит к имени, под которым шрифт знает office: из PDF
    приходит «Deja Vu Sans» вместо «DejaVu Sans», а office ищет шрифт по имени.

    Raises:
        FontError: шрифта нет ни в office, ни в Google Fonts, или они не ответили.
    """
    known = {_key(name): name for name in [*_office(), *_downloaded()]}
    wanted = {name: _key(name) for name in _used(template)}
    missing = {key for key in wanted.values() if key not in known}
    catalog = _catalog() if missing else {}
    unknown = [name for name, key in wanted.items() if key in missing - catalog.keys()]
    if unknown:
        raise FontError(
            f"Шрифта нет ни в office, ни в Google Fonts: {', '.join(sorted(unknown))}. "
            "Его файлы .ttf или .otf можно положить в папку шрифтов GOSTwriter "
            "(FONTS_DIR), office поставит их сам, — и загрузить образец снова"
        )
    downloaded = []
    for key in sorted(missing):
        family = catalog[key]
        _download(family)
        known[key] = family["family"]
        downloaded.append(family["family"])
    _rename(template, {name: known[key] for name, key in wanted.items()})
    return downloaded


def _used(template: Path) -> set[str]:
    """Шрифты в стилях шаблона и в свойствах текста по умолчанию."""
    with zipfile.ZipFile(template) as package:
        styles = parse_xml(package.read("word/styles.xml"))
    return {
        name
        for fonts in styles.iter(qn("w:rFonts"))
        for side in SIDES
        if (name := fonts.get(qn(side)))
    }


def _rename(template: Path, names: dict[str, str]) -> None:
    """Меняет имена шрифтов в стилях шаблона: names — прежнее имя → новое."""
    if all(old == new for old, new in names.items()):
        return
    document = docx.Document(str(template))
    for fonts in document.styles.element.iter(qn("w:rFonts")):
        for side in SIDES:
            old = fonts.get(qn(side))
            if old in names:
                fonts.set(qn(side), names[old])
    output = template.with_name(f".{template.name}.renamed")
    document.save(str(output))
    output.replace(template)


def _office() -> list[str]:
    """Шрифты, которые знает office."""
    url = f"{config.office.internal_url}/sdkjs/common/AllFonts.js"
    text = _get(url, "Office не отдал список шрифтов").text
    return OFFICE_FONT.findall(text.split('window["__fonts_infos"]', 1)[-1])


def _downloaded() -> list[str]:
    """Шрифты в папке шрифтов: скачанный шрифт office ставит не сразу. Имя файла —
    «PT Serif 700i.ttf»."""
    root = config.fonts.root
    return [file.stem.rsplit(" ", 1)[0] for file in root.glob("*.ttf")]


def _catalog() -> dict[str, dict[str, Any]]:
    """Каталог Google Fonts: ключ имени → семейство с его начертаниями и алфавитами."""
    text = _get(CATALOG, "Google Fonts не отдал каталог шрифтов").text
    # Перед JSON — «)]}'»: так Google защищает ответ от чтения чужими страницами
    data = json.loads(text[text.index("{") :])
    return {_key(family["family"]): family for family in data["familyMetadataList"]}


def _download(family: dict[str, Any]) -> None:
    """Скачивает в папку шрифтов начертания семейства: TTF со всеми его алфавитами."""
    name = family["family"]
    styles = [style for style in STYLES if style in family["fonts"]]
    subsets = [subset for subset in family["subsets"] if subset != "menu"]
    params = {
        "family": f"{name}:{','.join(styles or family['fonts'])}",
        "subset": ",".join(subsets),
    }
    # Программе, а не браузеру, Google Fonts отдаёт TTF — их и читает office. Браузеру
    # он отдал бы WOFF2, поэтому строка браузера из [web] здесь не годится
    css = _get(CSS, f"Google Fonts не отдал шрифт {name}", params).text
    faces = FACE.findall(css)
    if not faces:
        raise FontError(f"У шрифта {name} в Google Fonts нет файлов TTF")
    for style, weight, url in faces:
        data = _get(url, f"Google Fonts не отдал шрифт {name}").content
        suffix = "i" if style == "italic" else ""
        paths.replace(config.fonts.root / f"{name} {weight}{suffix}.ttf", data)


def _get(
    url: str, failure: str, params: dict[str, str] | None = None
) -> httpx.Response:
    # Только IPv4: Google отдаёт и адреса IPv6, а в сети compose их нет, и запрос
    # на такой адрес падает с «Network is unreachable»
    transport = httpx.HTTPTransport(local_address="0.0.0.0", retries=2)
    try:
        with httpx.Client(transport=transport, timeout=config.fonts.timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise FontError(f"{failure}: {error}") from None
    return response


def _key(name: str) -> str:
    """Имя шрифта без пробелов и регистра: «Times New Roman» → «timesnewroman»."""
    return re.sub(r"[\W_]", "", name.casefold())

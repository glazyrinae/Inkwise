"""Оформление по образцу: шаблон текстов и публикации из образца — PDF или документа
Word. Плагин читает в образце лист и поля, шрифт, кегль, интервал, отступы, заголовки,
подписи, сноски, номер страницы, содержание и список источников и собирает пустой
документ со стилями, как шаблоны «Научной статьи». Чего в образце нет, берётся от
основного текста.

Разбор образца — секунды, поэтому шаблон и что прочитано лежат рядом с образцом, в
папке плагина в книге, скрытыми файлами: «.шаблон <ключ>.docx» и «.прочитано
<ключ>.txt». Ключ — от размера и времени файла образца: новый образец разбирается
заново.
"""

from pathlib import Path

from . import build, pdf, word


def template(values: dict[str, str]) -> Path | None:
    """Хук ядра: шаблон по образцу; None — образца нет, шаблон решает не этот плагин."""
    sample = values["sample"]
    return _prepared(Path(sample))[0] if sample else None


def describe(values: dict[str, str]) -> str | None:
    """Хук ядра: что плагин прочитал в образце — для его карточки в «Расширениях»."""
    sample = values["sample"]
    if not sample:
        return None
    return _prepared(Path(sample))[1].read_text(encoding="utf-8")


def _prepared(sample: Path) -> tuple[Path, Path]:
    """Шаблон и описание образца; если образец ещё не разбирали — разбирает.

    Raises:
        ValueError: образец не читается: не тот файл, скан без текста.
    """
    stat = sample.stat()
    key = f"{stat.st_size}-{stat.st_mtime_ns}"
    folder = sample.parent
    result = folder / f".шаблон {key}.docx"
    found = folder / f".прочитано {key}.txt"
    if result.is_file() and found.is_file():
        return result, found
    read = pdf.read if sample.suffix.lower() == ".pdf" else word.read
    style = read(sample)
    for old in [*folder.glob(".шаблон *.docx"), *folder.glob(".прочитано *.txt")]:
        old.unlink()
    build.document(style).save(str(result))
    found.write_text(style.summary(), encoding="utf-8")
    return result, found
